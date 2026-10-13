import re
import unicodedata
import pandas as pd


def normalizar_numero_endereco(valor):
    """Remove apenas a parte decimal zero de um numero sem outros conteudos."""
    if pd.isna(valor):
        return ""

    texto = str(valor).strip()
    # fullmatch impede alterar sufixos, intervalos ou complementos.
    resultado = re.fullmatch(r"([0-9]+)\.0+", texto)
    return resultado.group(1) if resultado else texto


def normalizar_texto(texto):
    """
    Normaliza texto para facilitar comparação de endereços.

    Exemplo:
        'Rua João da Silva, nº 123'
        ->
        'RUA JOAO DA SILVA 123'
    """

    if pd.isna(texto):
        return ""

    texto = str(texto).strip().upper()

    # Remove acentos
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    # Padroniza algumas abreviações comuns
    substituicoes = {
        r"\bRUA\b": "R",
        r"\bAVENIDA\b": "AV",
        r"\bAV\b": "AV",
        r"\bALAMEDA\b": "AL",
        r"\bTRAVESSA\b": "TV",
        r"\bESTRADA\b": "EST",
        r"\bRODOVIA\b": "ROD",
        r"\bPRACA\b": "PC",
    }

    for padrao, substituicao in substituicoes.items():
        texto = re.sub(padrao, substituicao, texto)

    # Remove termos que normalmente não ajudam na identificação
    texto = re.sub(r"\bN[º°O]?\b", "", texto)

    # Mantém apenas letras, números e espaços
    texto = re.sub(r"[^A-Z0-9\s]", " ", texto)

    # Remove espaços duplicados
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def criar_endereco_id(endereco, numero, complemento):
    """
    Cria o ENDEREÇO_ID utilizando:
        Endereço + Número + Complemento

    O ID é normalizado para permitir comparação
    entre bases com pequenas diferenças de escrita.
    """

    partes = [
        normalizar_texto(endereco),
        normalizar_texto(normalizar_numero_endereco(numero)),
        normalizar_texto(complemento),
    ]

    partes = [parte for parte in partes if parte]

    if not partes:
        return pd.NA

    return " ".join(partes)


def adicionar_endereco_id(df):
    """
    Adiciona a coluna ENDEREÇO_ID ao DataFrame.

    Colunas esperadas:
        Endereço
        Número
        Complemento
    """

    colunas_necessarias = [
        "Endereço",
        "Número",
        "Complemento",
    ]

    faltantes = [
        coluna
        for coluna in colunas_necessarias
        if coluna not in df.columns
    ]

    if faltantes:
        raise ValueError(
            "Não foi possível criar ENDEREÇO_ID. "
            f"Colunas ausentes: {faltantes}"
        )

    df["ENDEREÇO_ID"] = df.apply(
        lambda linha: criar_endereco_id(
            linha["Endereço"],
            linha["Número"],
            linha["Complemento"],
        ),
        axis=1,
    )

    return df