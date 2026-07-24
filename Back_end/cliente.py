from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import String, select
from validador import ClienteSchema, ValidationError
from sqlalchemy.exc import IntegrityError
from models import Cliente, engine


def cadastrar_cliente(engine, nome: str, cpf: str, email: str, endereco: str = None, telefone: str = None) -> None:
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
            return True

    except ValidationError as e:
        print("\n[Erro de Validação]:")
        
        traducoes = {
            "string_too_short": "O campo deve conter pelo menos 3 caracteres.",
            "missing": "Este campo é obrigatório.",
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
            
            # 2. Se for um ValueError vindo dos seus validadores (CPF ou Telefone)
            elif tipo_erro == "value_error":
                # Remove o prefixo "Value error, " que o Pydantic adiciona automaticamente
                mensagem = mensagem.replace("Value error, ", "")
            
            if campo == "email" and ("email" in tipo_erro or "email" in erro['msg'].lower()):
                mensagem = "O formato do e-mail é inválido. Use o padrão: usuario@dominio.com"
                
            print(f" -> Campo '{campo}': {mensagem}")
            
        return False

    # ==============================================================================
    # TRATAMENTO DE DUPLICIDADE (CPF UNIQUE)
    # ==============================================================================
    except IntegrityError as e:
        erro_msg = str(e).lower()
        
        print(f"\n[Erro de Integridade no Banco]: Não foi possível cadastrar '{nome}'.")
        
        # 1. Verifica se o problema foi a restrição UNIQUE do CPF
        if "unique constraint failed" in erro_msg and "cpf" in erro_msg:
            print(f" -> O CPF '{cpf}' já está vinculado a outro usuário no sistema.")
            
        # 2. Verifica se o problema foi o NOT NULL do telefone ou outro campo
        elif "not null constraint failed" in erro_msg:
            # Extrai ou indica qual coluna falhou
            print(" -> Erro: Uma coluna obrigatória recebeu um valor nulo (None). Verifique os campos opcionais.")
            print(f" -> Detalhe técnico: {e.orig}") # e.orig mostra o erro limpo do sqlite
            
        # 3. Caso seja qualquer outro IntegrityError que não mapeamos
        else:
            print(f" -> Erro inesperado de integridade: {e.orig}")
            
        return False


def listar_cliente(engine) -> None:
    """Busca e exibe no console a listagem de todos os clientes cadastrados.

    Utiliza a otimização 'yield_per' para carregar os dados em blocos gerenciáveis.
    """
    comando = select(Cliente).where(Cliente.ativo == True).execution_options(yield_per=2000)

    with Session(engine) as db:
        resultado = db.scalars(comando)

        for lin in resultado:
            print(f"ID: {lin.id}\nNome: {lin.nome}")


def buscar_cliente(engine, identificador: int | str) -> Cliente | None:
    """Busca um cliente de forma extremamente rápida por ID ou por CPF.

    Aproveita os índices automáticos do banco de dados (B-Tree) para garantir
    uma busca com complexidade de tempo altamente eficiente (O(log n) ou O(1)).

    Args:
        engine: O Engine ativo do SQLAlchemy para comunicação com o banco.
        identificador (int | str): O ID (inteiro) ou o CPF (string) do cliente.

    Returns:
        Cliente | None: O objeto Cliente se for encontrado, ou None se não existir.
    """

    if isinstance(identificador, bool):
        return None

    with Session(engine) as db:
        # Cenário 1: Se o identificador for um número inteiro, busca pela Chave Primária
        if isinstance(identificador, int):
            cliente = db.get(Cliente, identificador)
            if cliente and cliente.ativo:
                return cliente
            return None

        # Cenário 2: Se for uma string, faz a busca pelo campo CPF
        elif isinstance(identificador, str):
            # Sanitiza a string caso o usuário envie o CPF com pontos ou traços
            cpf_limpo = identificador.replace(".", "").replace("-", "").strip()
            
            comando = select(Cliente).where(Cliente.cpf == cpf_limpo, Cliente.ativo == True)
            return db.scalars(comando).first()
        
        return None
    

def editar_cliente(engine, cliente_id: int, dados_atualizados: dict) -> bool:
    """Atualiza os dados de um cliente ativo, localizando-o via ID (O(1)).

    Regra de Negócio: Se o cliente estiver inativo (Soft Delete), a alteração 
    é bloqueada para preservar o histórico de auditoria e dados do sistema.

    Args:
        engine: O Engine ativo do SQLAlchemy.
        cliente_id (int): O ID único do cliente que será editado.
        dados_atualizados (dict): Dicionário contendo os campos a serem alterados.

    Returns:
        bool: True se o cliente foi atualizado com sucesso; 
        False se não foi encontrado ou se estiver inativo.
    """

    if not isinstance(cliente_id, int) or isinstance(cliente_id, bool):
        print(f"[Erro de Tipo] O ID fornecido deve ser um número inteiro. Recebido: {cliente_id} ({type(cliente_id).__name__})")
        return False
    

    with Session(engine) as db:
        # 1. Localiza o cliente imediatamente em O(1) pelo mapa de identidade
        cliente = db.get(Cliente, cliente_id)
        
        if not cliente:
            print(f"[Erro de Edição] Cliente com ID {cliente_id} não encontrado.")
            return False
        
        # 2. NOVA REGRA: Impede a edição se o cliente estiver inativo
        if not cliente.ativo:
            print(f"[Bloqueio de Segurança] Não é permitido editar o cliente '{cliente.nome}' (ID: {cliente_id}) porque ele está INATIVO no sistema.")
            return False
        
        # 3. Reconstrói os dados mesclando o estado atual com as novas alterações
        dados_finais = {
            "nome": dados_atualizados.get("nome", cliente.nome),
            "cpf": dados_atualizados.get("cpf", cliente.cpf),
            "email": dados_atualizados.get("email", cliente.email),
            "endereco": dados_atualizados.get("endereco", cliente.endereco),
            "telefone": dados_atualizados.get("telefone", cliente.telefone)
        }
        
        try:
            # 4. Valida a alteração de forma robusta com o Pydantic v2
            schema_validado = ClienteSchema(**dados_finais)
            
            # 5. Aplica as mudanças higienizadas no modelo do banco
            cliente.nome = schema_validado.nome
            cliente.cpf = schema_validado.cpf
            cliente.email = schema_validado.email
            cliente.endereco = schema_validado.endereco
            cliente.telefone = schema_validado.telefone
            
            # 6. Salva no banco de dados de forma extremamente rápida
            db.commit()
            print(f"Cliente {cliente.nome} atualizado com sucesso!")
            return True
            
        except ValidationError as e:
            print(f"[Erro de Validação na Edição]: {e}")
            return False

def desativar_cliente(engine, cliente_id: int) -> bool:
    """Realiza a exclusão lógica (Soft Delete) do cliente no sistema.

    Em vez de apagar o registro fisicamente do banco de dados, o que corromperia 
    o histórico para análises de dados futuras, este método apenas altera a 
    flag 'ativo' para False. A busca do registro utiliza a Chave Primária (O(1)).

    Args:
        engine: O Engine ativo do SQLAlchemy.
        cliente_id (int): O ID único do cliente que será desativado.

    Returns:
        bool: True se o cliente foi encontrado e desativado, False caso contrário.
    """

    if not isinstance(cliente_id, int) or isinstance(cliente_id, bool):
        print(f"[Erro de Tipo] O ID fornecido deve ser um número inteiro. Recebido: {cliente_id} ({type(cliente_id).__name__})")
        return False
    

    with Session(engine) as db:
        # 1. Localiza o cliente em O(1) pelo mapa de identidade do ORM
        cliente = db.get(Cliente, cliente_id)
        
        if not cliente:
            print(f"[Aviso] Cliente com ID {cliente_id} não encontrado para exclusão.")
            return False
        
        # 2. Verifica se o cliente já está inativo para evitar commits desnecessários
        if not cliente.ativo:
            print(f"[Aviso] O cliente {cliente.nome} (ID: {cliente_id}) já se encontra inativo.")
            return True
        
        # 3. Altera o estado do cliente (Exclusão Lógica)
        cliente.ativo = False
        
        # 4. Persiste a alteração no banco de dados de forma extremamente rápida
        db.commit()
        print(f"Cliente {cliente.nome} desativado com sucesso do sistema!")
        return True


def listar_clientes_inativos(engine) -> None:
    """Busca e exibe no console a listagem de todos os clientes inativos.

    Utiliza uma abordagem Pythonica de espiar o primeiro registro para evitar
    contadores manuais, mantendo a performance de paginação com yield_per.
    """
    comando = select(Cliente).where(Cliente.ativo == False).execution_options(yield_per=2000)

    with Session(engine) as db:
        resultado = db.scalars(comando)
        
        primeiro_cliente = next(resultado, None)
        
        if primeiro_cliente is None:
            print("Nenhum cliente inativo encontrado no sistema.")
            return

        print("\n--- LISTA DE CLIENTES INATIVOS ---")
        
        print(f"ID: {primeiro_cliente.id} | Nome: {primeiro_cliente.nome} | CPF: {primeiro_cliente.cpf}")
        
        for cliente in resultado:
            print(f"ID: {cliente.id} | Nome: {cliente.nome} | CPF: {cliente.cpf}")



def buscar_cliente_inativo(engine, identificador: int | str) -> Cliente | None:
    """Busca um cliente ESPECÍFICO que foi desativado (Soft Delete) por ID ou CPF.

    Aproveita os índices B-Tree do banco de dados para garantir alta performance
    (O(1) ou O(log n)) ao auditar ou tentar reativar contas antigas.

    Args:
        engine: O Engine ativo do SQLAlchemy.
        identificador (int | str): O ID (inteiro) ou o CPF (string) do cliente inativo.

    Returns:
        Cliente | None: O objeto Cliente se ele estiver inativo, ou None caso contrário.
    """
    # Validação estrita para o caso de ID (evita que o booleano True passe como 1)
    if isinstance(identificador, bool):
        return None

    with Session(engine) as db:
        # Cenário 1: Busca específica por ID (Chave Primária)
        if isinstance(identificador, int):
            cliente = db.get(Cliente, identificador)
            # Só retorna se o cliente existir E estiver inativo
            if cliente and not cliente.ativo:
                return cliente
            return None

        # Cenário 2: Busca específica por CPF (Índice Único)
        elif isinstance(identificador, str):
            cpf_limpo = identificador.replace(".", "").replace("-", "").strip()
            
            # Filtra estritamente pelo CPF e pela flag ativo=False na árvore do banco
            comando = select(Cliente).where(Cliente.cpf == cpf_limpo, Cliente.ativo == False)
            return db.scalars(comando).first()
        
        return None


def reativar_cliente(engine, identificador) -> bool:
    """Reativa um cliente que sofreu exclusão lógica (Soft Delete).

    Localiza o registro na base de inativos usando o ID (O(1)) ou CPF (O(log n)).
    Se encontrado, a flag 'ativo' é restaurada para True, devolvendo o cliente
    às consultas operacionais do sistema.

    Args:
        engine: O Engine ativo do SQLAlchemy.
        identificador (int | str): O ID ou o CPF do cliente a ser reativado.

    Returns:
        bool: True se o cliente foi reativado com sucesso;
        False se o cliente não foi encontrado na base de inativos.
    """

    if not isinstance(identificador, int):
        raise TypeError("O id precisa ser um número inteiro")
    
    # 1. Utiliza o método específico de busca de inativos que você criou
    cliente = buscar_cliente_inativo(engine, identificador)
    
    if not cliente:
        print(f"[Erro de Reativação] Nenhum cliente INATIVO foi encontrado com o identificador: {identificador}")
        return False

    # Como o 'buscar_cliente_inativo' roda dentro de sua própria sessão e fecha,
    # precisamos abrir uma nova sessão para persistir a alteração do objeto no banco
    with Session(engine) as db:
        # Puxa o objeto para a sessão atual para rastreamento de mudanças
        cliente_para_reativar = db.get(Cliente, cliente.id)
        
        # 2. Restaura o estado de atividade do cliente
        cliente_para_reativar.ativo = True
        
        # 3. Salva a alteração de volta no banco de dados
        db.commit()
        print(f"Cliente '{cliente_para_reativar.nome}' (ID: {cliente_para_reativar.id}) reativado com sucesso no sistema!")
        return True
    


