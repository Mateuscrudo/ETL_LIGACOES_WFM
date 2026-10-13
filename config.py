from mimetypes import init
import os
from pathlib import Path
from datetime import datetime
from colorama import Fore, Style, init

BASE_DIR = Path(__file__).resolve().parent

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

PASTA_DADOS = os.path.join(BASE_DIR, "ENTRADA", "WFM")
PASTA_LOGS = BASE_DIR / "logs"
PASTA_SAIDA = BASE_DIR / "saida"
PASTA_EXCEL = PASTA_SAIDA
PASTA_SQLITE = PASTA_SAIDA
PASTA_CONTROLE = os.path.join(BASE_DIR,"ENTRADA", "SHAREPOINT")
ARQUIVO_EXCEL = PASTA_SAIDA / "base_obra.xlsx"
BANCO_SQL = PASTA_SAIDA / "base_obra.db"

LOG = PASTA_LOGS / f"etl_obra_{datetime.now():%Y-%m-%d_%H-%M-%S}.txt"

TABELA = "adesoes"

COLUNAS_SQLITE = [
    "Número OS",
    "MATRICULA",
    "HD_WFM",
    "HD",
    "ORIGEM_HD",
    "DATA_EXECUCAO",
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
