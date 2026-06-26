import pytest
from pydantic import ValidationError
from Back_end.validador import ProdutoSchema

# ==============================================================================
# 1. TESTES DE SUCESSO (HAPPY PATH)
# ==============================================================================

def test_produto_com_dados_validos_deve_passar():
    """Garante que um produto com dados corretos seja instanciado sem erros.
    
    Verifica se o validador aplica o strip() no nome limpando espaços sobressalentes.
    """
    produto = ProdutoSchema(
        nome="   Teclado Mecânico RGB   ",  # Testando a limpeza do strip
        descricao="Teclado switch blue padrão ABNT2",
        preco_venda=250.0,
        preco_custo=150.0,
        quantidade_estoque=15,
        categoria_id=2
    )
    
    assert produto.nome == "Teclado Mecânico RGB"  # Nome deve vir limpo
    assert produto.preco_venda == 250.0
    assert produto.preco_custo == 150.0
    assert produto.quantidade_estoque == 15
    assert produto.categoria_id == 2


def test_produto_com_descricao_omitida_deve_passar():
    """Garante que a descrição seja opcional e assuma None por padrão."""
    produto = ProdutoSchema(
        nome="Mouse Gamer",
        preco_venda=120.0,
        preco_custo=60.0,
        quantidade_estoque=0,  # Estoque zero é permitido
        categoria_id=1
    )
    assert produto.descricao is None
    assert produto.quantidade_estoque == 0


# ==============================================================================
# 2. TESTES DE REGRAS DE NEGÓCIO (CENÁRIOS DE FALHA)
# ==============================================================================

def test_produto_com_nome_vazio_deve_retornar_erro():
    """Garante que strings vazias sejam barradas pelo min_length=1."""
    with pytest.raises(ValidationError) as exc_info:
        ProdutoSchema(
            nome="", 
            preco_venda=10.0, 
            preco_custo=5.0, 
            categoria_id=1
        )
    
    assert "String should have at least 1 character" in str(exc_info.value)


@pytest.mark.parametrize("preco_venda_invalido", [0.0, -10.50])
def test_preco_venda_menor_ou_igual_a_zero_deve_retornar_erro(preco_venda_invalido):
    """Garante que o preco_venda seja estritamente maior que zero (gt=0.0)."""
    with pytest.raises(ValidationError) as exc_info:
        ProdutoSchema(
            nome="Produto Teste", 
            preco_venda=preco_venda_invalido, 
            preco_custo=5.0, 
            categoria_id=1
        )
    
    assert "Input should be greater than 0" in str(exc_info.value)


@pytest.mark.parametrize("preco_custo_invalido", [0.0, -5.0])
def test_preco_custo_menor_ou_igual_a_zero_deve_retornar_erro(preco_custo_invalido):
    """Garante que o preco_custo seja estritamente maior que zero (gt=0.0)."""
    with pytest.raises(ValidationError) as exc_info:
        ProdutoSchema(
            nome="Produto Teste", 
            preco_venda=10.0, 
            preco_custo=preco_custo_invalido, 
            categoria_id=1
        )
    
    assert "Input should be greater than 0" in str(exc_info.value)


def test_quantidade_estoque_negativa_deve_retornar_erro():
    """Garante que a quantidade de estoque nunca fique negativa (ge=0)."""
    with pytest.raises(ValidationError) as exc_info:
        ProdutoSchema(
            nome="Produto Teste", 
            preco_venda=10.0, 
            preco_custo=5.0, 
            quantidade_estoque=-1, 
            categoria_id=1
        )
    
    assert "Input should be greater than or equal to 0" in str(exc_info.value)


@pytest.mark.parametrize("categoria_invalida", [0, -5])
def test_categoria_id_invalida_deve_retornar_erro(categoria_invalida):
    """Garante que o ID da categoria seja um inteiro positivo válido (gt=0)."""
    with pytest.raises(ValidationError) as exc_info:
        ProdutoSchema(
            nome="Produto Teste", 
            preco_venda=10.0, 
            preco_custo=5.0, 
            categoria_id=categoria_invalida
        )
    
    assert "Input should be greater than 0" in str(exc_info.value)


# ==============================================================================
# 3. TESTE DE VALIDAÇÃO CUSTOMIZADA: MARGEM DE LUCRO
# ==============================================================================

def test_preco_venda_menor_que_preco_custo_deve_retornar_erro_de_margem():
    """Garante que o validador personalizado barre prejuízos (venda < custo)."""
    with pytest.raises(ValidationError) as exc_info:
        ProdutoSchema(
            nome="Skate Pro", 
            preco_venda=350.0,   # Menor que o custo!
            preco_custo=400.0, 
            categoria_id=1
        )
    
    # Verifica se a sua mensagem customizada do raise ValueError foi disparada
    assert "O preço de venda não pode ser menor do que o preço de custo" in str(exc_info.value)