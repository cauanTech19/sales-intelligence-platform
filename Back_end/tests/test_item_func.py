import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from models import Base, Produto, Categoria
from item import validar_e_preparar_item  # Ajuste o import para o seu arquivo real

# ==============================================================================
# FIXTURE: BANCO DE TESTES DE VALIDAÇÃO
# ==============================================================================
@pytest.fixture
def banco_validacao():
    """Cria banco em memória e popula produtos para testar as regras do carrinho."""
    engine_local = create_engine("sqlite:///:memory:")
    
    @event.listens_for(engine_local, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    Base.metadata.create_all(bind=engine_local)
    
    with Session(engine_local) as db:
        # Produto OK com 5 unidades no estoque
        cat = Categoria(
            nome="Skate",
            descricao="venda de skate"
        )

        truck = Produto(
            id=1,
            nome="Truck Independent 139mm",
            preco_venda=420.00,
            preco_custo=250.00,
            quantidade_estoque=5,
            ativo=True,
            categoria_id=1
        )
        # Produto inativo para testar o bloqueio
        lixa_velha = Produto(
            id=2,
            nome="Lixa Nacional Antiga",
            preco_venda=25.00,
            preco_custo=10.00,
            quantidade_estoque=10,
            ativo=False,
            categoria_id=1

        )
        db.add_all([cat, truck, lixa_velha])
        db.commit()

    yield engine_local
    Base.metadata.drop_all(bind=engine_local)


# ==============================================================================
# TESTES DE VALIDAÇÃO DE ITEM
# ==============================================================================

def test_deve_preparar_item_com_sucesso(banco_validacao):
    """Garante que dados válidos retornam o dicionário limpo via model_dump()."""
    item_pronto = validar_e_preparar_item(
        banco_validacao, produto_id=1, quantidade=2, preco_unitario=420.00
    )
    
    assert item_pronto is not None
    assert item_pronto["produto_id"] == 1
    assert item_pronto["quantidade"] == 2
    assert item_pronto["preco_unitario"] == 420.00


def test_deve_barrar_se_quantidade_for_maior_que_o_estoque(banco_validacao):
    """Regra de Negócio 2: Não pode vender mais do que tem na prateleira."""
    # Temos 5 no estoque, tentando pedir 6
    item_pronto = validar_e_preparar_item(
        banco_validacao, produto_id=1, quantidade=6, preco_unitario=420.00
    )
    assert item_pronto is None


def test_deve_barrar_se_produto_nao_existir_ou_for_inativo(banco_validacao):
    """Sistema deve recusar produtos fantasmas ou desativados pelo gerente."""
    # Produto Inexistente (ID 99)
    assert validar_e_preparar_item(banco_validacao, produto_id=99, quantidade=1, preco_unitario=50.00) is None
    
    # Produto Inativo (ID 2)
    assert validar_e_preparar_item(banco_validacao, produto_id=2, quantidade=1, preco_unitario=25.00) is None


def test_deve_barrar_valores_invalidos_pelo_pydantic(banco_validacao):
    """Regra de Negócio 1: Pydantic deve capotar a validação se quantidade <= 0 ou preço incoerente."""
    # Quantidade zerada
    assert validar_e_preparar_item(banco_validacao, produto_id=1, quantidade=0, preco_unitario=420.00) is None
    
    # Quantidade negativa
    assert validar_e_preparar_item(banco_validacao, produto_id=1, quantidade=-3, preco_unitario=420.00) is None