import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from auth_admin import alterar_senha, autenticar, criar_usuario_admin_inicial
from models import Base


# ==========================================
# FIXTURES (CONFIGURAÇÃO DO BANCO EM MEMÓRIA)
# ==========================================
@pytest.fixture
def db_session():
    """Cria um banco de dados SQLite temporário em memória para cada teste."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session  # Executa o teste

    session.close()


# ==========================================
# TESTES: CRIAÇÃO DO ADMIN INICIAL
# ==========================================
def test_criar_admin_inicial_sucesso(db_session):
    """Garante que o admin é criado corretamente com dados válidos."""
    admin = criar_usuario_admin_inicial(
        db_session,
        nome="cauan silva",  # Testando a formatação .title() do Pydantic
        email="ADMIN@LOJA.COM",  # Testando a conversão .lower() do Pydantic
        senha="senhaSegura123",
    )

    assert admin is not None
    assert admin.id == 1
    assert admin.nome == "Cauan Silva"
    assert admin.email == "admin@loja.com"
    assert admin.cargo == "admin"
    assert admin.ativo is True


def test_criar_admin_inicial_email_duplicado_retorna_none(db_session):
    """Tenta cadastrar um segundo usuário com o mesmo e-mail e deve retornar None."""
    criar_usuario_admin_inicial(
        db_session, "Admin Um", "admin@loja.com", "senha123"
    )

    # Segunda tentativa com o mesmo e-mail
    segundo_admin = criar_usuario_admin_inicial(
        db_session, "Admin Dois", "admin@loja.com", "outraSenha123"
    )

    assert segundo_admin is None


def test_criar_admin_inicial_pydantic_validation_error(db_session):
    """Valida se lança ValidationError para e-mail mal formatado ou senha curta."""
    # E-mail inválido
    with pytest.raises(ValidationError):
        criar_usuario_admin_inicial(
            db_session, "Admin", "email_invalido", "senha123"
        )

    # Senha com menos de 6 caracteres
    with pytest.raises(ValidationError):
        criar_usuario_admin_inicial(
            db_session, "Admin", "admin@loja.com", "123"
        )


# ==========================================
# TESTES: AUTENTICAÇÃO
# ==========================================
def test_autenticar_sucesso(db_session):
    """Autentica com sucesso um usuário ativo com credenciais corretas."""
    criar_usuario_admin_inicial(
        db_session, "Cauan", "cauan@email.com", "senha123"
    )

    usuario = autenticar(db_session, "cauan@email.com", "senha123")

    assert usuario is not None
    assert usuario.email == "cauan@email.com"


def test_autenticar_senha_incorreta_retorna_none(db_session):
    """Tenta logar com senha errada e deve retornar None."""
    criar_usuario_admin_inicial(
        db_session, "Cauan", "cauan@email.com", "senhaCorreta123"
    )

    usuario = autenticar(db_session, "cauan@email.com", "senhaErrada123")

    assert usuario is None


def test_autenticar_usuario_inexistente_retorna_none(db_session):
    """Tenta logar com e-mail que não existe no banco e deve retornar None."""
    usuario = autenticar(
        db_session, "naoexiste@email.com", "senhaQualquer123"
    )

    assert usuario is None


def test_autenticar_usuario_inativo_retorna_none(db_session):
    """Usuário com ativo=False não deve conseguir autenticar."""
    admin = criar_usuario_admin_inicial(
        db_session, "Cauan Inativo", "inativo@email.com", "senha123"
    )

    # Desativa o usuário no banco
    admin.ativo = False
    db_session.commit()

    usuario = autenticar(db_session, "inativo@email.com", "senha123")

    assert usuario is None


def test_autenticar_email_invalido_lanca_validation_error(db_session):
    """Tentar autenticar com e-mail sem @ dispara ValidationError do Pydantic."""
    with pytest.raises(ValidationError):
        autenticar(db_session, "emailSemArroba", "senha123")


# ==========================================
# TESTES: ALTERAÇÃO DE SENHA
# ==========================================
def test_alterar_senha_sucesso(db_session):
    """Altera a senha com sucesso e valida se o novo login funciona."""
    admin = criar_usuario_admin_inicial(
        db_session, "Cauan", "cauan@email.com", "senhaAntiga123"
    )

    resultado = alterar_senha(
        session=db_session,
        usuario_id=admin.id,
        senha_atual="senhaAntiga123",
        nova_senha="novaSenha456",
        confirmar_nova_senha="novaSenha456",
    )

    assert resultado is True

    # Valida se a senha antiga NÃO funciona mais
    assert autenticar(db_session, "cauan@email.com", "senhaAntiga123") is None

    # Valida se a nova senha funciona
    assert (
        autenticar(db_session, "cauan@email.com", "novaSenha456") is not None
    )


def test_alterar_senha_senha_atual_incorreta_retorna_false(db_session):
    """Tenta alterar a senha informando a senha antiga errada."""
    admin = criar_usuario_admin_inicial(
        db_session, "Cauan", "cauan@email.com", "senhaAntiga123"
    )

    resultado = alterar_senha(
        session=db_session,
        usuario_id=admin.id,
        senha_atual="senhaErradaQueTentei",
        nova_senha="novaSenha456",
        confirmar_nova_senha="novaSenha456",
    )

    assert resultado is False


def test_alterar_senha_usuario_inexistente_retorna_false(db_session):
    """Tenta alterar senha de um ID de usuário que não existe no banco."""
    resultado = alterar_senha(
        session=db_session,
        usuario_id=999,  # ID inexistente
        senha_atual="senha123",
        nova_senha="novaSenha456",
        confirmar_nova_senha="novaSenha456",
    )

    assert resultado is False


def test_alterar_senha_confirmacao_divergente_lanca_validation_error(
    db_session,
):
    """Dispara ValidationError quando 'nova_senha' e 'confirmar_nova_senha' são diferentes."""
    admin = criar_usuario_admin_inicial(
        db_session, "Cauan", "cauan@email.com", "senha123"
    )

    with pytest.raises(ValidationError):
        alterar_senha(
            session=db_session,
            usuario_id=admin.id,
            senha_atual="senha123",
            nova_senha="novaSenha123",
            confirmar_nova_senha="senhaDiferente456",  # Não coincide
        )