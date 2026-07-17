# app.py
import streamlit as st
from layout_cliente import renderizar_cliente
from layout_produto import renderizar_produto
from layout_categoria import renderizar_categoria
from layout_movimentacao import renderizar_movimentacao
from layout_vendas import renderizar_vendas

# 1. Configuração da página (deve ser o primeiro comando Streamlit)
st.set_page_config(page_title="E-commerce Admin", layout="wide")

# 2. Injeção de CSS Customizado para forçar os botões laterais a ocuparem 100% da largura
st.markdown("""
    <style>
        [data-testid="stSidebar"] .stButton>button {
            width: 100%;
            text-align: left;
            justify-content: flex-start;
            padding: 10px 15px;
            font-size: 15px;
            border-radius: 8px;
            margin-bottom: 5px;
        }
        /* Ajusta o fundo da sidebar para um tom escuro mais elegante e comercial */
        [data-testid="stSidebar"] {
            background-color: #111625;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Título/Logotipo no topo da Barra Lateral
st.sidebar.markdown("<h2 style='text-align: center; color: white;'>PDV Admin</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# 4. Inicializa o estado da página ativa no session_state (padrão é Início)
if "menu_atual" not in st.session_state:
    st.session_state.menu_atual = "Início"

# 5. Renderização dos Botões Verticais com Ícones (Emojis)
# O parâmetro 'type' muda dinamicamente para 'primary' se a página estiver selecionada
if st.sidebar.button("Início", type="primary" if st.session_state.menu_atual == "Início" else "secondary"):
    st.session_state.menu_atual = "Início"
    st.rerun()

if st.sidebar.button("Clientes", type="primary" if st.session_state.menu_atual == "Cliente" else "secondary"):
    st.session_state.menu_atual = "Cliente"
    st.rerun()

if st.sidebar.button("Produtos", type="primary" if st.session_state.menu_atual == "Produto" else "secondary"):
    st.session_state.menu_atual = "Produto"
    st.rerun()

if st.sidebar.button("Categorias", type="primary" if st.session_state.menu_atual == "Categoria" else "secondary"):
    st.session_state.menu_atual = "Categoria"
    st.rerun()

if st.sidebar.button("Movimentações", type="primary" if st.session_state.menu_atual == "Movimentação" else "secondary"):
    st.session_state.menu_atual = "Movimentação"
    st.rerun()

if st.sidebar.button("Vendas", type="primary" if st.session_state.menu_atual == "Vendas" else "secondary"):
    st.session_state.menu_atual = "Vendas"
    st.rerun()

# 6. Rodapé da Barra Lateral com informações úteis do sistema
st.sidebar.markdown("---")
st.sidebar.caption("📌 **Status:** Operacional")
st.sidebar.caption("👤 **Caixa:** Operador 01")
st.sidebar.caption("Desenvolvido por Cauan Justino")


# 7. Roteamento de Páginas (Gatilhos das suas funções originais de layout)
if st.session_state.menu_atual == "Início":
    st.write("# Bem-vindo ao painel do E-commerce 🚀")
    st.markdown("---")
    with st.expander("🔍 Entenda o Funcionamento do Projeto"):
        st.markdown("""
        ### 💻 Arquitetura do Sistema
            Bem-vindo ao painel integrado! Este projeto foi estruturado seguindo boas práticas de desenvolvimento de software:
            
            Camada de Persistência: Banco de dados gerenciado via SQLAlchemy ORM com controle estrito de transações e concorrência segura.
            Camada de Validação: Motores orientados a modelos do Pydantic barram dados inconsistentes (como valores negativos ou CPFs inválidos) antes de chegarem ao banco.
            Camada de Visão: Interface reativa dividida em módulos isolados no Streamlit para garantir alta manutenibilidade do código.
        """)    

elif st.session_state.menu_atual == "Cliente":
    renderizar_cliente() 
    
elif st.session_state.menu_atual == "Produto":
    renderizar_produto()
    
elif st.session_state.menu_atual == "Categoria":
    renderizar_categoria()
    
elif st.session_state.menu_atual == "Movimentação":
    renderizar_movimentacao()
    
elif st.session_state.menu_atual == "Vendas":
    renderizar_vendas()