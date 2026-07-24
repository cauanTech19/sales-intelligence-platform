import streamlit as st
from app import inicializar_banco
from sqlalchemy.orm import Session
import pandas as pd
from cliente import (
    cadastrar_cliente,
    buscar_cliente,
    editar_cliente,
    desativar_cliente,
    reativar_cliente, 
    buscar_cliente_inativo
)
from models import Cliente 

engine = inicializar_banco()

def renderizar_cliente():
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
        
        # Carrega direto na tela de forma reativa, sem precisar de clique manual (estilo dashboard)
        with Session(engine) as session:
            # Filtrando apenas os que estão ativos (ajuste o nome do atributo se for diferente, ex: 'ativo' ou 'status')
            clientes_ativos = session.query(Cliente).filter(Cliente.ativo == True).all()
            
            if clientes_ativos:
                dados = [
                    {
                        "ID": c.id,
                        "Nome": c.nome,
                        "CPF": c.cpf,
                        "E-mail": c.email,
                        "Telefone": c.telefone or "Não informado",
                        "Endereço": c.endereco or "Não informado"
                    }
                    for c in clientes_ativos
                ]
                df_ativos = pd.DataFrame(dados)
                st.dataframe(df_ativos, width="stretch", hide_index=True)
            else:
                st.info("Nenhum cliente ativo encontrado.")
        
    with aba_buscar_editar:
        st.subheader("Buscar Cliente")
        busca = st.text_input("Digite o ID (número) ou CPF:")
        
        if busca:
            id_ou_cpf = int(busca) if busca.isdigit() else busca
            cliente = buscar_cliente(engine, id_ou_cpf)
        
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
                            
                            # Executa sua função original
                            sucesso = editar_cliente(engine, cliente.id, dados_novos)  
                            
                            if sucesso:
                                st.success("Cliente atualizado com sucesso!")
                                st.rerun()
                            else:
                                st.error("Erro ao atualizar o cliente. Verifique os dados fornecidos.")
                    
                st.write("---")
                st.warning("⚠️ **Zona de Perigo**")
                if st.button(f"🔴 Desativar Cliente: {cliente.nome}", key="btn_desativar"):
                    desativar_cliente(engine, cliente.id)
                    st.warning("Cliente desativado com sucesso!")
                    st.rerun()
            else:
                st.error("Cliente não encontrado.")
        
    with aba_inativos:
        st.subheader("Gerenciar Clientes Inativos")
        
        col_inativos1, col_inativos2 = st.columns([1.2, 1.0])  # Ajuste fino na proporção das colunas
        
        with col_inativos1:
            st.write("#### 📋 Lista de Inativos")
            with Session(engine) as session:
                # Filtrando os inativos
                clientes_inativos = session.query(Cliente).filter(Cliente.ativo == False).all()
                
                if clientes_inativos:
                    dados_inativos = [
                        {
                            "ID": c.id,
                            "Nome": c.nome,
                            "CPF": c.cpf,
                            "E-mail": c.email
                        }
                        for c in clientes_inativos
                    ]
                    df_inativos = pd.DataFrame(dados_inativos)
                    st.dataframe(df_inativos, width="stretch", hide_index=True)
                else:
                    st.info("Nenhum cliente inativo encontrado.")
                            
        with col_inativos2:
            st.write("#### 🔍 Buscar e Reativar Cliente")
            
            busca_inativo_input = st.text_input("Digite o ID ou CPF do inativo:", key="busca_inativo")
            
            if busca_inativo_input:
                id_ou_cpf_inativo = int(busca_inativo_input) if busca_inativo_input.isdigit() else busca_inativo_input
                cliente_inativo = buscar_cliente_inativo(engine, id_ou_cpf_inativo)
                
                if cliente_inativo:
                    st.warning(f"**Inativo Localizado:** {cliente_inativo.nome} (ID: {cliente_inativo.id})")
                    
                    if st.button("🟢 Restaurar Acesso / Reativar", type="primary", key="btn_reativar_confirmar"):
                        sucesso = reativar_cliente(engine, cliente_inativo.id)
                        
                        if sucesso:
                            st.success(f"Cliente '{cliente_inativo.nome}' reativado com sucesso!")
                            st.rerun()
                        else:
                            st.error("Não foi possível reativar o cliente.")
                else:
                    st.error("Nenhum cliente INATIVO foi localizado com esses dados.")