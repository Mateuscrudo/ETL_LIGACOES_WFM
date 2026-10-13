import time
from typing import Any, cast
from pathlib import Path

import config
from etl import consolidar, tratar, salvar_excel
from database import criar_sqlite
from logger import gerar_log, iniciar_logging, LOG_EXECUCAO
from terminal import titulo
from uitls import cronometro, TEMPOS


def executar():
    """Entry point de producao. Importar o modulo nao executa o ETL."""
    inicio_total = time.time()
    TEMPOS.clear()
    with iniciar_logging() as caminho_log:
        try:
            titulo("ETL SABESP")
            LOG_EXECUCAO.info("Fontes: WFM=%s | Controle=%s", config.PASTA_DADOS, config.PASTA_CONTROLE)
            inicio = time.time()
            base, total_arquivos, total_abas = cast(tuple[Any, int, int], consolidar())
            cronometro("Consolidação", inicio)
            if "ARQUIVO" in base:
                for arquivo, quantidade in base.groupby("ARQUIVO", dropna=False).size().items():
                    LOG_EXECUCAO.info("Fonte WFM processada: %s | registros=%s", arquivo, quantidade)
            controle = Path(config.PASTA_CONTROLE)
            if controle.is_dir():
                LOG_EXECUCAO.info("Arquivos de controle disponiveis: %s", [p.name for p in sorted(controle.iterdir()) if p.suffix.lower() in {".xlsx", ".xls"}])
            inicio = time.time()
            base = tratar(base)
            cronometro("Tratamento", inicio)
            inicio = time.time()
            salvar_excel(base)
            cronometro("Excel", inicio)
            LOG_EXECUCAO.info("Excel exportado: %s", config.ARQUIVO_EXCEL)
            inicio = time.time()
            banco = Path(config.BANCO_SQL)
            antes_sqlite = (banco.stat().st_mtime_ns, banco.stat().st_size) if banco.exists() else None
            criar_sqlite(base)
            cronometro("SQLite", inicio)
            depois_sqlite = (banco.stat().st_mtime_ns, banco.stat().st_size) if banco.exists() else None
            sqlite_atualizado = depois_sqlite is not None and depois_sqlite != antes_sqlite
            LOG_EXECUCAO.info("Caminho SQLite configurado: %s | atualizado nesta execucao=%s", config.BANCO_SQL, sqlite_atualizado)
            if not sqlite_atualizado:
                LOG_EXECUCAO.warning("SQLite nao foi atualizado; verificar confirmacao interativa e mensagens de colunas ausentes")
            cronometro("Total", inicio_total)
            gerar_log(base, inicio_total, total_arquivos, total_abas)
            LOG_EXECUCAO.info("STATUS=SUCESSO | sqlite_atualizado=%s", sqlite_atualizado)
            print(f"Log salvo em: {caminho_log}")
            titulo("PROCESSO FINALIZADO")
            return base
        except Exception:
            LOG_EXECUCAO.exception("STATUS=FALHA | execucao interrompida")
            print(f"Execucao interrompida. Consulte o log: {caminho_log}")
            raise
        finally:
            LOG_EXECUCAO.info("FIM DA EXECUCAO | tempo_total=%.2f segundos", time.time()-inicio_total)


if __name__ == "__main__":
    executar()
