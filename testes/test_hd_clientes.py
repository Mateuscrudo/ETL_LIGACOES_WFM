import unittest
from unittest.mock import patch
import pandas as pd
from hd_utils import preencher_hd, indexar_hd_clientes, ABAS_CLIENTES


class HDClientesTests(unittest.TestCase):
    def aplicar(self, wfm=None, geral=None, clientes=None, matricula="AR1"):
        df = pd.DataFrame({"MATRICULA": [matricula], "HD_WFM": [wfm]}, index=[17])
        with patch("hd_utils.construir_indice_hd", return_value=geral or {}), patch(
                "hd_utils.construir_indice_hd_clientes", return_value=clientes or {}):
            return preencher_hd(df, "controles")

    def test_fallback_cliente(self):
        r = self.aplicar(clientes={"AR1": [{"A25LM123"}]})
        self.assertEqual((r.iloc[0].HD, r.iloc[0].ORIGEM_HD), ("A25LM123", "CLIENTE"))

    def test_prioridade_wfm(self):
        r = self.aplicar(wfm="Y19L123", clientes={"AR1": [{"A25LM123"}]})
        self.assertEqual(r.iloc[0].ORIGEM_HD, "WFM")

    def test_prioridade_comercial(self):
        r = self.aplicar(geral={"AR1": {"Y19L123": {"COMERCIAL"}}}, clientes={"AR1": [{"A25LM123"}]})
        self.assertEqual(r.iloc[0].ORIGEM_HD, "COMERCIAL")

    def test_prioridade_social(self):
        r = self.aplicar(geral={"AR1": {"Y19L123": {"SOCIAL"}}}, clientes={"AR1": [{"A25LM123"}]})
        self.assertEqual(r.iloc[0].ORIGEM_HD, "SOCIAL")

    def test_nao_encontrada(self):
        self.assertTrue(pd.isna(self.aplicar().iloc[0].HD))

    def test_mesmo_hd_repetido_na_fonte_cliente(self):
        r = self.aplicar(clientes={"AR1": [{"A25LM123"}, {"A25LM123"}]})
        self.assertEqual(r.iloc[0].ORIGEM_HD, "CLIENTE")
        self.assertEqual(r.iloc[0].HD, "A25LM123")

    def test_multiplos_hds_seleciona_maior_ano(self):
        r = self.aplicar(clientes={"AR1": [{"A25LM123", "Y19L123"}]})
        self.assertEqual((r.iloc[0].HD, r.iloc[0].ORIGEM_HD), ("A25LM123", "CLIENTE"))

    def test_sem_hd_valido(self):
        self.assertTrue(pd.isna(self.aplicar(clientes={"AR1": [set()]}).iloc[0].HD))

    def test_linhas_indices_repetidos(self):
        df = pd.DataFrame({"MATRICULA": ["AR1", "AR1", None], "HD_WFM": [None]*3}, index=[8, 8, 2])
        with patch("hd_utils.construir_indice_hd", return_value={}), patch("hd_utils.construir_indice_hd_clientes", return_value={"AR1": [{"Y19L123"}]}):
            r = preencher_hd(df, "controles")
        self.assertEqual(len(r), 3)
        self.assertTrue(r.index.equals(df.index))
        self.assertEqual(r.HD.notna().sum(), 2)

    def test_indexacao_exata_e_compostos(self):
        indice = {}
        indexar_hd_clientes(pd.DataFrame({"Matricula": [" ar1 ", "AR1", "AR-1"], "Hidrometro": ["Y19L123", "A25LM123 / Y19L123", "123456"]}), indice)
        self.assertEqual(len(indice["AR1"]), 2)
        self.assertEqual(len(indice["AR1"][1]), 2)
        self.assertEqual(indice["AR-1"], [set()])

    def test_abas_validadas(self):
        self.assertIn("dados de cliente deep", ABAS_CLIENTES)
        self.assertIn("dados dos clientes", ABAS_CLIENTES)
        self.assertNotIn("dados clientes appdeep", ABAS_CLIENTES)

    def test_cliente_mais_recente_entre_ocorrencias(self):
        r = self.aplicar(clientes={"AR1": [{"A17L395245"}, {"A25LM1088153"}]})
        self.assertEqual((r.iloc[0].HD, r.iloc[0].ORIGEM_HD), ("A25LM1088153", "CLIENTE"))
        self.assertEqual(r.attrs["diagnostico_hd"]["conflitos_resolvidos_por_ano"], 1)

    def test_cliente_empate_no_maior_ano(self):
        r = self.aplicar(clientes={"AR1": [{"A17L1"}, {"Y25L2"}, {"A25LM3"}]})
        self.assertEqual(r.iloc[0].ORIGEM_HD, "CONFLITO")
        self.assertTrue(pd.isna(r.iloc[0].HD))

    def test_conflito_superior_preservado(self):
        r = self.aplicar(geral={"AR1": {"Y25L123": {"SOCIAL"}, "A25LM123": {"SOCIAL"}}}, clientes={"AR1": [{"Y11F123"}]})
        self.assertEqual(r.iloc[0].ORIGEM_HD, "CONFLITO")

if __name__ == "__main__":
    unittest.main()
