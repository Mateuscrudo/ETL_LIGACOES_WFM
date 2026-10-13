import unittest
from unittest.mock import patch
import pandas as pd
import etl
from regex_utils import analisar_matricula_nota_fallback as candidatos

class MatriculaNotasFallbackTests(unittest.TestCase):
    def aplicar(self, acatamento=None, execucao=None, matricula=None):
        return etl.preencher_matricula_notas_fallback(pd.DataFrame({"MATRICULA":[matricula],"Notas de Acatamento":[acatamento],"Nota Execução/Não Execução":[execucao]}))
    def test_espaco_letras_numeros(self):
        for nota, codigo in [("PMN 101629","PMN101629"),("PQ 1052","PQ1052")]:
            self.assertEqual(candidatos(nota),{codigo})
    def test_espacos_hifen(self):
        for nota,codigo in [("0018 - CGN","0018-CGN"),("0037- CGN","0037-CGN"),("0042 - CG","0042-CG")]:
            self.assertEqual(candidatos(nota),{codigo})
    def test_palavras_adjacentes_confirmadas(self):
        for nota,codigo in [("PMN7745HIDROMETRO","PMN7745"),("AR5267ANEXO","AR5267")]:
            self.assertEqual(candidatos(nota),{codigo})
    def test_texto_irregular(self):
        for nota,codigo in [("ADESÕA: PMN7742","PMN7742"),("DA L.APQ0974","APQ0974"),("ADESAORECUPERANDO DADOS.VB0628","VB0628")]:
            self.assertEqual(candidatos(nota),{codigo})
    def test_a_final_inteiro(self):
        for codigo in ["PMN9902A","MT0468A","VN1281A","JC0453A"]:
            self.assertEqual(candidatos(codigo),{codigo})
            self.assertEqual(self.aplicar(codigo).iloc[0].MATRICULA,codigo)
    def test_formatos_base(self):
        for codigo in ["AB1234","ABC1234","AB12345","ABC12345","AB123456","ABC123456","1234-AB","1234-ABC"]:
            self.assertEqual(candidatos(codigo),{codigo})
    def test_nao_trunca(self):
        for codigo in ["PMN9902B","AB1234567","AB123","ABCD1234","1234-ABCD","AB1234_A","AB1234/5","AB1234-XYZ","PMN9902AOUTRA"]:
            self.assertEqual(candidatos(codigo),set())
    def test_multiplos_sem_escolha(self):
        r=self.aplicar("PMN9902A MT0468A","ADESAO AR5267")
        self.assertTrue(pd.isna(r.iloc[0].MATRICULA))
        self.assertEqual(r.attrs["diagnostico_matricula_notas_fallback"]["ambiguos"],1)
    def test_repeticoes_mesmo_codigo(self):
        self.assertEqual(self.aplicar("PMN 101629; PMN101629").iloc[0].MATRICULA,"PMN101629")
    def test_ambiguidade_delimitacao(self):
        nota="VN1281AREGULARIZACAO ... ADESAO VN1281A"
        self.assertEqual(candidatos(nota),{"VN1281","VN1281A"})
        self.assertTrue(pd.isna(self.aplicar(nota).iloc[0].MATRICULA))
    def test_prioridade_acatamento(self):
        r=self.aplicar("PMN9902A","ADESAO AR5267")
        self.assertEqual(r.iloc[0].MATRICULA,"PMN9902A")
        self.assertEqual(r.attrs["diagnostico_matricula_notas_fallback"]["ACATAMENTO"],1)
    def test_fallback_execucao(self):
        r=self.aplicar("SEM CODIGO","ADESAO JC0453A")
        self.assertEqual(r.iloc[0].MATRICULA,"JC0453A")
        self.assertEqual(r.attrs["diagnostico_matricula_notas_fallback"]["EXECUCAO"],1)
    def test_matricula_existente(self):
        self.assertEqual(self.aplicar("PMN9902A","AR5267","VB0628").iloc[0].MATRICULA,"VB0628")
    def test_vazios(self):
        for valor in [None,pd.NA,""," "]:
            self.assertEqual(candidatos(valor),set())
        self.assertTrue(pd.isna(self.aplicar().iloc[0].MATRICULA))
    def test_indices_repetidos_sem_multiplicar(self):
        df=pd.DataFrame({"MATRICULA":[None,None,"VB0628"],"Notas de Acatamento":["PMN9902A","AR5267",None]},index=[7,7,20])
        r=etl.preencher_matricula_notas_fallback(df)
        self.assertEqual(r.MATRICULA.tolist(),["PMN9902A","AR5267","VB0628"])
        self.assertEqual(r.index.tolist(),[7,7,20]);self.assertEqual(len(r),len(df))
        self.assertTrue(df.MATRICULA.iloc[:2].isna().all())
    def test_fluxo_os_endereco_notas_hd(self):
        df=pd.DataFrame({"MATRICULA":[None]*3,"Notas de Acatamento":["PMN9902A","MT0468A","AR5267ANEXO"]})
        def os(df,pasta):
            r=df.copy();r.iloc[0,r.columns.get_loc("MATRICULA")]="VB0628";return r
        def endereco(df):
            r=df.copy();r.iloc[1,r.columns.get_loc("MATRICULA")]="PQ1052";return r
        def hd(df,pasta):
            self.assertEqual(df.MATRICULA.tolist(),["VB0628","PQ1052","AR5267"]);return df
        with patch("etl.adicionar_endereco_id",new=lambda df:df),patch("etl.preencher_matricula_os",new=os),patch("etl.aplicar_regra_01a",new=endereco),patch("etl.preencher_hd",new=hd),patch("etl.terminal.info"):
            r=etl.tratar(df)
        self.assertEqual(r.MATRICULA.tolist(),["VB0628","PQ1052","AR5267"])

if __name__=="__main__":
    unittest.main()
