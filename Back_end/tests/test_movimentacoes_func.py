import pytest
from datetime import datetime
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from models import Base, Produto, MovimentacaoEstoque, TipoMovimentacao, Categoria
from movimentacao import ajustar_estoque_manual, consultar_historico_produto

# ==============================================================================
# FIXTURE: BANCO DE TESTES DE ESTOQUE
# ==============================================================================
@pytest.fixture
def banco_estoque():
    """Cria banco em memória e popula produtos para testes de movimentação."""
    engine_local = create_engine("sqlite:///:memory:")
    
    @event.listens_for(engine_local, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    Base.metadata.create_all(bind=engine_local)
    
    with Session(engine_local) as db:
        cat = Categoria(
            nome="Skate",
            descricao="venda de skate"
        )
        # Produto ativo com estoque inicial
        shape = Produto(
            id=1,
            nome="Shape Maple Pro",
            preco_venda=349.90,
            preco_custo=180.00,
            quantidade_estoque=10,
            ativo=True,
            categoria_id=1
        )
        # Produto inativo para teste de bloqueio
        rolamento_velho = Produto(
            id=2,
            nome="Rolamento Abec 5 Antigo",
            preco_venda=50.00,
            preco_custo=20.00,
            quantidade_estoque=5,
            ativo=False,
            categoria_id=1
        )

        db.add_all([cat, shape, rolamento_velho])
        db.commit()

    yield engine_local
    Base.metadata.drop_all(bind=engine_local)


# ==============================================================================
# 1. TESTES DE AJUSTE MANUAL (ENTRADA, SAÍDA E VALIDAÇÕES)
# ==============================================================================
def test_ajuste_positivo_deve_somar_estoque_e_gerar_entrada(banco_estoque):
    """Garante que somar unidades funciona e gera log com tipo ENTRADA."""
    resultado = ajustar_estoque_manual(banco_estoque, produto_id=1, quantidade_alterada=5, motivo="Chegou do fornecedor")
    assert resultado is True
    
    with Session(banco_estoque) as db:
        produto = db.get(Produto, 1)
        assert produto.quantidade_estoque == 15  # 10 inicial + 5
        
        # Checa se gravou a auditoria corretamente
        mov = db.scalar(select(MovimentacaoEstoque).where(MovimentacaoEstoque.produto_id == 1))
        assert mov is not None
        # O tipo do seu enum pode vir como objeto ou string dependendo da declaração, testamos o valor de forma segura
        tipo_str = mov.tipo_movimentacao.value if hasattr(mov.tipo_movimentacao, 'value') else mov.tipo_movimentacao
        assert tipo_str == "ENTRADA"
        assert mov.quantidade == 5
        assert "[Ajuste Manual]" in mov.motivo


def test_ajuste_negativo_deve_subtrair_estoque_e_gerar_saida(banco_estoque):
    """Garante que subtrair unidades reduz o saldo e gera log de SAIDA com valor absoluto positivo."""
    resultado = ajustar_estoque_manual(banco_estoque, produto_id=1, quantidade_alterada=-3, motivo="Peca quebrada")
    assert resultado is True
    
    with Session(banco_estoque) as db:
        produto = db.get(Produto, 1)
        assert produto.quantidade_estoque == 7  # 10 inicial - 3
        
        mov = db.scalar(select(MovimentacaoEstoque).where(MovimentacaoEstoque.produto_id == 1))
        tipo_str = mov.tipo_movimentacao.value if hasattr(mov.tipo_movimentacao, 'value') else mov.tipo_movimentacao
        assert tipo_str == "SAIDA"
        assert mov.quantidade == 3  # Regra de negócio: quantidade salva na auditoria deve ser absoluta (positiva)


def test_ajuste_nao_deve_permitir_estoque_ficar_negativo(banco_estoque):
    """Regra de Segurança: Tentar remover mais itens do que o saldo em estoque deve ser barrado."""
    resultado = ajustar_estoque_manual(banco_estoque, produto_id=1, quantidade_alterada=-12, motivo="Giro insano")
    assert resultado is False
    
    with Session(banco_estoque) as db:
        produto = db.get(Produto, 1)
        assert produto.quantidade_estoque == 10  # Mantém os 10 intactos


def test_ajustes_invalidos_devem_retornar_false(banco_estoque):
    """Garante bloqueio para quantidade zerada, motivo em branco ou produto inativo/inexistente."""
    # Quantidade zero
    assert ajustar_estoque_manual(banco_estoque, produto_id=1, quantidade_alterada=0, motivo="Teste") is False
    
    # Motivo vazio
    assert ajustar_estoque_manual(banco_estoque, produto_id=1, quantidade_alterada=2, motivo="   ") is False
    
    # Produto Inativo (ID 2)
    assert ajustar_estoque_manual(banco_estoque, produto_id=2, quantidade_alterada=2, motivo="Teste") is False
    
    # Produto Inexistente (ID 99)
    assert ajustar_estoque_manual(banco_estoque, produto_id=99, quantidade_alterada=2, motivo="Teste") is False


# ==============================================================================
# 2. TESTES DE EXCEÇÃO (RAISE VALUEERROR)
# ==============================================================================
def test_id_nao_inteiro_deve_lancar_excecao(banco_estoque):
    """Valida se o raise ValueError do id funciona nas duas funções."""
    with pytest.raises(ValueError, match="Id deve ser um número inteiro"):
        ajustar_estoque_manual(banco_estoque, produto_id="TEXTO", quantidade_alterada=5, motivo="Erro")

    with pytest.raises(ValueError, match="Id deve ser um número inteiro"):
        consultar_historico_produto(banco_estoque, produto_id="TEXTO")


# ==============================================================================
# 3. TESTES DE CONSULTA DE HISTÓRICO
# ==============================================================================
def test_consultar_historico_deve_retornar_na_ordem_correta(banco_estoque):
    """Garante a listagem correta e ordenada por data decrescente."""
    ajustar_estoque_manual(banco_estoque, produto_id=1, quantidade_alterada=2, motivo="Primeiro")
    ajustar_estoque_manual(banco_estoque, produto_id=1, quantidade_alterada=-1, motivo="Segundo")
    
    historico = consultar_historico_produto(banco_estoque, produto_id=1)
    assert len(historico) == 2
    # O mais recente vem primeiro por conta do order_by desc
    assert "Segundo" in historico[0]["motivo"]
    assert "Primeiro" in historico[1]["motivo"]