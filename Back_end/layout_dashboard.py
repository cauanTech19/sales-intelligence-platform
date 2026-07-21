import streamlit as st
from sqlalchemy.orm import Session
from app import inicializar_banco
from dashboards import obter_desempenho_categorias, obter_desempenho_produtos, obter_indicadores_clientes, obter_indicadores_vendas, obter_metricas_faturamento

engine = inicializar_banco()

def renderizar_dashboard():
    st.title("📊 Dashboard & Relatórios de Vendas")
    st.markdown("---")

    with Session(engine) as session:
        fat_dia, fat_mes, fat_ano = obter_metricas_faturamento(session)

        # --- CARTÕES DE MÉTRICAS (KPIs) ---
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="📅 Faturamento Hoje", 
                value=f"R$ {fat_dia:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        with col2:
            st.metric(
                label="🗓️ Faturamento do Mês", 
                value=f"R$ {fat_mes:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        with col3:
            st.metric(
                label="🚀 Faturamento do Ano", 
                value=f"R$ {fat_ano:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

        st.markdown("---")

        # --- ABAS DE DESEMPENHO DE PRODUTOS ---
        st.subheader("📦 Análise de Desempenho do Estoque")
        
        df_mais, df_menos, df_nao_vendidos = obter_desempenho_produtos(session)

        aba_top, aba_baixo, aba_encalhado = st.tabs([
            "🔥 Top 10 Mais Vendidos", 
            "📉 10 Menos Vendidos", 
            "⚠️ Produtos Não Vendidos"
        ])

        with aba_top:
            if not df_mais.empty:
                # Formatação bonita do preço
                df_mais["Preço Unitário"] = df_mais["Preço Unitário"].apply(lambda x: f"R$ {x:.2f}")
                st.dataframe(df_mais, width="stretch", hide_index=True)
            else:
                st.info("Nenhuma venda registrada para gerar o ranking dos mais vendidos.")

        with aba_baixo:
            if not df_menos.empty:
                df_menos["Preço Unitário"] = df_menos["Preço Unitário"].apply(lambda x: f"R$ {x:.2f}")
                st.dataframe(df_menos, width="stretch", hide_index=True)
            else:
                st.info("Nenhuma venda registrada para gerar o ranking dos menos vendidos.")

        with aba_encalhado:
            if not df_nao_vendidos.empty:
                df_nao_vendidos["Preço Unitário"] = df_nao_vendidos["Preço Unitário"].apply(lambda x: f"R$ {x:.2f}")
                st.warning(f"Existem **{len(df_nao_vendidos)}** produtos cadastrados que nunca foram vendidos.")
                st.dataframe(df_nao_vendidos, width="stretch", hide_index=True)
            else:
                st.success("Excelente! Todos os produtos do catálogo possuem ao menos uma venda registrada.")
    
        st.markdown("---")
        st.subheader("🏷️ Análise de Desempenho por Categoria")

        df_cat = obter_desempenho_categorias(session)

        if not df_cat.empty:
            col_cat_esq, col_cat_dir = st.columns([1.3, 1.0])

            with col_cat_esq:
                sub_col1, sub_col2 = st.columns(2)
                
                with sub_col1:
                    st.markdown("##### 📦 Mais Vendidas (Volume)")
                    df_volume = (
                        df_cat.sort_values(by="Qtd Itens Vendidos", ascending=False)
                        [["Categoria", "Qtd Itens Vendidos"]]
                    )
                    st.dataframe(df_volume, width="stretch", hide_index=True)

                with sub_col2:
                    st.markdown("##### 💰 Faturamento (R$)")
                    df_faturamento = df_cat.sort_values(by="Faturamento Total", ascending=False).copy()
                    df_faturamento["Faturamento Total"] = df_faturamento["Faturamento Total"].apply(
                        lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    )
                    st.dataframe(df_faturamento[["Categoria", "Faturamento Total"]], width="stretch", hide_index=True)

            with col_cat_dir:
                # SE TIVER APENAS 1 CATEGORIA: Mostra um Card de Métrica limpo
                if len(df_cat) == 1:
                    st.markdown("##### 🏆 Categoria Principal")
                    cat_unica = df_cat.iloc[0]
                    val_formatado = f"R$ {cat_unica['Faturamento Total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    
                    with st.container(border=True):
                        st.metric(
                            label=f"📂 {cat_unica['Categoria']}", 
                            value=val_formatado,
                            delta=f"{cat_unica['Qtd Itens Vendidos']} itens vendidos (100% da receita)"
                        )
                # SE TIVER 2 OU MAIS CATEGORIAS: Renderiza o gráfico de barras normalmente
                else:
                    st.markdown("##### 📊 Faturamento por Categoria")
                    st.bar_chart(
                        data=df_cat, 
                        x="Categoria", 
                        y="Faturamento Total", 
                        color="#2e7bcf",
                        height=240
                    )
        else:
            st.info("Nenhuma venda realizada até o momento para gerar o relatório por categoria.")


        st.markdown("---")
        st.subheader("📈 Indicadores e Comportamento de Vendas")

        df_mes, df_pgto = obter_indicadores_vendas(session)

        col_ind1, col_ind2 = st.columns([1.4, 1.0])

        # 1. Gráfico de Barras Preenchido (Jan a Dez)
        with col_ind1:
            st.markdown("##### 📅 Vendas Realizadas por Mês")
            st.bar_chart(
                data=df_mes,
                x="Mês",
                y="Qtd Vendas",
                color="#00C853"
            )

        # 2. Card Corrigido + Tabela
        with col_ind2:
            st.markdown("##### 💳 Formas de Pagamento")
            if not df_pgto.empty:
                top_pgto = df_pgto.iloc[0]
                val_formatado = f"R$ {top_pgto['total_movimentado']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                
                # Formatação limpa do card sem quebra esquisita de texto
                st.success(
                    f"🏆 **Mais Utilizada:** {top_pgto['Forma de Pagamento']}\n\n"
                    f"📊 **{top_pgto['Qtd Usos']} transações** ({val_formatado})"
                )

                df_exibicao_pgto = df_pgto[["Forma de Pagamento", "Qtd Usos"]].copy()
                st.dataframe(df_exibicao_pgto, width="stretch", hide_index=True)
            else:
                st.info("Nenhum dado de pagamento disponível.")

        st.markdown("---")
        st.subheader("👥 Indicadores de Clientes")

        df_vips, df_inativos = obter_indicadores_clientes(session)

        aba_vips, aba_inativos = st.tabs([
            "👑 Clientes VIP (Mais Compram)", 
            "⚠️ Clientes Inativos / Sem Compras"
        ])

        with aba_vips:
            if not df_vips.empty:
                # Formatação da coluna de valor para Real (R$)
                df_vips["Total Gasto"] = df_vips["Total Gasto"].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )
                st.dataframe(df_vips, width="stretch", hide_index=True)
            else:
                st.info("Nenhuma compra associada a clientes cadastrados até o momento.")

        with aba_inativos:
            if not df_inativos.empty:
                st.warning(f"Existem **{len(df_inativos)}** clientes cadastrados no sistema que ainda não realizaram nenhuma compra.")
                st.dataframe(df_inativos, width="stretch", hide_index=True)
            else:
                st.success("Excelente! Todos os clientes cadastrados na sua base possuem ao menos uma compra realizada.")