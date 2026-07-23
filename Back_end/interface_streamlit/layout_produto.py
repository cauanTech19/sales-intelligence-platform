import streamlit as st
import io
from contextlib import redirect_stdout
from produto import cadastrar_produto, listar_produtos, buscar_produto, editar_produto, alterar_preco, atualizar_estoque
from app import inicializar_banco

engine = inicializar_banco()

def renderizar_produto():
    st.title("📦 Gerenciamento de Produtos")

    # Criando abas para não tumultuar a tela do usuário
    aba_visualizar, aba_cadastrar, aba_movimentar, aba_edicao = st.tabs([
        "Visualizar Estoque", 
        "Cadastrar Novo", 
        "Movimentações e Preços",
        "Buscar e Editar Produtos"
    ])

    # ----------------------------------------------------
    # ABA 1: VISUALIZAR PRODUTOS
    # ----------------------------------------------------
    with aba_visualizar:
        st.subheader("Estoque Atual")
        
        # Checkbox para o usuário escolher se quer ver itens desativados/históricos
        mostrar_inativos = st.checkbox("Mostrar produtos desativados")
        apenas_ativos = not mostrar_inativos
        
        produtos = listar_produtos(engine, apenas_ativos=apenas_ativos)
        
        if not produtos:
            st.info("Nenhum produto cadastrado ou ativo encontrado.")
        else:
            # Montando uma tabela bonita para o e-commerce
            dados_tabela = []
            for p in produtos:
                dados_tabela.append({
                    "ID": p.id,
                    "Nome": p.nome,
                    "Descrição": p.descricao if p.descricao else "-",
                    "Preço Custo (R$)": f"{p.preco_custo:.2f}",
                    "Preço Venda (R$)": f"{p.preco_venda:.2f}",
                    "Estoque": p.quantidade_estoque,
                    "Categoria ID": p.categoria_id,
                    "Status": "🟢 Ativo" if p.ativo else "🔴 Inativo"
                })
            
            st.dataframe(dados_tabela, width="stretch")

    # ----------------------------------------------------
    # ABA 2: CADASTRAR NOVO PRODUTO
    # ----------------------------------------------------
    with aba_cadastrar:
        st.subheader("Adicionar Produto ao Catálogo")
        
        with st.form("form_cadastro_produto", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                nome = st.text_input("Nome do Produto *")
                preco_custo = st.number_input("Preço de Custo (R$) *", min_value=0.0, step=0.10, format="%.2f")
                quantidade_estoque = st.number_input("Quantidade Inicial em Estoque *", min_value=0, step=1)
                
            with col2:
                categoria_id = st.number_input("ID da Categoria *", min_value=1, step=1)
                preco_venda = st.number_input("Preço de Venda (R$) *", min_value=0.0, step=0.10, format="%.2f")
                descricao = st.text_area("Descrição do Produto (Opcional)", placeholder="Detalhes, especificações técnicas, etc.")
                
            botao_cadastrar = st.form_submit_button("Finalizar Cadastro")
            
            if botao_cadastrar:
                if not nome.strip():
                    st.error("O campo 'Nome do Produto' é obrigatório.")
                else:
                    # Como suas funções usam 'print()', vamos capturar o retorno Booleano
                    sucesso = cadastrar_produto(
                        engine=engine,
                        nome=nome,
                        descricao=descricao if descricao.strip() else None,
                        preco_venda=preco_venda,
                        preco_custo=preco_custo,
                        quantidade_estoque=quantidade_estoque,
                        categoria_id=categoria_id
                    )
                    
                    if sucesso:
                        st.success(f"Produto '{nome}' cadastrado com sucesso no banco de dados!")
                    else:
                        st.error("Erro ao cadastrar. Verifique os logs do console para ver qual regra do Pydantic ou do Banco foi violada.")

    # ----------------------------------------------------
    # ABA 3: MOVIMENTAÇÕES E PREÇOS
    # ----------------------------------------------------
    with aba_movimentar:
        st.subheader("Ações Rápidas de Estoque e Finanças")
        
        # Buscamos a lista atualizada para preencher os seletores
        produtos_validos = listar_produtos(engine, apenas_ativos=True)
        
        if not produtos_validos:
            st.warning("Cadastre produtos primeiro para liberar as opções de movimentação.")
        else:
            # Cria um dicionário prático para o usuário selecionar por Nome, mas o código usar o ID
            dict_produtos = {f"ID {p.id} - {p.nome}": p for p in produtos_validos}
            produto_selecionado_str = st.selectbox("Selecione o Produto:", list(dict_produtos.keys()))
            prod = dict_produtos[produto_selecionado_str]
            
            st.divider()
            
            # Dividindo a tela em duas ações independentes
            col_estoque, col_preco = st.columns(2)
            
            with col_estoque:
                st.markdown("#### 📦 Entrada / Saída de Estoque")
                st.metric(label="Estoque Atual", value=prod.quantidade_estoque)
                
                tipo_mov = st.radio("Tipo de operação:", ["Entrada (Compra/Reposição)", "Saída (Venda/Ajuste)"], horizontal=True)
                qtd = st.number_input("Quantidade de itens:", min_value=1, step=1)
                
                # Se for saída, manda o valor negativo para a sua função
                valor_movimentado = qtd if "Entrada" in tipo_mov else -qtd
                
                if st.button("Confirmar Movimentação"):
                    if atualizar_estoque(engine, prod.id, valor_movimentado):
                        st.success("Estoque atualizado!")
                        st.rerun() # Recarrega a página para atualizar os números na tela
                    else:
                        st.error("A operação falhou. (Estoque não pode ficar negativo).")
                        
            with col_preco:
                st.markdown("#### 💰 Atualizar Valores de Venda/Custo")
                st.write(f"Preço de Custo atual: **R$ {prod.preco_custo:.2f}**")
                st.write(f"Preço de Venda atual: **R$ {prod.preco_venda:.2f}**")
                
                novo_custo = st.number_input("Novo Preço de Custo (R$):", min_value=0.0, value=prod.preco_custo, step=0.10, format="%.2f")
                novo_venda = st.number_input("Novo Preço de Venda (R$):", min_value=0.0, value=prod.preco_venda, step=0.10, format="%.2f")
                
                if st.button("Salvar Preço"):
                    if alterar_preco(engine, prod.id, novo_preco_venda=novo_venda, novo_preco_custo=novo_custo):
                        st.success("Preços alterados com sucesso!")
                        st.rerun()
                    else:
                        st.error("Operação Recusada. Verifique se a margem de lucro não ficou negativa.")
            
    with aba_edicao:
        st.subheader("Buscar e Modificar Cadastro de Produto")

        # Força o campo a aceitar e retornar apenas INTEIRO (step=1 e min_value=0)
        busca_id = st.number_input("Digite o ID do produto para buscar:", min_value=0, step=1, value=0)

        prod = None

        # Se o usuário digitou um ID maior que 0
        if busca_id > 0:
            # Passa explicitamente como int(busca_id)
            prod = buscar_produto(engine, int(busca_id))

            if prod:
                st.write("---")
                st.success(f"📦 **Produto Localizado:** {prod.nome} (ID: {prod.id})")
                
                # Formulário blindado para edição cadastral
                with st.form("form_edicao_produto"):
                    st.write("### 📝 Alterar Informações Cadastrais")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        novo_nome = st.text_input("Nome do Produto:", value=prod.nome)
                        nova_categoria = st.number_input("ID da Categoria:", value=int(prod.categoria_id), min_value=1, step=1)

                    with col2:
                        nova_descricao = st.text_area("Descrição:", value=prod.descricao or "")
                    
                    btn_salvar_edicao = st.form_submit_button("Salvar Modificações", type="primary")
                    
                    if btn_salvar_edicao:
                        dados_novos = {
                            "nome": novo_nome,
                            "descricao": nova_descricao if nova_descricao.strip() else None,
                            "categoria_id": int(nova_categoria)
                        }
                        
                        f = io.StringIO()
                        with redirect_stdout(f):
                            sucesso = editar_produto(engine, prod.id, dados_novos)
                        
                        if sucesso:
                            st.success("Cadastro atualizado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Falha ao salvar alterações. Verifique as regras de negócio no console.")
            else:
                st.error("Produto ativo não encontrado com o ID informado.")