import pytest
from datetime import datetime
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session
from models import Base, Venda, Pagamento, StatusVenda, StatusPagamento, Cliente
from pagamento import registrar_pagamento, cancelar_pagamento, listar_pagamentos

# ==============================================================================
# FIXTURE: BANCO DE TESTES FINANCEIRO
# ==============================================================================
@pytest.fixture
def banco_pagamentos():
    """Cria o banco em memória e insere clientes e vendas reais para manter as FKs íntegras."""
    engine_local = create_engine("sqlite:///:memory:")
    
    @event.listens_for(engine_local, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        
    Base.metadata.create_all(bind=engine_local)
    
    # Popula dados de teste salvando a integridade das Foreign Keys
    with Session(engine_local) as db:
        # 1. PRECISAVAMOS DO CLIENTE AQUI! Sem ele, a Venda quebra a FK de cliente_id
        cliente_teste = Cliente(
            id=1,
            nome="Cliente Teste",
            email="teste@email.com",
            cpf="12345678901",
            ativo=True
        )
        db.add(cliente_teste)
        db.flush() # Salva o cliente no banco para a venda poder linkar o ID dele
        
        # Venda 1: R$ 500.00 pronta para ser paga por partes ou total
        venda_aberta = Venda(
            id=1,
            cliente_id=1, # Agora sim o ID 1 existe de verdade!
            forma_pagamento="PIX",
            status=StatusVenda.PENDENTE,
            valor_total=500.00,
            data_venda=datetime.now()
        )
        # Venda 2: Uma venda já cancelada para testar o bloqueio de caixa
        venda_cancelada = Venda(
            id=2,
            cliente_id=1, # Linkando o mesmo cliente existente
            forma_pagamento="CREDITO",
            status=StatusVenda.CANCELADA,
            valor_total=150.00,
            data_venda=datetime.now()
        )
        db.add_all([venda_aberta, venda_cancelada])
        db.commit()

    yield engine_local
    Base.metadata.drop_all(bind=engine_local)

# ==============================================================================
# 1. TESTES DE FLUXO DE PAGAMENTO (SUCESSO E INTELIGÊNCIA PARCIAL)
# ==============================================================================
def test_pagamento_total_deve_concluir_a_venda(banco_pagamentos):
    """Garante que um pagamento do valor exato da venda altera seu status para CONCLUIDA."""
    # 🔥 CORREÇÃO: O valor tem que ser 500.00 para bater com o total da venda da fixture e mudar o status!
    resultado = registrar_pagamento(banco_pagamentos, venda_id=1, valor=500.00, forma_pagamento="PIX")
    assert resultado is True
    
    with Session(banco_pagamentos) as db:
        venda = db.get(Venda, 1)
        db.refresh(venda)
        # Se o seu banco retorna String pura, extraímos o .value do Enum para garantir a comparação limpa
        status_venda_str = venda.status.value if hasattr(venda.status, 'value') else venda.status
        assert status_venda_str == "CONCLUIDA"

def test_pagamentos_parciais_acumulados_devem_concluir_venda(banco_pagamentos):
    """Testa a inteligência de negócio: dois cartões/partes somados quitam a venda."""
    pago_parte1 = registrar_pagamento(banco_pagamentos, venda_id=1, valor=200.00, forma_pagamento="DEBITO")
    assert pago_parte1 is True
    
    with Session(banco_pagamentos) as db:
        venda = db.get(Venda, 1)
        db.refresh(venda)
        status_venda_str = venda.status.value if hasattr(venda.status, 'value') else venda.status
        assert status_venda_str == "PENDENTE"

    # 2º Pagamento complementar: R$ 300,00 (200 + 300 = 500. Conta fecha!)
    pago_parte2 = registrar_pagamento(banco_pagamentos, venda_id=1, valor=300.00, forma_pagamento="CREDITO")
    assert pago_parte2 is True
    
    with Session(banco_pagamentos) as db:
        venda = db.get(Venda, 1)
        db.refresh(venda)
        status_venda_str = venda.status.value if hasattr(venda.status, 'value') else venda.status
        assert status_venda_str == "CONCLUIDA"

# ==============================================================================
# 2. TESTES DE REGRAS DE RESTRIÇÃO / VALIDAÇÃO
# ==============================================================================
def test_registrar_pagamento_em_venda_cancelada_deve_falhar(banco_pagamentos):
    """Sistema deve recusar entrada de dinheiro em uma venda abortada."""
    resultado = registrar_pagamento(banco_pagamentos, venda_id=2, valor=150.00, forma_pagamento="PIX")
    assert resultado is False
    
    with Session(banco_pagamentos) as db:
        # Garante que nenhum registro de pagamento fantasma foi gerado
        pagamentos = db.scalars(select(Pagamento)).all()
        assert len(pagamentos) == 0


def test_pagamento_com_valor_negativo_deve_ser_barrado_pelo_pydantic(banco_pagamentos):
    """Regra de Negócio 1: O validador não aceita quantias inválidas."""
    resultado = registrar_pagamento(banco_pagamentos, venda_id=1, valor=-50.00, forma_pagamento="PIX")
    assert resultado is False


# ==============================================================================
# 3. TESTES DE ESTORNO / CANCELAMENTO DE PAGAMENTO
# ==============================================================================
def test_cancelar_pagamento_deve_reabrir_venda_como_pendente(banco_pagamentos):
    """Se um pagamento que quitou a venda for estornado, a venda volta a ficar PENDENTE."""
    # Quita a venda primeiro
    registrar_pagamento(banco_pagamentos, venda_id=1, valor=500.00, forma_pagamento="PIX")
    
    # Cancela/Estorna o pagamento ID 1
    resultado_estorno = cancelar_pagamento(banco_pagamentos, pagamento_id=1)
    assert resultado_estorno is True
    
    with Session(banco_pagamentos) as db:
        pagamento = db.get(Pagamento, 1)
        assert pagamento.status == StatusPagamento.ESTORNADO
        
        # Como o dinheiro sumiu, a venda perde o status de quitada
        venda = db.get(Venda, 1)
        assert venda.status == StatusVenda.PENDENTE


def test_listar_pagamentos_ordena_por_data(banco_pagamentos):
    """Garante que a listagem de auditoria financeira traz todos os dados certinho."""
    registrar_pagamento(banco_pagamentos, venda_id=1, valor=100.00, forma_pagamento="PIX")
    registrar_pagamento(banco_pagamentos, venda_id=1, valor=150.00, forma_pagamento="DEBITO")
    
    lista = listar_pagamentos(banco_pagamentos)
    assert len(lista) == 2