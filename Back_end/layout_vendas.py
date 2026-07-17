import streamlit as st
import io
from contextlib import redirect_stdout
from produto import listar_produtos 
from vendas import  criar_venda, calcular_total, listar_vendas, cancelar_venda
from item import validar_e_preparar_item
from pagamento import registrar_pagamento, listar_pagamentos, cancelar_pagamento
from models import FormaPagamento, StatusVenda, StatusPagamento
from app import inicializar_banco

engine = inicializar_banco()

def renderizar_vendas():
    st.title("🛒 Módulo de Vendas & Histórico")
    
    aba_pdv, aba_historico, aba_financeiro = st.tabs(["⚡ Frente de Caixa (PDV)", "📜 Histórico & Cancelamentos", "Financeiro"])

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
                with st.form("form_add_item", clear_on_submit=True):
                    prod_str = st.selectbox("Selecione:", list(mapa_produtos.keys()))
                    produto = mapa_produtos[prod_str]
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        qtd = st.number_input("Quantidade:", min_value=1, step=1, value=1)
                    with c2:
                        preco = st.number_input("Preço Unitário (R$):", min_value=0.01, format="%.2f", value=float(produto.preco_venda))
                    
                    if st.form_submit_button("Adicionar ao Carrinho"):
                        string_buffer = io.StringIO()
                        with redirect_stdout(string_buffer):
                            item_ok = validar_e_preparar_item(engine, produto.id, qtd, preco)
                        
                        if item_ok:
                            # Injeta o nome para renderizar na tabela do Streamlit
                            item_ok["nome_produto"] = produto.nome
                            st.session_state.carrinho.append(item_ok)
                            st.toast(f"✅ {produto.nome} no carrinho!")
                            st.rerun()
                        else:
                            st.error("Rejeitado pelo validador do item:")
                            st.code(string_buffer.getvalue(), language="text")

                # Listagem do carrinho
                st.subheader("📋 Itens Adicionados")
                if not st.session_state.carrinho:
                    st.info("Carrinho vazio.")
                else:
                    st.dataframe(st.session_state.carrinho, width="stretch", hide_index=True)
                    if st.button("🗑️ Limpar Tudo"):
                        st.session_state.carrinho = []
                        st.rerun()

            with col_dir:
                st.subheader("💳 Finalizar Transação")
                total = calcular_total(st.session_state.carrinho)
                st.metric(label="Total Geral", value=f"R$ {total:.2f}")
                
                cliente_id = st.number_input("ID do Cliente:", min_value=1, step=1, value=1)
                forma_pgto = st.selectbox("Forma de Pagamento:", options=[f.value for f in FormaPagamento])
                
                btn_fechar = st.button("🚀 Concluir Venda", type="primary", width="stretch", disabled=len(st.session_state.carrinho) == 0)
                
                if btn_fechar:
                    # Higieniza o dicionário removendo chaves visuais ('nome_produto') antes de mandar pro backend
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
            
            st.dataframe(dados_tabela, width="stretch", hide_index=True)
            
            st.divider()
            st.subheader("🚨 Estorno e Cancelamento de Venda")
            
            # Form focado para executar a ação de cancelamento com segurança
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
    
    with aba_financeiro:
        st.subheader("💰 Registrar Pagamento")
        
        # Filtra vendas que ainda não estão canceladas
        vendas_abertas = [v for v in listar_vendas(engine) if v.status != StatusVenda.CANCELADA]
        
        if not vendas_abertas:
            st.info("Nenhuma venda pendente para registrar pagamento.")
        else:
            with st.form("form_pagamento"):
                venda_sel = st.selectbox("Selecione a Venda:", options=vendas_abertas, format_func=lambda v: f"Venda #{v.id} - Total: R$ {v.valor_total:.2f}")
                valor_pgto = st.number_input("Valor a Pagar (R$):", min_value=0.01, format="%.2f", value=float(venda_sel.valor_total))
                forma_pgto = st.selectbox("Forma de Pagamento:", [f.value for f in FormaPagamento])
                
                if st.form_submit_button("Confirmar Pagamento"):
                    sb_pag = io.StringIO()
                    with redirect_stdout(sb_pag):
                        sucesso = registrar_pagamento(engine, venda_sel.id, valor_pgto, forma_pgto)
                    
                    if sucesso:
                        st.success("Pagamento registrado!")
                        st.code(sb_pag.getvalue())
                        st.rerun()
                    else:
                        st.error("Falha ao registrar pagamento:")
                        st.code(sb_pag.getvalue())

        st.divider()
        st.subheader("↩️ Estorno de Pagamento")
        
        pagamentos_lista = listar_pagamentos(engine)
        if not pagamentos_lista:
            st.info("Nenhum pagamento registrado no sistema.")
        else:
            # Lista de pagamentos ativos para estorno
            pags_ativos = [p for p in pagamentos_lista if p.status != StatusPagamento.ESTORNADO]
            
            if not pags_ativos:
                st.info("Não há pagamentos disponíveis para estorno.")
            else:
                with st.form("form_estorno"):
                    pg_sel = st.selectbox("Selecione o Pagamento:", options=pags_ativos, format_func=lambda p: f"ID: {p.id} | Venda #{p.venda_id} | R$ {p.valor:.2f}")
                    
                    if st.form_submit_button("Executar Estorno"):
                        sb_est = io.StringIO()
                        with redirect_stdout(sb_est):
                            ok = cancelar_pagamento(engine, pg_sel.id)
                        
                        if ok:
                            st.success("Estorno realizado com sucesso!")
                            st.code(sb_est.getvalue())
                            st.rerun()
                        else:
                            st.error("Erro no estorno:")
                            st.code(sb_est.getvalue())