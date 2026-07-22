import streamlit as st
from pydantic import ValidationError
from sqlalchemy.orm import Session
from app import inicializar_banco  
from auth_admin import autenticar, criar_usuario_admin_inicial, verificar_existem_usuarios
from layout_cliente import renderizar_cliente
from layout_produto import renderizar_produto
from layout_categoria import renderizar_categoria
from layout_movimentacao import renderizar_movimentacao
from layout_vendas import renderizar_vendas
from layout_dashboard import renderizar_dashboard



engine = inicializar_banco()
# 1. Configuração da página (DEVE SER O PRIMEIRO COMANDO STREAMLIT)
st.set_page_config(page_title="E-commerce Admin", layout="wide")

# 2. Injeção de CSS Customizado
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
        [data-testid="stSidebar"] {
            background-color: #111625;
        }
    </style>
""", unsafe_allow_html=True)

# 3. Inicialização dos Estados da Sessão
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
    st.session_state["usuario_id"] = None
    st.session_state["usuario_nome"] = ""
    st.session_state["usuario_cargo"] = ""

if "menu_atual" not in st.session_state:
    st.session_state.menu_atual = "Início"

# 4. Gerenciamento de Autenticação e Roteamento
with Session(engine) as session:

    # -------------------------------------------------------------
    # CENÁRIO A: PRIMEIRO ACESSO (CRIAÇÃO DO ADMIN MASTER)
    # -------------------------------------------------------------
    if not verificar_existem_usuarios(session):
        st.warning("⚠️ **Primeiro Acesso Detectado!** Cadastre o Administrador Principal.")
        
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            st.subheader("👑 Cadastro do Admin Master")
            with st.form("form_primeiro_admin"):
                nome = st.text_input("Nome Completo")
                email = st.text_input("E-mail corporativo")
                senha = st.text_input("Senha Master", type="password")
                confirmar_senha = st.text_input("Confirme a Senha", type="password")
                
                btn_criar = st.form_submit_button("Inicializar Sistema", use_container_width=True, type="primary")

                if btn_criar:
                    if senha != confirmar_senha:
                        st.error("As senhas não coincidem.")
                    else:
                        try:
                            admin = criar_usuario_admin_inicial(session, nome, email, senha)
                            if admin:
                                st.success(f"Admin {admin.nome} cadastrado! Faça seu login.")
                                st.rerun()
                            else:
                                st.error("Este e-mail já está em uso.")
                        except ValidationError as e:
                            msg_erro = e.errors()[0]["msg"].replace("Value error, ", "")
                            st.error(f"Erro na validação: {msg_erro}")

    # -------------------------------------------------------------
    # CENÁRIO B: TELA DE LOGIN (NÃO AUTENTICADO)
    # -------------------------------------------------------------
    elif not st.session_state["autenticado"]:
        col1, col2, col3 = st.columns([1, 1.2, 1])
        
        with col2:
            st.markdown("<h2 style='text-align: center;'>Acesso ao PDV Admin</h2>", unsafe_allow_html=True)
            
            with st.form("form_login"):
                email_input = st.text_input("E-mail")
                senha_input = st.text_input("Senha", type="password")
                btn_entrar = st.form_submit_button("Entrar", use_container_width=True, type="primary")

                if btn_entrar:
                    try:
                        usuario = autenticar(session, email_input, senha_input)
                        if usuario:
                            st.session_state["autenticado"] = True
                            st.session_state["usuario_id"] = usuario.id
                            st.session_state["usuario_nome"] = usuario.nome
                            st.session_state["usuario_cargo"] = usuario.cargo
                            st.rerun()
                        else:
                            st.error("E-mail ou senha incorretos (ou usuário inativo).")
                    except ValidationError as e:
                        msg_erro = e.errors()[0]["msg"].replace("Value error, ", "")
                        st.warning(f"Entrada inválida: {msg_erro}")

    # -------------------------------------------------------------
    # CENÁRIO C: SISTEMA LIBERADO (USUÁRIO LOGADO)
    # -------------------------------------------------------------
    else:
        # Título da Sidebar
        st.sidebar.markdown("<h2 style='text-align: center; color: white;'>PDV Admin</h2>", unsafe_allow_html=True)
        st.sidebar.markdown("---")

        # Botões de Navegação
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

        if st.sidebar.button("Dashboard", type="primary" if st.session_state.menu_atual == "Dashboard" else "secondary"):
            st.session_state.menu_atual = "Dashboard"
            st.rerun()

        # Rodapé da Barra Lateral com Dados Dinâmicos do Usuário e Logout
        st.sidebar.markdown("---")
        st.sidebar.caption(f"👤 **Usuário:** {st.session_state['usuario_nome']}")
        st.sidebar.caption(f"🛡️ **Cargo:** {st.session_state['usuario_cargo'].upper()}")
        st.sidebar.caption("Desenvolvido por Cauan Justino")
        
        st.sidebar.markdown(" ")
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["usuario_id"] = None
            st.session_state["usuario_nome"] = ""
            st.session_state["usuario_cargo"] = ""
            st.rerun()

        # Roteamento de Conteúdo Principal
        if st.session_state.menu_atual == "Início":
            st.write(f"# Bem-vindo ao painel, {st.session_state['usuario_nome']}! 🚀")
            st.markdown("---")
            with st.expander("🔍 Entenda o Funcionamento do Projeto"):
                st.markdown("""
                ### 💻 Arquitetura do Sistema
                Este projeto foi estruturado seguindo boas práticas de desenvolvimento de software:
                
                * **Camada de Persistência:** Banco de dados gerenciado via SQLAlchemy ORM (v2.0) com controle estrito de transações.
                * **Camada de Validação:** Motores Pydantic barram dados inconsistentes antes de chegarem ao banco.
                * **Camada de Visão:** Interface reativa dividida em módulos isolados no Streamlit.
                * **Autenticação Segura:** Criptografia de senhas via SHA-256 e controle de sessão por perfil.
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

        elif st.session_state.menu_atual == "Dashboard":
            renderizar_dashboard()