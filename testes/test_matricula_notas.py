import unittest

import pandas as pd

from regex_utils import extrair_matricula, extrair_matricula_complemento, matricula_valida
from etl import preencher_matricula_nota, preencher_matricula_coluna_n


# Fragmento, codigo esperado, arquivo WFM, aba e linha de origem.
CASOS_REAIS = [('ADESAO:AR0045', 'AR0045', 'Arei\xe3o_subs.xlsx', 'ABRIL-26', 2), ('ADESAOARN4229', 'ARN4229', 'Arei\xe3o.xlsx', 'ABRIL-26', 30), ('ADESAO (PM1440)', 'PM1440', 'Pedreira Matarazzo_nova.xlsx', 'FEVEREIRO ', 29), ('ADESAO 2146-CGN', '2146-CGN', 'Barreira_nova.xlsx', 'Maio', 39), ('ADESAO:  3114-CG', '3114-CG', 'Canta Galo _nova.xlsx', 'MAIO', 115), ('ADESAO RGI: MC8143', 'MC8143', 'Mar e C\xe9u_nova.xlsx', 'JANEIRO-26', 10), ('ADESAO: ---AR1094', 'AR1094', 'Arei\xe3o_subs.xlsx', 'MAIO-26', 236), ('4600057296ADESAO: AR0100', 'AR0100', 'Arei\xe3o.xlsx', 'NOVEMBRO', 2), ('VULNERAVELADESAO BAN0177', 'BAN0177', 'Barreira_nova.xlsx', 'Maio', 105)]
CASOS_REAIS += [('SOCIALADESAO: ARN0063', 'ARN0063', 'Arei\xe3o.xlsx', 'ABRIL-26', 4), ('SOCIALADESAOBAN0631', 'BAN0631', 'Barreira_subs.xlsx', 'Maio', 49), ('VULNERAVEISADESAO: MC5040', 'MC5040', 'Mar e C\xe9u_nova.xlsx', 'JULHO', 410)]


class MatriculaNotasTests(unittest.TestCase):
    def test_matricula_explicita(self):
        for nota in ("Matr\u00edcula: AR0045", "matricula - AR0045"):
            with self.subTest(nota=nota):
                self.assertEqual(extrair_matricula(nota), "AR0045")

    def test_adesao_explicita(self):
        for nota in ("Ades\u00e3o: 2146-CG", "adesao - 2146-CG"):
            with self.subTest(nota=nota):
                self.assertEqual(extrair_matricula(nota), "2146-CG")

    def test_codigo_sem_contexto(self):
        for nota in ("ABC1234", "PROTOCOLO ABC1234", "EQUIPAMENTO AB123456", "2146-CGN"):
            with self.subTest(nota=nota):
                self.assertIsNone(extrair_matricula(nota))

    def test_outros_codigos(self):
        self.assertIsNone(extrair_matricula("OS ABC1234; protocolo XYZ9876; equipamento AB123456"))
        self.assertIsNone(extrair_matricula("Adesao pendente; protocolo ABC1234"))
        self.assertIsNone(extrair_matricula("SEMADESAO ABC1234"))

    def test_nota_vazia(self):
        for nota in (None, pd.NA, float("nan"), "", "   "):
            with self.subTest(nota=nota):
                self.assertIsNone(extrair_matricula(nota))

    def test_matricula_junto_de_outros_codigos(self):
        self.assertEqual(extrair_matricula("OS ABC1234; Matricula: AR0045; protocolo XYZ9876"), "AR0045")

    def test_formatos_reais(self):
        for nota, esperado, arquivo, aba, linha in CASOS_REAIS:
            with self.subTest(arquivo=arquivo, aba=aba, linha=linha):
                self.assertEqual(extrair_matricula(nota), esperado)

    def test_identificacoes_conflitantes(self):
        self.assertIsNone(extrair_matricula("Adesao AR0045; Matricula ARN4229"))
        self.assertEqual(extrair_matricula("Adesao AR0045; Matricula AR0045"), "AR0045")

    def test_nao_truncar_codigo(self):
        for nota in ("Adesao MC9015A", "Matricula ABC1234_X", "Adesao ABC1234-XYZ", "Adesao ABC1234/5"):
            with self.subTest(nota=nota):
                self.assertIsNone(extrair_matricula(nota))

    def test_preenchimento_das_notas_preserva_matricula_existente(self):
        df=pd.DataFrame({"Notas de Acatamento": ["ABC1234", "Adesao AR0045", "Adesao ARN4229"],
                         "MATRICULA": [None, None, "JA_EXISTENTE"]})
        resultado=preencher_matricula_nota(df)
        self.assertTrue(pd.isna(resultado.loc[0, "MATRICULA"]))
        self.assertEqual(resultado.loc[1, "MATRICULA"], "AR0045")
        self.assertEqual(resultado.loc[2, "MATRICULA"], "JA_EXISTENTE")

    def test_oito_formatos_autorizados(self):
        for codigo in ("AB1234", "ABC1234", "AB12345", "ABC12345",
                       "AB123456", "ABC123456", "1234-AB", "2146-CGN"):
            with self.subTest(codigo=codigo):
                self.assertEqual(extrair_matricula("ADESAO: " + codigo), codigo)
                self.assertEqual(extrair_matricula_complemento(codigo), codigo)
                self.assertTrue(matricula_valida(codigo))

    def test_formatos_fora_da_lista_nao_ampliados(self):
        for codigo in ("A1234", "AB123", "ABC123", "ABCD1234", "AB1234567",
                       "ABC1234567", "123-AB", "12345-AB", "1234-ABCD", "2146-CGNN",
                       "ABC1234-XYZ", "ABC1234/5", "ABC1234_X", "1234-AB-C"):
            with self.subTest(codigo=codigo):
                self.assertIsNone(extrair_matricula("ADESAO: " + codigo))
                self.assertIsNone(extrair_matricula_complemento(codigo))

    def test_regra_complemento_preservada(self):
        self.assertEqual(extrair_matricula_complemento("ABC1234"), "ABC1234")
        df=pd.DataFrame({"Complemento": ["ABC1234"], "MATRICULA": [None]})
        self.assertEqual(preencher_matricula_coluna_n(df).loc[0, "MATRICULA"], "ABC1234")


if __name__ == "__main__":
    unittest.main()
