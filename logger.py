"""Log por execucao, preservando stdout/stderr e sem alterar os dados."""
from contextlib import contextmanager
from datetime import datetime
import logging
from pathlib import Path
import re
import sys
import time

import config
from hd_utils import hd_valido
from uitls import TEMPOS

LOG_EXECUCAO = logging.getLogger("etl_obra")
LOG_EXECUCAO.setLevel(logging.INFO)
LOG_EXECUCAO.propagate = False


class _ConsoleComLog:
    def __init__(self, original, nivel):
        self.original = original
        self.nivel = nivel
        self.pendente = ""

    def write(self, texto):
        retorno = self.original.write(texto)
        self.pendente += re.sub(r"\x1b\[[0-9;]*m", "", texto).replace("\r", "\n")
        while "\n" in self.pendente:
            linha, self.pendente = self.pendente.split("\n", 1)
            if linha.strip():
                nivel = logging.ERROR if "❌" in linha else logging.WARNING if "⚠" in linha else self.nivel
                LOG_EXECUCAO.log(nivel, "%s", linha)
        return retorno

    def flush(self):
        self.original.flush()

    def finalizar(self):
        if self.pendente.strip():
            LOG_EXECUCAO.log(self.nivel, "%s", self.pendente)
        self.pendente = ""
        self.flush()

    def __getattr__(self, nome):
        return getattr(self.original, nome)


@contextmanager
def iniciar_logging(pasta=None):
    pasta = Path(pasta if pasta is not None else config.PASTA_LOGS)
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"etl_obra_{datetime.now():%Y-%m-%d_%H-%M-%S}"
    caminho = pasta / f"{nome}.txt"
    numero = 0
    while caminho.exists():
        numero += 1
        caminho = pasta / f"{nome}_{numero:02d}.txt"
    handler = logging.FileHandler(caminho, mode="x", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    LOG_EXECUCAO.addHandler(handler)
    stdout, stderr = sys.stdout, sys.stderr
    console = _ConsoleComLog(stdout, logging.INFO)
    erros = _ConsoleComLog(stderr, logging.WARNING)
    sys.stdout, sys.stderr = console, erros
    try:
        LOG_EXECUCAO.info("INICIO DA EXECUCAO | %s", datetime.now().isoformat())
        LOG_EXECUCAO.info("Log: %s", caminho)
        yield caminho
    finally:
        try:
            console.finalizar()
            erros.finalizar()
        finally:
            sys.stdout, sys.stderr = stdout, stderr
            LOG_EXECUCAO.removeHandler(handler)
            handler.close()


def _sem_matricula(df):
    if "MATRICULA" not in df.columns:
        return len(df)
    valores = df["MATRICULA"]
    return int((valores.isna() | valores.astype(str).str.strip().eq("")).sum())


def registrar_recuperacao(nome, funcao, df, *args):
    antes = _sem_matricula(df)
    resultado = funcao(df, *args)
    depois = _sem_matricula(resultado)
    LOG_EXECUCAO.info("%s | recuperadas=%s | sem_matricula_antes=%s | sem_matricula_depois=%s", nome, antes-depois, antes, depois)
    return resultado


def registrar_limpeza(funcao, df):
    antes = len(df)
    resultado = funcao(df)
    LOG_EXECUCAO.info("Limpeza | consolidados=%s | linhas_vazias_removidas=%s | restantes=%s", antes, antes-len(resultado), len(resultado))
    return resultado


def gerar_log(df, inicio, total_arquivos, total_abas):
    sem = _sem_matricula(df)
    validos = df["HD"].map(hd_valido)
    origens = df["ORIGEM_HD"].fillna("").value_counts().to_dict()
    LOG_EXECUCAO.info("Fontes WFM | arquivos=%s | abas=%s", total_arquivos, total_abas)
    LOG_EXECUCAO.info("Registros finais=%s | com_matricula=%s | sem_matricula=%s", len(df), len(df)-sem, sem)
    LOG_EXECUCAO.info("HD por origem=%s", origens)
    LOG_EXECUCAO.info("Com HD=%s | sem HD=%s | conflitos=%s | origem OS=%s", int(validos.sum()), int((~validos).sum()), origens.get("CONFLITO", 0), origens.get("OS", 0))
    LOG_EXECUCAO.info("Diagnostico matricula OS=%s", df.attrs.get("diagnostico_matricula_os", {}))
    LOG_EXECUCAO.info("Diagnostico notas adicionais=%s", df.attrs.get("diagnostico_matricula_notas_fallback", {}))
    LOG_EXECUCAO.info("Diagnostico HD=%s", df.attrs.get("diagnostico_hd", {}))
    LOG_EXECUCAO.info("Duplicatas completas preservadas=%s", int(df.duplicated().sum()))
    for etapa, tempo in TEMPOS.items():
        LOG_EXECUCAO.info("Tempo %s: %.2f segundos", etapa, tempo)
    LOG_EXECUCAO.info("Tempo total de execucao: %.2f segundos", time.time()-inicio)
    print(f"Registros finais: {len(df)} | com matricula: {len(df)-sem} | sem matricula: {sem}")
    print(f"HD por origem: {origens}")
    print(f"Com HD: {int(validos.sum())} | sem HD: {int((~validos).sum())} | conflitos: {origens.get('CONFLITO', 0)}")
