from datetime import datetime
from sqlalchemy.orm import Session, Mapped, selectinload
from sqlalchemy import select
from models import Venda, ItemVenda, Produto, StatusVenda, FormaPagamento, TipoMovimentacao, MovimentacaoEstoque, engine

def calcular_total(itens_da_venda: list[dict]) -> float:
    """Calcula matematicamente o valor total da venda com base nos itens fornecidos.
    
    Cada item na lista deve ser um dict: {"preco_unitario": float, "quantidade": int}
    """
    return sum(item["preco_unitario"] * item["quantidade"] for item in itens_da_venda)


def criar_venda(engine, cliente_id: int, forma_pagamento: FormaPagamento, itens_validados: list[dict]) -> bool:
    """Executa a persistência da venda no banco de dados após os itens já terem sido validados.
    
    Recebe a lista de dicionários já higienizados pelo 'validar_e_preparar_item()'.
    """
    # Regra de Negócio 1: Não permitir venda sem itens
    if not itens_validados:
        print("\n[Erro de Venda]: Operação recusada. O carrinho de compras está vazio.")
        return False

    with Session(engine) as db:
        try:
            with db.begin():
                # 1. Instancia o cabeçalho da venda (Calculamos o total direto aqui usando a nossa função)
                venda = Venda(
                    cliente_id=cliente_id,
                    forma_pagamento=forma_pagamento,
                    status=StatusVenda.CONCLUIDA,
                    data_venda=datetime.now(),
                    valor_total=calcular_total(itens_validados) # Reutiliza o calcular_total()
                )
                db.add(venda)
                db.flush() # Descarrega para gerar o venda.id

                # 2. Como os dados já chegam limpos, aqui nós só salvamos e atualizamos
                for item in itens_validados:
                    prod_id = item["produto_id"]
                    qtd_solicitada = item["quantidade"]
                    preco_praticado = item["preco_unitario"]

                    # Busca o produto aplicando o Lock de concorrência
                    produto = db.execute(
                        select(Produto).where(Produto.id == prod_id).with_for_update()
                    ).scalar_one()

                    # Regra de Negócio 3: Atualiza o estoque automaticamente
                    produto.quantidade_estoque -= qtd_solicitada

                    # 3. Cria o registro do Item
                    novo_item = ItemVenda(
                        venda_id=venda.id,
                        produto_id=prod_id,
                        quantidade=qtd_solicitada,
                        preco_unitario=preco_praticado
                    )
                    db.add(novo_item)

                    # 4. Alimenta o histórico de auditoria
                    movimentacao = MovimentacaoEstoque(
                        produto_id=prod_id,
                        tipo_movimentacao=TipoMovimentacao.SAIDA,
                        quantidade=qtd_solicitada,
                        motivo=f"Venda efetuada. ID da Venda: #{venda.id}",
                        data_movimentacao=datetime.now()
                    )
                    db.add(movimentacao)
                
            print(f"Venda #{venda.id} realizada com sucesso! Total: R$ {venda.valor_total:.2f}")
            return True

        except Exception as e:
            print(f"\n[Erro Inesperado na Transação da Venda]: {e}")
            return False

def cancelar_venda(engine, venda_id: int) -> bool:
    """Cancela uma venda ativa e DEVOLVE todos os itens comprados de volta ao estoque."""
    with Session(engine) as db:
        try:
            with db.begin():
                venda = db.get(Venda, venda_id)
                
                if not venda:
                    print(f"\n[Erro de Cancelamento]: Venda #{venda_id} não encontrada.")
                    return False
                
                if venda.status == StatusVenda.CANCELADA:
                    print(f"\n[Aviso]: Venda #{venda_id} já se encontra cancelada.")
                    return False

                # Devolve os itens ao estoque e gera movimentação de ENTRADA
                for item in venda.itens:
                    produto = db.get(Produto, item.produto_id)
                    if produto:
                        produto.quantidade_estoque += item.quantidade
                        
                        # Histórico de estorno no estoque
                        movimentacao = MovimentacaoEstoque(
                            produto_id=item.produto_id,
                            tipo_movimentacao=TipoMovimentacao.ENTRADA,
                            quantidade=item.quantidade,
                            motivo=f"Estorno por Cancelamento da Venda #{venda.id}",
                            data_movimentacao=datetime.now()
                        )
                        db.add(movimentacao)

                # Altera o status do cabeçalho
                venda.status = StatusVenda.CANCELADA
                
            print(f"Venda #{venda_id} cancelada e estoque estornado com sucesso!")
            return True
        except Exception as e:
            print(f"\n[Erro ao cancelar venda]: {e}")
            return False


def buscar_venda(engine, venda_id: int) -> Venda | None:
    """Busca os detalhes de uma venda e seus itens associados."""
    if not isinstance(venda_id, int) or isinstance(venda_id, bool):
        return None
        
    with Session(engine) as db:
        # O selectinload força a carregar a relação 'itens' ANTES da session fechar
        comando = select(Venda).options(selectinload(Venda.itens)).where(Venda.id == venda_id)
        return db.scalar(comando)

def listar_vendas(engine) -> list[Venda]:
    """Retorna o histórico completo de todas as vendas do sistema."""
    with Session(engine) as db:
        comando = select(Venda).options(selectinload(Venda.itens)).order_by(Venda.data_venda.desc())
        return list(db.scalars(comando).all())



