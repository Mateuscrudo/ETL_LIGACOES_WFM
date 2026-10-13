import contextlib
import hashlib
import importlib
import io
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid
import warnings

import pandas as pd
import config
import database
import etl
import logger
import main


class EstruturaProjetoTests(unittest.TestCase):
    def setUp(self):
        self.pasta = Path(config.BASE_DIR) / "work" / "test_estrutura" / uuid.uuid4().hex
        raiz = (Path(config.BASE_DIR) / "work" / "test_estrutura").resolve()
        assert self.pasta.resolve().is_relative_to(raiz)
        self.pasta.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.pasta)

    def test_caminhos_relativos_a_raiz(self):
        self.assertEqual(config.ARQUIVO_EXCEL, Path(config.BASE_DIR)/"saida"/"base_obra.xlsx")
        self.assertEqual(config.BANCO_SQL, Path(config.BASE_DIR)/"saida"/"base_obra.db")
        self.assertEqual(config.PASTA_LOGS, Path(config.BASE_DIR)/"logs")

    def test_importacao_main_nao_executa_etl(self):
        with patch("etl.consolidar") as consolidar, patch("etl.salvar_excel") as excel, patch("database.criar_sqlite") as sql:
            importlib.reload(main)
        consolidar.assert_not_called(); excel.assert_not_called(); sql.assert_not_called()
        importlib.reload(main)

    def test_imports_e_configuracao_em_outro_diretorio(self):
        codigo="import main, config; from pathlib import Path; assert config.ARQUIVO_EXCEL == Path(config.BASE_DIR)/'saida'/'base_obra.xlsx'; print('IMPORT_OK')"
        env=os.environ.copy(); env["PYTHONPATH"]=str(config.BASE_DIR)+os.pathsep+env.get("PYTHONPATH", ""); env["PYTHONIOENCODING"]="utf-8"
        r=subprocess.run([sys.executable,"-B","-c",codigo],cwd=self.pasta,env=env,capture_output=True,text=True,encoding="utf-8")
        self.assertEqual(r.returncode,0,r.stderr); self.assertIn("IMPORT_OK",r.stdout)

    def test_logging_console_warning_e_fechamento(self):
        console=io.StringIO()
        with contextlib.redirect_stdout(console):
            with logger.iniciar_logging(self.pasta/"logs") as caminho:
                print("MENSAGEM_CONSOLE")
                with warnings.catch_warnings():
                    warnings.simplefilter("always")
                    warnings.warn("WARNING_CONTROLADO",UserWarning)
        texto=caminho.read_text(encoding="utf-8")
        self.assertIn("MENSAGEM_CONSOLE",console.getvalue()); self.assertIn("MENSAGEM_CONSOLE",texto)
        self.assertIn("WARNING_CONTROLADO",texto); self.assertTrue(caminho.name.startswith("etl_obra_"))
        self.assertEqual(logger.LOG_EXECUCAO.handlers,[])

    def test_logs_distintos_sem_sobrescrever_e_console_restaurado(self):
        stdout,stderr=sys.stdout,sys.stderr
        with logger.iniciar_logging(self.pasta/"logs") as primeiro:
            print("PRIMEIRA_EXECUCAO_CONTROLADA")
        digest=hashlib.sha256(primeiro.read_bytes()).hexdigest()
        with logger.iniciar_logging(self.pasta/"logs") as segundo:
            print("SEGUNDA_EXECUCAO_CONTROLADA")
        self.assertNotEqual(primeiro,segundo)
        self.assertEqual(hashlib.sha256(primeiro.read_bytes()).hexdigest(),digest)
        self.assertIs(sys.stdout,stdout);self.assertIs(sys.stderr,stderr)

    def fixture(self):
        colunas=config.COLUNAS_SQLITE
        a={c:None for c in colunas}; b=a.copy(); vazia=a.copy()
        a.update({"Número OS":123,"Notas de Acatamento":"ADESAO ABC1234","Nota Execução/Não Execução":"A25LM003340","Endereço":"Rua A","Número":0,"ARQUIVO":"fixture.xlsx","ABA":"GERAL"})
        a["Data Fim Execução"] = "02/07/2026 14:25"
        b.update({"Número OS":124,"Notas de Acatamento":"ADESAO PMN9902A","Nota Execução/Não Execução":"Y25LM029939","Endereço":"Rua B","ARQUIVO":"fixture.xlsx","ABA":"GERAL"})
        # HD_WFM e uma coluna tecnica derivada; fixture sem coluna para exercitar extracao.
        df=pd.DataFrame([a,b,vazia]).drop(columns=["HD_WFM","HD","ORIGEM_HD"])
        df.loc[2,["ARQUIVO","ABA"]]=["fixture.xlsx","GERAL"]
        return df

    def ambiente(self):
        from contextlib import ExitStack
        ctx=ExitStack(); saida=self.pasta/"saida"; logs=self.pasta/"logs"; controle=self.pasta/"controle"
        controle.mkdir(exist_ok=True)
        ctx.enter_context(patch.object(config,"ARQUIVO_EXCEL",saida/"base_obra.xlsx"))
        ctx.enter_context(patch.object(config,"BANCO_SQL",saida/"base_obra.db"))
        ctx.enter_context(patch.object(config,"PASTA_LOGS",logs))
        ctx.enter_context(patch.object(config,"PASTA_CONTROLE",controle))
        ctx.enter_context(patch.object(database,"BANCO_SQL",saida/"base_obra.db"))
        ctx.enter_context(patch.dict(os.environ,{"EXECUCAO_AGENTE":"1"}))
        ctx.enter_context(patch.object(main,"consolidar",return_value=(self.fixture(),1,1)))
        return ctx,saida,logs

    def test_entrypoint_exportacao_e_log_controlados(self):
        ambiente,saida,logs=self.ambiente()
        with ambiente,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            base=main.executar()
        excel=pd.read_excel(saida/"base_obra.xlsx")
        with contextlib.closing(sqlite3.connect(saida/"base_obra.db")) as conn:
            sql=pd.read_sql_query("SELECT * FROM adesoes",conn)
            self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0],"ok")
        self.assertEqual(len(base),2); self.assertEqual(len(excel),2); self.assertEqual(len(sql),2)
        for dados in [excel,sql]:
            self.assertTrue({"HD_WFM","HD","ORIGEM_HD"}.issubset(dados.columns))
            self.assertEqual(dados.DATA_EXECUCAO.iloc[0], "02/07/2026 14:25")
            self.assertTrue(pd.isna(dados.DATA_EXECUCAO.iloc[1]))
            self.assertEqual(dados.MATRICULA.tolist(),["ABC1234","PMN9902A"])
            self.assertEqual(dados.HD.tolist(),["A25LM003340","Y25LM029939"])
        texto=next(logs.glob("*.txt")).read_text(encoding="utf-8")
        for trecho in ["INICIO DA EXECUCAO","STATUS=SUCESSO","linhas_vazias_removidas=1","sem_matricula=0","Com HD=2","Matricula pela OS","Matricula pelo endereco","HD por origem","FIM DA EXECUCAO"]:
            self.assertIn(trecho,texto)

    def test_falha_de_exportacao_fica_no_log(self):
        ambiente,saida,logs=self.ambiente()
        with ambiente,patch.object(main,"salvar_excel",side_effect=PermissionError("BLOQUEIO_CONTROLADO")),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(PermissionError):main.executar()
        texto=next(logs.glob("*.txt")).read_text(encoding="utf-8")
        self.assertIn("STATUS=FALHA",texto); self.assertIn("PermissionError",texto); self.assertIn("BLOQUEIO_CONTROLADO",texto)
        self.assertIn("FIM DA EXECUCAO",texto); self.assertNotIn("STATUS=SUCESSO",texto)
        self.assertFalse((saida/"base_obra.db").exists())


if __name__=="__main__":
    unittest.main()
