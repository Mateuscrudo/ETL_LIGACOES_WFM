"""Limite esparso de leitura dos cadastros em arquivos XLSX, sem edita-los."""

import posixpath
import re
import warnings
import xml.etree.ElementTree as ET
from zipfile import ZipFile


NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MAIN = "{" + NS["m"] + "}"
REL_ID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def _strings_preenchidas(arquivo):
    """Resolve presenca de texto compartilhado, incluindo '0', sem converter dados."""
    if "xl/sharedStrings.xml" not in arquivo.namelist():
        return []
    resultado = []
    with arquivo.open("xl/sharedStrings.xml") as stream:
        eventos = ET.iterparse(stream, events=("start", "end"))
        _, raiz = next(eventos)
        for evento, elemento in eventos:
            if evento == "end" and elemento.tag == MAIN + "si":
                texto = "".join(t.text or "" for t in elemento.iter(MAIN + "t"))
                resultado.append(bool(texto.strip()))
                raiz.clear()
    return resultado


def _celula_preenchida(celula, strings):
    # Uma formula sem cache tambem pode representar um cadastro valido.
    if celula.find("m:f", NS) is not None:
        return True
    if celula.attrib.get("t") == "inlineStr":
        texto = "".join(t.text or "" for t in celula.iter(MAIN + "t"))
        return bool(texto.strip())
    valor = celula.find("m:v", NS)
    if valor is None or valor.text is None:
        return False
    if celula.attrib.get("t") == "s":
        return strings[int(valor.text)]
    # Numeros zero e booleanos falsos sao valores, nao ausencia de dados.
    return bool(valor.text.strip())


def _numero_coluna(referencia):
    letras = re.match(r"[A-Za-z]+", referencia)
    if letras is None:
        raise ValueError(f"Referencia de celula invalida: {referencia}")
    numero = 0
    for letra in letras.group().upper():
        numero = numero * 26 + ord(letra) - ord("A") + 1
    return numero


def determinar_ultima_linha_cadastro(caminho, nome_aba, linha_cabecalho, colunas_relevantes):
    """Retorna linha Excel (1-based), usando cabecalho pandas (0-based).

    Examina todas as celulas fisicamente armazenadas nos campos ja escolhidos
    pelo ETL. Nao depende de dimension, max_row, filtros ou linhas consecutivas.
    Preserva registros parciais e formulas; conversao de valores continua no
    pandas. Conteudos em outras colunas apos o cadastro sao apenas avisados.
    """
    relevantes = set(colunas_relevantes)
    if not relevantes:
        raise ValueError("Nenhuma coluna de cadastro identificada para limitar a leitura.")
    ultima = linha_cabecalho + 1
    outras_linhas = set()
    with ZipFile(caminho) as arquivo:
        workbook = ET.fromstring(arquivo.read("xl/workbook.xml"))
        rels = ET.fromstring(arquivo.read("xl/_rels/workbook.xml.rels"))
        destinos = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels
                    if rel.attrib.get("TargetMode") != "External"}
        aba = next((s for s in workbook.find("m:sheets", NS)
                    if s.attrib["name"] == nome_aba), None)
        if aba is None:
            raise ValueError(f"Aba nao encontrada: {nome_aba}")
        destino = destinos[aba.attrib[REL_ID]]
        xml_aba = (posixpath.normpath(destino.lstrip("/")) if destino.startswith("/")
                   else posixpath.normpath(posixpath.join("xl", destino)))
        strings = _strings_preenchidas(arquivo)
        with arquivo.open(xml_aba) as stream:
            eventos = ET.iterparse(stream, events=("start", "end"))
            _, raiz = next(eventos)
            numero_linha = 0
            for evento, elemento in eventos:
                if evento != "end" or elemento.tag != MAIN + "row":
                    continue
                numero_linha = int(elemento.attrib.get("r", numero_linha + 1))
                if numero_linha > linha_cabecalho + 1:
                    numero_coluna = 0
                    for celula in elemento:
                        if celula.tag != MAIN + "c":
                            continue
                        referencia = celula.attrib.get("r")
                        numero_coluna = (_numero_coluna(referencia) if referencia
                                         else numero_coluna + 1)
                        if not _celula_preenchida(celula, strings):
                            continue
                        if numero_coluna in relevantes:
                            ultima = max(ultima, numero_linha)
                        else:
                            outras_linhas.add(numero_linha)
                raiz.clear()
    fora = sorted(linha for linha in outras_linhas if linha > ultima)
    if fora:
        warnings.warn(
            f"{caminho} / {nome_aba}: {len(fora)} linha(s) com conteudo fora dos "
            f"campos de cadastro apos a linha {ultima}; ultima linha isolada: {fora[-1]}. "
            "Conteudo mantido no arquivo; leitura limitada aos campos de cadastro.",
            UserWarning,
            stacklevel=2,
        )
    return ultima
