from io import BytesIO
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import pandas as pd
import etl
from matricula_os import (normalizar_os, indexar_matriculas_os,
                          indexar_arquivo_matriculas_os, preencher_matricula_os)


class MatriculaOSTests(unittest.TestCase):
    def aplicar(self, ordens, indice, matriculas=None, index=None):
        df = pd.DataFrame({"Número OS": ordens,
                           "MATRICULA": matriculas or [None]*len(ordens)}, index=index)
        with patch("matricula_os.construir_indice_matriculas_os", return_value=indice):
            return preencher_matricula_os(df, "controles")

    def test_representacoes_equivalentes(self):
        r = self.aplicar([123456, "123456", 123456.0], {"123456": {"AR0001"}})
        self.assertEqual(r.MATRICULA.tolist(), ["AR0001"]*3)

    def test_mesma_matricula_repetida(self):
        indice = {}
        indexar_matriculas_os(pd.DataFrame({"OS / FORNECIMENTO": [123, 123, 123],
                                           "ADESAO": ["AR0001", " ar0001 ", "AR0001"]}), indice)
        self.assertEqual(indice, {"123": {"AR0001"}})
        self.assertEqual(self.aplicar([123], indice).iloc[0].MATRICULA, "AR0001")

    def test_matriculas_distintas_nao_escolhe(self):
        r = self.aplicar([123], {"123": {"AR0001", "AR0002"}})
        self.assertTrue(pd.isna(r.iloc[0].MATRICULA))
        self.assertEqual(r.attrs["diagnostico_matricula_os"]["ambiguas"], 1)

    def test_os_ausente_sem_matricula(self):
        r = self.aplicar([124, None, ""], {"123": {"AR0001"}})
        self.assertTrue(r.MATRICULA.isna().all())

    def test_nao_altera_os_zeros_hifens(self):
        for valor in ("001234", "123-456", "123 456"):
            self.assertEqual(normalizar_os(valor), valor)
        r = self.aplicar(["00123", "12-3"], {"123": {"AR0001"}})
        self.assertTrue(r.MATRICULA.isna().all())

    def test_apenas_matriculas_validas(self):
        indice = {}
        indexar_matriculas_os(pd.DataFrame({"OS": [123]*4,
                                           "MATRICULA": ["1234-CGNN", "AR123", "123456", "AR0001"]}), indice)
        self.assertEqual(indice, {"123": {"AR0001"}})

    def test_preserva_matricula_existente(self):
        r = self.aplicar([123], {"123": {"AR0001"}}, ["AR0002"])
        self.assertEqual(r.iloc[0].MATRICULA, "AR0002")

    def test_indices_repetidos_e_nao_multiplicacao(self):
        r = self.aplicar([123, 124, 125], {"123": {"AR0001"}, "124": {"AR0002"}}, index=[7, 7, 20])
        self.assertEqual(r.MATRICULA.tolist()[:2], ["AR0001", "AR0002"])
        self.assertEqual(r.index.tolist(), [7, 7, 20])
        self.assertEqual(len(r), 3)

    def test_fluxo_os_antes_endereco_e_ambiguidades(self):
        df = pd.DataFrame({"Número OS": [123, 124, 125], "MATRICULA": [None]*3,
                           "ENDEREÇO_ID": ["R A 1", "R B 2", "R C 3"]}, index=[7, 7, 20])
        os_indice = {"123": {"AR0001"}, "124": {"AR0002", "AR0003"}}
        controle = {"indice": {"R A 1": {"ZZ0010"}, "R B 2": {"AR0004"},
                               "R C 3": {"AR0005", "AR0006"}},
                    "arquivos_processados": 1, "abas_processadas": 1, "registros_processados": 4}
        with patch("etl.adicionar_endereco_id", side_effect=lambda x: x), patch(
                "matricula_os.construir_indice_matriculas_os", return_value=os_indice), patch(
                "etl.construir_indice_controle", return_value=controle), patch(
                "etl.preencher_hd", side_effect=lambda x, pasta: x), patch("etl.terminal.info"), patch("etl.terminal.aviso"):
            r = etl.tratar(df)
        self.assertEqual(r.MATRICULA.tolist()[:2], ["AR0001", "AR0004"])
        self.assertTrue(pd.isna(r.iloc[2].MATRICULA))
        self.assertEqual(r.index.tolist(), [7, 7, 20])
        self.assertEqual(len(r), 3)

    def test_endereco_unico_com_matricula_invalida_nao_preenche(self):
        df = pd.DataFrame({"MATRICULA": [None], "ENDEREÇO_ID": ["R A 1"]})
        controle = {"indice": {"R A 1": {"1234-CGNN"}}, "arquivos_processados": 1,
                    "abas_processadas": 1, "registros_processados": 1}
        with patch("etl.construir_indice_controle", return_value=controle), patch("etl.terminal.info"):
            r = etl.aplicar_regra_01a(df)
        self.assertTrue(pd.isna(r.iloc[0].MATRICULA))

    def test_nnnn_lll_recuperavel_por_os_e_endereco(self):
        r = self.aplicar([123], {"123": {"2146-CGN"}})
        self.assertEqual(r.iloc[0].MATRICULA, "2146-CGN")
        df = pd.DataFrame({"MATRICULA": [None], "ENDEREÇO_ID": ["R A 1"]})
        controle = {"indice": {"R A 1": {"2146-CGN"}}, "arquivos_processados": 1,
                    "abas_processadas": 1, "registros_processados": 1}
        with patch("etl.construir_indice_controle", return_value=controle), patch("etl.terminal.info"):
            r = etl.aplicar_regra_01a(df)
        self.assertEqual(r.iloc[0].MATRICULA, "2146-CGN")

    def test_xml_cabecalho_deslocado_lacunas_e_os_exata(self):
        buffer = BytesIO()
        with ZipFile(buffer, "w") as z:
            z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Outra aba" sheetId="1" r:id="rId1"/></sheets></workbook>')
            z.writestr("xl/_rels/workbook.xml.rels", '<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
            z.writestr("xl/worksheets/sheet1.xml", '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:C1048576"/><sheetData><row r="3"><c r="A3" t="inlineStr"><is><t>OS / FORNECIMENTO</t></is></c><c r="B3" t="inlineStr"><is><t>ADESAO</t></is></c><c r="C3" t="inlineStr"><is><t>Hidrometro</t></is></c></row><row r="9"><c r="A9"><v>123.0</v></c><c r="B9" t="inlineStr"><is><t>AR0001</t></is></c><c r="C9" t="inlineStr"><is><t>A25LM123</t></is></c></row><row r="20"><c r="A20"><v>123</v></c><c r="B20" t="inlineStr"><is><t>AR0001</t></is></c></row></sheetData></worksheet>')
        indice = {}
        with patch("matricula_os.ZipFile", return_value=ZipFile(BytesIO(buffer.getvalue()))):
            indexar_arquivo_matriculas_os("controle.xlsx", indice, {"123"})
        self.assertEqual(indice, {"123": {"AR0001"}})


if __name__ == "__main__":
    unittest.main()
