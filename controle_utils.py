import os
import re
import unicodedata
from collections import defaultdict

import pandas as pd

from endereco_utils import normalizar_numero_endereco
from controle_leitura import determinar_ultima_linha_cadastro


# ============================================================
# ALIASES DAS COLUNAS
# ============================================================

ALIASES_MATRICULA = {
    "matricula",
    "matrícula",
    "adesao",
    "adesão",
    "codigo",
    "código",
    "code deep",
}

ALIASES_ENDERECO = {
    "endereco",
    "endereço",
    "endereco completo",
    "endereço completo",
    "logradouro",
}

ALIASES_NUMERO = {
    "numero",
    "número",
    "num",
    "n",
}

ALIASES_COMPLEMENTO = {
    "complemento",
    "compl",
    "comp",
}


# ============================================================
# NORMALIZAÇÃO DE NOME DE COLUNA
# ============================================================

def normalizar_nome_coluna(valor):
    if pd.isna(valor):
        return ""

    texto = str(valor).strip().lower()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    return texto


# ============================================================
# NORMALIZAÇÃO DE ENDEREÇO
# ============================================================

def normalizar_endereco(valor):

    if pd.isna(valor):
        return ""

    texto = str(valor).strip().upper()

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    substituicoes = {
        r"\bRUA\b": "R",
        r"\bAVENIDA\b": "AV",
        r"\bALAMEDA\b": "AL",
        r"\bTRAVESSA\b": "TV",
        r"\bESTRADA\b": "EST",
        r"\bRODOVIA\b": "ROD",
        r"\bPRACA\b": "PC",
    }

    for padrao, substituicao in substituicoes.items():
        texto = re.sub(
            padrao,
            substituicao,
            texto
        )

    # Remove "N", "Nº", "N°", "NO" usado antes do número
    texto = re.sub(
        r"\bN[º°O]?\b",
        "",
        texto
    )

    # Pontuação vira espaço
    texto = re.sub(
        r"[^A-Z0-9\s]",
        " ",
        texto
    )

    # Espaços duplicados
    texto = re.sub(
        r"\s+",
        " ",
        texto
    ).strip()

    return texto


# ============================================================
# CRIAR ID DO ENDEREÇO DA BASE DE CONTROLE
# ============================================================

def criar_endereco_controle(
    endereco=None,
    numero=None,
    complemento=None
):

    partes = []

    for valor in (
        endereco,
        normalizar_numero_endereco(numero),
        complemento
    ):

        valor_normalizado = normalizar_endereco(
            valor
        )

        if valor_normalizado:
            partes.append(
                valor_normalizado
            )

    if not partes:
        return ""

    return " ".join(partes)


# ============================================================
# IDENTIFICAR COLUNA
# ============================================================

def encontrar_coluna(
    colunas,
    aliases
):

    mapa = {
        normalizar_nome_coluna(coluna): coluna
        for coluna in colunas
    }

    for alias in aliases:

        alias_normalizado = normalizar_nome_coluna(
            alias
        )

        if alias_normalizado in mapa:
            return mapa[alias_normalizado]

    return None


# ============================================================
# IDENTIFICAR COLUNAS DA PLANILHA
# ============================================================

def identificar_colunas_controle(df):

    return {
        "matricula": encontrar_coluna(
            df.columns,
            ALIASES_MATRICULA
        ),

        "endereco": encontrar_coluna(
            df.columns,
            ALIASES_ENDERECO
        ),

        "numero": encontrar_coluna(
            df.columns,
            ALIASES_NUMERO
        ),

        "complemento": encontrar_coluna(
            df.columns,
            ALIASES_COMPLEMENTO
        ),
    }


# ============================================================
# ENCONTRAR CABEÇALHO
# ============================================================

def encontrar_linha_cabecalho(
    caminho,
    nome_aba="GERAL",
    limite_linhas=50
):

    try:

        bruto = pd.read_excel(
            caminho,
            sheet_name=nome_aba,
            header=None,
            nrows=limite_linhas
        )

    except Exception:
        return None

    melhor_linha = None
    melhor_pontuacao = -1

    aliases_matricula = {
        normalizar_nome_coluna(x)
        for x in ALIASES_MATRICULA
    }

    aliases_endereco = {
        normalizar_nome_coluna(x)
        for x in ALIASES_ENDERECO
    }

    aliases_numero = {
        normalizar_nome_coluna(x)
        for x in ALIASES_NUMERO
    }

    aliases_complemento = {
        normalizar_nome_coluna(x)
        for x in ALIASES_COMPLEMENTO
    }

    for indice in bruto.index:

        linha = bruto.loc[indice]

        valores = {
            normalizar_nome_coluna(valor)
            for valor in linha.tolist()
            if pd.notna(valor)
        }

        if not valores:
            continue

        pontuacao = 0

        if valores.intersection(
            aliases_matricula
        ):
            pontuacao += 4

        if valores.intersection(
            aliases_endereco
        ):
            pontuacao += 4

        if valores.intersection(
            aliases_numero
        ):
            pontuacao += 1

        if valores.intersection(
            aliases_complemento
        ):
            pontuacao += 1

        if pontuacao > melhor_pontuacao:

            melhor_pontuacao = pontuacao
            melhor_linha = int(indice)

    return melhor_linha


# ============================================================
# CARREGAR SOMENTE A ABA GERAL
# ============================================================

def carregar_aba_controle(
    caminho,
    nome_aba="GERAL"
):

    linha_cabecalho = encontrar_linha_cabecalho(
        caminho,
        nome_aba
    )

    if linha_cabecalho is None:
        return None

    try:

        opcoes_leitura = {}
        if os.path.splitext(os.fspath(caminho))[1].lower() == ".xlsx":
            cabecalho = pd.read_excel(
                caminho,
                sheet_name=nome_aba,
                header=linha_cabecalho,
                nrows=0,
            )
            colunas_cabecalho = identificar_colunas_controle(cabecalho)
            if (
                colunas_cabecalho["matricula"] is None
                or colunas_cabecalho["endereco"] is None
            ):
                return None
            relevantes = {
                indice + 1
                for indice, coluna in enumerate(cabecalho.columns)
                if coluna in colunas_cabecalho.values()
            }
            ultima_linha = determinar_ultima_linha_cadastro(
                caminho, nome_aba, linha_cabecalho, relevantes
            )
            opcoes_leitura["nrows"] = ultima_linha - linha_cabecalho - 1

        df = pd.read_excel(
            caminho,
            sheet_name=nome_aba,
            header=linha_cabecalho,
            **opcoes_leitura,
        )

    except Exception:
        return None

    if df.empty:
        return None

    colunas = identificar_colunas_controle(df)

    if (
        colunas["matricula"] is None
        or colunas["endereco"] is None
    ):
        return None

    return (
        df,
        colunas,
        linha_cabecalho
    )


# ============================================================
# CONSTRUIR ÍNDICE DE CONTROLE
# ============================================================

def construir_indice_controle(
    pasta_controle
):

    indice = defaultdict(set)

    arquivos_processados = 0
    abas_processadas = 0
    registros_processados = 0

    detalhes = []

    if not os.path.isdir(
        pasta_controle
    ):
        raise FileNotFoundError(
            f"Pasta de controle não encontrada: "
            f"{pasta_controle}"
        )

    arquivos = sorted(
        arquivo
        for arquivo in os.listdir(
            pasta_controle
        )
        if arquivo.lower().endswith(
            (".xlsx", ".xls")
        )
    )

    print(
        f"Planilhas de controle encontradas: "
        f"{len(arquivos)}"
    )

    # ========================================================
    # PROCESSA UM ARQUIVO POR VEZ
    # ========================================================

    for numero_arquivo, arquivo in enumerate(
        arquivos,
        start=1
    ):

        caminho = os.path.join(
            pasta_controle,
            arquivo
        )

        print(
            f"[{numero_arquivo}/{len(arquivos)}] "
            f"Processando: {arquivo}"
        )

        # ----------------------------------------------------
        # Abre o workbook apenas para verificar se GERAL existe
        # ----------------------------------------------------

        try:

            excel = pd.ExcelFile(
                caminho
            )

        except Exception as erro:

            print(
                f"  ERRO ao abrir arquivo: {erro}"
            )

            continue

        # ----------------------------------------------------
        # REGRA: SOMENTE GERAL
        # ----------------------------------------------------

        if "GERAL" not in excel.sheet_names:

            print(
                "  Aba GERAL não encontrada. Ignorado."
            )

            continue

        # ----------------------------------------------------
        # CARREGA EXCLUSIVAMENTE GERAL
        # ----------------------------------------------------

        resultado = carregar_aba_controle(
            caminho,
            "GERAL"
        )

        if resultado is None:

            print(
                "  Não foi possível interpretar a aba GERAL."
            )

            continue

        (
            df,
            colunas,
            linha_cabecalho
        ) = resultado

        abas_processadas += 1

        coluna_matricula = colunas.get(
            "matricula"
        )

        coluna_endereco = colunas.get(
            "endereco"
        )

        coluna_numero = colunas.get(
            "numero"
        )

        coluna_complemento = colunas.get(
            "complemento"
        )

        print(
            f"  GERAL carregada: "
            f"{len(df)} registros"
        )

        print(
            f"  Matrícula: {coluna_matricula}"
        )

        print(
            f"  Endereço: {coluna_endereco}"
        )

        print(
            f"  Número: {coluna_numero}"
        )

        print(
            f"  Complemento: {coluna_complemento}"
        )

        # ----------------------------------------------------
        # VALIDAÇÃO MÍNIMA
        # ----------------------------------------------------

        if (
            coluna_matricula is None
            or coluna_endereco is None
        ):

            print(
                "  Colunas obrigatórias não encontradas."
            )

            continue

        registros_arquivo = 0

        # ----------------------------------------------------
        # CONSTRÓI ÍNDICE
        # ----------------------------------------------------

        for _, linha in df.iterrows():

            matricula = linha[
                coluna_matricula
            ]

            if pd.isna(matricula):
                continue

            matricula = str(
                matricula
            ).strip()

            if not matricula:
                continue

            endereco = (
                linha[coluna_endereco]
                if coluna_endereco is not None
                else None
            )

            numero = (
                linha[coluna_numero]
                if coluna_numero is not None
                else None
            )

            complemento = (
                linha[coluna_complemento]
                if coluna_complemento is not None
                else None
            )

            endereco_id = criar_endereco_controle(
                endereco=endereco,
                numero=numero,
                complemento=complemento
            )

            if not endereco_id:
                continue

            indice[
                endereco_id
            ].add(
                matricula
            )

            registros_processados += 1
            registros_arquivo += 1

        arquivos_processados += 1

        detalhes.append(
            {
                "arquivo": arquivo,
                "aba": "GERAL",
                "linha_cabecalho": (
                    linha_cabecalho + 1
                ),
                "coluna_matricula": (
                    coluna_matricula
                ),
                "coluna_endereco": (
                    coluna_endereco
                ),
                "coluna_numero": (
                    coluna_numero
                ),
                "coluna_complemento": (
                    coluna_complemento
                ),
                "registros": (
                    registros_arquivo
                ),
            }
        )

        print(
            f"  Registros indexados: "
            f"{registros_arquivo}"
        )

    # ========================================================
    # RESUMO
    # ========================================================

    print()
    print(
        "CONTROLES CARREGADOS"
    )

    print(
        f"Arquivos processados: "
        f"{arquivos_processados}"
    )

    print(
        f"Abas GERAL processadas: "
        f"{abas_processadas}"
    )

    print(
        f"Registros processados: "
        f"{registros_processados}"
    )

    print(
        f"Endereços únicos no índice: "
        f"{len(indice)}"
    )

    return {
        "indice": indice,

        "arquivos_processados": (
            arquivos_processados
        ),

        "abas_processadas": (
            abas_processadas
        ),

        "registros_processados": (
            registros_processados
        ),

        "detalhes": detalhes,
    }


# ============================================================
# BUSCAR MATRÍCULA PELO ENDEREÇO
# ============================================================

def buscar_matricula_por_endereco(
    endereco_id,
    indice
):

    endereco_normalizado = normalizar_endereco(
        endereco_id
    )

    if not endereco_normalizado:
        return None

    matriculas = indice.get(
        endereco_normalizado
    )

    if not matriculas:
        return None

    # Só retorna quando o endereço
    # possui uma única matrícula.
    if len(matriculas) != 1:
        return None

    return next(
        iter(matriculas)
    )