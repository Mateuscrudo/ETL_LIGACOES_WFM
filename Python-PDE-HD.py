from logging import log
import os
import sqlite3
import pandas as pd
import re
from datetime import datetime
import time
import unicodedata
from colorama import Fore, Style, init
from tqdm import tqdm
    

TEMPOS = {}

init(autoreset=True)

def titulo(texto):
    print("\n" + "=" * 50)
    print(f" {texto}")
    print("=" * 50)

def sucesso(texto):
    print(Fore.GREEN + "✅ " + texto)

def aviso(texto):
    print(Fore.YELLOW + "⚠ " + texto)

def erro(texto):
    print(Fore.RED + "❌ " + texto)

def info(texto):
    print(Fore.CYAN + "ℹ " + texto)


# =====================================================
# CONFIGURAÇÃO
# =====================================================

PASTA_DADOS = r"C:\Users\MateusCrudodeBarros\DEEPESSOAS\PROJETOS - SABESP - PERFORMANCE GUARUJÁ\PERFORMANCE_GUARUJA_AGUA\EXECUÇÃO\BACKOFFICE\CONFERENCIA\Reconferencia\Ligações de água"

ARQUIVO_EXCEL = os.path.join(PASTA_DADOS, "base_unificada.xlsx")
BANCO_SQL = os.path.join(PASTA_DADOS, "base_unificada.db")
TABELA = "adesoes"

COLUNAS_SQLITE = [
    "Número OS",
    "MATRICULA",
    "Notas de Acatamento",
    "PDE",
    "Endereço",
    "Número",
    "Complemento",
    "Bairro",
    "Nota Execução/Não Execução",
    "ARQUIVO",
    "ABA"
]

# =====================================================
# FUNÇÕES
# =====================================================
def cronometro(nome,inicio):
    tempo = time.time() - inicio
    TEMPOS[nome] = tempo
    print(f"⏱ {nome:<15}: {tempo:.2f} segundos")

def consolidar():

    
    titulo("1 - CONSOLIDANDO PLANILHAS")

    lista_df = []
    total_abas = 0

    arquivos = [
        f for f in os.listdir(PASTA_DADOS)
        if f.endswith(".xlsx") or f.endswith(".xls")
    ]

    info(f"Arquivos encontrados: {len(arquivos)}")

    input("\nENTER para iniciar...")

    for arquivo in tqdm(arquivos, desc="Processando arquivos",colour="green", unit="arquivo"):

        if arquivo == "base_unificada.xlsx":
            continue

        caminho = os.path.join(PASTA_DADOS, arquivo)

        info(f"📂 {arquivo}" )

        abas = pd.read_excel(caminho, sheet_name=None)

        for nome_aba, df in tqdm(abas.items(), desc="Processando abas",colour="blue", unit="aba"):

            if df.empty:
                continue

            df["ARQUIVO"] = arquivo
            df["ABA"] = nome_aba

            lista_df.append(df)

            info(f"   ✔ {nome_aba} ({len(df)} linhas)")

    base = pd.concat(lista_df, ignore_index=True)

    info(f"\nTotal consolidado: {len(base):,}")

    return base, len(arquivos), total_abas
# =====================================================
# EXTRAIR MATRICULA
# =====================================================

def normalizar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.upper()

def extrair_matricula(texto):
    if pd.isna(texto):
        return None

    texto = normalizar_texto(texto)

    # Primeiro tenta pegar o código logo depois de ADESAO / ADESÃO
    m = re.search(
        r'ADESAO\s*[:\-]?\s*'
        r'('
        r'[A-Z]{2,5}\d{3,8}'
        r'|\d{4,6}-(?:CGN|CG|[A-Z]{2,3})'
        r')\b',
        texto
    )
    if m:
        return m.group(1)

    # Fallback: procura um código parecido em qualquer lugar do texto
    m = re.search(
        r'(?<![A-Z0-9])('
        r'[A-Z]{2,5}\d{3,8}'
        r'|\d{4,6}-(?:CGN|CG|[A-Z]{2,3})'
        r')(?![A-Z0-9])',
        texto
    )
    if m:
        return m.group(1)

    return None

def tratar(df):

    
    titulo("2 - TRATAMENTO")

# Converte células vazias ou com espaços para NaN
    df = df.replace(r'^\s*$', pd.NA, regex=True)

# ==========================================
# EXTRAI A MATRÍCULA DAS NOTAS DE ACATAMENTO
# ==========================================

    tqdm.pandas(desc="🔎Extraindo matrículas...")

    df["MATRICULA"] = df["Notas de Acatamento"].progress_apply(extrair_matricula)

    encontradas = df["MATRICULA"].notna().sum()
    nao_encontradas = df["MATRICULA"].isna().sum()

    sucesso(f"Matrículas encontradas : {encontradas:,}")
    erro(f"Sem matrícula          : {nao_encontradas:,}")

    if nao_encontradas > 0:

     info("\nPrimeiros registros sem matrícula:")

    print(
        df.loc[
            df["MATRICULA"].isna(),
            "Notas de Acatamento"
        ].head(10)
    )

    input("\nENTER para verificar linhas em branco...")

    linhas = df.isna().all(axis=1).sum()

    print(f"\nLinhas totalmente vazias: {linhas}")

    if linhas:

        resp = input("Remover? (S/N): ").upper()

        if resp == "S":

            antes = len(df)

            df = df.dropna(how="all")

            print(f"Removidas: {antes - len(df)}")

    input("\nENTER para verificar duplicatas...")

    antes = len(df)

    df.drop_duplicates(inplace=True)

    print(f"Duplicatas restantes : {df.duplicated().sum():,}")
    return df


def gerar_log(df, inicio, total_arquivos, total_abas):

    fim = time.time()

    print(f"Tempo total de execução: {fim - inicio:.2f} segundos")

    with open(LOG, "w", encoding="utf-8") as log:

        log.write("=" * 50 + "\n")
        log.write("RELATÓRIO DE EXECUÇÃO DO ETL\n")
        log.write("=" * 50 + "\n\n")

        log.write(f"Data..............: {datetime.now()}\n")
        log.write(f"Tempo de execução.: {fim - inicio:.2f} segundos\n\n")
        log.write("TEMPO POR ETAPA\n")
        log.write("-" * 40 + "\n")

        for etapa, tempo in TEMPOS.items():
            log.write(f"{etapa:<20}: {tempo:.2f} s\n")

        log.write("\n")

        log.write(f"Total registros...: {len(df):,}\n")
        log.write(f"Matrículas........: {df['MATRICULA'].notna().sum():,}\n")
        log.write(f"Sem matrícula.....: {df['MATRICULA'].isna().sum():,}\n")
        log.write(f"Duplicatas........: {df.duplicated().sum():,}\n")
        log.write(f"Arquivos Excel....: {len([f for f in os.listdir(PASTA_DADOS) if f.endswith(('.xlsx','.xls'))])}\n")
        log.write(f"Arquivos processados: {total_arquivos}\n")
        log.write(f"Abas processadas....: {total_abas}\n")

    print(f"\n📄 Log salvo em:\n{LOG}")

# ==========================================
# RESUMO DA BASE
# ==========================================
def resumo_base(df):
    
    titulo("RESUMO DA BASE")
    

    print(f"Total de registros : {len(df):,}")
    print(f"Matrículas         : {df['MATRICULA'].notna().sum():,}")
    print(f"Sem matrícula      : {df['MATRICULA'].isna().sum():,}")
    print(f"Duplicatas         : {df.duplicated().sum():,}")

    return df


def salvar_excel(df):

    
    titulo("3 - SALVANDO EXCEL")
    

    resp = input("\nSalvar Excel? (S/N): ").upper()

    if resp != "S":
        return

    df.to_excel(ARQUIVO_EXCEL, index=False)

    print(Fore.GREEN + "✅ Excel salvo." + Style.RESET_ALL)


def criar_sqlite(df):

    titulo("4 - GERANDO SQLITE")

    resp = input("\nCriar banco SQLite? (S/N): ").upper()

    if resp != "S":
        return

    faltando = [c for c in COLUNAS_SQLITE if c not in df.columns]

    if faltando:

        print(Fore.RED + "\nColunas ausentes:" + Style.RESET_ALL)

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

    print(Fore.GREEN + "✅ Banco SQLite criado." + Style.RESET_ALL)

    inicio = time.time()

LOG = os.path.join(
    PASTA_DADOS,
    f"log_ETL_{datetime.now():%Y%m%d_%H%M%S}.txt"
)


# =====================================================
# EXECUÇÃO
# =====================================================

titulo("ETL SABESP")

inicio_total = time.time()
inicio = time.time()
base, total_arquivos, total_abas = consolidar()
cronometro("Consolidação", inicio)

inicio = time.time()
base = tratar(base)
cronometro("Tratamento", inicio)

inicio = time.time()
salvar_excel(base)
cronometro("Excel", inicio)

inicio = time.time()
criar_sqlite(base)
cronometro("SQLite", inicio)

cronometro("Total", inicio_total)

gerar_log(base, inicio_total,total_arquivos,total_abas)

titulo("PROCESSO FINALIZADO")