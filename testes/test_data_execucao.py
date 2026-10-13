import contextlib
import os
from datetime import datetime
import sqlite3
import shutil
import uuid
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import config
import database
import etl


class DataExecucaoTests(unittest.TestCase):
    def test_preserva_valores_e_indices(self):
        df = pd.DataFrame({"Data Fim Execução": [datetime(2026, 7, 2, 14, 25), "02/07/2026 14:25", None, "texto original"]}, index=[8, 2, 2, 9])
        resultado = etl.adicionar_data_execucao(df)
        pd.testing.assert_series_equal(resultado.DATA_EXECUCAO, df["Data Fim Execução"], check_names=False)
        assert resultado.index.equals(df.index) and len(resultado) == len(df)
        assert "DATA_EXECUCAO" not in df.columns
    
    
    def test_ausencia_nao_usa_outras_datas(self):
        df = pd.DataFrame({"Data Início Execução": ["01/07/2026"], "Data Agendada": ["02/07/2026"]})
        assert etl.adicionar_data_execucao(df).DATA_EXECUCAO.isna().all()
    
    
    def test_exportacao_excel_e_sqlite_preserva_data_e_ausencia(self):
        df = pd.DataFrame([{c: None for c in config.COLUNAS_SQLITE} for _ in range(3)])
        df["Número OS"] = [123, 124, 125]
        df["Data Fim Execução"] = pd.Series([datetime(2026, 7, 2, 14, 25), "03/07/2026 09:38", None], dtype=object)
        df = etl.adicionar_data_execucao(df)
        raiz = (Path(config.BASE_DIR) / "work").resolve()
        pasta = raiz / ("test_data_execucao_" + uuid.uuid4().hex)
        assert pasta.resolve().is_relative_to(raiz)
        pasta.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, pasta)
        excel = Path(pasta) / "teste.xlsx"
        banco = Path(pasta) / "teste.db"
        with patch.dict(os.environ, {"EXECUCAO_AGENTE": "1"}), patch.object(config, "ARQUIVO_EXCEL", excel), patch.object(database, "BANCO_SQL", banco):
            etl.salvar_excel(df)
            database.criar_sqlite(df)
        gravado = pd.read_excel(excel)
        assert len(gravado) == 3
        assert gravado.DATA_EXECUCAO.iloc[0] == datetime(2026, 7, 2, 14, 25)
        assert gravado.DATA_EXECUCAO.iloc[1] == "03/07/2026 09:38"
        assert pd.isna(gravado.DATA_EXECUCAO.iloc[2])
        with contextlib.closing(sqlite3.connect(banco)) as conn:
            valores = conn.execute('SELECT DATA_EXECUCAO FROM adesoes').fetchall()
        assert valores == [("2026-07-02 14:25:00",), ("03/07/2026 09:38",), (None,)]
