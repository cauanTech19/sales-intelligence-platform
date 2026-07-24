from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import ValidationError
from models import Venda, Pagamento, StatusVenda, StatusPagamento, FormaPagamento
from validador import PagamentoSchema



def registrar_pagamento(engine, venda_id: int, valor: float, forma_pagamento: FormaPagamento) -> bool:
    """Registra um pagamento para uma venda e atualiza o status da venda se o total for atingido.
    
    Regras de Negócio: Valor maior que zero e Registro de histórico.
    """
    try:
        # Regra de Negócio 1: Pydantic barra na hora valores negativos ou zerados (gt=0)
        dados_validados = PagamentoSchema(
            venda_id=venda_id,
            valor=valor,
            forma_pagamento=forma_pagamento
        )
        
        with Session(engine) as db:
            try:
                with db.begin():
                    # Busca a venda usando Lock para evitar que dois pagamentos idênticos processem juntos
                    venda = db.execute(
                        select(Venda).where(Venda.id == venda_id).with_for_update()
                    ).scalar_one_or_none()
                    
                    if not venda:
                        print(f"\n[Erro Financeiro]: Venda ID {venda_id} não encontrada.")
                        return False
                        
                    if venda.status == StatusVenda.CANCELADA:
                        print(f"\n[Erro Financeiro]: Não é possível registrar pagamento para uma venda CANCELADA.")
                        return False

                    # Regra de Negócio 2: Registrar histórico de pagamento (Gera a linha na tabela)
                    novo_pagamento = Pagamento(
                        venda_id=dados_validados.venda_id,
                        valor=dados_validados.valor,
                        forma_pagamento=dados_validados.forma_pagamento,
                        status=StatusPagamento.APROVADO, # Simulando aprovação imediata
                        data_pagamento=datetime.now()
                    )
                    db.add(novo_pagamento)
                    db.flush()
                    
                    # Inteligência de Negócio: Verifica o total pago acumulado dessa venda
                    # Para cenários onde o cliente pode pagar em parcelas ou dois cartões
                    comando_total_pago = select(Pagamento).where(
                        Pagamento.venda_id == venda_id, 
                        Pagamento.status == StatusPagamento.APROVADO
                    )
                    
                    pagamentos_anteriores = db.scalars(comando_total_pago).all()
                    total_pago_acumulado = sum(p.valor for p in pagamentos_anteriores)

                    # Se o total pago cobrir ou passar o valor total da venda, atualiza a venda para CONCLUIDA
                    if float(total_pago_acumulado) >= float(venda.valor_total):
                        venda.status = StatusVenda.CONCLUIDA
                        print(f" -> Venda #{venda.id} quitada com sucesso! (Pago: R$ {total_pago_acumulado:.2f})")
                        
                print(f"Pagamento de R$ {dados_validados.valor:.2f} registrado com sucesso!")
                return True
                
            except Exception as e:
                print(f"\n[Erro Inesperado na Transação Financeira]: {e}")
                return False

    except ValidationError as e:
        print("\n[Erro de Validação de Pagamento]:")
        for erro in e.errors():
            print(f" -> Campo '{erro['loc'][0]}': {erro['msg']}")
        return False


def cancelar_pagamento(engine, pagamento_id: int) -> bool:
    """Estorna um pagamento do sistema e reavalia o status da venda vinculada para PENDENTE."""
    with Session(engine) as db:
        try:
            with db.begin():
                pagamento = db.execute(
                    select(Pagamento).where(Pagamento.id == pagamento_id).with_for_update()
                ).scalar_one_or_none()
                
                if not pagamento:
                    print(f"\n[Erro Financeiro]: Pagamento ID {pagamento_id} não localizado.")
                    return False
                    
                if pagamento.status == StatusPagamento.ESTORNADO:
                    print(f"\n[Aviso]: Pagamento ID {pagamento_id} já se encontra estornado.")
                    return False
                    
                # Altera o status do histórico para Estornado
                pagamento.status = StatusPagamento.ESTORNADO
                
                # Se a venda estava concluída, ela volta a ficar Pendente porque o dinheiro sumiu
                venda = db.get(Venda, pagamento.venda_id)
                if venda and venda.status == StatusVenda.CONCLUIDA:
                    venda.status = StatusVenda.PENDENTE
                    print(f" -> Alerta: Venda #{venda.id} retornou ao status PENDENTE devido ao estorno.")
                    
            print(f"Pagamento ID {pagamento_id} estornado com sucesso!")
            return True
        except Exception as e:
            print(f"\n[Erro ao cancelar pagamento]: {e}")
            return False


def listar_pagamentos(engine) -> list[Pagamento]:
    """Retorna o histórico completo de todas as transações financeiras (pagamentos e estornos)."""
    with Session(engine) as db:
        comando = select(Pagamento).order_by(Pagamento.data_pagamento.desc())
        return list(db.scalars(comando).all())