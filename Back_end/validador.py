from pydantic import BaseModel, EmailStr, Field, field_validator, ValidationError, model_validator

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
    nome: str = Field(..., min_length=3, max_length=100)
    cpf: str
    email: EmailStr
    endereco: str | None = None  
    telefone: str | None = None

    # 1. VALIDADOR DE HIGIENIZAÇÃO (Unificado e inteligente)
    @field_validator('nome', 'endereco', 'telefone', 'cpf', mode='before')
    @classmethod
    def higienizar_e_verificar_vazio(cls, valor: str, info) -> str:
        """Faz o strip automático e garante que campos obrigatórios não fiquem vazios."""
        # Se o campo opcional vier como None, deixa passar para o Pydantic tratar
        if valor is None:
            return valor
            
        if not isinstance(valor, str):
            return valor
            
        valor_limpo = valor.strip()
        
        # Se for string mas ficou vazia pós-strip nos campos obrigatórios
        if valor_limpo == "" and info.field_name in ['nome', 'email', 'cpf']:
            raise ValueError("O campo não pode ficar vazio ou conter apenas espaços.")
            
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
        if valor is None:
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
            ValueError: Se o CPF não for recebido como texto.
            ValueError: Se contiver letras ou não possuir 11 dígitos.
        """            
        cpf_limpo = valor.replace(".", "").replace("-", "").strip()
        
        if not cpf_limpo.isdigit():
            raise ValueError("O CPF deve conter apenas números.")
        
        if len(cpf_limpo) != 11:
            raise ValueError("O CPF precisa ter exatamente 11 números.")
            
        return cpf_limpo



class ProdutoSchema(BaseModel):
    """Schema de validação para criação e atualização de produtos.
    
    Aplica as regras de negócio estritas antes de permitir a persistência no banco.
    """
    # 1. Nome obrigatório (Pydantic garante por não ter valor padrão) e limpa espaços
    nome: str = Field(..., min_length=1, max_length=100)
    descricao: str | None = Field(None, max_length=255)
    
    # 2. Preço de venda maior que zero (gt = greater than / maior que)
    preco_venda: float = Field(..., gt=0.0)
    preco_custo: float = Field(..., gt=0.0)
    
    # 3. Quantidade de estoque nunca pode ficar negativa (ge = greater or equal / maior ou igual)
    quantidade_estoque: int = Field(0, ge=0)
    
    # 4. Produto deve pertencer a uma categoria (ID inteiro válido)
    categoria_id: int = Field(..., gt=0)

    # Validador extra para higienizar o nome (remover espaços extras nas pontas)
    @field_validator('nome')
    @classmethod
    def limpar_nome(cls, nome: str) -> str:
        return nome.strip()

    # Validação customizada avançada: Margem de lucro 
    @model_validator(mode='after')
    def verificar_preco(self) -> ProdutoSchema:
        # Se o preco_custo já foi validado e estiver disponível nos dados informados
        if self.preco_venda < self.preco_custo:
            raise ValueError("O preço de venda não pode ser menor do que o preço de custo (margem de lucro negativa).")
        return self


class CategoriaSchema(BaseModel):
    nome: str = Field(..., min_length=3, max_length=50)
    descricao: str = Field(..., max_length=255)