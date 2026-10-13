"""Recuperacao exata de matricula pela OS nas abas dos controles."""
import os
import posixpath
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

import pandas as pd
from controle_utils import normalizar_nome_coluna
from regex_utils import matricula_valida

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
MAIN = "{" + NS["m"] + "}"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"


def normalizar_os(valor):
    if pd.isna(valor):
        return ""
    texto = str(valor).strip()
    return re.sub(r"\.0+$", "", texto) if re.fullmatch(r"\d+(?:\.0+)?", texto) else texto


def coluna_os(nome):
    texto = re.sub(r"[^a-z0-9]+", " ", normalizar_nome_coluna(nome)).strip()
    return texto in {
        "os", "numero os", "numero da os", "n os", "o s",
        "ordem de servico", "ordem servico", "numero ordem de servico",
        "numero da ordem de servico", "os fornecimento", "os supressao",
        "os regularizacao", "os hm parado",
    }


def coluna_matricula(nome):
    return normalizar_nome_coluna(nome) in {"matricula", "adesao", "codigo", "code deep"}


def _matricula(valor):
    return "" if pd.isna(valor) else str(valor).strip().upper()


def indexar_matriculas_os(df, indice, ordens=None):
    os_cols = [c for c in df if coluna_os(c)]
    mat_cols = [c for c in df if coluna_matricula(c)]
    for _, linha in df.iterrows():
        matriculas = {_matricula(linha[c]) for c in mat_cols if matricula_valida(linha[c])}
        if not matriculas:
            continue
        for chave in {normalizar_os(linha[c]) for c in os_cols} - {""}:
            if ordens is None or chave in ordens:
                indice.setdefault(chave, set()).update(matriculas)


def _strings(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    strings = []
    with z.open("xl/sharedStrings.xml") as stream:
        eventos = ET.iterparse(stream, events=("start", "end"))
        _, raiz = next(eventos)
        for evento, elemento in eventos:
            if evento == "end" and elemento.tag == MAIN + "si":
                strings.append("".join(t.text or "" for t in elemento.iter(MAIN + "t")))
                raiz.clear()
    return strings


def _valor(celula, strings):
    if celula.attrib.get("t") == "inlineStr":
        return "".join(t.text or "" for t in celula.iter(MAIN + "t"))
    valor = celula.find("m:v", NS)
    if valor is None or valor.text is None:
        return ""
    return strings[int(valor.text)] if celula.attrib.get("t") == "s" else valor.text


def _linhas(z, caminho, strings):
    with z.open(caminho) as stream:
        eventos = ET.iterparse(stream, events=("start", "end"))
        _, raiz = next(eventos)
        for evento, elemento in eventos:
            if evento == "end" and elemento.tag == MAIN + "row":
                valores = {re.match(r"[A-Z]+", c.attrib["r"]).group(): _valor(c, strings)
                           for c in elemento if c.tag == MAIN + "c"}
                yield int(elemento.attrib["r"]), valores
                raiz.clear()



def indexar_arquivo_matriculas_os(caminho, indice, ordens):
    if str(caminho).lower().endswith(".xls"):
        for df in pd.read_excel(caminho, sheet_name=None).values():
            indexar_matriculas_os(df, indice, ordens)
        return
    with ZipFile(caminho) as z:
        strings = _strings(z)
        rels = {e.attrib["Id"]: e.attrib["Target"]
                for e in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
        workbook = ET.fromstring(z.read("xl/workbook.xml"))
        for aba in workbook.find("m:sheets", NS):
            target = rels[aba.attrib[RID]]
            xml = (target.lstrip("/") if target.startswith("/") else
                   posixpath.normpath(posixpath.join("xl", target)))
            cabecalho = None
            for numero, valores in _linhas(z, xml, strings):
                if numero > 30:
                    break
                os_cols = [c for c, nome in valores.items() if coluna_os(nome)]
                mat_cols = [c for c, nome in valores.items() if coluna_matricula(nome)]
                if os_cols and mat_cols:
                    cabecalho = numero, os_cols, mat_cols
                    break
            if cabecalho is None:
                continue
            linha_header, os_cols, mat_cols = cabecalho
            for numero, valores in _linhas(z, xml, strings):
                if numero <= linha_header:
                    continue
                chaves = {normalizar_os(valores.get(c, "")) for c in os_cols} & ordens
                if not chaves:
                    continue
                matriculas = {_matricula(valores.get(c, "")) for c in mat_cols
                              if matricula_valida(valores.get(c, ""))}
                for chave in chaves:
                    if matriculas:
                        indice.setdefault(chave, set()).update(matriculas)


def construir_indice_matriculas_os(pasta_controle, ordens):
    indice = {}
    for arquivo in sorted(os.listdir(pasta_controle)):
        if arquivo.startswith("~$") or not arquivo.lower().endswith((".xlsx", ".xls")):
            continue
        indexar_arquivo_matriculas_os(os.path.join(pasta_controle, arquivo), indice, ordens)
    return indice


def preencher_matricula_os(df, pasta_controle):
    resultado = df.copy()
    if "MATRICULA" not in resultado:
        resultado["MATRICULA"] = pd.NA
    os_cols = [c for c in resultado if coluna_os(c)]
    if not os_cols:
        return resultado
    valores = resultado["MATRICULA"].tolist()
    chaves = [{normalizar_os(resultado.iloc[i][c]) for c in os_cols} - {""}
              for i in range(len(resultado))]
    pendentes = {chave for i, conjunto in enumerate(chaves)
                 if not _matricula(valores[i]) for chave in conjunto}
    indice = construir_indice_matriculas_os(pasta_controle, pendentes) if pendentes else {}
    recuperadas = ambiguas = 0
    for i, conjunto in enumerate(chaves):
        if _matricula(valores[i]):
            continue
        candidatos = {m for chave in conjunto for m in indice.get(chave, set())
                      if matricula_valida(m)}
        if len(candidatos) == 1:
            valores[i] = next(iter(candidatos))
            recuperadas += 1
        elif len(candidatos) > 1:
            ambiguas += 1
    resultado["MATRICULA"] = valores
    resultado.attrs["diagnostico_matricula_os"] = {
        "recuperadas": recuperadas, "ambiguas": ambiguas,
    }
    if len(resultado) != len(df) or not resultado.index.equals(df.index):
        raise AssertionError("A recuperacao de matricula por OS alterou linhas/indices.")
    return resultado
