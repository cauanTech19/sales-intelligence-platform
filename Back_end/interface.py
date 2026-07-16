import streamlit as st
from app import inicializar_banco
from sqlalchemy.orm import Session
import io
from contextlib import redirect_stdout
from cliente import (

    cadastrar_cliente,
    listar_cliente,
    buscar_cliente,
    editar_cliente,
    desativar_cliente,
    listar_clientes_inativos,
    reativar_cliente, 
    buscar_cliente_inativo
)
from models import Base, Cliente


try:
    engine = inicializar_banco()
    Base.metadata.create_all(engine)
except Exception:
    print("O sistema não pôde ser iniciado porque o banco de dados está indisponível.")
    exit(1)

st.sidebar.title("Dados de clientes")
opcao_menu = st.sidebar.radio(
    "Pesquisa:",
    ["Gestão de Clientes", "Produtos"]
)

if opcao_menu == "Gestão de Clientes":
    st.title("Controle e Cadastro de Clientes")

    aba_cadastrar, aba_listar, aba_buscar_editar, aba_inativos = st.tabs([
        "Cadastrar",
        "Listar ativos",
        "Buscar e Editar ",
        "Clientes Inativos/Reativar",
    ])

    with aba_cadastrar:
        st.subheader("Cadastrar Novo Cliente")

        with st.form("form_cadastro_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)

            with col1:
                nome = st.text_input("Nome Completo:")
                cpf = st.text_input("CPF (Apenas números ou formatado):")
                email = st.text_input("E-mail:")
            
            with col2:
                telefone = st.text_input("Telefone (DDD + Número)")
                endereco = st.text_input("Endereço Completo:")
            
            btn_enviar = st.form_submit_button("Salvar Cadastro", type="primary")

            if btn_enviar:
                # Chama a sua função cadastrar_cliente passando os inputs da tela
                sucesso = cadastrar_cliente(
                    engine, 
                    nome=nome, 
                    cpf=cpf, 
                    email=email, 
                    endereco=endereco if endereco else None, 
                    telefone=telefone if telefone else None
                )
                if sucesso:
                    st.success(f"Cliente '{nome}' cadastrado com sucesso!")
                else:
                    st.error("Falha na validação dos dados. Verifique as mensagens no terminal ou corrija os campos.")


    with aba_listar:        
        st.subheader("Clientes Ativos")
        if st.button("Carregar Lista"):
            # Captura os prints que o seu método dá no console
            f = io.StringIO()
            with redirect_stdout(f):
                listar_cliente(engine) # Seu método original!
            
            resultado_texto = f.getvalue()
            if resultado_texto.strip():
                st.text(resultado_texto) # Exibe o texto exatamente formatado como no console
            else:
                st.info("Nenhum cliente ativo encontrado.")
    
    with aba_buscar_editar:
        st.subheader("Buscar Cliente")
        busca = st.text_input("Digite o ID (número) ou CPF:")
    
        if busca:
            id_ou_cpf = int(busca) if busca.isdigit() else busca
            cliente = buscar_cliente(engine, id_ou_cpf) # Seu método original!
            
            if cliente:
                with st.form("form_edicao_real"):
                    st.write(f"**Cliente Encontrado:** {cliente.nome} (ID: {cliente.id})")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        novo_nome = st.text_input("Nome Completo:", value=cliente.nome)
                        novo_cpf = st.text_input("CPF:", value=cliente.cpf)
                        novo_email = st.text_input("E-mail:", value=cliente.email)

                    with col2:
                        novo_tel = st.text_input("Telefone:", value=cliente.telefone or "")
                        novo_end = st.text_input("Endereço:", value=cliente.endereco or "")

                        btn_salvar = st.form_submit_button("Salvar Alterações", type="primary")
                        
                        if btn_salvar:
                            dados_novos = {
                                "nome": novo_nome,
                                "cpf": novo_cpf,
                                "email": novo_email,
                                "telefone": novo_tel if novo_tel else None,
                                "endereco": novo_end if novo_end else None
                            }
                            
                            # Captura os prints de sucesso ou de erro do Pydantic na edição
                            f = io.StringIO()
                            with redirect_stdout(f):
                                sucesso = editar_cliente(engine, cliente.id, dados_novos)  
                            
                            retorno_console = f.getvalue()
                            if sucesso:
                                st.success(retorno_console)
                                st.rerun()  # Recarrega a tela para atualizar os dados mostrados no topo!
                            else:
                                st.error(retorno_console)
                
                # O Botão de Desativar fica aqui fora, pois não faz parte do formulário de edição
                st.write("---")
                st.warning("⚠️ **Zona de Perigo**")
                if st.button(f"🔴 Desativar Cliente: {cliente.nome}", key="btn_desativar"):
                    f = io.StringIO()
                    with redirect_stdout(f):
                        desativar_cliente(engine, cliente.id)  # Seu método original!
                    st.warning(f.getvalue())
            else:
                st.error("Cliente não encontrado.")
    

    with aba_inativos:
        st.subheader("Gerenciar Clientes Inativos")
        
        col_inativos1, col_inativos2 = st.columns(2)
        
        # Coluna 1: Apenas lista quem está fora do sistema
        with col_inativos1:
            st.write("#### 📋 Lista de Inativos")
            if st.button("Carregar Clientes Inativos", key="btn_carregar_inativos"):
                f = io.StringIO()
                with redirect_stdout(f):
                    listar_clientes_inativos(engine)  # Seu método original!
                
                resultado_texto = f.getvalue()
                if resultado_texto.strip():
                    st.text(resultado_texto)
                else:
                    st.info("Nenhum cliente inativo encontrado.")
                        
        # Coluna 2: Busca o inativo específico e dá a opção de reativar
        with col_inativos2:
            st.write("#### 🔍 Buscar e Reativar Cliente")
            
            # Input aceita ID (número) ou CPF (texto)
            busca_inativo_input = st.text_input("Digite o ID ou CPF do inativo:", key="busca_inativo")
            
            if busca_inativo_input:
                # Sanitiza se é ID ou CPF
                id_ou_cpf_inativo = int(busca_inativo_input) if busca_inativo_input.isdigit() else busca_inativo_input
                
                # Seu método original de busca específica de inativos!
                cliente_inativo = buscar_cliente_inativo(engine, id_ou_cpf_inativo)
                
                if cliente_inativo:
                    st.warning(f"**Inativo Localizado:** {cliente_inativo.nome} (ID: {cliente_inativo.id})")
                    
                    # Só exibe o botão de reativar se o cliente for encontrado e estiver inativo
                    if st.button("🟢 Restaurar Acesso / Reativar", type="primary", key="btn_reativar_confirmar"):
                        f = io.StringIO()
                        with redirect_stdout(f):
                            sucesso = reativar_cliente(engine, cliente_inativo.id)  # Seu método original!
                        
                        retorno_console = f.getvalue()
                        if sucesso:
                            st.success(retorno_console)
                            st.rerun()  # Recarrega para limpar o estado e atualizar as listas
                        else:
                            st.error(retorno_console)
                else:
                    st.error("Nenhum cliente INATIVO foi localizado com esses dados.")