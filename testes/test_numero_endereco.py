import unittest

import pandas as pd

from endereco_utils import criar_endereco_id, normalizar_numero_endereco
from controle_utils import criar_endereco_controle, buscar_matricula_por_endereco


class NumeroEnderecoTests(unittest.TestCase):
    def test_equivalentes(self):
        for numero in (123, 123.0, "123.0", " 123.00 "):
            with self.subTest(numero=numero):
                self.assertEqual(normalizar_numero_endereco(numero), "123")
                self.assertEqual(criar_endereco_id("Rua Teste", numero, None), "R TESTE 123")
                self.assertEqual(criar_endereco_controle("Rua Teste", numero, None), "R TESTE 123")

    def test_vazios(self):
        for numero in (None, pd.NA, float("nan"), "", "   "):
            with self.subTest(numero=numero):
                self.assertEqual(normalizar_numero_endereco(numero), "")
                self.assertEqual(criar_endereco_id("Rua Teste", numero, None), "R TESTE")
                self.assertEqual(criar_endereco_controle("Rua Teste", numero, None), "R TESTE")

    def test_conteudo_adicional_preservado(self):
        for numero, chave in (("123-A", "123 A"), ("123 apto 2", "123 APTO 2"),
                              ("123/125", "123 125"), ("123.5", "123 5"),
                              ("123.0-A", "123 0 A"), ("S/N", "S")):
            with self.subTest(numero=numero):
                self.assertEqual(normalizar_numero_endereco(numero), numero)
                self.assertEqual(criar_endereco_id("Rua Teste", numero, "Casa 2"), "R TESTE " + chave + " CASA 2")
                self.assertEqual(criar_endereco_controle("Rua Teste", numero, "Casa 2"), "R TESTE " + chave + " CASA 2")

    def test_complemento_e_logradouro_nao_alterados(self):
        self.assertEqual(criar_endereco_id("Rua 123.0", "123.0", "Bloco 2.0"), "R 123 0 123 BLOCO 2 0")
        self.assertEqual(criar_endereco_controle("Rua 123.0", "123.0", "Bloco 2.0"), "R 123 0 123 BLOCO 2 0")

    def test_cruzamento_entre_tipos(self):
        indice = {criar_endereco_controle("Rua Teste", 123, "Casa 2"): {"ABC1234"}}
        for numero in (123, 123.0, "123.0"):
            with self.subTest(numero=numero):
                self.assertEqual(buscar_matricula_por_endereco(criar_endereco_id("Rua Teste", numero, "Casa 2"), indice), "ABC1234")
        self.assertIsNone(buscar_matricula_por_endereco(criar_endereco_id("Rua Teste", "123-A", "Casa 2"), indice))


if __name__ == "__main__":
    unittest.main()
