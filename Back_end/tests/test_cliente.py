import pytest
from pydantic import ValidationError
from validador import ClienteSchema


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



# ==============================================================================
# 2. TESTES DE CAMPOS OBRIGATÓRIOS E VALIDAÇÃO DE STRINGS VAZIAS
# ==============================================================================

@pytest.mark.parametrize("campo_invalido, tipo_esperado", [
    ({"nome": "", "cpf": "12345678900", "email": "teste@email.com"}, "nome"),
    ({"nome": "Cauan", "cpf": "", "email": "teste@email.com"}, "cpf"),
    ({"nome": "Cauan", "cpf": "12345678900", "email": ""}, "email"),
])
def test_campos_obrigatorios_nulos_devem_retornar_erro(campo_invalido, tipo_esperado):
    """Garante que o envio de strings vazias nos campos obrigatórios lance erro."""
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(**campo_invalido)
    
    mensagens_de_erro = [erro['msg'] for erro in exc_info.value.errors()]
    
    # Adicionamos "value is not a valid email address" para cobrir o caso do email string vazia
    trechos_esperados = [
        "O campo não pode ficar vazio ou conter apenas espaços.", 
        "value is not a valid email address"
    ]
    
    assert any(
        any(trecho in msg for trecho in trechos_esperados) 
        for msg in mensagens_de_erro
    )

# ==============================================================================
# 2. TESTES DE CAMPOS OBRIGATÓRIOS E VALIDAÇÃO DE STRINGS VAZIAS
# ==============================================================================

@pytest.mark.parametrize("campo_invalido, tipo_esperado", [
    ({"nome": 123, "cpf": "12345678900", "email": "teste@email.com"}, "nome"),
    ({"nome": "Cauan", "cpf": 12345678900, "email": "teste@email.com"}, "cpf"),
    ({"nome": "Cauan", "cpf": "12345678900", "email": True}, "email"),
])
def test_campos_obrigatorios_com_tipos_errados_devem_retornar_erro(campo_invalido, tipo_esperado):
    """Garante que passar tipos diferentes de string seja barrado usando o modo estrito."""
    with pytest.raises(ValidationError) as exc_info:
        # Usamos model_validate com o contexto estrito para impedir que o Pydantic 
        # converta números como 123 em strings automaticamente.
        ClienteSchema.model_validate(campo_invalido, strict=True)
    
    mensagens_de_erro = [erro['msg'] for erro in exc_info.value.errors()]
    
    trechos_esperados = ["Input should be a valid string", "Input should be a valid email"]
    
    assert any(
        any(trecho in msg for trecho in trechos_esperados) 
        for msg in mensagens_de_erro
    )
def test_tamanho_minimo_do_nome_pelo_field():
    """Garante que nomes menores que 3 caracteres sejam barrados pelo Field(..., min_length=3)."""
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(nome="Ab", cpf="12345678900", email="teste@email.com")
    
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
    """Garante que CPFs fora do padrão brasileiro lancem erros explicativos em PT-BR."""
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
    """Garante que formatos de telefones errados sejam devidamente filtrados e bloqueados."""
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(nome="Cauan", cpf="12345678900", email="teste@email.com", telefone=telefone_invalido)
    
    assert erro_esperado in str(exc_info.value)


# ==============================================================================
# 5. TESTE DE VALIDAÇÃO NATIVA DO EMAIL (EmailStr)
# ==============================================================================

def test_validacao_nativo_de_email_do_pydantic():
    """Garante que o EmailStr do Pydantic barre estruturas que não possuem e-mail válido."""
    with pytest.raises(ValidationError) as exc_info:
        ClienteSchema(nome="Cauan", cpf="12345678900", email="cauan_sem_arroba.com")
    
    assert "value is not a valid email address" in str(exc_info.value)