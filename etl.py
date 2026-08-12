import os
import re
import unicodedata
import pandas as pd
from tqdm import tqdm
from config import *
from terminal import *
from regex_utils import extrair_matricula


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

    sucesso("✅ Excel salvo.")