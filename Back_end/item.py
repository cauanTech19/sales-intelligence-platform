from sqlalchemy.orm import Session
from pydantic import ValidationError
from models import Produto
from validador import ItemVendaSchema

def validar_e_preparar_item(engine, produto_id: int, quantidade: int, preco_unitario: float) -> dict | None:
    """Valida as regras de negócio do item individualmente antes de ir para o carrinho.
    
    Regras: Quantidade maior que zero e Estoque suficiente.
    """
    try:
        # Regra de Negócio 1: Pydantic barra quantidade <= 0 ou preços inválidos
        dados_validados = ItemVendaSchema(
            produto_id=produto_id,
            quantidade=quantidade,
            preco_unitario=preco_unitario
        )
        
        with Session(engine) as db:
            produto = db.get(Produto, produto_id)
            
            if not produto or not produto.ativo:
                print(f"\n[Erro de Item]: Produto ID {produto_id} não existe ou está desativado.")
                return None
                
            # Regra de Negócio 2: Estoque suficiente
            if produto.quantidade_estoque < dados_validados.quantidade:
                print(f"\n[Erro de Estoque]: Não há estoque suficiente para '{produto.nome}'.")
                print(f" -> Disponível: {produto.quantidade_estoque} | Solicitado: {dados_validados.quantidade}")
                return None
            
            # Retorna o dicionário higienizado pronto para ser empilhado na lista da função criar_venda()
            return dados_validados.model_dump()

    except ValidationError as e:
        print("\n[Erro de Validação do Item]:")
        for erro in e.errors():
            print(f" -> Campo '{erro['loc'][0]}': {erro['msg']}")
        return None