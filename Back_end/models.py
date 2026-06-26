from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from datetime import datetime
from app import inicializar_banco
from zoneinfo import ZoneInfo

class Base(DeclarativeBase):
    ...


class Cliente(Base):
    """Modelo ORM que representa a tabela 'cliente' no banco de dados.

    Mapeia os atributos do objeto Python diretamente para as colunas do SQL.
    """
    __tablename__ = 'cliente'

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    telefone : Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    endereco:  Mapped[str | None] = mapped_column(String(100), nullable=True)
    data_cadastro: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo"))
    )    
    cpf:  Mapped[str] = mapped_column(String(14), unique=True, nullable=False)
    ativo: Mapped[bool] = mapped_column(default=True)



class Produto(Base):
    """Modelo ORM que representa a tabela 'produto' no banco de dados.
    
    Responsável pelo catálogo de itens e controle estrito de estoque.
    """
    __tablename__ = 'produto'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Em produção, para moedas, costuma-se usar Numeric, mas para o seu escopo
    # de IA e análise ágil, o Float atende perfeitamente o processamento matemático.
    preco_venda: Mapped[float] = mapped_column(Float, nullable=False)
    preco_custo: Mapped[float] = mapped_column(Float, nullable=False)
    
    quantidade_estoque: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
        
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

    categoria_id: Mapped[int] = mapped_column(Integer, ForeignKey('categoria.id'), nullable=False)
    categoria_objeto: Mapped["Categoria"] = relationship("Categoria", back_populates="produtos")

    @property
    def margem_lucro(self) -> float:
        """Propriedade utilitária para calcular o lucro bruto por unidade nas análises."""
        return self.preco_venda - self.preco_custo


class Categoria(Base):
    """Modelo ORM que representa a tabela de categorias de forma dinâmica no sistema."""
    __tablename__ = 'categoria'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

    produtos: Mapped[list["Produto"]] = relationship("Produto", back_populates="categoria_objeto")




try:
    engine = inicializar_banco()
    Base.metadata.create_all(engine)
except Exception:
    print("O sistema não pôde ser iniciado porque o banco de dados está indisponível.")
    exit(1)

