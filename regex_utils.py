import re
import unicodedata
import pandas as pd

def normalizar_texto(texto):
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return texto.upper()
def extrair_matricula(texto):
    if pd.isna(texto):
        return None

    texto = normalizar_texto(texto)

    # Primeiro tenta pegar o código logo depois de ADESAO / ADESÃO
    m = re.search(
        r'ADESAO\s*[:\-]?\s*'
        r'('
        r'[A-Z]{2,5}\d{3,8}'
        r'|\d{4,6}-(?:CGN|CG|[A-Z]{2,3})'
        r')\b',
        texto
    )
    if m:
        return m.group(1)

    # Fallback: procura um código parecido em qualquer lugar do texto
    m = re.search(
        r'(?<![A-Z0-9])('
        r'[A-Z]{2,5}\d{3,8}'
        r'|\d{4,6}-(?:CGN|CG|[A-Z]{2,3})'
        r')(?![A-Z0-9])',
        texto
    )
    if m:
        return m.group(1)

    return None