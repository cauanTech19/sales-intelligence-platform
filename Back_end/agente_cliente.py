import os
from google import genai
from google.genai import types
from cliente import cadastrar_cliente
from app import inicializar_banco

CHAVE_DO_GEMINI = "SUA_CHAVE_AQUI"

# 2. Inicializa o cliente oficial novo passando a chave de forma explícita
client = genai.Client(api_key=CHAVE_DO_GEMINI)
engine = inicializar_banco()

def ia_cadastrar_cliente(nome: str, cpf: str, email: str, endereco: str = None, telefone: str = None) -> str:
    """Executa o fluxo completo de validação e persistência de um NOVO cliente no banco de dados.

    Args:
        nome: Nome completo do cliente.
        cpf: CPF do cliente (apenas números ou formatado).
        email: Endereço de e-mail válido.
        endereco: Endereço residencial (opcional).
        telefone: Número de telefone/WhatsApp (opcional).
    """
    # Como o seu método 'cadastrar_cliente' printa na tela os erros do Pydantic ou IntegrityError,
    # nós podemos capturar esses prints redirecionando o stdout, ou simplesmente deixar o fluxo rodar.
    # Para o agente, o ideal é retornar uma string confirmando que a tentativa foi enviada ao banco:
    sucesso = cadastrar_cliente(engine, nome=nome, cpf=cpf, email=email, endereco=endereco, telefone=telefone)
    if sucesso:
        return f"Sucesso: O cliente {nome} foi cadastrado com sucesso no banco de dados."
    
    return f"Erro: Não foi possível cadastrar o cliente {nome}. Houve uma violação nas regras de validação ou o CPF já existe no sistema. Verifique os alertas no console."


config = types.GenerateContentConfig(
    system_instruction=(
        "Você é o assistente virtual oficial do sistema CRM. Você tem acesso direto ao banco "
        "de dados de clientes através de ferramentas de código. Use-as sempre que o usuário "
        "solicitar cadastros, buscas, edições ou exclusões."
        ),
    tools=[ia_cadastrar_cliente],
    temperature=0.0
)

# 5. Cria o chat utilizando o modelo padrão atual (gemini-2.5-flash)
chat = client.chats.create(model="gemini-2.5-flash", config=config)

print("Sistemas iniciados com o novo SDK! Faça sua pergunta ao Agente de Estoque:")

# 6. Executa o teste
resposta = chat.send_message("Mano, cadastra o João, cpf 444.555.666-77, email joao@gmail.com Ah, ele mora na Rua das Flores, 10")

print("\nResposta da IA:")
print(resposta.text)