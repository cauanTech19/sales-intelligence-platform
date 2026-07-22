import pytest
from datetime import datetime
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from models import Base, Venda, ItemVenda, Produto, MovimentacaoEstoque, StatusVenda, TipoMovimentacao, Categoria, Cliente
from vendas import calcular_total, criar_venda, cancelar_venda, buscar_venda, listar_vendas

# ==============================================================================
# FIXTURE: BANCO DE TESTES BLINDADO
# ==============================================================================
@pytest.fixture
def banco_vendas():
    """Cria banco em memória, ativa FKs e popula dados iniciais para os testes."""
    engine_local = create_engine("sqlite:///:memory:")
    
    @event.listens_for(engine_local, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    Base.metadata.create_all(bind=engine_local)
    
    # POPULA DADOS CORES PARA PODER VENDER
    with Session(engine_local) as db:

        cat = Categoria(
            nome="exemplo_produto",
            descricao="Apenas exemplo"
        )
        cli = Cliente(
            nome="Cauan", 
            cpf="123.567.897-06",
            email="cauan@gmail.com", 
            endereco="Rua do barcos 235", 
            telefone="11982116413"
        )

        # 1. Cria um produto válido com estoque
        skate = Produto(
            id=1,
            nome="Skate Montado Pro",
            preco_venda=599.90,
            preco_custo=300.00,
            quantidade_estoque=10,
            ativo=True,
            categoria_id=1
        )
        # 2. Cria outro produto para testes de múltiplos itens
        rodas = Produto(
            id=2,
            nome="Rodas 54mm",
            preco_venda=120.00,
            preco_custo=60.00,
            quantidade_estoque=20,
            ativo=True,
            categoria_id=1
        )
        db.add_all([cat, cli, skate, rodas])
        db.commit()

    yield engine_local
    Base.metadata.drop_all(bind=engine_local)


# ==============================================================================
# 1. TESTE UNITÁRIO: MATEMÁTICA DO TOTAL
# ==============================================================================
def test_calcular_total_deve_retornar_soma_correta():
    """Garante que a função calcula o valor bruto sem precisar de banco."""
    itens = [
        {"produto_id": 1, "quantidade": 2, "preco_unitario": 10.0},
        {"produto_id": 2, "quantidade": 3, "preco_unitario": 50.0}
    ]
    # (2 * 10) + (3 * 50) = 20 + 150 = 170
    assert calcular_total(itens) == 170.0


def test_criar_venda_com_sucesso(banco_vendas):
    """Garante que a venda salva o cabeçalho, os itens, deduz estoque e gera auditoria."""
    itens = [
        {"produto_id": 1, "quantidade": 2, "preco_unitario": 599.90}, # Total: 1199.80
        {"produto_id": 2, "quantidade": 1, "preco_unitario": 120.00}  # Total: 120.00
    ]                                                                 # Geral: 1319.80
    
    resultado = criar_venda(banco_vendas, cliente_id=1, forma_pagamento="PIX", itens_validados=itens)
    
    assert resultado is True
    
    with Session(banco_vendas) as db:
        # Verifica se o cabeçalho foi salvo com o valor somado correto
        venda = db.get(Venda, 1)
        # assert venda is not None
        assert venda.valor_total == 1319.80
        assert venda.status == StatusVenda.CONCLUIDA
        
        # Regra de Negócio 3: Estoque deduzido corretamente? (10-2=8) e (20-1=19)
        prod1 = db.get(Produto, 1)
        prod2 = db.get(Produto, 2)
        assert prod1.quantidade_estoque == 8
        assert prod2.quantidade_estoque == 19
        
        # Verifica se gerou o histórico na tabela de MovimentacaoEstoque (SAIDA)
        movimentacoes = db.scalars(select(MovimentacaoEstoque)).all()
        assert len(movimentacoes) == 2
        assert movimentacoes[0].tipo_movimentacao == TipoMovimentacao.SAIDA


def test_criar_venda_carrinho_vazio_deve_retornar_false(banco_vendas):
    """Regra de Negócio 1: Impede a criação de venda se não houver itens."""
    resultado = criar_venda(banco_vendas, cliente_id=1, forma_pagamento="CREDITO", itens_validados=[])
    assert resultado is False


# ==============================================================================
# 3. TESTES DE CANCELAMENTO E BUSCA
# ==============================================================================
def test_cancelar_venda_deve_estornar_estoque_e_mudar_status(banco_vendas):
    """Garante que o cancelamento devolve as quantidades e gera logs de ENTRADA."""
    itens = [{"produto_id": 1, "quantidade": 3, "preco_unitario": 599.90}]
    
    # Realiza a venda primeiro (Estoque cai de 10 para 7)
    criar_venda(banco_vendas, cliente_id=1, forma_pagamento="DEBITO", itens_validados=itens)
    
    # Cancela a venda ID 1
    resultado_cancelamento = cancelar_venda(banco_vendas, venda_id=1)
    assert resultado_cancelamento is True
    
    with Session(banco_vendas) as db:
        venda = db.get(Venda, 1)
        assert venda.status == StatusVenda.CANCELADA
        
        # O estoque do produto 1 deve ter voltado para 10!
        produto = db.get(Produto, 1)
        assert produto.quantidade_estoque == 10
        
        # Deve ter um log de ENTRADA mapeado para o estorno
        mov_estorno = db.scalars(
            select(MovimentacaoEstoque).where(MovimentacaoEstoque.tipo_movimentacao == TipoMovimentacao.ENTRADA)
        ).first()

        assert mov_estorno is not None
        assert "Estorno por Cancelamento" in mov_estorno.motivo


def test_buscar_e_listar_vendas(banco_vendas):
    """Valida os métodos de consulta do histórico comercial."""
    itens = [{"produto_id": 2, "quantidade": 2, "preco_unitario": 120.00}]
    
    criar_venda(banco_vendas, cliente_id=1, forma_pagamento="PIX", itens_validados=itens)
    
    # Testa buscar_venda
    venda_buscada = buscar_venda(banco_vendas, venda_id=1)
    assert venda_buscada.id == 1
    assert venda_buscada is not None
    assert len(venda_buscada.itens) == 1
  
    # Testa buscar_venda com ID bizarro/inválido
    assert buscar_venda(banco_vendas, "ID_STRING") is None
    
    # Testa listar_vendas
    lista = listar_vendas(banco_vendas)
    assert len(lista) == 1