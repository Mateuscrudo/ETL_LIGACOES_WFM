from mimetypes import init
import os
from datetime import datetime
from colorama import Fore, Style, init

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

PASTA_DADOS = r"C:\Users\MateusCrudodeBarros\DEEPESSOAS\PROJETOS - SABESP - PERFORMANCE GUARUJÁ\PERFORMANCE_GUARUJA_AGUA\EXECUÇÃO\BACKOFFICE\CONFERENCIA\Reconferencia\Ligações de água"
PASTA_LOGS = r"C:\Users\MateusCrudodeBarros\DEEPESSOAS\PROJETOS - SABESP - PERFORMANCE GUARUJÁ\PERFORMANCE_GUARUJA_AGUA\EXECUÇÃO\AUTOMATIZAÇÃO\PYTHON\DATABASE LIGAÇÕES WFM\ETL_SABESP\logs"
PASTA_EXCEL = r"C:\Users\MateusCrudodeBarros\DEEPESSOAS\PROJETOS - SABESP - PERFORMANCE GUARUJÁ\PERFORMANCE_GUARUJA_AGUA\EXECUÇÃO\AUTOMATIZAÇÃO\PYTHON\DATABASE LIGAÇÕES WFM\database_excel"
PASTA_SQLITE = r"C:\Users\MateusCrudodeBarros\DEEPESSOAS\PROJETOS - SABESP - PERFORMANCE GUARUJÁ\PERFORMANCE_GUARUJA_AGUA\EXECUÇÃO\AUTOMATIZAÇÃO\PYTHON\DATABASE LIGAÇÕES WFM\database_SQL"

ARQUIVO_EXCEL = os.path.join(PASTA_EXCEL, "base_unificada.xlsx")
BANCO_SQL = os.path.join(PASTA_SQLITE, "base_unificada.db")

LOG = os.path.join(PASTA_LOGS,f"log_ETL_{datetime.now():%Y%m%d_%H%M%S}.txt")

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
