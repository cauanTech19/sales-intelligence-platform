from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from models import Produto, MovimentacaoEstoque, TipoMovimentacao, engine

def ajustar_estoque_manual(engine, produto_id: int, quantidade_alterada: int, motivo: str) -> bool:
    """Ajusta o estoque de um produto manualmente e grava a movimentação para auditoria.
    
    Se quantidade_alterada for POSITIVA (+5): Adiciona ao estoque (Entrada).
    Se quantidade_alterada for NEGATIVA (-3): Subtrai do estoque (Saída).
    """
    if not isinstance(produto_id, int):
        raise ValueError("Id deve ser um número inteiro")

    if quantidade_alterada == 0:
        print("\n[Aviso de Ajuste]: A quantidade alterada não pode ser zero.")
        return False

    if not motivo.strip():
        print("\n[Erro de Ajuste]: É obrigatório informar um motivo para o ajuste manual.")
        return False

    with Session(engine) as db:
        try:
            with db.begin():
                # Busca o produto com Lock para garantir consistência jurídica do estoque
                produto = db.execute(
                    select(Produto).where(Produto.id == produto_id).with_for_update()
                ).scalar_one_or_none()

                if not produto or not produto.ativo:
                    print(f"\n[Erro de Ajuste]: Produto ID {produto_id} não encontrado ou está inativo.")
                    return False

                # Define o Tipo de Movimentação com base no sinal do número
                if quantidade_alterada > 0:
                    tipo = TipoMovimentacao.ENTRADA
                else:
                    tipo = TipoMovimentacao.SAIDA
                    # Regra de Segurança: Não deixar o estoque real ficar negativo por ajuste manual
                    if produto.quantidade_estoque + quantidade_alterada < 0:
                        print(f"\n[Bloqueio de Estoque]: Saldo insuficiente para essa saída.")
                        print(f" -> Atual: {produto.quantidade_estoque} | Tentativa de remover: {abs(quantidade_alterada)}")
                        return False

                # 1. Aplica a alteração matemática no produto
                produto.quantidade_estoque += quantidade_alterada

                nova_movimentacao = MovimentacaoEstoque(
                    produto_id=produto_id,
                    tipo_movimentacao=tipo,
                    quantidade=abs(quantidade_alterada), # Sempre salvamos o valor absoluto (positivo) na auditoria
                    motivo=f"[Ajuste Manual]: {motivo}",
                    data_movimentacao=datetime.now()
                )
                db.add(nova_movimentacao)

            print(f"Estoque do produto '{produto.nome}' ajustado com sucesso! Novo saldo: {produto.quantidade_estoque}")
            return True

        except Exception as e:
            print(f"\n[Erro Inesperado no Ajuste de Estoque]: {e}")
            return False


def consultar_historico_produto(engine, produto_id: int) -> list[MovimentacaoEstoque]:
    """Retorna todas as entradas e saídas que um produto específico sofreu no sistema."""
    if not isinstance(produto_id, int):
        raise ValueError("Id deve ser um número inteiro")

    with Session(engine) as db:
        comando = select(MovimentacaoEstoque).where(
            MovimentacaoEstoque.produto_id == produto_id
        ).order_by(MovimentacaoEstoque.data_movimentacao.desc())
        
        return list(db.scalars(comando).all())
    


ajustar_estoque_manual(engine, 1, 500, "teste de modificação #3")