from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from validador import ProdutoSchema, ValidationError
from models import Produto, engine


def cadastrar_produto(engine, nome: str, descricao: str | None, preco_venda: float, preco_custo: float, quantidade_estoque: int, categoria_id: int) -> bool:
    """Executa o fluxo completo de validação e persistência de um novo produto.

    Os dados passam pelo ProdutoSchema (Pydantic) e, se aceitos, são salvos no banco.
    As mensagens de erro são interceptadas e traduzidas de forma amigável.
    """
    try:
        # 1. Validação estrita de tipos e regras com o Pydantic
        dados_validados = ProdutoSchema(
            nome=nome,
            descricao=descricao,
            preco_venda=preco_venda,
            preco_custo=preco_custo,
            quantidade_estoque=quantidade_estoque,
            categoria_id=categoria_id
        )

        # 2. Se passar, persistimos os dados higienizados no banco
        with Session(engine) as db:
            novo_produto = Produto(**dados_validados.model_dump())
            db.add(novo_produto)
            db.commit()
            print(f"Produto '{dados_validados.nome}' cadastrado com sucesso!")
            return True

    except ValidationError as e:
        print("\n[Erro de Validação do Produto]:")
        
        # Dicionário de traduções estendida para abranger regras matemáticas e customizadas
        traducoes = {
            "string_too_short": "O nome do produto deve conter pelo menos 1 caractere.",
            "missing": "Este campo é obrigatório.",
            "value_error": "O valor fornecido é inválido."
        }
        
        for erro in e.errors():
            tipo_erro = erro['type']
            mensagem = erro['msg']

            if erro['loc']:
                campo = erro['loc'][0]
            else:
                campo = "produto" # Se estiver vazio, é um erro geral do modelo

            # 1. Aplica as traduções genéricas se existirem
            if tipo_erro in traducoes:
                # Se for erro geral (Sem campo específico), usamos a mensagem direta que veio do raise ValueError
                if campo != "produto":
                    mensagem = traducoes[tipo_erro]
            
            # 2. Tratamento específico para as regras numéricas do Pydantic (gt e ge)
            elif tipo_erro == "greater_than" and "0" in erro.get("msg", ""):
                mensagem = "O valor deve ser estritamente maior do que zero."

            elif tipo_erro == "greater_than_equal" and "0" in erro.get("msg", ""):
                mensagem = "A quantidade em estoque não pode ser negativa (deve ser maior ou igual a zero)."
            
            # 3. Captura a nossa validação customizada (Margem de lucro negativa)
            elif "margem de lucro" in mensagem.lower():
                # Mantém a mensagem clara gerada no seu @field_validator / @model_validator
                pass
                
            print(f" -> Campo '{campo}': {mensagem}")
        
        return False

    except IntegrityError as e:
        erro_msg = str(e).lower()
        print("\n[Erro de Integridade no Banco]:")
        
        # Captura especificamente a violação da Chave Estrangeira (Foreign Key)
        if "foreign key constraint failed" in erro_msg:
            print(f" -> Erro: A categoria informada (ID {categoria_id}) não existe no sistema.")
            print(" -> Dica: Cadastre a categoria primeiro antes de vincular um produto a ela.")
        else:
            print(f" -> Erro inesperado no banco de dados: {e.orig}")
            
        return False


def listar_produtos(engine, apenas_ativos: bool = True) -> list[Produto]:
    """Retorna a lista de produtos cadastrados no sistema.
    
    Performance: Utiliza lazy loading padrão, mas filtra registros históricos
    de soft delete caso 'apenas_ativos' seja True.
    """
    with Session(engine) as db:
        if apenas_ativos:

            stmt = select(Produto).where(Produto.ativo == True)
        else:
            stmt = select(Produto)
        
        return list(db.scalars(stmt).all())



def buscar_produto(engine, produto_id: int) -> Produto | None:
    """Busca um produto ativo ou inativo diretamente pela chave primária (B-Tree).
    
    Garante tipagem estrita no ID antes de tocar no banco de dados.
    """
    if not isinstance(produto_id, int) or isinstance(produto_id, bool):
        print("\n[Erro de Busca]: O ID do produto precisa ser um número inteiro válido.")
        return None

    with Session(engine) as db:
        produto = db.get(Produto, produto_id)

        if produto and produto.ativo:
            return produto
        return None
        


def alterar_preco(engine, produto_id: int, novo_preco_venda: float, novo_preco_custo: float | None = None) -> bool:
    """Altera estrategicamente as métricas de preço de um produto ativo.
    
    Cruza dados para impedir margens negativas através do motor do Pydantic.

    """
    
    if not isinstance(produto_id, int) or isinstance(produto_id, bool):
        return False

    with Session(engine) as db:
        produto = db.get(Produto, produto_id)
        
        if not produto or not produto.ativo:
            print(f"\n[Erro de Preço]: Produto indisponível para alteração financeira.")
            return False

        custo_final = novo_preco_custo if novo_preco_custo is not None else produto.preco_custo

        try:
            # Força o Pydantic a validar o cruzamento do novo preço com o custo
            ProdutoSchema(
                nome=produto.nome,
                preco_venda=novo_preco_venda,
                preco_custo=custo_final,
                quantidade_estoque=produto.quantidade_estoque,
                categoria_id=produto.categoria_id
            )
            
            produto.preco_venda = novo_preco_venda
            produto.preco_custo = custo_final
            db.commit()
            print(f"Preços do produto '{produto.nome}' atualizados com sucesso!")
            return True
            

        except ValidationError as e:
            print("\n[Erro de Alteração de Preço]:")
            for erro in e.errors():
                if "margem de lucro" in erro['msg'].lower():
                    print(f" -> Operação Recusada: {erro['msg']}")
                else:
                    print(f" -> Campo '{erro['loc'][0]}': {erro['msg']}")
            return False



def editar_produto(engine, produto_id: int, novos_dados: dict) -> bool:
    """Modifica dados cadastrais textuais (nome, descrição, categoria) de um produto ativo.
    
    Regra de negócio: Impede alteração se o produto passou por soft delete.
    """
    if not isinstance(produto_id, int) or isinstance(produto_id, bool):
        print("\n[Erro de Edição]: O ID do produto precisa ser um número inteiro válido.")
        return False

    with Session(engine) as db:
        produto = db.get(Produto, produto_id)
        
        if not produto:
            print(f"\n[Erro de Edição]: Produto com ID {produto_id} não encontrado.")
            return False
            
        if not produto.ativo:
            print(f"\n[Erro de Edição]: Não é possível editar o produto '{produto.nome}' porque ele está desativado.")
            return False

        # Monta um dicionário temporário mesclando os dados antigos com os novos
        # para validar o estado final completo do objeto no Pydantic
        dados_finais = {
            "nome": novos_dados.get("nome", produto.nome),
            "descricao": novos_dados.get("descricao", produto.descricao),
            "preco_venda": novos_dados.get("preco_venda", produto.preco_venda),
            "preco_custo": novos_dados.get("preco_custo", produto.preco_custo),
            "quantidade_estoque": novos_dados.get("quantidade_estoque", produto.quantidade_estoque),
            "categoria_id": novos_dados.get("categoria_id", produto.categoria_id)
        }

        try:
            # Valida se a alteração quebra alguma regra de negócio estrutural
            ProdutoSchema(**dados_finais)
            
            # Aplica apenas os campos cadastrais permitidos nesta rota
            if "nome" in novos_dados: produto.nome = novos_dados["nome"].strip()
            if "descricao" in novos_dados: produto.descricao = novos_dados["descricao"]
            if "categoria_id" in novos_dados: produto.categoria_id = novos_dados["categoria_id"]
            
            db.commit()
            print("cadastro realizado")
            return True
            
        except ValidationError as e:
            print("\n[Erro de Validação na Edição do Produto]:")
            for erro in e.errors():
                print(f" -> Campo '{erro['loc'][0]}': {erro['msg']}")
            return False


def atualizar_estoque(engine, produto_id: int, quantidade_movimentada: int) -> bool:
    """Gerencia a entrada e saída física de itens do estoque de forma segura.
    
    Args:
        quantidade_movimentada (int): Pode ser positiva (ex: +10 para compras)
        ou negativa (ex: -2 para vendas).
    """
    if not isinstance(produto_id, int) or isinstance(produto_id, bool):
        return False
        
    if not isinstance(quantidade_movimentada, int) or isinstance(quantidade_movimentada, bool):
        print("\n[Erro de Estoque]: A quantidade movimentada precisa ser um número inteiro.")
        return False

    with Session(engine) as db:
        produto = db.get(Produto, produto_id)
        
        if not produto or not produto.ativo:
            print(f"\n[Erro de Estoque]: Produto não localizado ou inativo.")
            return False

        novo_estoque_calculado = produto.quantidade_estoque + quantidade_movimentada

        try:
            # Testa se a variação vai deixar o estoque negativo usando a regra ge=0 do Schema
            ProdutoSchema(
                nome=produto.nome,
                preco_venda=produto.preco_venda,
                preco_custo=produto.preco_custo,
                quantidade_estoque=novo_estoque_calculado,
                categoria_id=produto.categoria_id
            )
            
            produto.quantidade_estoque = novo_estoque_calculado
            db.commit()
            return True
            
        except ValidationError:
            print(f"\n[Erro de Estoque Insuficiente]: Falha ao debitar {abs(quantidade_movimentada)} unidades.")
            print(f" -> O estoque atual de '{produto.nome}' é {produto.quantidade_estoque}, não podendo ficar negativo.")
            return False





