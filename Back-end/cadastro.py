from datetime import datetime, date, timezone
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column, Session
from sqlalchemy import String, select
from validador import ClienteSchema, ValidationError
from app import inicializar_banco

class Base(DeclarativeBase):
    """Classe base declarativa do SQLAlchemy para o mapeamento de tabelas."""
    ...

class Cliente(Base):
    """Modelo ORM que representa a tabela 'cliente' no banco de dados.

    Mapeia os atributos do objeto Python diretamente para as colunas do SQL.
    """
    __tablename__ = 'cliente'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    telefone : Mapped[str] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    endereco:  Mapped[str] = mapped_column(String(100), nullable=True)
    data_cadastro: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc)
    )    
    cpf:  Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    ativo: Mapped[bool] = mapped_column(default=True)


# Inicialização segura do banco de dados ao carregar o módulo
try:
    engine = inicializar_banco()
    Base.metadata.create_all(engine)
except Exception:
    print("O sistema não pôde ser iniciado porque o banco de dados está indisponível.")
    exit(1)


def cadastrar_cliente(engine, nome: str, cpf: str, email: str, endereco: str, telefone: str) -> None:
    """Executa o fluxo completo de validação e persistência de um novo cliente.

    Os dados passam primeiro pelo motor de validação do ClienteSchema (Pydantic). 
    Se forem aceitos, abre-se uma sessão com o banco para salvar o registro.

    Args:
        engine: O Engine ativo do SQLAlchemy para comunicação com o banco.
        nome (str): Nome do cliente enviado pela interface.
        cpf (str): CPF enviado pela interface.
        email (str): E-mail enviado pela interface.
        endereco (str): Endereço enviado pela interface.
        telefone (str): Telefone enviado pela interface.
    """
    try:
        # 1. Tenta validar (Se der erro aqui, vai direto para o 'except')
        dados_validados = ClienteSchema(
            nome=nome,
            cpf=cpf,
            email=email,
            endereco=endereco,
            telefone=telefone
        )

        # 2. Se os dados forem válidos, salva no banco
        with Session(engine) as db:
            novo_cliente = Cliente(**dados_validados.model_dump())
            db.add(novo_cliente)
            db.commit()
            print(f"Cliente {dados_validados.nome} cadastrado com sucesso!")

    except ValidationError as e:
        print("\n[Erro de Validação]:")
        
        traducoes = {
            "string_too_short": "O campo deve conter pelo menos 3 caracteres.",
            "missing": "Este campo é obrigatório.",
            "value_error": "O valor fornecido é inválido."
        }
        
        for erro in e.errors():
            tipo_erro = erro['type']
            campo = erro['loc'][0]
            mensagem = erro['msg']
            
            if tipo_erro in traducoes:
                mensagem = traducoes[tipo_erro]
                ctx = erro.get("ctx")
                if ctx:
                    mensagem = mensagem.format(**ctx)
            
            if campo == "email" and ("email" in tipo_erro or "email" in erro['msg'].lower()):
                mensagem = "O formato do e-mail é inválido. Use o padrão: usuario@dominio.com"
                
            print(f" -> Campo '{campo}': {mensagem}")


def listar_cliente(engine) -> None:
    """Busca e exibe no console a listagem de todos os clientes cadastrados.

    Utiliza a otimização 'yield_per' para carregar os dados em blocos gerenciáveis.
    """
    comando = select(Cliente).execution_options(yield_per=2000)

    with Session(engine) as db:
        resultado = db.scalars(comando)

        for lin in resultado:
            print(f"ID: {lin.id}\nNome: {lin.nome}")


# Execução de teste
cadastrar_cliente(engine, "Paulo", "567.898.145-04", "paulo@gmail.com", "Rua dos Memes 777", "1192425555")