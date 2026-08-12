import sqlite3
import time
from colorama import Fore, Style, init
from terminal import titulo
from config import *

def criar_sqlite(df):

    titulo("4 - GERANDO SQLITE")

    resp = input("\nCriar banco SQLite? (S/N): ").upper()

    if resp != "S":
        return

    faltando = [c for c in COLUNAS_SQLITE if c not in df.columns]

    if faltando:

        erro("\nColunas ausentes:")

        for coluna in faltando:
            print(coluna)

        return

    conn = sqlite3.connect(BANCO_SQL)

    df_sql = df[COLUNAS_SQLITE]

    df_sql.to_sql(
        TABELA,
        conn,
        if_exists="replace",
        index=False
    )

    cursor = conn.cursor()

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_os
    ON adesoes("Número OS")
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_pde
    ON adesoes(PDE)
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_matricula
    ON adesoes(MATRICULA)
    """)

    conn.commit()

    conn.close()

    sucesso("✅ Banco SQLite criado.")

    inicio = time.time()

BANCO = r"C:\Users\MateusCrudodeBarros\DEEPESSOAS\PROJETOS - SABESP - PERFORMANCE GUARUJÁ\PERFORMANCE_GUARUJA_AGUA\EXECUÇÃO\AUTOMATIZAÇÃO\PYTHON\DATABASE LIGAÇÕES WFM\database_SQL\base_unificada.db"

def conectar():
    return sqlite3.connect(BANCO)