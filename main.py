

import time
from etl import consolidar, tratar, salvar_excel
from database import criar_sqlite
from logger import gerar_log
from terminal import titulo
from uitls import cronometro

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

gerar_log(
    base,
    inicio_total,
    total_arquivos,
    total_abas
)

titulo("PROCESSO FINALIZADO")
# %%
