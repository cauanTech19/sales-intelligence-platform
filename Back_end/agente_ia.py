import os
import tomllib
from pathlib import Path
import streamlit as st
from google import genai
from google.genai import types
from sqlalchemy.orm import Session
from cliente import cadastrar_cliente
from sqlalchemy import select, func
from models import Venda, Produto, engine
from movimentacao import consultar_historico_produto, ajustar_estoque_manual

def obter_resumo_vendas_db(session: Session) -> str:
    """Retorna um resumo financeiro e estatístico das vendas cadastradas no sistema."""
    total_vendas = session.scalar(select(func.count(Venda.id))) or 0
    faturamento_total = session.scalar(select(func.sum(Venda.valor_total))) or 0.0

    if total_vendas == 0:
        return "Nenhuma venda registrada no sistema até o momento."

    return (
        f"Resumo Geral de Vendas:\n"
        f"- Total de pedidos realizados: {total_vendas}\n"
        f"- Faturamento acumulado: R$ {faturamento_total:,.2f}\n"
    )

def obter_produtos_criticos_db(session: Session) -> str:
    """Retorna a lista de produtos com estoque baixo (menor ou igual a 5 unidades)."""
    # Consulta produtos com quantidade <= 5
    comando = select(Produto).where(Produto.quantidade_estoque <= 5)
    produtos_baixos = session.scalars(comando).all()

    if not produtos_baixos:
        return "Todos os produtos estão com níveis de estoque saudáveis (acima de 5 unidades)."

    lista_produtos = [
        f"- {p.nome} (Qtd atual: {p.quantidade_estoque})" 
        for p in produtos_baixos
    ]
    return "Atenção! Produtos com estoque crítico:\n" + "\n".join(lista_produtos)



def criar_ferramentas_ia(session: Session):
    """
    Define e conecta as funções (Tools) que a IA poderá executar no banco.
    """
    def ia_cadastrar_cliente(nome: str, cpf: str, email: str, endereco: str = None, telefone: str = None) -> str:
        """Cadastra um novo cliente no banco de dados do sistema.

        Args:
            nome: Nome completo do cliente.
            cpf: CPF do cliente (com ou sem pontuação).
            email: E-mail válido do cliente.
            endereco: Endereço residencial (opcional).
            telefone: Telefone de contato (opcional).
        """
        sucesso = cadastrar_cliente(
            session, 
            nome=nome, 
            cpf=cpf, 
            email=email, 
            endereco=endereco, 
            telefone=telefone
        )
        if sucesso:
            return f"Sucesso: O cliente '{nome}' foi cadastrado no banco de dados."
        return f"Erro: Não foi possível cadastrar o cliente '{nome}'. Verifique se o CPF ou e-mail já existem."
    

    def ia_obter_resumo_vendas() -> str:
        """Obtém o faturamento total e quantidade de pedidos realizados para análise de desempenho."""
        return obter_resumo_vendas_db(session)


    def ia_buscar_produto_por_nome(nome_produto: str) -> str:
        """Busca produtos no banco pelo nome para identificar o ID e o estoque atual."""
        comando = select(Produto).where(Produto.nome.ilike(f"%{nome_produto}%"))
        produtos = session.scalars(comando).all()
        
        if not produtos:
            return f"Nenhum produto encontrado com o nome '{nome_produto}'."
            
        resultado = [f"ID: {p.id} | Nome: {p.nome} | Estoque Atual: {p.quantidade_estoque}" for p in produtos]
        return "Produtos encontrados:\n" + "\n".join(resultado)



    def ia_ajustar_estoque_manual(produto_id: int, quantidade_alterada: int, motivo: str) -> str:
        """Ajusta o estoque de um produto manualmente e grava a movimentação para auditoria.

        Args:
            produto_id: O ID numérico inteiro do produto.
            quantidade_alterada: Valor POSITIVO para adicionar ao estoque (+5) ou NEGATIVO para remover (-3).
            motivo: Descrição ou justificativa obrigatória para o ajuste.
        """
        sucesso = ajustar_estoque_manual(
            engine=engine, 
            produto_id=produto_id, 
            quantidade_alterada=quantidade_alterada, 
            motivo=motivo
        )
        if sucesso:
            return f"Sucesso: Estoque do produto ID {produto_id} ajustado em {quantidade_alterada} unidades."
        return f"Erro: Não foi possível ajustar o estoque do produto ID {produto_id}. Verifique se o ID existe, se está ativo ou se há saldo suficiente."
    

    def ia_verificar_estoque_critico() -> str:
        """Consulta o banco de dados e retorna quais produtos estão com estoque baixo ou zerado."""
        return obter_produtos_criticos_db(session)
    
    def ia_consultar_historico_estoque(produto_id: int) -> str:
        """Retorna o histórico detalhado de movimentações (entradas e saídas) de um produto especifico."""
        historico = consultar_historico_produto(engine=engine, produto_id=produto_id)
        if not historico:
            return f"Nenhuma movimentação encontrada para o produto ID {produto_id}."
        
        linhas = [f"- [{mov['data']}] {mov['tipo']} de {mov['quantidade']} un | Motivo: {mov['motivo']}" for mov in historico]
        return f"Histórico do Produto ID {produto_id}:\n" + "\n".join(linhas)

    return [
        ia_cadastrar_cliente, 
        ia_obter_resumo_vendas, 
        ia_verificar_estoque_critico, 
        ia_consultar_historico_estoque,
        ia_ajustar_estoque_manual,
        ia_buscar_produto_por_nome
        ]



def obter_chave_api() -> str:
    """Busca a chave API no st.secrets com fallback seguro lendo o arquivo secrets.toml diretamente."""
    # 1. Tenta pegar pelo st.secrets do Streamlit
    try:
        if "GEMINI_API_KEY" in st.secrets:
            chave = st.secrets["GEMINI_API_KEY"]
            if chave and chave != "SUA_CHAVE_AQUI":
                return chave
    except Exception:
        pass

    # 2. Tenta pegar por variável de ambiente
    chave_env = os.getenv("GEMINI_API_KEY")
    if chave_env:
        return chave_env

    # 3. Fallback: Lê diretamente o arquivo secrets.toml subindo até a raiz do projeto
    caminhos_para_testar = [
        Path(__file__).resolve().parent.parent / ".streamlit" / "secrets.toml", 
        Path.cwd() / ".streamlit" / "secrets.toml"
    ]

    for caminho in caminhos_para_testar:
        if caminho.exists():
            try:
                with open(caminho, "rb") as f:
                    dados = tomllib.load(f)
                    chave_toml = dados.get("GEMINI_API_KEY", "")
                    if chave_toml:
                        return chave_toml
            except Exception:
                pass

    return ""

def renderizar_ia(session: Session):
    """Função principal da tela do Assistente IA."""
    st.header("🤖 Copiloto IA - Assistente Operacional")
    st.caption("Converse em linguagem natural para realizar ações rápidas no sistema.")
    st.markdown("---")

    # 1. Inicializa o histórico na sessão se não existir
    if "historico_ia" not in st.session_state:
        st.session_state.historico_ia = []

    # 2. Exibe o histórico de mensagens salvas
    for mensagem in st.session_state.historico_ia:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

    # 3. Caixa de entrada para novas perguntas/comandos
    if prompt := st.chat_input("Ex: Cadastre o cliente Lucas, CPF 111.222.333-44, e-mail lucas@email.com"):
        
        # Mostra e guarda a mensagem do usuário
        st.session_state.historico_ia.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        api_key = obter_chave_api()
        if not api_key:
            st.error("❌ A chave 'GEMINI_API_KEY' não foi encontrada no arquivo .streamlit/secrets.toml!")
            st.stop()

        client = genai.Client(api_key=api_key)
        tools = criar_ferramentas_ia(session)

        config = types.GenerateContentConfig(
            system_instruction=(
                "Você é o Copiloto IA e Analista do sistema PDV Admin.\n"
                "Sua função é auxiliar na operação do sistema e na análise de dados do negócio em linguagem natural.\n\n"
                "DIRETRIZES DE ATUAÇÃO E USO DE FERRAMENTAS:\n"
                "1. CADASTRO DE CLIENTES:\n"
                "   - Cadastre novos clientes utilizando 'ia_cadastrar_cliente'. Solcite dados faltantes se necessário.\n\n"
                "2. ANÁLISE DE VENDAS E DASHBOARD:\n"
                "   - Ao responder sobre vendas, faturamento e desempenho financeiro, consulte 'ia_obter_resumo_vendas'.\n"
                "   - Para perguntas sobre reposição, alertas ou falta de itens, consulte 'ia_verificar_estoque_critico'.\n\n"
                "3. GESTÃO E MOVIMENTAÇÃO DE ESTOQUE:\n"
                "   - Se o usuário citar o NOME do produto (ex: 'Baixa de 2 bonés'), PRIMEIRO busque o ID com 'ia_buscar_produto_por_nome'.\n"
                "   - Para movimentar estoque, use 'ia_ajustar_estoque_manual'. Dica: valores POSITIVOS (+X) para entradas "
                "e NEGATIVOS (-X) para saídas. Sempre forneça uma justificativa clara no campo 'motivo'.\n"
                "   - Para analisar o histórico de movimentações, use 'ia_consultar_historico_estoque'.\n\n"
                "COMPORTAMENTO:\n"
                "- Seja direto, profissional e prestativo.\n"
                "- Ao concluir qualquer operação, confirme os dados retornados pelas ferramentas com clareza."
            ),
            tools=tools,
            temperature=0.0,
        )
        chat = client.chats.create(model="gemini-2.5-flash", config=config)

        # 5. Envia para o Gemini e processa
        with st.chat_message("assistant"):
            with st.spinner("O assistente está processando..."):
                try:
                    resposta = chat.send_message(prompt)
                    st.markdown(resposta.text)
                    
                    # Registra a resposta do assistente no histórico
                    st.session_state.historico_ia.append({"role": "assistant", "content": resposta.text})
                except Exception as e:
                    st.error(f"Erro na comunicação com a IA: {str(e)}")