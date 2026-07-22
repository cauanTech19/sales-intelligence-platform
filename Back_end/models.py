from sqlalchemy import String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from datetime import datetime
from app import inicializar_banco
from zoneinfo import ZoneInfo
from enum import Enum
import hashlib


class StatusVenda(str, Enum):
    PENDENTE = 'PENDENTE'
    CONCLUIDA = 'CONCLUIDA'
    CANCELADA = 'CANCELADA'

class FormaPagamento(str,Enum):
    PIX = 'PIX'
    CREDITO = 'CREDITO'
    DEBITO = 'DEBITO'

class StatusPagamento(str, Enum):
    PENDENTE = "PENDENTE"
    APROVADO = "APROVADO"
    RECUSADO = "RECUSADO"
    ESTORNADO = "ESTORNADO"


class TipoMovimentacao(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"
    AJUSTE = "AJUSTE"



class Base(DeclarativeBase):
    ...

class Usuario(Base):
    """Modelo ORM que representa a tabela 'usuario' no banco de dados."""

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    cargo: Mapped[str] = mapped_column(String(50), default="admin")  # Ex: 'admin', 'vendedor'
    ativo: Mapped[bool] = mapped_column(default=True)
    data_cadastro: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

    @staticmethod
    def gerar_hash_senha(senha: str) -> str:
        """Gera um hash SHA-256 seguro para a senha."""
        return hashlib.sha256(senha.encode("utf-8")).hexdigest()

    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha digitada corresponde ao hash salvo."""
        return self.senha_hash == hashlib.sha256(senha.encode("utf-8")).hexdigest()
    

class Cliente(Base):
    """Modelo ORM que representa a tabela 'cliente' no banco de dados.

    Mapeia os atributos do objeto Python diretamente para as colunas do SQL.
    """
    __tablename__ = 'cliente'

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    data_criacao: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo"))
    )

    produtos: Mapped[list["Produto"]] = relationship("Produto", back_populates="categoria_objeto")



class Venda(Base):
    __tablename__ = "vendas"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Relacionamento com Cliente (Chave Estrangeira)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("cliente.id"), nullable=False)
    
    # Dados da movimentação
    data_venda: Mapped[datetime] = mapped_column (DateTime, default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")))
    valor_total: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[StatusVenda] = mapped_column(String, default=StatusVenda.PENDENTE, nullable=False)
    forma_pagamento: Mapped[FormaPagamento] = mapped_column(String, nullable=False)

    # cascade="all, delete-orphan" garante que se uma venda sumir, os itens dela somem junto
    itens: Mapped[list["ItemVenda"]] = relationship(back_populates="venda", cascade="all, delete-orphan")



class ItemVenda(Base):
    __tablename__ = "itens_venda"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    venda_id: Mapped[int] = mapped_column(ForeignKey("vendas.id"), nullable=False)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"), nullable=False)
    
    # Guardamos a foto do momento: a quantidade vendida e o preço praticado na hora
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[float] = mapped_column(Float, nullable=False)

    # Relacionamentos
    venda: Mapped["Venda"] = relationship(back_populates="itens")
    produto: Mapped["Produto"] = relationship()



class Pagamento(Base):
    __tablename__ = "pagamentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Vinculação estrita com a Venda (Chave Estrangeira)
    venda_id: Mapped[int] = mapped_column(ForeignKey("vendas.id"), nullable=False)
    
    # Detalhes do fluxo financeiro
    valor: Mapped[float] = mapped_column(Float, nullable=False)
    forma_pagamento: Mapped[FormaPagamento] = mapped_column(String, nullable=False)
    status: Mapped[StatusPagamento] = mapped_column(String, default=StatusPagamento.PENDENTE, nullable=False)
    data_pagamento: Mapped[datetime] = mapped_column (DateTime, default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")))

    # Relacionamento para conseguir acessar os dados da venda direto pelo objeto pagamento (ex: pagamento.venda.cliente)
    venda: Mapped["Venda"] = relationship()



class MovimentacaoEstoque(Base):
    __tablename__ = "movimentacoes_estoque"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Vinculação com o Produto (Chave Estrangeira)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produto.id"), nullable=False)
    
    # Detalhes da movimentação
    tipo_movimentacao: Mapped[TipoMovimentacao] = mapped_column(String, nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    motivo: Mapped[str] = mapped_column(String, nullable=False) 
    data_movimentacao: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(ZoneInfo("America/Sao_Paulo")))


    # Relacionamento
    produto: Mapped["Produto"] = relationship()


try:
    engine = inicializar_banco()
    Base.metadata.create_all(engine)
except Exception:
    print("O sistema não pôde ser iniciado porque o banco de dados está indisponível.")
    exit(1)

