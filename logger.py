import os
from datetime import datetime
import time
from config import *
from uitls import *


def gerar_log(df, inicio, total_arquivos, total_abas):

    fim = time.time()

    info(f"Tempo total de execução: {fim - inicio:.2f} segundos")

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

    info(f"\n📄 Log salvo em:\n{LOG}")