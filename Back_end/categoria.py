from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from validador import CategoriaSchema, ValidationError
from sqlalchemy.exc import IntegrityError
from models import Categoria, engine, Produto


def cadastrar_categoria(engine, nome: str, descricao: str) -> bool:
    """Cadastra uma nova categoria salvando-a no banco. 
    Bloqueia nomes duplicados via IntegrityError.
    """
    try:
        with Session(engine) as db:
            nova_categoria = Categoria(nome=nome, descricao=descricao)
            db.add(nova_categoria)
            db.commit()
            print(f"Categoria {nome} cadastrada com sucesso!")
            return True
            
    except IntegrityError as e:
        # Como o nome é UNIQUE, se tentar duplicar vai cair aqui
        print(f"\n[Erro de Cadastro]: A categoria '{nome}' já existe no sistema.")
        return False


# ==============================================================================
# 2. REGRA DE EXCLUSÃO (Bloqueando se houver produtos vinculados)
# ==============================================================================
def desativar_categoria(engine, categoria_id: int) -> bool:
    """Desativa uma categoria (soft delete) apenas se não houver produtos ativos vinculados."""
    with Session(engine) as db:
        # 1. Verifica se existem produtos ATIVOS vinculados a essa categoria
        comando_verificacao = select(Produto).where(
            Produto.categoria_id == categoria_id,
            Produto.ativo == True
        )
        produtos_vinculados = db.scalars(comando_verificacao).first()
        
        if produtos_vinculados:
            print(f"\n[Bloqueio de Segurança]: Não é possível desativar a categoria ID {categoria_id}.")
            print(f" -> O produto ativo '{produtos_vinculados.nome}' depende dela.")
            print(" -> Dica: Desative ou mude a categoria dos produtos antes de desativar a categoria pai.")
            return False
            
        # 2. Localiza a categoria para alternar o estado
        categoria = db.get(Categoria, categoria_id)
        if not categoria:
            print(f"[Aviso] Categoria ID {categoria_id} não encontrada.")
            return False
            
        if not categoria.ativo:
            print(f"[Aviso] A categoria '{categoria.nome}' já está desativada.")
            return True

        # Altera o estado em vez de deletar
        categoria.ativo = False
        db.commit()
        print(f"Categoria '{categoria.nome}' desativada com sucesso!")
        return True

def buscar_categoria(engine, categoria_id: int) -> Categoria | None:
    """Busca uma categoria diretamente pela chave primária (B-Tree).
    
    Performance: Busca ultrarrápida indexada por ID. Retorna None se não encontrar.
    """
    if not isinstance(categoria_id, int) or isinstance(categoria_id, bool):
        print("\n[Erro de Busca]: O ID da categoria precisa ser um número inteiro válido.")
        return None

    with Session(engine) as db:
        categoria = db.get(Categoria, categoria_id)

        if categoria and categoria.ativo:
            return categoria
        return None


def listar_categorias(engine) -> list[Categoria]:
    """Retorna a lista de todas as categorias cadastradas para o sistema.
    
    Segurança de Sessão: Consolida os objetos em uma lista estável na memória,
    permitindo que a IA ou a interface consumam os dados com a sessão fechada.
    """
    comando = select(Categoria).order_by(Categoria.nome)

    with Session(engine) as db:
        return list(db.scalars(comando).all())


def editar_categoria(engine, categoria_id: int, novo_nome: str, descricao: str) -> bool:
    """Modifica o nome de uma categoria existente de forma segura.
    
    Aplica a higienização do Pydantic antes de salvar a alteração no banco.
    """
    if not isinstance(categoria_id, int) or isinstance(categoria_id, bool):
        print("\n[Erro de Edição]: O ID da categoria precisa ser um número inteiro válido.")
        return False

    with Session(engine) as db:
        categoria = db.get(Categoria, categoria_id)
        
        if not categoria:
            print(f"\n[Erro de Edição]: Categoria com ID {categoria_id} não localizada.")
            return False

        try:
            # 1. Passa o novo nome pelo Pydantic para validar tamanho e strings vazias
            # Se você usar um validador genérico de string/nome, ele limpa espaços extras aqui
            dados_validados = CategoriaSchema(nome=novo_nome, descricao=descricao)
            
            # 2. Aplica o nome higienizado no objeto do banco
            categoria.nome = dados_validados.nome
            categoria.descricao = dados_validados.descricao
            db.commit()
            print(f"Categoria ID {categoria_id} atualizada com sucesso para '{dados_validados.nome}'!")
            return True
            
        except ValidationError as e:
            print("\n[Erro de Validação na Edição da Categoria]:")
            for erro in e.errors():
                print(f" -> Campo '{erro['loc'][0]}': {erro['msg']}")
            return False



