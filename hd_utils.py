import os
import re
import warnings
from collections import defaultdict

import pandas as pd

from controle_utils import carregar_aba_controle, normalizar_nome_coluna


PADRAO_HD = re.compile(r"\b[AY]\d{2}(?:LM|SG|TL|F|G|K|N|T|X|Z|L|S)?\d+\b")
PADRAO_HD_VALIDO = re.compile(r"^[AY]\d{2}(?:LM|SG|TL|F|G|K|N|T|X|Z|L|S)?\d+$")
PADRAO_MANTER_HM = re.compile(r"\bMANTER\s+HM\b")


def _texto(valor):
    return "" if pd.isna(valor) else str(valor).upper().strip()


def hd_valido(valor):
    return bool(PADRAO_HD_VALIDO.fullmatch(_texto(valor)))


def extrair_hds(texto):
    """Todos os codigos validos distintos, na ordem em que aparecem."""
    return tuple(dict.fromkeys(PADRAO_HD.findall(_texto(texto))))


def extrair_hd(texto):
    valores = extrair_hds(texto)
    if len(valores) == 1:
        return valores[0]
    # Preserva o texto composto para auditoria e identificacao do conflito.
    return _texto(texto) if valores else None


def identificar_colunas_hd(colunas):
    nomes = {coluna: normalizar_nome_coluna(coluna) for coluna in colunas}
    comercial = next((c for c, n in nomes.items()
                      if "hidrometro" in n and "comercial" in n), None)
    social = next((c for c, n in nomes.items()
                   if "hidrometro" in n and "social" in n), None)
    if comercial is not None or social is not None:
        return comercial, social
    # Layouts atuais: primeiro hidrometro e Social; ultimo e Comercial.
    # CG possui apenas um campo Hidrometro, destinado ao Comercial.
    hidrometros = [c for c, n in nomes.items()
                  if re.fullmatch(r"hidrometro(?:\.\d+)?", n)]
    if len(hidrometros) == 1:
        return hidrometros[0], None
    if len(hidrometros) == 2:
        return hidrometros[-1], hidrometros[0]
    return None, None


def indexar_hd_controle(df, indice, matriculas=None):
    adesao = next((c for c in df.columns
                   if normalizar_nome_coluna(c) == "adesao"), None)
    comercial, social = identificar_colunas_hd(df.columns)
    if adesao is None or (comercial is None and social is None):
        return
    for _, linha in df.iterrows():
        chave = _texto(linha[adesao])
        if not chave or (matriculas is not None and chave not in matriculas):
            continue
        texto_comercial = _texto(linha[comercial]) if comercial is not None else ""
        valores = set(PADRAO_HD.findall(texto_comercial))
        origem = "COMERCIAL"
        if not valores and social is not None:
            valores = set(PADRAO_HD.findall(_texto(linha[social])))
            origem = "SOCIAL"
        for hd in valores:
            indice[chave].setdefault(hd, set()).add(origem)


def construir_indice_hd(pasta_controle, matriculas):
    indice = defaultdict(dict)
    for arquivo in sorted(os.listdir(pasta_controle)):
        if arquivo.startswith("~$") or not arquivo.lower().endswith((".xlsx", ".xls")):
            continue
        caminho = os.path.join(pasta_controle, arquivo)
        with pd.ExcelFile(caminho) as excel:
            if "GERAL" not in excel.sheet_names:
                continue
        resultado = carregar_aba_controle(caminho, "GERAL")
        if resultado is None:
            warnings.warn(f"Controle de HD nao interpretado: {caminho}", UserWarning)
            continue
        indexar_hd_controle(resultado[0], indice, matriculas)
    return indice



ABAS_CLIENTES = frozenset({
    "dados cliente deep", "dados de cliente deep",
    "dados clientes deep", "dados dos clientes",
})


def indexar_hd_clientes(df, indice, matriculas=None):
    """Guarda cada linha fisica; duplicatas nunca viram correspondencia unica."""
    identificadores = [c for c in df.columns
                      if normalizar_nome_coluna(c) == "matricula"]
    hidrometros = [c for c in df.columns
                  if normalizar_nome_coluna(c) == "hidrometro"]
    for _, linha in df.iterrows():
        chaves = {_texto(linha[c]) for c in identificadores} - {""}
        valores = set(hd for c in hidrometros for hd in extrair_hds(linha[c]))
        for chave in chaves:
            if matriculas is None or chave in matriculas:
                indice.setdefault(chave, []).append(valores)


def construir_indice_hd_clientes(pasta_controle, matriculas):
    from controle_leitura import determinar_ultima_linha_cadastro
    indice = {}
    if not os.path.isdir(pasta_controle):
        return indice
    for arquivo in sorted(os.listdir(pasta_controle)):
        if arquivo.startswith("~$") or not arquivo.lower().endswith((".xlsx", ".xls")):
            continue
        caminho = os.path.join(pasta_controle, arquivo)
        with pd.ExcelFile(caminho) as excel:
            abas = [a for a in excel.sheet_names if a.strip().lower() in ABAS_CLIENTES]
        for aba in abas:
            cabecalho = pd.read_excel(caminho, sheet_name=aba, nrows=0)
            relevantes = [i + 1 for i, c in enumerate(cabecalho.columns)
                          if normalizar_nome_coluna(c) == "matricula"]
            if not relevantes:
                continue
            kwargs = {}
            if arquivo.lower().endswith(".xlsx"):
                ultima = determinar_ultima_linha_cadastro(caminho, aba, 0, relevantes)
                kwargs["nrows"] = max(0, ultima - 1)
            dados = pd.read_excel(caminho, sheet_name=aba, **kwargs)
            indexar_hd_clientes(dados, indice, matriculas)
    return indice


def selecionar_hd_mais_recente(codigos):
    validos = {_texto(hd) for hd in codigos if hd_valido(hd)}
    if not validos:
        return None, False, False
    maior_ano = max(int(hd[1:3]) for hd in validos)
    recentes = {hd for hd in validos if int(hd[1:3]) == maior_ano}
    if len(recentes) > 1:
        return None, True, False
    return next(iter(recentes)), False, len(validos) > 1


def preencher_hd(df, pasta_controle):
    """Prioridade WFM > Comercial > Social > Cliente; sem merge ou HD por OS."""
    resultado = df.copy()
    if "HD_WFM" not in resultado:
        resultado["HD_WFM"] = (resultado["Nota Execução/Não Execução"].apply(extrair_hd)
                               if "Nota Execução/Não Execução" in resultado else pd.NA)
    valores_wfm = resultado["HD_WFM"].tolist()
    matriculas = (resultado["MATRICULA"].tolist() if "MATRICULA" in resultado
                  else [None] * len(resultado))
    consultar = {_texto(m) for hd, m in zip(valores_wfm, matriculas)
                 if not extrair_hds(hd) and _texto(m)}
    indice = construir_indice_hd(pasta_controle, consultar) if consultar else {}
    hds, origens = [], []
    resolvidos_ano = 0
    for wfm, matricula in zip(valores_wfm, matriculas):
        candidatos = set(extrair_hds(wfm))
        origem = "WFM"
        if not candidatos:
            controle = indice.get(_texto(matricula), {})
            candidatos = {hd for hd, fontes in controle.items() if "COMERCIAL" in fontes}
            origem = "COMERCIAL"
            if not candidatos:
                candidatos = {hd for hd, fontes in controle.items() if "SOCIAL" in fontes}
                origem = "SOCIAL"
        hd, conflito, resolvido = selecionar_hd_mais_recente(candidatos)
        hds.append(hd)
        origens.append("CONFLITO" if conflito else origem if hd else None)
        resolvidos_ano += int(resolvido)
    pendentes = {_texto(m) for m, hd, origem in zip(matriculas, hds, origens)
                 if hd is None and origem != "CONFLITO" and _texto(m)}
    clientes = construir_indice_hd_clientes(pasta_controle, pendentes) if pendentes else {}
    for i, matricula in enumerate(matriculas):
        if hds[i] is not None or origens[i] == "CONFLITO":
            continue
        candidatos = {hd for valores in clientes.get(_texto(matricula), []) for hd in valores}
        hd, conflito, resolvido = selecionar_hd_mais_recente(candidatos)
        hds[i] = hd
        origens[i] = "CONFLITO" if conflito else "CLIENTE" if hd else None
        resolvidos_ano += int(resolvido)
    resultado["HD"] = hds
    resultado["ORIGEM_HD"] = origens
    resultado.attrs["diagnostico_hd"] = {"conflitos_resolvidos_por_ano": resolvidos_ano}
    if len(resultado) != len(df) or not resultado.index.equals(df.index):
        raise AssertionError("A integracao de HD alterou as linhas da base.")
    return resultado
