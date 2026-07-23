import streamlit as st
import io
from contextlib import redirect_stdout
from movimentacao import ajustar_estoque_manual, consultar_historico_produto
from app import inicializar_banco
from produto import listar_produtos  

engine = inicializar_banco()

def renderizar_movimentacao():
    st.title("📦 Movimentação e Auditoria de Estoque")
    st.markdown("Gerencie entradas e saídas manuais e consulte o histórico de transações com segurança transacional.")

    # 1. BUSCA E SELEÇÃO DO PRODUTO
    produtos_ativos = listar_produtos(engine, apenas_ativos=True)

    if not produtos_ativos:
        st.warning("Nenhum produto ativo encontrado no catálogo. Cadastre produtos para habilitar as movimentações.")
        return

    # Criamos um mapeamento prático: "Nome do Produto (ID: X)" -> Objeto do Produto
    opcoes_produtos = {f"{p.nome} (ID: {p.id})": p for p in produtos_ativos}
    produto_selecionado_str = st.selectbox("Selecione o Produto para Operação:", list(opcoes_produtos.keys()))
    produto_atual = opcoes_produtos[produto_selecionado_str]

    # Exibe um card com o saldo atual do produto selecionado
    st.metric(label="Saldo Atual em Estoque", value=f"{produto_atual.quantidade_estoque} unidades")

    st.divider()

    # Dividindo a tela em duas colunas: Esquerda faz a ação, Direita mostra o extrato/histórico
    col_acao, col_historico = st.columns([1.0, 1.3])

    # -------------------------------------------------------------------------
    # COLUNA 1: FORMULÁRIO DE AJUSTE MANUAL
    # -------------------------------------------------------------------------
    with col_acao:
        st.subheader("Novo Ajuste Manual")
        
        with st.form("form_ajuste_estoque", clear_on_submit=True):
            tipo_operacao = st.radio(
                "Tipo de Movimentação:",
                ["🟢 Entrada (+)", "🔴 Saída (-)"],
                horizontal=True
            )
            
            quantidade = st.number_input(
                "Quantidade de Itens:",
                min_value=1,
                step=1
            )
            
            motivo = st.text_area(
                "Motivo da Movimentação *",
                placeholder="Ex: Correção de inventário, produto danificado, reposição de fornecedor...",
                help="O motivo é obrigatório para fins de auditoria interna."
            )
            
            btn_confirmar = st.form_submit_button("Confirmar Movimentação", type="primary")
            
            if btn_confirmar:
                # Tratamento do sinal matemático baseado no rádio selecionado
                quantidade_ajustada = quantidade if "Entrada" in tipo_operacao else -quantidade
                
                if not motivo.strip():
                    st.error("Erro: Você precisa preencher o motivo do ajuste.")
                else:
                    # Captura o print do backend para tratar o erro na tela caso o estoque fosse ficar negativo
                    f = io.StringIO()
                    with redirect_stdout(f):
                        sucesso = ajustar_estoque_manual(
                            engine=engine,
                            produto_id=produto_atual.id,
                            quantidade_alterada=quantidade_ajustada,
                            motivo=motivo
                        )
                    
                    retorno_console = f.getvalue()
                    
                    if sucesso:
                        st.success("Estoque atualizado com sucesso!")
                        st.rerun()  # Recarrega a página para atualizar o componente de métrica e a tabela
                    else:
                        # Se falhou (ex: estoque ia ficar negativo), exibe o aviso amigável
                        st.error("Operação Recusada pelo Banco de Dados.")
                        if "[Bloqueio de Estoque]" in retorno_console:
                            st.warning("Saldo insuficiente em estoque para realizar essa saída.")
                        else:
                            st.text(retorno_console)

    # -------------------------------------------------------------------------
    # COLUNA 2: HISTÓRICO DE AUDITORIA (EXTRATO)
    # -------------------------------------------------------------------------
    with col_historico:
        st.subheader("📜 Extrato do Produto")
        
        # Puxa o histórico tratado como lista de dicionários que alteramos no backend
        historico = consultar_historico_produto(engine, produto_atual.id)
        
        if not historico:
            st.info("Nenhuma movimentação registrada para este produto até o momento.")
        else:
            # Formatando os dicionários para exibição em uma tabela elegante no Streamlit
            dados_tabela = []
            for registro in historico:
                tipo_visual = "🟢 ENTRADA" if registro["tipo"] == "ENTRADA" or registro["tipo"] == "TipoMovimentacao.ENTRADA" else "🔴 SAÍDA"
                
                dados_tabela.append({
                    "Data/Hora": registro["data"],
                    "Operação": tipo_visual,
                    "Qtd": registro["quantidade"],
                    "Motivo/Origem": registro["motivo"]
                })
                
            # Exibe os dados em formato de tabela scannable preenchendo toda a largura da coluna
            st.dataframe(dados_tabela, width="stretch", hide_index=True)