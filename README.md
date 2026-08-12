🚰 ETL SABESP -- Consolidação de Ligações de Água

📌 Sobre o projeto

Este projeto automatiza o processo de consolidação e tratamento das planilhas de conferência de ligações de água da SABESP.

O sistema realiza a leitura de diversos arquivos Excel, consolida todasas abas, executa tratamentos automáticos, extrai matrículas utilizandoExpressões Regulares (Regex), remove duplicidades e gera uma base únicaem Excel e SQLite para consultas rápidas.

Além disso, o projeto produz logs detalhados da execução, mede o tempode processamento de cada etapa e apresenta barras de progresso durante oprocessamento.

🎯 Objetivos

Automatizar a consolidação de múltiplas planilhas Excel.

Reduzir o tempo gasto na preparação dos dados.

Padronizar o tratamento das informações.

Facilitar consultas através de um banco SQLite.

Gerar uma base única para análise.

⚙️ Funcionalidades

Consolidação automática de múltiplos arquivos Excel

Leitura de múltiplas abas

Tratamento de dados

Normalização de textos

Extração automática de matrículas utilizando Regex

Remoção de linhas vazias

Remoção de registros duplicados

Exportação para Excel

Exportação para SQLite

Criação automática de índices no banco

Barra de progresso (tqdm)

Cronômetro por etapa

Log automático de execução

Interface colorida no terminal

🏗 Arquitetura

ETL_SABESP/
├── main.py
├── config.py
├── etl.py
├── database.py
├── logger.py
├── regex_utils.py
├── terminal.py
├── utils.py
├── entrada/
├── output/
├── logs/
└── README.md

🛠 Tecnologias

Python

Pandas

SQLite

Regex

Colorama

tqdm

OpenPyXL

🚀 Como executar

pip install -r requirements.txt
python main.py

👨‍💻 Autor

Mateus Crudo de Barros

Projeto desenvolvido para fins de estudo, automação de processos eportfólio profissional