import sqlite3
import time
import os
from datetime import date, datetime
import pandas as pd
from colorama import Fore, Style, init
from terminal import titulo
from config import *

def criar_sqlite(df):

    titulo("4 - GERANDO SQLITE")

    resp = (
        "S"
        if os.environ.get("EXECUCAO_AGENTE") == "1"
        else input("\nCriar banco SQLite? (S/N): ").upper()
    )

    if resp != "S":
        return

    faltando = [c for c in COLUNAS_SQLITE if c not in df.columns]

    if faltando:

        erro("\nColunas ausentes:")

        for coluna in faltando:
            print(coluna)

        return

    os.makedirs(os.path.dirname(BANCO_SQL), exist_ok=True)
    conn = sqlite3.connect(BANCO_SQL)

    df_sql = df[COLUNAS_SQLITE].copy()
    # Colunas mistas podem conter Timestamp como objeto, sem conversão
    # automática do pandas antes de chegar ao driver SQLite.
    def valor_sqlite(valor):
        if valor is None or valor is pd.NA or valor is pd.NaT:
            return None
        if isinstance(valor, (pd.Timestamp, datetime)):
            return valor.isoformat(sep=" ")
        if isinstance(valor, date):
            return valor.isoformat()
        return valor

    for coluna in df_sql.columns:
        if df_sql[coluna].dtype == object:
            df_sql[coluna] = pd.Series(
                [valor_sqlite(valor) for valor in df_sql[coluna]],
                index=df_sql.index,
                dtype=object,
            )

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

BANCO = BANCO_SQL

def conectar():
    return sqlite3.connect(BANCO)
