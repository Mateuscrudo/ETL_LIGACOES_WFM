import os
import sqlite3
import unittest
from collections import defaultdict
from unittest.mock import patch

import pandas as pd

import config
from hd_utils import (extrair_hd, hd_valido, identificar_colunas_hd,
                      indexar_hd_controle, preencher_hd)


class HDIntegracaoTests(unittest.TestCase):
    def aplicar(self, wfm=None, comercial=None, social=None, matricula='AR0045'):
        controle = pd.DataFrame({'ADESAO': ['AR0045'],
                                 'Hidrômetro Comercial': [comercial],
                                 'Hidrômetro Social': [social]})
        indice = defaultdict(dict)
        indexar_hd_controle(controle, indice)
        df = pd.DataFrame({'HD_WFM': [wfm], 'MATRICULA': [matricula]})
        with patch('hd_utils.construir_indice_hd', return_value=indice) as carregar:
            resultado = preencher_hd(df, 'controles')
        return resultado.iloc[0], carregar

    def test_formatos_validos_inclusive_serie_s(self):
        for hd in ('A25LM003340', 'Y19L023938', 'Y25LM029939', 'A19S20301',
                   'Y11F162958', 'A22G022413', 'Y08T002069', 'A25SG0197833',
                   'Y09TL311254', 'A175716186', 'Y11N197685', 'Y15K081930',
                   'Y04X134233', 'A18Z018802'):
            with self.subTest(hd=hd):
                self.assertTrue(hd_valido(hd))
                self.assertEqual(extrair_hd('Instalado ' + hd), hd)

    def test_formatos_invalidos(self):
        for hd in (None, pd.NA, '', 'BAIXA INTERNA', 'Y20Q746226', 'ABC1234',
                   'A19SL20301', 'A25LM', 'A25LM123ABC', '4852135401',
                   '018L504248', 'A225LM0260421', 'A25LM0264919C'):
            with self.subTest(hd=hd):
                self.assertFalse(hd_valido(hd))

    def test_wfm_valido_prevalece_sem_consultar_controle(self):
        linha, carregar = self.aplicar('A19S20301', 'Y25LM029939')
        self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('A19S20301', 'WFM'))
        self.assertEqual(linha['HD_WFM'], 'A19S20301')
        carregar.assert_not_called()

    def test_wfm_vazio_recupera_comercial(self):
        for vazio in (None, pd.NA, ''):
            with self.subTest(vazio=vazio):
                linha, carregar = self.aplicar(vazio, 'A25LM003340')
                self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('A25LM003340', 'COMERCIAL'))
                carregar.assert_called_once_with('controles', {'AR0045'})

    def test_baixa_interna_consulta_controle_e_preserva_auditoria(self):
        linha, _ = self.aplicar('BAIXA INTERNA', 'Y19L023938')
        self.assertEqual(linha['HD'], 'Y19L023938')
        self.assertEqual(linha['HD_WFM'], 'BAIXA INTERNA')

    def test_wfm_invalido_consulta_controle(self):
        linha, _ = self.aplicar('Y20Q746226', 'Y25LM029939')
        self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('Y25LM029939', 'COMERCIAL'))

    def test_manter_hm_recupera_social(self):
        linha, _ = self.aplicar(None, 'MANTER HM', 'A19S20301')
        self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('A19S20301', 'SOCIAL'))

    def test_manter_hm_sem_social_valido(self):
        linha, _ = self.aplicar(None, 'MANTER HM', 'Y20Q746226')
        self.assertTrue(pd.isna(linha['HD']))
        self.assertTrue(pd.isna(linha['ORIGEM_HD']))

    def test_social_usado_sem_manter_hm(self):
        for comercial in (None, '', 'BAIXA INTERNA'):
            linha, _ = self.aplicar(None, comercial, 'A19S20301')
            self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('A19S20301', 'SOCIAL'))

    def test_comercial_prevalece_sobre_social(self):
        linha, _ = self.aplicar(None, 'Y25LM029939', 'A19S20301')
        self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('Y25LM029939', 'COMERCIAL'))

    def test_conflito_nao_escolhe_hd(self):
        indice = defaultdict(dict)
        controle = pd.DataFrame({'ADESAO': ['AR0045', 'AR0045'],
                                 'Hidrômetro Comercial': ['A25LM003340', 'Y25LM029939']})
        indexar_hd_controle(controle, indice)
        with patch('hd_utils.construir_indice_hd', return_value=indice):
            resultado = preencher_hd(pd.DataFrame({'MATRICULA': ['AR0045']}), 'controles')
        self.assertTrue(pd.isna(resultado.iloc[0]['HD']))
        self.assertEqual(resultado.iloc[0]['ORIGEM_HD'], 'CONFLITO')

    def test_conflito_na_mesma_celula(self):
        linha, _ = self.aplicar(None, 'A25LM003340 / Y25LM029939')
        self.assertTrue(pd.isna(linha['HD']))
        self.assertEqual(linha['ORIGEM_HD'], 'CONFLITO')

    def test_ausencia_total_de_hd(self):
        linha, _ = self.aplicar()
        self.assertTrue(pd.isna(linha['HD']))
        self.assertTrue(pd.isna(linha['ORIGEM_HD']))

    def test_linhas_e_indices_duplicados_preservados(self):
        indice = defaultdict(dict)
        controle = pd.DataFrame({'ADESAO': ['AR0045', 'AR0045'],
                                 'Hidrômetro Comercial': ['A25LM003340', 'A25LM003340']})
        indexar_hd_controle(controle, indice)
        df = pd.DataFrame({'MATRICULA': ['AR0045', 'AR0045', 'AR9999'],
                           'HD_WFM': [None, 'A19S20301', None], 'original': [1, 2, 3]},
                          index=[7, 7, 20])
        antes = df.copy(deep=True)
        with patch('hd_utils.construir_indice_hd', return_value=indice) as carregar:
            resultado = preencher_hd(df, 'controles')
        self.assertEqual(len(resultado), len(df))
        self.assertTrue(resultado.index.equals(df.index))
        self.assertEqual(resultado['original'].tolist(), [1, 2, 3])
        self.assertEqual(resultado['HD'].tolist()[:2], ['A25LM003340', 'A19S20301'])
        carregar.assert_called_once_with('controles', {'AR0045', 'AR9999'})
        pd.testing.assert_frame_equal(df, antes)

    def test_extrai_wfm_das_notas(self):
        df = pd.DataFrame({'Nota Execução/Não Execução': ['Instalado A19S20301'],
                           'MATRICULA': ['AR0045']})
        with patch('hd_utils.construir_indice_hd') as carregar:
            resultado = preencher_hd(df, 'controles')
        self.assertEqual(resultado.iloc[0]['HD_WFM'], 'A19S20301')
        self.assertEqual(resultado.iloc[0]['ORIGEM_HD'], 'WFM')
        carregar.assert_not_called()

    def test_colunas_dos_layouts_atuais(self):
        self.assertEqual(identificar_colunas_hd(['HIDROMETRO', 'Hidrometro', 'INFO Hidrometro']),
                         ('Hidrometro', 'HIDROMETRO'))
        self.assertEqual(identificar_colunas_hd(['Hidrometro', 'Hidrometro.1', 'STATUS DO HD']),
                         ('Hidrometro.1', 'Hidrometro'))
        self.assertEqual(identificar_colunas_hd(['Hidrometro', 'STATUS DO HD']), ('Hidrometro', None))

    def test_mesmo_hd_com_origens_diferentes_nao_e_conflito(self):
        indice = defaultdict(dict)
        df = pd.DataFrame({'ADESAO': ['AR0045', 'AR0045'],
                           'Hidrômetro Comercial': ['MANTER HM', 'A19S20301'],
                           'Hidrômetro Social': ['A19S20301', None]})
        indexar_hd_controle(df, indice)
        with patch('hd_utils.construir_indice_hd', return_value=indice):
            resultado = preencher_hd(pd.DataFrame({'MATRICULA': ['AR0045']}), 'controles')
        self.assertEqual(resultado.iloc[0]['ORIGEM_HD'], 'COMERCIAL')

    def test_etl_integra_apos_recuperar_matricula(self):
        import etl
        df = pd.DataFrame({'MATRICULA': [None]})
        indice = {'AR0045': {'A19S20301': {'COMERCIAL'}}}
        with patch('etl.limpar_dados_basicos', side_effect=lambda x: x), \
             patch('etl.adicionar_endereco_id', side_effect=lambda x: x), \
             patch('etl.preencher_matricula_nota', side_effect=lambda x: x), \
             patch('etl.preencher_matricula_coluna_n', side_effect=lambda x: x), \
             patch('etl.aplicar_regra_01a', side_effect=lambda x: x.assign(MATRICULA='AR0045')), \
             patch('etl.validar_matriculas', side_effect=lambda x: x), \
             patch('etl.terminal.info'), \
             patch('hd_utils.construir_indice_hd', return_value=indice) as carregar:
            resultado = etl.tratar(df)
        carregar.assert_called_once_with(config.PASTA_CONTROLE, {'AR0045'})
        self.assertEqual(resultado.iloc[0]['HD'], 'A19S20301')

    def test_carregamento_real_de_controles_preserva_duplicatas_e_conflitos(self):
        import shutil
        import uuid
        from pathlib import Path
        from openpyxl import Workbook
        from hd_utils import construir_indice_hd
        raiz = Path(__file__).resolve().parents[1] / 'work' / 'test_hd_integracao'
        raiz.mkdir(parents=True, exist_ok=True)
        pasta = raiz / uuid.uuid4().hex
        pasta.mkdir()
        self.addCleanup(shutil.rmtree, pasta)
        for numero, codigo in enumerate(('A25LM003340', 'Y25LM029939')):
            wb = Workbook()
            ws = wb.active
            ws.title = 'GERAL'
            ws.append(['ADESAO', 'Endereco', 'Hidrometro', 'Hidrometro', 'INFO Hidrometro'])
            ws.append(['AR0045', 'Rua A', 'A19S20301', codigo, 'HM INSTALADO'])
            ws.append(['AR0046', 'Rua B', 'A19S20301', 'MANTER HM', None])
            ws.append(['AR9999', 'Rua C', None, codigo, None])
            wb.save(pasta / f'controle_{numero}.xlsx')
            wb.close()
        indice = construir_indice_hd(pasta, {'AR0045', 'AR0046'})
        self.assertEqual(set(indice['AR0045']), {'A25LM003340', 'Y25LM029939'})
        self.assertEqual(indice['AR0046'], {'A19S20301': {'SOCIAL'}})
        self.assertNotIn('AR9999', indice)

    def test_composto_wfm_mais_recente_sem_consultar_controle(self):
        df = pd.DataFrame({'MATRICULA': ['AR0045'],
                           'Nota Execução/Não Execução': ['Y11F162958 / A175716186']})
        with patch('hd_utils.construir_indice_hd') as carregar:
            resultado = preencher_hd(df, 'controles')
        self.assertEqual(resultado.iloc[0]['HD_WFM'], 'Y11F162958 / A175716186')
        self.assertEqual(resultado.iloc[0]['ORIGEM_HD'], 'WFM')
        self.assertEqual(resultado.iloc[0]['HD'], 'A175716186')
        carregar.assert_not_called()

    def test_composto_auditado_preexistente_mais_recente(self):
        linha, carregar = self.aplicar('A25SG0197833 / Y09TL311254', 'A25LM003340')
        self.assertEqual(linha['HD'], 'A25SG0197833')
        self.assertEqual(linha['ORIGEM_HD'], 'WFM')
        carregar.assert_not_called()

    def test_composto_social_mais_recente(self):
        linha, _ = self.aplicar(None, 'MANTER HM', 'Y11F162958/A175716186')
        self.assertEqual(linha['HD'], 'A175716186')
        self.assertEqual(linha['ORIGEM_HD'], 'SOCIAL')

    def test_mesmo_codigo_repetido_nao_e_ambiguo(self):
        self.assertEqual(extrair_hd('Y11F162958 / Y11F162958'), 'Y11F162958')

    def test_numeros_puros_nao_sao_convertidos(self):
        linha, _ = self.aplicar('4852135401', '69990', 'A175716186')
        self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('A175716186', 'SOCIAL'))
        self.assertEqual(linha['HD_WFM'], '4852135401')
        self.assertFalse(hd_valido('4852135401'))
        self.assertIsNone(extrair_hd('4852135401'))

    def test_extracao_nao_trunca_codigo_invalido(self):
        for valor in ('A25LM0264919C', 'ABCY11F162958', 'Y11F162958ABC',
                      'A225LM0260421', '018L504248'):
            with self.subTest(valor=valor):
                self.assertIsNone(extrair_hd(valor))

    def test_serie_nova_comercial(self):
        linha, _ = self.aplicar(None, 'A25SG0197833')
        self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('A25SG0197833', 'COMERCIAL'))

    def test_sem_serie_social(self):
        linha, _ = self.aplicar(None, 'MANTER HM', 'A175716186')
        self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('A175716186', 'SOCIAL'))

    def test_comercial_invalido_permite_social(self):
        linha, _ = self.aplicar(None, 'Y20Q746226', 'Y11F162958')
        self.assertEqual((linha['HD'], linha['ORIGEM_HD']), ('Y11F162958', 'SOCIAL'))

    def test_social_conflitante_sem_manter_hm(self):
        linha, _ = self.aplicar(None, None, 'Y17F162958/A175716186')
        self.assertTrue(pd.isna(linha['HD']))
        self.assertEqual(linha['ORIGEM_HD'], 'CONFLITO')

    def test_comercial_conflitante_nao_cai_para_social(self):
        linha, _ = self.aplicar(None, 'Y17F162958/A175716186', 'A19S20301')
        self.assertTrue(pd.isna(linha['HD']))
        self.assertEqual(linha['ORIGEM_HD'], 'CONFLITO')

    def test_comercial_prioritario_entre_ocorrencias_da_mesma_adesao(self):
        controle = pd.DataFrame({'ADESAO': ['AR0045', 'AR0045'],
                                 'Hidrômetro Comercial': [None, 'A19S20301'],
                                 'Hidrômetro Social': ['Y11F162958', None]})
        indice = defaultdict(dict)
        indexar_hd_controle(controle, indice)
        with patch('hd_utils.construir_indice_hd', return_value=indice):
            resultado = preencher_hd(pd.DataFrame({'MATRICULA': ['AR0045']}), 'controles')
        self.assertEqual((resultado.iloc[0]['HD'], resultado.iloc[0]['ORIGEM_HD']),
                         ('A19S20301', 'COMERCIAL'))

    def test_controle_com_apenas_coluna_social(self):
        controle = pd.DataFrame({'ADESAO': ['AR0045'], 'Hidrômetro Social': ['A175716186']})
        indice = defaultdict(dict)
        indexar_hd_controle(controle, indice)
        with patch('hd_utils.construir_indice_hd', return_value=indice):
            resultado = preencher_hd(pd.DataFrame({'MATRICULA': ['AR0045']}), 'controles')
        self.assertEqual(resultado.iloc[0]['HD'], 'A175716186')
        self.assertEqual(resultado.iloc[0]['ORIGEM_HD'], 'SOCIAL')

    def test_comercial_mais_recente_entre_ocorrencias(self):
        controle = pd.DataFrame({"ADESAO": ["AR0045"]*3,
                                 "Hidrômetro Comercial": ["A17L395245", "A25LM1088153", "A25LM1088153"]})
        indice = defaultdict(dict)
        indexar_hd_controle(controle, indice)
        with patch("hd_utils.construir_indice_hd", return_value=indice):
            r = preencher_hd(pd.DataFrame({"MATRICULA": ["AR0045"]}), "controles")
        self.assertEqual((r.iloc[0].HD, r.iloc[0].ORIGEM_HD), ("A25LM1088153", "COMERCIAL"))
        self.assertEqual(r.attrs["diagnostico_hd"]["conflitos_resolvidos_por_ano"], 1)

    def test_wfm_empate_maior_ano_nao_consulta_inferior(self):
        r, carregar = self.aplicar("A17L1 / Y25L2 / A25LM3", "A25LM4")
        self.assertTrue(pd.isna(r.HD))
        self.assertEqual(r.ORIGEM_HD, "CONFLITO")
        carregar.assert_not_called()

    def test_prioridade_independe_de_ano_da_fonte_inferior(self):
        r, _ = self.aplicar("A17L395245", "A25LM1088153")
        self.assertEqual((r.HD, r.ORIGEM_HD), ("A17L395245", "WFM"))
        r, _ = self.aplicar(None, "A17L395245", "A25LM1088153")
        self.assertEqual((r.HD, r.ORIGEM_HD), ("A17L395245", "COMERCIAL"))

    def test_os_nao_e_fonte_de_hd(self):
        df = pd.DataFrame({"Número OS": [123, 123], "HD_WFM": [None, "A25LM1088153"]}, index=[8, 8])
        r = preencher_hd(df, "controles")
        self.assertTrue(pd.isna(r.iloc[0].HD))
        self.assertEqual(r.iloc[1].ORIGEM_HD, "WFM")
        self.assertFalse(r.ORIGEM_HD.eq("OS").any())
        self.assertEqual(r.index.tolist(), [8, 8])

    def test_sqlite_exporta_hd_wfm_hd_e_origem(self):
        import database
        class ConexaoTeste(sqlite3.Connection):
            def close(self):
                pass
        conexao = sqlite3.connect(':memory:', factory=ConexaoTeste)
        self.addCleanup(sqlite3.Connection.close, conexao)
        df = pd.DataFrame([{c: None for c in config.COLUNAS_SQLITE}])
        df['HD_WFM'] = 'BAIXA INTERNA'
        df['HD'] = 'A19S20301'
        df['ORIGEM_HD'] = 'SOCIAL'
        with patch.dict(os.environ, {'EXECUCAO_AGENTE': '1'}), \
             patch('database.os.makedirs'), \
             patch('database.sqlite3.connect', return_value=conexao), \
             patch('database.titulo'), patch('database.sucesso'):
            database.criar_sqlite(df)
        self.assertEqual(conexao.execute('SELECT HD_WFM, HD, ORIGEM_HD FROM adesoes').fetchall(),
                         [('BAIXA INTERNA', 'A19S20301', 'SOCIAL')])


if __name__ == '__main__':
    unittest.main()
