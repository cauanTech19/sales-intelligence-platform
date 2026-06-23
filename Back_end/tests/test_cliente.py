import pytest
from pydantic import ValidationError
from Back_end.validador import ClienteSchema


# ==============================================================================
# 1. TESTES DE SUCESSO (HAPPY PATH)
# ==============================================================================

def test_cliente_com_dados_validos_deve_passar():
    """Garante que dados válidos criam o objeto e aplicam as limpezas automáticas.

    Verifica se os validadores executam o strip correto de espaços nas pontas
    e a remoção de máscaras/pontuações para os campos de CPF e telefone.
    """
    cliente = ClienteSchema(
        nome="  Cauan da Paz  ",  # Espaços nas pontas para testar strip
        cpf=" 123.456.789-00 ",   # Espaços e pontuação
        email="cauan@email.com",
        endereco="  Rua das Flores, 123  ",
        telefone=" (11) 99999-5555 "
    )
    
    assert cliente.nome == "Cauan da Paz"
    assert cliente.cpf == "12345678900"  # Salva limpo
    assert cliente.email == "cauan@email.com"
    assert cliente.endereco == "Rua das Flores, 123"
    assert cliente.telefone == "11999995555"  # Salva limpo


def test_cliente_com_campos_opcionais_vazios_ou_nulos_deve_passar():
    """Garante que os campos de endereço e telefone podem ser omitidos, vazios ou nulos.

    Verifica se o validador aceita valores nulos e se converte strings vazias
    de telefone de forma segura para None, respeitando a regra de negócio.
    """
    cliente_nulo = ClienteSchema(
        nome="Cauan Justino",
        cpf="12345678900",
        email="cauan@email.com",
        endereco=None,
        telefone=None
    )
    assert cliente_nulo.endereco is None
    assert cliente_nulo.telefone is None

    cliente_vazio = ClienteSchema(
        nome="Cauan Justino",
        cpf="12345678900",
        email="cauan@email.com",
        endereco="",
        telefone=""
    )
    assert cliente_vazio.endereco == ""
    assert cliente_vazio.telefone is None  # O validador do telefone converte "" para None


# ==============================================================================
# 2. TESTES DE CAMPOS OBRIGATÓRIOS E VALIDAÇÃO DE STRINGS VAZIAS
# ==============================================================================

@pytest.mark.parametrize("campo_invalido, tipo_esperado", [
    ({"nome": 123, "cpf": "12345678900", "email": "teste@email.com"}, "nome"),
    ({"nome": "Cauan", "cpf": 12345678900, "email": "teste@email.com"}, "cpf"),
    ({"nome": "Cauan", "cpf": "12345678900", "email": True}, "email"),
])
def test_campos_obrigatorios_com_tipos_errados_devem_retornar_erro(campo_invalido, tipo_esperado):
    """Garante que passar tipos diferentes de string acione o ValueError customizado.

    Args:
        campo_invalido (dict): Dicionário de dados contendo um dos campos com tipo incorreto.
        tipo_esperado (str): Nome do campo que deve falhar na validação de tipo.
    """
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(**campo_invalido)
    
    # Vasculha a lista de erros do Pydantic para achar a sua mensagem customizada do 'validar_dados_vazios'
    mensagens_de_erro = [erro['msg'] for erro in exc_info.value.errors()]
    trecho_esperado = "Os campos precisa ser um texto válido."
    
    assert any(trecho_esperado in msg for msg in mensagens_de_erro)


@pytest.mark.parametrize("campo_invalido, tipo_esperado", [
    ({"nome": "", "cpf": "12345678900", "email": "teste@email.com"}, "nome"),
    ({"nome": "Cauan", "cpf": "", "email": "teste@email.com"}, "cpf"),
    ({"nome": "Cauan", "cpf": "12345678900", "email": ""}, "email"),
])
def test_campos_obrigatorios_nulos_devem_retornar_erro(campo_invalido, tipo_esperado):
    """Garante que o envio de strings vazias nos campos obrigatórios lance erro.

    Args:
        campo_invalido (dict): Dicionário contendo um dos campos obrigatórios vazio.
        tipo_esperado (str): Nome do campo que deve disparar o erro de obrigatoriedade.
    """
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(**campo_invalido)
    
    # Vasculha a lista de erros do Pydantic para achar a sua mensagem customizada do 'validar_dados_vazios'
    mensagens_de_erro = [erro['msg'] for erro in exc_info.value.errors()]
    trecho_esperado = "O campo não pode ficar vazio."
    
    assert any(trecho_esperado in msg for msg in mensagens_de_erro)


def test_tamanho_minimo_do_nome_pelo_field():
    """Garante que nomes menores que 3 caracteres sejam barrados pelo Field(..., min_length=3).

    Verifica se o comportamento do erro nativo em inglês do Pydantic é mantido
    quando o Schema é instanciado isoladamente sem a camada de tradução externa.
    """
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(nome="Ab", cpf="12345678900", email="teste@email.com")
    
    # Como chamamos o Schema direto, o Pydantic responde com o erro nativo dele em inglês
    assert "String should have at least 3 characters" in str(exc_info.value)


# ==============================================================================
# 3. TESTES DE REGRAS DE NEGÓCIO: CPF
# ==============================================================================

@pytest.mark.parametrize("cpf_invalido, erro_esperado", [
    ("123456789", "precisa ter exatamente 11 números"),       # Curto demais
    ("1234567890123", "precisa ter exatamente 11 números"),   # Longo demais
    ("123.456.789-AB", "deve conter apenas números"),         # Letras misturadas
])
def test_validacoes_de_regra_do_cpf(cpf_invalido, erro_esperado):
    """Garante que CPFs fora do padrão brasileiro lancem erros explicativos em PT-BR.

    Args:
        cpf_invalido (str): Strings contendo estruturas e formatos incorretos de CPF.
        erro_esperado (str): Trecho da mensagem de erro personalizada definida no validador.
    """
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(nome="Cauan", cpf=cpf_invalido, email="teste@email.com")
    
    assert erro_esperado in str(exc_info.value)


# ==============================================================================
# 4. TESTES DE REGRAS DE NEGÓCIO: TELEFONE
# ==============================================================================

@pytest.mark.parametrize("telefone_invalido, erro_esperado", [
    ("1199999", "precisa ter 10 (fixo) ou 11 (celular) dígitos"),         # Faltando números
    ("1199999999999", "precisa ter 10 (fixo) ou 11 (celular) dígitos"),   # Números demais
    ("(11) 99999-99AA", "deve conter apenas números"),                   # Letras no telefone
])
def test_validacoes_de_regra_do_telefone(telefone_invalido, erro_esperado):
    """Garante que formatos de telefones errados sejam devidamente filtrados e bloqueados.

    Args:
        telefone_invalido (str): Números de telefone fora do padrão ou com caracteres ilegais.
        erro_esperado (str): Mensagem de erro que descreve a quebra da regra de telefonia nacional.
    """
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(nome="Cauan", cpf="12345678900", email="teste@email.com", telefone=telefone_invalido)
    
    assert erro_esperado in str(exc_info.value)


# ==============================================================================
# 5. TESTE DE VALIDAÇÃO NATIVA DO EMAIL (EmailStr)
# ==============================================================================

def test_validacao_nativo_de_email_do_pydantic():
    """Garante que o EmailStr do Pydantic barre estruturas que não possuem e-mail válido.

    Avalia o comportamento padrão da biblioteca contra strings mal formatadas que
    não contêm o caractere essencial arroba (@) ou que violam as especificações da RFC.
    """
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(nome="Cauan", cpf="12345678900", email="cauan_sem_arroba.com")
    
    # O EmailStr nativo joga essa frase em inglês quando falta a arroba
    assert "value is not a valid email address" in str(exc_info.value)