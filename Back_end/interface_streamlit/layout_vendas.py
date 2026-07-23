import streamlit as st
import io
from contextlib import redirect_stdout
from produto import listar_produtos 
from vendas import criar_venda, calcular_total, listar_vendas, cancelar_venda
from item import validar_e_preparar_item
from pagamento import registrar_pagamento, listar_pagamentos, cancelar_pagamento
from models import FormaPagamento, StatusVenda, StatusPagamento
from app import inicializar_banco

engine = inicializar_banco()

def renderizar_vendas():
    st.title("🛒 Módulo de Vendas & Histórico")
    
    aba_pdv, aba_historico, aba_financeiro = st.tabs(["Frente de Caixa (PDV)", "Histórico & Cancelamentos", "Financeiro"])

    # -------------------------------------------------------------------------
    # ABA 1: FRENTE DE CAIXA (PDV)
    # -------------------------------------------------------------------------
    with aba_pdv:
        if "carrinho" not in st.session_state:
            st.session_state.carrinho = []

        produtos_ativos = [p for p in listar_produtos(engine) if p.ativo]
        if not produtos_ativos:
            st.warning("Nenhum produto ativo no sistema para realizar vendas.")
        else:
            mapa_produtos = {f"{p.nome} (Estoque: {p.quantidade_estoque})": p for p in produtos_ativos}
            
            col_esq, col_dir = st.columns([1.3, 1.0])

            with col_esq:
                st.subheader("🛍️ Adicionar Produto")
                
                # 1. SELECTBOX FORA DO FORMULÁRIO (Atualiza o preço na hora!)
                prod_str = st.selectbox("Selecione o Produto:", list(mapa_produtos.keys()), key="select_pdv_prod")
                produto_selecionado = mapa_produtos[prod_str]

                # 2. FORMULÁRIO DE ADIÇÃO AO CARRINHO
                with st.form("form_add_item", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        # Exibe o preço unitário em um retângulo travado e elegante
                        st.text_input(
                            "Preço Unitário (R$):", 
                            value=f"{produto_selecionado.preco_venda:.2f}", 
                            disabled=True
                        )
                    with c2:
                        qtd = st.number_input("Quantidade:", min_value=1, max_value=produto_selecionado.quantidade_estoque if produto_selecionado.quantidade_estoque > 0 else 1, step=1, value=1)
                    
                    if st.form_submit_button("Adicionar ao Carrinho", use_container_width=True):
                        string_buffer = io.StringIO()
                        with redirect_stdout(string_buffer):
                            item_ok = validar_e_preparar_item(engine, produto_selecionado.id, qtd, produto_selecionado.preco_venda)
                        
                        if item_ok:
                            item_ok["nome_produto"] = produto_selecionado.nome
                            st.session_state.carrinho.append(item_ok)
                            st.toast(f"✅ {produto_selecionado.nome} no carrinho!")
                            st.rerun()
                        else:
                            st.error("Rejeitado pelo validador do item:")
                            st.code(string_buffer.getvalue(), language="text")

                # Listagem do carrinho
                st.subheader("📋 Itens Adicionados")
                if not st.session_state.carrinho:
                    st.info("Carrinho vazio.")
                else:
                    st.dataframe(st.session_state.carrinho, use_container_width=True, hide_index=True)
                    if st.button("🗑️ Limpar Tudo"):
                        st.session_state.carrinho = []
                        st.rerun()

            with col_dir:
                st.subheader("💳 Finalizar Transação")
                total = calcular_total(st.session_state.carrinho)
                st.metric(label="Total Geral", value=f"R$ {total:.2f}")
                
                cliente_id = st.number_input("ID do Cliente:", min_value=1, step=1, value=1)
                forma_pgto = st.selectbox("Forma de Pagamento:", options=[f.value for f in FormaPagamento])
                
                btn_fechar = st.button("🚀 Concluir Venda", type="primary", use_container_width=True, disabled=len(st.session_state.carrinho) == 0)
                
                if btn_fechar:
                    itens_puros = []
                    for item in st.session_state.carrinho:
                        itens_puros.append({
                            "produto_id": item["produto_id"],
                            "quantidade": item["quantidade"],
                            "preco_unitario": item["preco_unitario"]
                        })

                    sb_venda = io.StringIO()
                    with redirect_stdout(sb_venda):
                        sucesso = criar_venda(
                            engine=engine,
                            cliente_id=cliente_id,
                            forma_pagamento=forma_pgto,
                            itens_validados=itens_puros
                        )
                    logs_venda = sb_venda.getvalue()

                    if sucesso:
                        st.success("Transação realizada com sucesso!")
                        st.code(logs_venda, language="text")
                        st.session_state.carrinho = []
                        st.balloons()
                    else:
                        st.error("Erro ao persistir a venda no banco:")
                        st.code(logs_venda, language="text")

    # -------------------------------------------------------------------------
    # ABA 2: HISTÓRICO E CANCELAMENTOS
    # -------------------------------------------------------------------------
    with aba_historico:
        st.subheader("📜 Registro de Vendas Realizadas")
        vendas_lista = listar_vendas(engine)
        
        if not vendas_lista:
            st.info("Nenhuma venda registrada no sistema até o momento.")
        else:
            dados_tabela = []
            for v in vendas_lista:
                dados_tabela.append({
                    "ID": v.id,
                    "Data": v.data_venda.strftime("%d/%m/%Y %H:%M"),
                    "Cliente ID": v.cliente_id,
                    "Pagamento": v.forma_pagamento if hasattr(v.forma_pagamento, 'value') else v.forma_pagamento,
                    "Total": f"R$ {v.valor_total:.2f}",
                    "Status": v.status.value if hasattr(v.status, 'value') else v.status
                })
            
            st.dataframe(dados_tabela, use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🚨 Estorno e Cancelamento de Venda")
            
            with st.form("form_cancelar"):
                id_venda_cancelar = st.number_input("Digite o ID da Venda para Cancelar:", min_value=1, step=1)
                confirmar = st.checkbox("Confirmo que desejo estornar os produtos e cancelar esta venda em definitivo.")
                btn_cancelar = st.form_submit_button("Executar Cancelamento", type="primary")
                
                if btn_cancelar:
                    if not confirmar:
                        st.warning("Você precisa marcar o campo de confirmação antes de prosseguir.")
                    else:
                        sb_cancelar = io.StringIO()
                        with redirect_stdout(sb_cancelar):
                            cancelado_ok = cancelar_venda(engine, id_venda_cancelar)
                        logs_cancelar = sb_cancelar.getvalue()
                        
                        if cancelado_ok:
                            st.success(f"Venda #{id_venda_cancelar} cancelada!")
                            st.code(logs_cancelar, language="text")
                            st.rerun()
                        else:
                            st.error("Não foi possível processar o cancelamento:")
                            st.code(logs_cancelar, language="text")
    
# -------------------------------------------------------------------------
    # ABA 3: FINANCEIRO
    # -------------------------------------------------------------------------
    with aba_financeiro:
        st.subheader("💰 Registrar Pagamento")
        
        pagamentos_existentes = listar_pagamentos(engine)
        
        # 1. Mapeia TODAS as vendas que já tiveram um pagamento (mesmo que tenha sido estornado)
        vendas_com_pagamento_ids = [p.venda_id for p in pagamentos_existentes]

        # 2. Filtra APENAS vendas ativas que NUNCA foram pagas nem canceladas
        vendas_abertas = [
            v for v in listar_vendas(engine) 
            if (
                v.status != StatusVenda.CANCELADA 
                and (isinstance(v.status, str) and v.status.upper() != "CANCELADA")
                and v.id not in vendas_com_pagamento_ids
            )
        ]
        
        if not vendas_abertas:
            st.info("Nenhuma venda pendente para registrar pagamento.")
        else:
            venda_sel = st.selectbox(
                "Selecione a Venda Pendente:", 
                options=vendas_abertas, 
                format_func=lambda v: f"Venda #{v.id} - Total: R$ {v.valor_total:.2f}",
                key="select_venda_financeiro"
            )
            
            forma_pgto_venda = venda_sel.forma_pagamento if isinstance(venda_sel.forma_pagamento, str) else venda_sel.forma_pagamento.value
            valor_venda = float(venda_sel.valor_total)

            with st.form("form_pagamento"):
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.text_input("Valor a Pagar (R$):", value=f"{valor_venda:.2f}", disabled=True)
                with col_info2:
                    st.text_input("Forma de Pagamento Definida:", value=str(forma_pgto_venda), disabled=True)

                if st.form_submit_button("Confirmar Pagamento", type="primary"):
                    sb_pag = io.StringIO()
                    with redirect_stdout(sb_pag):
                        sucesso = registrar_pagamento(engine, venda_sel.id, valor_venda, forma_pgto_venda)
                    
                    if sucesso:
                        st.success("Pagamento registrado com sucesso!")
                        st.code(sb_pag.getvalue())
                        st.rerun()
                    else:
                        st.error("Falha ao registrar pagamento:")
                        st.code(sb_pag.getvalue())

        st.divider()

        # ---------------------------------------------------------------------
        # SEÇÃO DE ESTORNO DE PAGAMENTO (FILTRADO POR CLIENTE)
        # ---------------------------------------------------------------------
        st.subheader("🔍 Estorno / Cancelamento de Pagamento por Cliente")
        st.caption("Filtre pelo ID do cliente para visualizar apenas as transações dele e evitar cancelamentos indevidos.")

        col_busca, _ = st.columns([1, 1])
        with col_busca:
            cliente_id_busca = st.number_input("Informe o ID do Cliente:", min_value=1, step=1, value=1, key="input_busca_cliente_estorno")

        vendas_lista = listar_vendas(engine)

        vendas_do_cliente_ids = [v.id for v in vendas_lista if v.cliente_id == cliente_id_busca]

        # Exibe no estorno apenas os pagamentos que ainda estão ativos (não estornados)
        pagamentos_do_cliente = [
            p for p in pagamentos_existentes 
            if p.venda_id in vendas_do_cliente_ids and p.status != StatusPagamento.ESTORNADO
        ]

        if not pagamentos_do_cliente:
            st.warning(f"Nenhum pagamento ativo encontrado para o Cliente ID #{cliente_id_busca}.")
        else:
            st.info(f"Exibindo pagamentos do **Cliente #{cliente_id_busca}**:")

            with st.form("form_estorno_cliente"):
                pg_sel = st.selectbox(
                    "Selecione o Pagamento que deseja estornar:", 
                    options=pagamentos_do_cliente, 
                    format_func=lambda p: f"ID Pagamento: {p.id} | Venda #{p.venda_id} | Valor: R$ {p.valor:.2f}"
                )
                
                confirmar_estorno = st.checkbox(f"Confirmo que desejo estornar este pagamento do Cliente #{cliente_id_busca}.")
                
                if st.form_submit_button("Executar Estorno", type="primary"):
                    if not confirmar_estorno:
                        st.warning("Marque a caixa de confirmação para efetuar o estorno.")
                    else:
                        sb_est = io.StringIO()
                        with redirect_stdout(sb_est):
                            ok = cancelar_pagamento(engine, pg_sel.id)
                        
                        if ok:
                            st.success(f"Pagamento #{pg_sel.id} do Cliente #{cliente_id_busca} estornado com sucesso!")
                            st.code(sb_est.getvalue())
                            st.rerun()
                        else:
                            st.error("Erro ao processar o estorno:")
                            st.code(sb_est.getvalue())