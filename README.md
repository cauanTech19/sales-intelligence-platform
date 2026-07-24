# 🛒 Sistema de PDV & Gestão Financeira (Streamlit + SQLAlchemy)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B.svg)](https://streamlit.io/)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-red.svg)](https://www.sqlalchemy.org/)

Um sistema completo de **Ponto de Venda (PDV)** e **Controle Financeiro/Estoque** desenvolvido em Python. O projeto conta com uma interface reativa moderna construída em **Streamlit**, persistência de dados via **SQLAlchemy ORM** e validações rigorosas para garantir a integridade das transações de caixa, estoque e pagamentos.

---

## 📌 Principais Funcionalidades

### 🛍️ Frente de Caixa (PDV)
* **Carrinho Dinâmico:** Adição e remoção de produtos com cálculo automático do total geral.

* **Preço Unitário Imutável:** O preço de venda é puxado diretamente do banco de dados, prevenindo alterações indevidas ou descontos não autorizados pelo operador.

* **Validação de Estoque:** Impedimento automático de adição de itens com quantidade superior ao estoque disponível.

### 📜 Histórico & Cancelamentos
* **Registro de Vendas:** Tabela consolidada com ID, data/hora, cliente, total e status.

* **Estorno de Vendas:** Interface segura com checkbox de confirmação para cancelamento definitivo de vendas e estorno automático dos produtos ao estoque.

### 💰 Módulo Financeiro
* **Fila de Pagamentos Pendentes:** Exibe apenas vendas ativas que ainda não foram pagas.

* **Fixação de Regras de Negócio:** Transações concluídas ou canceladas são removidas da fila de pagamentos para evitar duplicidade.

* **Cancelamento/Estorno Direcionado:** Busca obrigatória por **ID do Cliente** para listar apenas as transações pertinentes, reduzindo drasticamente o risco de estornar pagamentos de terceiros por engano.

---

## 🏗️ Arquitetura e Estrutura do Projeto

O projeto é modularizado para manter o código limpo e de fácil manutenção:

STRORAGE_IA/
├── .streamlit/             # Configurações de tema e layout do Streamlit
├── Back_end/               # Regras de negócio, modelos e serviços
│   ├── interface_streamlit/ # Telas e componentes da interface gráfica
│   ├── tests/              # Suíte de testes automatizados (Pytest)
│   ├── agente_ia.py        # Agente/Serviço de Inteligência Artificial
│   ├── app.py              # Ponto de entrada e inicialização do banco
│   ├── auth_admin.py       # Módulo de autenticação e permissões
│   ├── categoria.py        # Gestão de categorias de produtos
│   ├── cliente.py          # Gestão e cadastro de clientes
│   ├── dashboards.py       # Indicadores e gráficos de desempenho
│   ├── item.py             # Validação e gerenciamento dos itens da venda
│   ├── models.py           # Mapeamento do banco de dados (SQLAlchemy)
│   ├── movimentacao.py     # Controle de movimentações de estoque
│   ├── pagamento.py        # Regras de registro e estorno de pagamentos
│   ├── produto.py          # CRUD e controle de produtos
│   ├── validador.py        # Módulo de validação de dados
│   └── vendas.py           # Regras de negócio do PDV e cancelamentos
├── .gitignore              # Arquivos ignorados pelo Git
├── README.md               # Documentação principal do projeto
├── requirements.txt        # Dependências e bibliotecas do projeto


### 3. Instalar as dependências
```bash
pip install -r requirements.txt


E para gerar o arquivo atualizado direto do seu ambiente no VS Code/Terminal com as versões exatas que você usou, você também pode rodar:


```bash
pip freeze > requirements.txt



4. Executar a aplicação:
git clone [https://github.com/cauanTech19/sales-intelligence-platform]
cd sales-intelligence-platform
streamlit run Back_end/interface_streamlit/interface.py
