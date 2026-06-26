import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from Back_end.cliente import  cadastrar_cliente, buscar_cliente, editar_cliente, desativar_cliente, reativar_cliente
from sqlalchemy.exc import IntegrityError
from models import Base, Cliente
# ==============================================================================
# CONFIGURAÇÃO DOS FIXTURES (AMBIENTE DE INTEGRAÇÃO)
# ==============================================================================


# # 1. Diz para o Windows que a pasta atual é a raiz de módulos do Python
# $env:PYTHONPATH="."

# # 2. Roda o pytest novamente
# pytest

@pytest.fixture
def db_engine():
    """Cria um banco de dados SQLite isolado em memória RAM para cada teste."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


# ==============================================================================
# TESTES DE INTEGRAÇÃO
# ==============================================================================

def test_fluxo_completo_cadastro_e_busca_por_id_e_cpf(db_engine):
    """Garante que um cliente válido possa ser cadastrado e localizado por ID ou CPF."""
    # 1. Cadastra o cliente
    cadastrar_cliente(
        db_engine, 
        nome="Cauan da Paz", 
        cpf="12345678900", 
        email="cauan@exemplo.com", 
        endereco="Av. São Miguel", 
        telefone="11999998888"
    )

    # 2. Testa a busca indexada por ID (O(1) / B-Tree)
    cliente_por_id = buscar_cliente(db_engine, 1)
    assert cliente_por_id is not None
    assert cliente_por_id.nome == "Cauan da Paz"
    assert cliente_por_id.ativo is True

    # 3. Testa a busca por string de CPF (O(log n))
    cliente_por_cpf = buscar_cliente(db_engine, "123.456.789-00")
    assert cliente_por_cpf is not None
    assert cliente_por_cpf.id == 1


def test_editar_cliente_ativo_deve_atualizar_banco(db_engine):
    """Garante que dados válidos alterem o registro se o cliente estiver ativo."""
    cadastrar_cliente(db_engine, "Brother", "11122233344", "brother@gamers.com", "Rua A", "11911112222")

    # Modifica o nome e telefone
    alteracoes = {"nome": "Brother Atualizado", "telefone": "11988887777"}
    sucesso = editar_cliente(db_engine, 1, alteracoes)

    assert sucesso is True
    
    # Verifica se persistiu a mudança no banco
    cliente_verificado = buscar_cliente(db_engine, 1)
    assert cliente_verificado.nome == "Brother Atualizado"
    assert cliente_verificado.telefone == "11988887777"


def test_bloqueio_de_tipagem_estrita_no_id_ao_editar(db_engine):
    """Garante que passar strings como "1" ou booleanos seja barrado pelo isinstance."""
    cadastrar_cliente(db_engine, "Mãe", "55566677788", "mae@exemplo.com", "Rua B", "11933334444")
    
    # Tentativa passando string numérica "1"
    assert editar_cliente(db_engine, "1", {"nome": "Tentativa"}) is False
    
    # Tentativa passando booleano True (que herda de int por baixo dos panos)
    assert editar_cliente(db_engine, True, {"nome": "Tentativa"}) is False


def test_fluxo_soft_delete_bloqueio_de_edicao_e_reativacao(db_engine):
    """Cenário completo de ciclo de vida: desativação, bloqueio e restauração."""
    cadastrar_cliente(db_engine, "Cliente Teste", "99988877766", "teste@exemplo.com", "Rua C", "11944445555")

    # 1. Executa a exclusão lógica (Soft Delete)
    desativacao_sucesso = desativar_cliente(db_engine, 1)
    assert desativacao_sucesso is True

    # 2. Garante que a busca padrão não localiza mais o cliente nas rotas ativas
    assert buscar_cliente(db_engine, 1) == None

    # 3. Garante que a regra de negócio impede edições em registros históricos/congelados
    assert editar_cliente(db_engine, 1, {"nome": "Alterar Inativo"}) is False

    # 4. Executa o fluxo de reativação para recuperar o cliente
    reativacao_sucesso = reativar_cliente(db_engine, 1)
    assert reativacao_sucesso is True

    # 5. Comprova que o cliente voltou a ficar visível no sistema operacional
    cliente_restaurado = buscar_cliente(db_engine, 1)
    assert cliente_restaurado is not None
    assert cliente_restaurado.ativo is True


def test_tentativa_de_cadastrar_cpf_duplicado_deve_falhar(db_engine):
    """Garante que o banco de dados barre CPFs idênticos (Restrição UNIQUE)."""
    # Cadastra o primeiro normalmente
    cadastrar_cliente(db_engine, "Cauan", "12345678900", "cauan@email.com", "Rua 1", "11999999999")
    
    # O segundo cadastro com o MESMO CPF deve falhar no nível do banco.
    # Usamos o pytest.raises para capturar o erro de integridade do SQLAlchemy.
    with pytest.raises(IntegrityError):
        from sqlalchemy.orm import Session
        with Session(db_engine) as db:
            # Forçando a inserção direta para testar a restrição da tabela
            dublê = Cliente(nome="Outro", cpf="12345678900", email="outro@email.com")
            db.add(dublê)
            db.commit()


def test_buscar_cliente_com_identificadores_inexistentes(db_engine):
    """Garante segurança no retorno (None) ao buscar dados que não constam no banco."""
    # Busca por ID que não existe
    assert buscar_cliente(db_engine, 999) is None
    
    # Busca por CPF que não existe
    assert buscar_cliente(db_engine, "000.000.000-00") is None


def test_editar_cliente_apos_sua_reativacao(db_engine):
    """Garante que o fluxo de reativação libere o registro para edições futuras.
    
    Testa a alternância completa de estados do ciclo de vida do dado.
    """
    cadastrar_cliente(db_engine, "Paulo", "56789814504", "paulo@gmail.com", "Rua X", "1192425555")
    
    # 1. Desativa o cliente (Soft Delete) -> Edição bloqueada
    desativar_cliente(db_engine, 1)
    assert editar_cliente(db_engine, 1, {"nome": "Paulo Alterado"}) is False
    
    # 2. Reativa o cliente -> Edição deve ser desbloqueada
    reativar_cliente(db_engine, 1)
    
    # 3. Tenta editar novamente
    sucesso_edicao = editar_cliente(db_engine, 1, {"nome": "Paulo Reativado e Editado"})
    assert sucesso_edicao is True
    
    # 4. Confirma no banco se o dado novo entrou
    cliente_final = buscar_cliente(db_engine, 1)
    assert cliente_final.nome == "Paulo Reativado e Editado"