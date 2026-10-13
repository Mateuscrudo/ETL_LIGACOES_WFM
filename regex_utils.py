import re
import unicodedata
import pandas as pd

def normalizar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.upper()
FORMATO_MATRICULA = r"(?:[A-Z]{2,3}\d{4,6}|\d{4}-[A-Z]{2,3})"
PADRAO_MATRICULA_VALIDO = re.compile("^" + FORMATO_MATRICULA + "$")


def matricula_valida(valor):
    if pd.isna(valor):
        return False
    return bool(PADRAO_MATRICULA_VALIDO.fullmatch(str(valor).strip().upper()))


def extrair_matricula_complemento(texto):
    """Extrai do Complemento somente os formatos de adesao autorizados."""
    if pd.isna(texto):
        return None

    texto = normalizar_texto(texto)

    # Primeiro tenta pegar o código logo depois de ADESAO / ADESÃO
    m = re.search(
        r'ADESAO\s*[:\-]?\s*'
        r'('
        r'[A-Z]{2,3}\d{4,6}'
        r'|\d{4}-[A-Z]{2,3}'
        r')(?![A-Z0-9_]|[-/][A-Z0-9])',
        texto
    )
    if m:
        return m.group(1)

    # Fallback: procura um código parecido em qualquer lugar do texto
    m = re.search(
        r'(?<![A-Z0-9])('
        r'[A-Z]{2,3}\d{4,6}'
        r'|\d{4}-[A-Z]{2,3}'
        r')(?![A-Z0-9_]|[-/][A-Z0-9])',
        texto
    )
    if m:
        return m.group(1)

    return None

# Formatos autorizados, exigindo identificacao explicita nas notas.
PADRAO_MATRICULA_NOTA = re.compile(
    r'(?:(?<![A-Z])|(?<=VULNERAVEL)|(?<=SOCIAL)|(?<=VULNERAVEIS))'
    r'(?:ADESAO|MATRICULA)'
    r'[\s:;\-]*'
    r'(?:RGI[\s:;\-]*)?'
    r'\(?\s*'
    r'(?P<matricula>[A-Z]{2,3}\d{4,6}|\d{4}-[A-Z]{2,3})'
    r'(?![A-Z0-9_]|[-/][A-Z0-9])'
)


def extrair_matricula(texto):
    """Extrai das notas apenas um codigo explicitamente identificado.

    Tolera separadores e concatenacoes observados na WFM, sem buscar
    codigos genericos em qualquer trecho. Identificacoes conflitantes
    permanecem sem matricula para revisao.
    """
    if pd.isna(texto):
        return None

    texto = normalizar_texto(texto)
    matriculas = {
        resultado.group('matricula')
        for resultado in PADRAO_MATRICULA_NOTA.finditer(texto)
    }
    return next(iter(matriculas)) if len(matriculas) == 1 else None


# Fallback complementar, sem alterar o extrator das regras anteriores.
# Palavras adjacentes confirmadas nas notas: nao cortar outros sufixos.
PADRAO_MATRICULA_FALLBACK = re.compile(
    r"(?<![A-Z0-9_])"
    r"(?P<codigo>[A-Z]{2,3}[ \t]*\d{4,6}A?|\d{4}[ \t]*-[ \t]*[A-Z]{2,3})"
    r"(?=$|[^A-Z0-9_]|(?:HIDROMETRO|ANEXO|AREGULARIZACAO)\b)"
    r"(?![-/][A-Z0-9])"
)


def analisar_matricula_nota_fallback(texto):
    """Identifica codigos completos; remove apenas espacos de apresentacao.

    O A final e parte do codigo. Codigos distintos permanecem separados,
    inclusive quando uma delimitacao por palavra adjacente sugere outro valor.
    """
    if pd.isna(texto):
        return set()
    texto = normalizar_texto(texto)
    return {
        re.sub(r"[ \t]+", "", m.group("codigo"))
        for m in PADRAO_MATRICULA_FALLBACK.finditer(texto)
    }
