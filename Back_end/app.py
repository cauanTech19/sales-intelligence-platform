from sqlalchemy import create_engine, Engine
from sqlalchemy.exc import ArgumentError, SQLAlchemyError

def inicializar_banco(url_conexao: str = "sqlite:///storage.db") -> Engine:
    """Inicializa o Engine do SQLAlchemy e testa a conexão com o banco de dados.

    Cria uma instância do Engine e abre uma conexão temporária para garantir
     que as credenciais e a URL fornecida estão válidas.

    Args:
        url_conexao (str): A string de conexão (connection string) do banco.
            Por padrão, utiliza um banco SQLite local ('sqlite:///storage.db').

    Returns:
        Engine: O objeto Engine do SQLAlchemy pronto para ser usado pelo ORM.

    Raises:
        ArgumentError: Se a URL do banco de dados estiver mal formatada.
        SQLAlchemyError: Se houver uma falha de comunicação ou autenticação
            com o banco de dados.
    """
    try:
        # Cria o engine
        engine = create_engine(url_conexao)
        
        # Faz um "ping" no banco de dados para testar a conexão real
        with engine.connect() as conexao:
            print("[Banco de Dados] Conexão estabelecida com sucesso!")
            
        return engine

    except ArgumentError as e:
        print(f"[Erro Crítico] A URL do banco de dados está mal formatada: {e}")
        raise e  # Repassa o erro para o sistema saber que não pode continuar
    except SQLAlchemyError as e:
        print(f"[Erro Crítico] Não foi possível conectar ao banco de dados: {e}")
        raise e