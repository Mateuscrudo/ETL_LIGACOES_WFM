import os
import sqlite3
import pandas as pd


# Caminhos
PASTA = os.path.dirname(os.path.abspath(__file__))

ARQUIVO_EXCEL = r"C:\Users\MateusCrudodeBarros\DEEPESSOAS\PROJETOS - SABESP - PERFORMANCE GUARUJÁ\PERFORMANCE_GUARUJA_ESGOTO\EXECUÇÃO\BACKOFFICE\BASE_BAIRROS_ESGOTO\BASE ESGOTO DEEP ROTEIRO.xlsx"
BANCO_SQL = os.path.join(PASTA, "base_unificada.db")
TABELA = "adesoes"

print("📖 Lendo Excel...")

# Lê os dados
df = pd.read_excel(ARQUIVO_EXCEL)

# seleciona as colunas

print("📋 importando colunas...")

colunas_uteis = ["status","Dt. Execução","Oficial","Bairro","Matricula","Endereço","Foto(s)"]

df_sqlite = df[colunas_uteis]


print("💾 Gravando banco SQLite...")

# Salva no SQLite
conn = sqlite3.connect(BANCO_SQL)

print(df.columns.tolist())

df_sqlite.to_sql(
    TABELA,
    conn,
    if_exists="replace",
    index=False
)

conn.close()


print("✅ Banco criado com sucesso!")
print(f"📊 Registros importados: {len(df)}")
print(f"📋 Colunas salvas: {len(df_sqlite.columns)}")