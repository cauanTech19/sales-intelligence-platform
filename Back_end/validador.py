from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationError

class ClienteSchema(BaseModel):
    """Schema de validação para os dados de entrada de um Cliente.

    Esta classe utiliza o Pydantic v2 para garantir a tipagem correta,
    sanitizar entradas textuais e aplicar regras de negócio brasileiras
    para os campos de CPF e Telefone.

    Attributes:
        nome (str): Nome do cliente (mínimo de 3 caracteres pós-strip).
        cpf (str): CPF do cliente (será limpo para conter apenas 11 números).
        email (EmailStr): E-mail do cliente, validado sob as normas da RFC 5322.
        endereco (str | None): Endereço opcional do cliente.
        telefone (str | None): Telefone opcional (será limpo para 10 ou 11 dígitos).
    """
    nome: str = Field(..., min_length=3)
    cpf: str
    email: EmailStr
    endereco: str | None = None  
    telefone: str | None = None

    @field_validator('nome', 'endereco', 'telefone', 'cpf', mode='before')
    @classmethod
    def fazer_strip_strings(cls, valor: str) -> str:
        """Remove espaços em branco sobressalentes nas pontas das strings.

        Roda em modo 'before', agindo diretamente nos dados brutos enviados.
        """
        if isinstance(valor, str):
            return valor.strip()
        return valor

    @field_validator('nome', 'email', 'cpf', mode='before')
    @classmethod
    def validar_dados_vazios(cls, valor: str) -> str:
        """Garante que os campos obrigatórios não recebam tipos inválidos ou textos vazios.

        Args:
            valor (str): O dado que está sendo validado.
            info: O contexto do Pydantic contendo metadados como o 'field_name'.

        Returns:
            str: A string limpa e validada.

        Raises:
            ValueError: Se o valor não for uma string ou se a string estiver vazia.
        """
        # 1. Checa se o argumento NÃO é uma string
        if not isinstance(valor, str):
            raise ValueError("Os campos precisa ser um texto válido.")
        
        # 2. Agora que temos certeza que é str, fazemos o strip e checamos se está vazio
        valor_limpo = valor.strip()
        if not valor_limpo:  
            raise ValueError("O campo não pode ficar vazio.")
            
        return valor_limpo
    
    @field_validator('telefone')
    @classmethod
    def validar_telefone(cls, valor: str) -> str | None:
        """Sanitiza o número de telefone e valida o tamanho padrão nacional.

        Remove caracteres de máscara como '(', ')', '-' e espaços. Aceita apenas
        formatos com 10 dígitos (fixo com DDD) ou 11 dígitos (celular com DDD).

        Raises:
            ValueError: Se o telefone contiver letras ou tamanho inválido.
        """
        if valor is None or valor == "":
            return None

        telefone_limpo = (
            valor.replace("(", "")
            .replace(")", "")
            .replace("-", "")
            .replace(" ", "")
        )

        if not telefone_limpo.isdigit():
            raise ValueError("O telefone deve conter apenas números.")

        if len(telefone_limpo) not in [10, 11]:
            raise ValueError("O telefone precisa ter 10 (fixo) ou 11 (celular) dígitos com o DDD.")

        return telefone_limpo
    
    @field_validator('cpf')
    @classmethod
    def limpar_e_validar_cpf(cls, valor: str) -> str:
        """Sanitiza a string do CPF e valida se ela possui exatamente 11 dígitos.

        Remove pontos e traços, checando se a string resultante é puramente numérica.

        Raises:
            TypeError: Se o CPF não for recebido como texto.
            ValueError: Se contiver letras ou não possuir 11 dígitos.
        """
        if not isinstance(valor, str):
            raise TypeError("O CPF precisa ser uma string.")
            
        cpf_limpo = valor.replace(".", "").replace("-", "").strip()
        
        if not cpf_limpo.isdigit():
            raise ValueError("O CPF deve conter apenas números.")
        if len(cpf_limpo) != 11:
            raise ValueError("O CPF precisa ter exatamente 11 números.")
            
        return cpf_limpo