import pytest
from datetime import datetime
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, Session
from Back_end.produto import  cadastrar_produto, editar_produto, alterar_preco, atualizar_estoque, buscar_produto, listar_produtos
from sqlalchemy.exc import IntegrityError
from models import Base, Produto, Categoria

#==============================================================================
# FIXTURE LOCAL: CRIA O BANCO EM MEMÓRIA EXCLUSIVO PARA ESTE ARQUIVO
# ==============================================================================
@pytest.fixture
def banco_memoria():
    """Cria um banco SQLite em memória isolado e ATIVA as chaves estrangeiras."""
    engine_local = create_engine("sqlite:///:memory:")
    
    # ATIVADOR DE FOREIGN KEYS PARA O SQLITE
    @event.listens_for(engine_local, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    # Cria as tabelas com a regra ativa
    Base.metadata.create_all(bind=engine_local)
    
    yield engine_local
    
    Base.metadata.drop_all(bind=engine_local)

# ==============================================================================
# FIXTURE DE SUPORTE: CRIA UMA CATEGORIA VÁLIDA ANTES DOS TESTES
# ==============================================================================
@pytest.fixture
def categoria_valida(banco_memoria):
    """Garante que exista uma categoria ID=1 no banco de testes para os produtos."""
    with Session(banco_memoria) as db:
        cat = Categoria(id=1, nome="Equipamentos")
        db.add(cat)
        db.commit()
    return 1


# ==============================================================================
# 1. TESTES DE CADASTRO (CADASTRAR_PRODUTO)
# ==============================================================================

def test_cadastrar_produto_com_sucesso(banco_memoria, categoria_valida):
    """Garante que um produto válido seja cadastrado e persistido com sucesso."""
    resultado = cadastrar_produto(
        engine=banco_memoria,
        nome="Skate Profissional",
        descricao="Shape de marfim, rodas 54mm",
        preco_venda=350.0,
        preco_custo=200.0,
        quantidade_estoque=10,
        categoria_id=categoria_valida
    )
    
    assert resultado is True
    
    # Valida se realmente está gravado na tabela
    with Session(banco_memoria) as db:
        prod = db.get(Produto, 1)
        assert prod is not None
        assert prod.nome == "Skate Profissional"


def test_cadastrar_produto_com_erro_de_validacao(banco_memoria, categoria_valida):
    """Garante que o Pydantic intercepte erros (ex: margem de lucro negativa) e retorne False."""
    resultado = cadastrar_produto(
        engine=banco_memoria,
        nome="Skate Prejuízo",
        descricao="Preço venda menor que custo",
        preco_venda=100.0,  # Menor que o custo!
        preco_custo=150.0,
        quantidade_estoque=5,
        categoria_id=categoria_valida
    )
    
    assert resultado is False


def test_cadastrar_produto_com_categoria_inexistente(banco_memoria):
    """Garante que o IntegrityError seja capturado se a categoria_id não existir."""
    resultado = cadastrar_produto(
        engine=banco_memoria,
        nome="Produto Sem Categoria",
        descricao="Teste Chave Estrangeira",
        preco_venda=50.0,
        preco_custo=25.0,
        quantidade_estoque=2,
        categoria_id=999  # ID fantasma
    )
    
    assert resultado is False


# ==============================================================================
# 2. TESTES DE BUSCA E LISTAGEM (BUSCAR / LISTAR)
# ==============================================================================

def test_buscar_produto_com_sucesso_e_filtragem_ativo(banco_memoria, categoria_valida):
    """Garante que a busca traga o produto ativo e barre se o ID for inválido ou inativo."""
    cadastrar_produto(banco_memoria, "P1 Ativo", None, 50.0, 30.0, 5, categoria_valida)
    
    # Testa ID válido
    prod = buscar_produto(banco_memoria, 1)
    assert prod is not None
    assert prod.nome == "P1 Ativo"
    
    # Testa ID com tipo errado (Garante proteção isinstance)
    assert buscar_produto(banco_memoria, "1") is None
    assert buscar_produto(banco_memoria, True) is None


def test_listar_produtos_com_filtros_de_status(banco_memoria, categoria_valida):
    """Garante que a listagem diferencie ativos de inativos usando as funções de persistência."""
    cadastrar_produto(banco_memoria, "Ativo A", None, 40.0, 20.0, 2, categoria_valida)
    cadastrar_produto(banco_memoria, "Ativo B", None, 60.0, 30.0, 4, categoria_valida)
    
    # Força um soft delete manual na tabela para testar o filtro da listagem
    with Session(banco_memoria) as db:
        p2 = db.get(Produto, 2)
        p2.ativo = False
        db.commit()
        
    ativos = listar_produtos(banco_memoria, apenas_ativos=True)
    todos = listar_produtos(banco_memoria, apenas_ativos=False)
    
    assert len(ativos) == 1
    assert len(todos) == 2


# ==============================================================================
# 3. TESTES DE ALTERAÇÃO FINANCEIRA E ESTOQUE (ALTERAR_PRECO / ATUALIZAR_ESTOQUE)
# ==============================================================================

def test_alterar_preco_com_sucesso_e_bloqueio_de_margem(banco_memoria, categoria_valida):
    """Garante alterações financeiras seguras e consistentes."""
    cadastrar_produto(banco_memoria, "Rolamento", None, 100.0, 50.0, 10, categoria_valida)
    
    # 1. Sucesso: Alterar preço mantendo lucro estável
    assert alterar_preco(banco_memoria, produto_id=1, novo_preco_venda=120.0) is True
    
    # 2. Falha: Tentar forçar prejuízo (venda 40 < custo atual 50)
    assert alterar_preco(banco_memoria, produto_id=1, novo_preco_venda=40.0) is False


def test_atualizar_estoque_entrada_e_saida(banco_memoria, categoria_valida):
    """Valida movimentações de entrada (+) e saída (-) de mercadorias."""
    cadastrar_produto(banco_memoria, "Shape", None, 200.0, 100.0, 10, categoria_valida)
    
    # Entrada de estoque (+5) -> Deve ir para 15
    assert atualizar_estoque(banco_memoria, produto_id=1, quantidade_movimentada=5) is True
    
    # Venda / Débito de estoque (-12) -> Deve ir para 3
    assert atualizar_estoque(banco_memoria, produto_id=1, quantidade_movimentada=-12) is True
    
    with Session(banco_memoria) as db:
        prod = db.get(Produto, 1)
        assert prod.quantidade_estoque == 3
        
    # Falha: Tentar vender mais do que tem (-5 unidades num estoque de 3) -> Negativo barrado!
    assert atualizar_estoque(banco_memoria, produto_id=1, quantidade_movimentada=-5) is False


# ==============================================================================
# 4. TESTE DE EDIÇÃO CADASTRAL (EDITAR_PRODUTO)
# ==============================================================================

def test_editar_dados_cadastrais_com_sucesso_e_validacao(banco_memoria, categoria_valida):
    """Valida a atualização parcial de textos mesclando dados antigos e novos."""
    cadastrar_produto(banco_memoria, "Truck Antigo", "Leve", 150.0, 90.0, 4, categoria_valida)
    
    novos_dados = {
        "nome": "   Truck Importado Pro   ",  # Testando se aplica o .strip() na gravação
        "descricao": "Liga de alumínio premium"
    }
    
    assert editar_produto(banco_memoria, produto_id=1, novos_dados=novos_dados) is True
    
    with Session(banco_memoria) as db:
        prod = db.get(Produto, 1)
        assert prod.nome == "Truck Importado Pro"  # Gravado limpo
        assert prod.descricao == "Liga de alumínio premium"
        assert prod.preco_venda == 150.0  # Manteve o preço original intacto