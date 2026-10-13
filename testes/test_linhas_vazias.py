import unittest
from unittest.mock import patch

import pandas as pd

from etl import consolidar, limpar_dados_basicos


class LinhasVaziasTests(unittest.TestCase):
    def test_linha_completamente_vazia(self):
        df = pd.DataFrame({"campo": [None, pd.NA, float("nan"), "", "   ", "\t\n"]})
        resultado = limpar_dados_basicos(df)
        self.assertTrue(resultado.empty)
        self.assertEqual(resultado.columns.tolist(), df.columns.tolist())

    def test_linha_vazia_com_metadados(self):
        df = pd.DataFrame([{"campo": None, "outro": "   ", "ARQUIVO": "a.xlsx", "ABA": "GERAL"}])
        self.assertTrue(limpar_dados_basicos(df).empty)

    def test_apenas_um_dado_valido(self):
        # Zero e False tambem sao dados; nao usar teste de valor booleano.
        for valor in ("observacao", 0, False):
            with self.subTest(valor=valor):
                df = pd.DataFrame([{"campo": valor, "outro": None, "ARQUIVO": "a.xlsx", "ABA": "GERAL"}])
                pd.testing.assert_frame_equal(limpar_dados_basicos(df), df)

    def test_linha_normal_preenchida(self):
        df = pd.DataFrame([{"campo": "Rua Teste", "numero": 123, "ARQUIVO": "a.xlsx", "ABA": "GERAL"}])
        pd.testing.assert_frame_equal(limpar_dados_basicos(df), df)

    def test_somente_colunas_tecnicas(self):
        df = pd.DataFrame([{"ARQUIVO": "a.xlsx", "ABA": "GERAL"}])
        self.assertTrue(limpar_dados_basicos(df).empty)

    def test_consolidacao_seguida_de_limpeza(self):
        origem = pd.DataFrame({"campo": [None, "   ", "valido"], "numero": [None, None, 123]})
        original = origem.copy(deep=True)
        with patch("etl.os.listdir", return_value=["a.xlsx"]), \
             patch("etl.pd.read_excel", return_value={"GERAL": origem}), \
             patch("etl.terminal.info"), \
             patch("etl.tqdm", side_effect=lambda itens, **kwargs: itens):
            base, arquivos, abas = consolidar()
        resultado = limpar_dados_basicos(base)
        self.assertEqual((arquivos, abas), (1, 1))
        self.assertEqual(resultado.index.tolist(), [2])
        self.assertEqual(resultado.iloc[0]["campo"], "valido")
        self.assertEqual(resultado.iloc[0]["ARQUIVO"], "a.xlsx")
        self.assertEqual(resultado.iloc[0]["ABA"], "GERAL")
        pd.testing.assert_frame_equal(origem, original)


if __name__ == "__main__":
    unittest.main()
