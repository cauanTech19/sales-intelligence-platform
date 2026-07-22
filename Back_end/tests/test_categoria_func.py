import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from models import Base, Categoria, Produto
from categoria import (  # Ajuste para o nome real do seu arquivo
    cadastrar_categoria,
    desativar_categoria,
    buscar_categoria,
    listar_categorias,
    editar_categoria
)

# ==============================================================================
# FIXTURE: BANCO ISOLADO COM FOREIGN KEYS ATIVAS
# ==============================================================================
@pytest.fixture
def banco_categoria():
    """Cria o banco em memória e garante que as FKs estejam ligadas para os testes."""
    engine_local = create_engine("sqlite:///:memory:")
    
    @event.listens_for(engine_local, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    Base.metadata.create_all(bind=engine_local)
    yield engine_local
    Base.metadata.drop_all(bind=engine_local)


# ==============================================================================
# 1. TESTES DE CADASTRO E DUPLICIDADE
# ==============================================================================

def test_cadastrar_categoria_com_sucesso(banco_categoria):
    """Garante que uma categoria nova e válida seja gravada no banco."""
    resultado = cadastrar_categoria(banco_categoria, nome="Skates", descricao="Shapes e complementos")
    assert resultado is True
    
    with Session(banco_categoria) as db:
        cat = db.get(Categoria, 1)
        assert cat is not None
        assert cat.nome == "Skates"


def test_cadastrar_categoria_duplicada_deve_retornar_false(banco_categoria):
    """Garante que a restrição UNIQUE do banco barre nomes duplicados e retorne False."""
    # Cadastra a primeira vez
    cadastrar_categoria(banco_categoria, nome="Roupas", descricao="Vestuário geral")
    
    # Tenta cadastrar exatamente o mesmo nome
    resultado_duplicado = cadastrar_categoria(banco_categoria, nome="Roupas", descricao="Outra descrição")
    
    assert resultado_duplicado is False


# ==============================================================================
# 2. TESTES DE EDICAO E LISTAGEM
# ==============================================================================

def test_editar_categoria_com_sucesso(banco_categoria):
    """Garante que os dados textuais de uma categoria sejam atualizados corretamente."""
    cadastrar_categoria(banco_categoria, nome="Pecas", descricao="Pecas antigas")
    
    resultado = editar_categoria(banco_categoria, categoria_id=1, novo_nome="Peças Pro", descricao="Peças importadas")
    assert resultado is True
    
    with Session(banco_categoria) as db:
        cat = db.get(Categoria, 1)
        assert cat.nome == "Peças Pro"
        assert cat.descricao == "Peças importadas"


def test_listar_categorias_deve_retornar_em_ordem_alfabetica(banco_categoria):
    """Garante que a listagem traga todas as linhas ordenadas por nome."""
    cadastrar_categoria(banco_categoria, nome="Rodas", descricao="...")
    cadastrar_categoria(banco_categoria, nome="Trucks", descricao="...")
    cadastrar_categoria(banco_categoria, nome="Amortecedores", descricao="...")
    
    lista = listar_categorias(banco_categoria)
    
    assert len(lista) == 3
    # Verifica a ordenação do select(...).order_by(Categoria.nome)
    assert lista[0].nome == "Amortecedores"
    assert lista[1].nome == "Rodas"
    assert lista[2].nome == "Trucks"


# ==============================================================================
# 3. TESTES DA REGRA DE EXCLUSÃO (SEGURANÇA DE VINCULO)
# ==============================================================================

def test_excluir_categoria_sem_produtos_deve_funcionar(banco_categoria):
    """Garante que uma categoria vazia (sem nenhum produto) possa ser deletada do sistema."""
    cadastrar_categoria(banco_categoria, nome="Acessórios", descricao="...")
    
    resultado = desativar_categoria(banco_categoria, categoria_id=1)
    assert resultado is True
    
    with Session(banco_categoria) as db:
        cat = db.get(Categoria, 1) 
        assert cat.ativo is False



def test_excluir_categoria_com_produtos_vinculados_deve_ser_bloqueado(banco_categoria):
    """Garante que a regra de segurança impeça a exclusão de uma categoria que possui produtos."""
    # 1. Cria a categoria
    cadastrar_categoria(banco_categoria, nome="Tênis", descricao="Calçados")
    
    # 2. Vincula um produto manualmente a essa categoria ID 1
    with Session(banco_categoria) as db:
        produto_teste = Produto(
            nome="Tênis Skate Pro",
            preco_venda=299.90,
            preco_custo=150.00,
            quantidade_estoque=5,
            categoria_id=1  # Vinculado aqui!
        )
        db.add(produto_teste)
        db.commit()
        
    # 3. Tenta deletar a categoria ID 1 -> Deve retornar False pelo select de verificação
    resultado_exclusao = desativar_categoria(banco_categoria, categoria_id=1)
    
    assert resultado_exclusao is False
    
    # Garante que a categoria continua intacta lá dentro
    with Session(banco_categoria) as db:
        assert db.get(Categoria, 1) is not None