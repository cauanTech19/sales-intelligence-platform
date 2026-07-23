import streamlit as st
import io
from contextlib import redirect_stdout
from categoria import (
    cadastrar_categoria,
    listar_categorias,
    buscar_categoria,
    editar_categoria,
    desativar_categoria  
)
from app import inicializar_banco

engine = inicializar_banco()

def renderizar_categoria():
    st.title("🗂️ Gerenciamento de Categorias")
    
    tab_listar, tab_editar, tab_desativar = st.tabs([
        "Listar e Cadastrar", 
        "Editar Categoria", 
        "Desativar Categoria"  # Nome da aba atualizado
    ])
    
    # --- ABA 1: LISTAR E CADASTRAR ---
    with tab_listar:
        col_lista, col_cadastro = st.columns([1.2, 1.0])
        with col_lista:
            st.subheader("Categorias Ativas")
            categorias = listar_categorias(engine)
            if categorias:
                dados_tabela = [
                    {"ID": c.id, "Nome": c.nome, "Descrição": c.descricao or "Sem descrição"}
                    for c in categorias
                ]
                st.dataframe(dados_tabela, width="stretch", hide_index=True)
            else:
                st.info("Nenhuma categoria ativa encontrada.")
                

        with col_cadastro:
            st.subheader("Nova Categoria")
            with st.form("form_cadastro_categoria"):
                nome_cat = st.text_input("Nome da Categoria:")
                desc_cat = st.text_area("Descrição (Opcional):")
                btn_cadastrar = st.form_submit_button("Cadastrar Categoria", type="primary")
                
                if btn_cadastrar:
                    if not nome_cat.strip():
                        st.error("O nome da categoria não pode ficar vazio.")
                    else:
                        f = io.StringIO()
                        with redirect_stdout(f):
                            sucesso = cadastrar_categoria(engine, nome_cat, desc_cat)
                        if sucesso:
                            st.success(f"Categoria '{nome_cat}' adicionada!")
                            st.rerun()
                        else:
                            st.error("Erro ao cadastrar. Nome duplicado ou inválido.")

    # --- ABA 2: EDITAR CATEGORIA ---
    with tab_editar:
        st.subheader("Modificar Informações da Categoria")
        busca_id = st.text_input("Digite o ID da categoria para editar:", key="id_edicao_cat")
        
        if busca_id:
            if not busca_id.isdigit():
                st.error("Insira um número de ID válido.")
            else:
                cat = buscar_categoria(engine, int(busca_id))
                if cat:
                    st.info(f"Modificando: **{cat.nome}**")
                    with st.form("form_edicao_categoria"):
                        novo_nome = st.text_input("Nome da Categoria:", value=cat.nome)
                        nova_desc = st.text_area("Descrição:", value=cat.descricao or "")
                        btn_salvar = st.form_submit_button("Salvar Alterações", type="primary")
                        
                        if btn_salvar:
                            f = io.StringIO()
                            with redirect_stdout(f):
                                sucesso = editar_categoria(engine, cat.id, novo_nome, nova_desc)
                            if sucesso:
                                st.success("Categoria atualizada com sucesso!")
                                st.rerun()
                            else:
                                st.error("Erro na validação dos dados.")
                else:
                    st.error("Categoria ativa não encontrada com este ID.")

    # --- ABA 3: DESATIVAR CATEGORIA (SUBSTITUINDO A ANTIGA EXCLUSÃO) ---
    with tab_desativar:
        st.subheader("Desativação Lógica de Categoria")
        st.warning("O sistema impedirá a desativação se houver produtos ATIVOS dependendo desta categoria.")
        
        id_desativar = st.text_input("Digite o ID da categoria para desativar:", key="id_desativar_cat")
        
        if id_desativar:
            if not id_desativar.isdigit():
                st.error("Insira um número de ID válido.")
            else:
                cat_para_desativar = buscar_categoria(engine, int(id_desativar))
                
                if cat_para_desativar:
                    st.error(f"Deseja realmente desativar a categoria **{cat_para_desativar.nome}**?")
                    
                    if st.button("Confirmar Desativação", type="primary", key="btn_confirma_desat"):
                        f = io.StringIO()
                        with redirect_stdout(f):
                            sucesso = desativar_categoria(engine, cat_para_desativar.id)
                        
                        retorno_console = f.getvalue()
                        
                        if sucesso:
                            st.success(f"Categoria '{cat_para_desativar.nome}' desativada com sucesso!")
                            st.rerun()
                        else:
                            st.error("Desativação Bloqueada!")
                            st.text(retorno_console)
                else:
                    st.error("Categoria ativa não encontrada com o ID informado.")