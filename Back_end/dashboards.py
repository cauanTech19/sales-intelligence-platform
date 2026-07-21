from models import Cliente, Categoria, Venda, StatusVenda, ItemVenda, Produto, Categoria, Cliente
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
import pandas as pd


def obter_indicadores_clientes(session: Session):
    """
    Calcula os Clientes VIPs (acima da média de gastos) e os Clientes Inativos.
    """
    
    # 1. Consulta base: Todos os clientes que possuem compras registradas
    compras_clientes_query = (
        session.query(
            Cliente.id.label("ID"),
            Cliente.nome.label("Cliente"),
            Cliente.cpf.label("CPF"),
            func.count(Venda.id).label("Total Pedidos"),
            func.coalesce(func.sum(Venda.valor_total), 0.0).label("Total Gasto")
        )
        .join(Venda, Cliente.id == Venda.cliente_id)
        .filter(Venda.status != StatusVenda.CANCELADA)
        .group_by(Cliente.id)
        .all()
    )

    df_compras = pd.DataFrame(compras_clientes_query)

    if not df_compras.empty:
        # Calcula a média de gastos entre os clientes que compraram
        media_gastos = df_compras["Total Gasto"].mean()

        # CLIENTES VIP: Apenas quem gastou MAIOR OU IGUAL à média geral
        df_vips = (
            df_compras[df_compras["Total Gasto"] >= media_gastos]
            .sort_values(by="Total Gasto", ascending=False)
            .head(10)
        )
    else:
        df_vips = pd.DataFrame()


    clientes_com_compras = (
        session.query(Venda.cliente_id)
        .filter(Venda.status != StatusVenda.CANCELADA)
        .distinct()
        .scalar_subquery()
    )

    inativos_query = (
        session.query(
            Cliente.id.label("ID"),
            Cliente.nome.label("Cliente"),
            Cliente.cpf.label("CPF"),
            Cliente.email.label("E-mail")
        )
        .filter(Cliente.id.not_in(clientes_com_compras))
        .all()
    )

    df_inativos = pd.DataFrame(inativos_query)

    return df_vips, df_inativos


def obter_indicadores_vendas(session: Session):
    """
    Calcula a Quantidade de Vendas por Mês garantindo os 12 meses no eixo X
    e o ranking das Formas de Pagamento.
    """
    
    vendas_validas = session.query(Venda).filter(Venda.status != StatusVenda.CANCELADA)

    # 1. Consulta das vendas no ano atual
    vendas_mes_query = (
        vendas_validas
        .with_entities(
            func.extract('month', Venda.data_venda).label("mes_num"),
            func.count(Venda.id).label("total_vendas")
        )
        .group_by("mes_num")
        .all()
    )

    meses_map = {
        1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
        7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
    }
    
    dados_completos = {meses_map[m]: 0 for m in range(1, 13)}

    for item in vendas_mes_query:
        mes_nome = meses_map.get(int(item.mes_num))
        if mes_nome:
            dados_completos[mes_nome] = int(item.total_vendas)

    # Converte em DataFrame
    df_vendas_mes = pd.DataFrame(
        list(dados_completos.items()), 
        columns=["Mês", "Qtd Vendas"]
    )


    # 2. Formas de Pagamento
    pagamento_query = (
        vendas_validas
        .with_entities(
            Venda.forma_pagamento.label("forma_pgto"),
            func.count(Venda.id).label("qtd_usada"),
            func.sum(Venda.valor_total).label("total_movimentado")
        )
        .group_by(Venda.forma_pagamento)
        .order_by(func.count(Venda.id).desc())
        .all()
    )

    df_pagamentos = pd.DataFrame(pagamento_query)

    if not df_pagamentos.empty:
        df_pagamentos["Forma de Pagamento"] = df_pagamentos["forma_pgto"].apply(
            lambda x: x.value if hasattr(x, 'value') else str(x)
        )
        df_pagamentos["Qtd Usos"] = df_pagamentos["qtd_usada"].astype(int)
    else:
        df_pagamentos = pd.DataFrame(columns=["Forma de Pagamento", "Qtd Usos", "total_movimentado"])

    return df_vendas_mes, df_pagamentos



def obter_metricas_faturamento(session: Session):
    """Calcula o faturamento Diário, Mensal e Anual ignorando vendas canceladas."""
    hoje = datetime.now()
    
    query_base = session.query(Venda).filter(Venda.status != StatusVenda.CANCELADA)
    
    # 1. Diário
    faturamento_dia = query_base.filter(
        func.date(Venda.data_venda) == hoje.date()
    ).with_entities(func.coalesce(func.sum(Venda.valor_total), 0.0)).scalar()

    # 2. Mensal
    faturamento_mes = query_base.filter(
        func.extract('year', Venda.data_venda) == hoje.year,
        func.extract('month', Venda.data_venda) == hoje.month
    ).with_entities(func.coalesce(func.sum(Venda.valor_total), 0.0)).scalar()

    # 3. Anual
    faturamento_ano = query_base.filter(
        func.extract('year', Venda.data_venda) == hoje.year
    ).with_entities(func.coalesce(func.sum(Venda.valor_total), 0.0)).scalar()

    return faturamento_dia, faturamento_mes, faturamento_ano



def obter_desempenho_produtos(session: Session):
    """
    Calcula as vendas por produto e aplica filtro condicional baseado na Média de Vendas
    para garantir que um produto 'Mais Vendido' nunca apareça na aba de 'Menos Vendido'.
    """
    
    # 1. Consulta base: Agrupa todos os produtos e soma as vendas
    query_total_vendas = (
        session.query(
            Produto.id.label("ID"),
            Produto.nome.label("Produto"),
            Produto.preco_venda.label("Preço Unitário"),
            Produto.quantidade_estoque.label("Estoque"),
            func.coalesce(func.sum(ItemVenda.quantidade), 0).label("total_vendido")
        )
        .outerjoin(ItemVenda, Produto.id == ItemVenda.produto_id)
        .outerjoin(Venda, (ItemVenda.venda_id == Venda.id) & (Venda.status != StatusVenda.CANCELADA))
        .group_by(Produto.id)
        .all()
    )

    # Converte tudo para DataFrame para facilitar os filtros lógicos
    df_geral = pd.DataFrame(query_total_vendas)

    if df_geral.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    # --- REGRA DE CORTE E FILTROS ---
    
    # Produtos que tiveram pelo menos 1 venda
    df_vendidos = df_geral[df_geral["total_vendido"] > 0].copy()
    
    # Produtos NUNCA vendidos
    df_nao_vendidos = df_geral[df_geral["total_vendido"] == 0].copy()

    if not df_vendidos.empty:
        # Calcula a média de vendas entre os produtos comercializados
        media_vendas = df_vendidos["total_vendido"].mean()

        # MAIS VENDIDOS: Apenas quem vendeu MAIOR OU IGUAL à média (ou seja, os líderes)
        df_mais_vendidos = (
            df_vendidos[df_vendidos["total_vendido"] >= media_vendas]
            .sort_values(by="total_vendido", ascending=False)
            .head(10)
        )

        # MENOS VENDIDOS: Apenas quem vendeu ABAIXO da média (os lanternas)
        df_menos_vendidos = (
            df_vendidos[df_vendidos["total_vendido"] < media_vendas]
            .sort_values(by="total_vendido", ascending=True)
            .head(10)
        )
    else:
        df_mais_vendidos = pd.DataFrame()
        df_menos_vendidos = pd.DataFrame()

    return df_mais_vendidos, df_menos_vendidos, df_nao_vendidos



def obter_desempenho_categorias(session: Session):
    """
    Calcula o Faturamento Total e a Quantidade de Itens Vendidos por Categoria,
    desconsiderando vendas canceladas.
    """
    query_categorias = (
        session.query(
            Categoria.id.label("ID"),
            Categoria.nome.label("Categoria"),
            func.coalesce(func.sum(ItemVenda.quantidade), 0).label("Qtd Itens Vendidos"),
            func.coalesce(func.sum(ItemVenda.quantidade * ItemVenda.preco_unitario), 0.0).label("Faturamento Total")
        )
        .outerjoin(Produto, Categoria.id == Produto.categoria_id)
        .outerjoin(ItemVenda, Produto.id == ItemVenda.produto_id)
        .outerjoin(Venda, (ItemVenda.venda_id == Venda.id) & (Venda.status != StatusVenda.CANCELADA))
        .group_by(Categoria.id)
        .all()
    )

    df_categorias = pd.DataFrame(query_categorias)

    if df_categorias.empty:
        return pd.DataFrame()

    # Considera apenas categorias que tiveram pelo menos 1 venda
    df_categorias = df_categorias[df_categorias["Qtd Itens Vendidos"] > 0].copy()

    return df_categorias

