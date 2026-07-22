from typing import Optional
from sqlalchemy.orm import Session
from models import Usuario
from validador import UsuarioLoginSchema, UsuarioCreateSchema, AlterarSenhaSchema

def autenticar(session: Session, email: str, senha: str) -> Optional[Usuario]:
    """
    Valida os dados de login e autentica o usuário.
    Retorna a instância do Usuario se correto e ativo, ou None se falhar.
    Lança ValueError se os dados de entrada forem inválidos (Pydantic).
    """
    # Valida schema (se falhar, lança ValueError naturalmente)
    dados = UsuarioLoginSchema(email=email, senha=senha)

    usuario = (
        session.query(Usuario)
        .filter(Usuario.email == dados.email)
        .first()
    )

    if usuario and usuario.ativo and usuario.verificar_senha(dados.senha):
        return usuario

    return None


def criar_usuario_admin_inicial(session: Session, nome: str, email: str, senha: str) -> Optional[Usuario]:
    """
    Cria o admin inicial.
    Retorna o Usuario criado, ou None se o e-mail já existir.
    Lança ValueError se a validação do Pydantic falhar.
    """
    dados = UsuarioCreateSchema(nome=nome, email=email, senha=senha)

    # Checa duplicidade
    if session.query(Usuario).filter(Usuario.email == dados.email).first():
        return None

    admin = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=Usuario.gerar_hash_senha(dados.senha),
        cargo="admin",
        ativo=True,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)

    return admin


def alterar_senha(session: Session, usuario_id: int, senha_atual: str, nova_senha: str, confirmar_nova_senha: str) -> bool:
    """
    Valida e altera a senha. Retorna True em caso de sucesso e False para erros de negócio.
    Lança ValueError em erros de schema/confirmação.
    """
    dados = AlterarSenhaSchema(
        senha_atual=senha_atual,
        nova_senha=nova_senha,
        confirmar_nova_senha=confirmar_nova_senha,
    )

    usuario = session.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario or not usuario.verificar_senha(dados.senha_atual):
        return False

    usuario.senha_hash = Usuario.gerar_hash_senha(dados.nova_senha)
    session.commit()

    return True


def verificar_existem_usuarios(session: Session) -> bool:
    """
    Verifica se já existe pelo menos um usuário cadastrado no banco de dados.
    Retorna True se houver usuários, False se o banco estiver vazio.
    """
    return session.query(Usuario).first() is not None