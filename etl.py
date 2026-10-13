import os

import pandas as pd
from tqdm import tqdm

import config
import terminal
from logger import registrar_recuperacao, registrar_limpeza

from regex_utils import extrair_matricula, extrair_matricula_complemento, matricula_valida, analisar_matricula_nota_fallback
from matricula_os import preencher_matricula_os
from endereco_utils import adicionar_endereco_id
from hd_utils import preencher_hd

from controle_utils import (
    construir_indice_controle,
    buscar_matricula_por_endereco,
    normalizar_endereco,
)


# ============================================================
# CONSOLIDAÇÃO
# ============================================================


def consolidar():
    """
    Lê todos os arquivos Excel existentes na pasta WFM
    e consolida todas as abas em um único DataFrame.

    Retorna:
        base
        total_arquivos
        total_abas
    """

    arquivos = [
        arquivo
        for arquivo in os.listdir(config.PASTA_DADOS)
        if arquivo.lower().endswith((".xlsx", ".xls"))
    ]

    if not arquivos:
        raise FileNotFoundError(
            f"Nenhum arquivo Excel encontrado em: "
            f"{config.PASTA_DADOS}"
        )

    bases = []
    total_abas = 0

    terminal.info(
        f"Encontrados {len(arquivos)} arquivo(s) para consolidação."
    )

    for arquivo in tqdm(
        arquivos,
        desc="Consolidando arquivos",
    ):

        caminho = os.path.join(
            config.PASTA_DADOS,
            arquivo
        )

        try:

            abas = pd.read_excel(
                caminho,
                sheet_name=None
            )

            total_abas += len(abas)

            for nome_aba, df in abas.items():

                if df.empty:
                    continue

                df = df.copy()

                df["ARQUIVO"] = arquivo
                df["ABA"] = nome_aba

                bases.append(df)

        except Exception as erro:

            terminal.erro(
                f"Erro ao ler {arquivo}: {erro}"
            )

    if not bases:
        raise ValueError(
            "Nenhum dado válido foi encontrado nos arquivos."
        )

    base = pd.concat(
        bases,
        ignore_index=True,
        sort=False
    )

    terminal.info(
        f"Consolidação concluída: {len(base)} registros."
    )

    return base, len(arquivos), total_abas


# ============================================================
# LIMPEZA BÁSICA
# ============================================================


def limpar_dados_basicos(df):
    """
    Executa somente a limpeza básica dos dados.
    """

    df = df.copy()

    # Transformar strings vazias ou somente com espaços em NA
    df = df.replace(
        r"^\s*$",
        pd.NA,
        regex=True
    )

    # Metadados de proveniencia nao tornam uma linha de origem preenchida.
    colunas_origem = [
        coluna for coluna in df.columns
        if coluna not in {"ARQUIVO", "ABA"}
    ]
    df = df.loc[df[colunas_origem].notna().any(axis=1)]

    return df


# ============================================================
# EXTRAÇÃO DE MATRÍCULA DAS NOTAS
# ============================================================


def preencher_matricula_nota(df):
    """
    Extrai a matrícula das Notas de Acatamento.

    Essa etapa reutiliza a função existente
    extrair_matricula().
    """

    if "MATRICULA" not in df.columns:
        df["MATRICULA"] = pd.NA

    if "Notas de Acatamento" not in df.columns:

        terminal.aviso(
            "Coluna 'Notas de Acatamento' não encontrada."
        )

        return df

    mascara = (
        df["MATRICULA"].isna()
        |
        (
            df["MATRICULA"]
            .astype(str)
            .str.strip()
            .eq("")
        )
    )

    df.loc[mascara, "MATRICULA"] = (
        df.loc[mascara, "Notas de Acatamento"]
        .apply(extrair_matricula)
    )

    return df


# ============================================================
# REGRA 01
# ============================================================


def preencher_matricula_coluna_n(df):
    """
    REGRA 01

    Caso a matrícula continue vazia,
    procura a matrícula na coluna N.

    No DataFrame consolidado do WFM,
    a coluna física N corresponde ao campo
    'Complemento'.

    Nesta etapa não procuramos por endereço.

    Apenas aproveitamos uma matrícula que
    eventualmente tenha sido digitada no campo N.
    """

    if "MATRICULA" not in df.columns:
        df["MATRICULA"] = pd.NA

    if "Complemento" not in df.columns:

        terminal.aviso(
            "Coluna 'Complemento' não encontrada. "
            "Regra 01 não executada."
        )

        return df

    mascara_vazia = (
        df["MATRICULA"].isna()
        |
        (
            df["MATRICULA"]
            .astype(str)
            .str.strip()
            .eq("")
        )
    )

    def tentar_extrair(valor):

        if pd.isna(valor):
            return pd.NA

        matricula = extrair_matricula_complemento(valor)

        if matricula:
            return matricula

        return pd.NA

    df.loc[
        mascara_vazia,
        "MATRICULA"
    ] = (
        df.loc[
            mascara_vazia,
            "Complemento"
        ]
        .apply(tentar_extrair)
    )

    return df


# ============================================================
# REGRA 01A
# ============================================================


def aplicar_regra_01a(df):
    """
    REGRA 01A

    Para registros que ainda estão sem matrícula:

        ENDEREÇO_ID
             ↓
        SHAREPOINT
             ↓
        MATRÍCULA

    O ENDEREÇO_ID é utilizado como chave
    de cruzamento com as planilhas de controle.

    Matrícula não é utilizada como chave
    de ligação nesta etapa.

    Nesta versão também é executado um
    diagnóstico dos endereços que não foram
    encontrados, sem alterar a regra de busca.
    """

    if "MATRICULA" not in df.columns:
        df["MATRICULA"] = pd.NA

    if "ENDEREÇO_ID" not in df.columns:

        raise ValueError(
            "ENDEREÇO_ID não existe. "
            "A Regra 01A não pode ser executada."
        )

    terminal.info(
        "Carregando planilhas de controle do SHAREPOINT..."
    )

    resultado_controle = construir_indice_controle(
        config.PASTA_CONTROLE
    )

    indice_controle = resultado_controle["indice"]

    terminal.info(
        "Controles carregados: "
        f"{resultado_controle['arquivos_processados']} arquivo(s), "
        f"{resultado_controle['abas_processadas']} aba(s), "
        f"{resultado_controle['registros_processados']} registro(s)."
    )

    mascara_vazia = (
        df["MATRICULA"].isna()
        |
        (
            df["MATRICULA"]
            .astype(str)
            .str.strip()
            .eq("")
        )
    )

    total_vazias = int(
        mascara_vazia.sum()
    )

    encontrados = 0
    ambiguos = 0
    nao_encontrados = 0

    # ========================================================
    # DIAGNÓSTICO
    # ========================================================

    exemplos_nao_encontrados = []
    exemplos_ambiguos = []

    # Usamos loc + iterrows para evitar
    # problemas de tipagem do Pylance.
    linhas_vazias = df.loc[
        mascara_vazia
    ]

    for posicao in range(len(df)):
        if not mascara_vazia.iloc[posicao]:
            continue
        indice_df = df.index[posicao]
        linha = df.iloc[posicao]

        endereco_id = linha[
            "ENDEREÇO_ID"
        ]

        matricula = buscar_matricula_por_endereco(
            endereco_id,
            indice_controle
        )

        if matricula is not None and not matricula_valida(matricula):
            matricula = None

        if matricula is not None:

            df.iat[posicao, df.columns.get_loc("MATRICULA")] = matricula

            encontrados += 1

            continue

        # ====================================================
        # DIAGNÓSTICO DO ENDEREÇO
        # ====================================================

        if pd.isna(endereco_id):

            nao_encontrados += 1

            if len(exemplos_nao_encontrados) < 10:

                exemplos_nao_encontrados.append(
                    {
                        "linha": indice_df,
                        "endereco_wfm": "<VAZIO>",
                        "endereco_normalizado": "<VAZIO>",
                        "candidatos": []
                    }
                )

            continue

        endereco_normalizado = normalizar_endereco(
            endereco_id
        )

        if not endereco_normalizado:

            nao_encontrados += 1

            if len(exemplos_nao_encontrados) < 10:

                exemplos_nao_encontrados.append(
                    {
                        "linha": indice_df,
                        "endereco_wfm": str(endereco_id),
                        "endereco_normalizado": "<VAZIO>",
                        "candidatos": []
                    }
                )

            continue

        candidatos = indice_controle.get(
            endereco_normalizado,
            set()
        )

        # ====================================================
        # ENDEREÇO EXISTE, MAS TEM MAIS DE UMA MATRÍCULA
        # ====================================================

        if len(candidatos) > 1:

            ambiguos += 1

            if len(exemplos_ambiguos) < 10:

                exemplos_ambiguos.append(
                    {
                        "linha": indice_df,
                        "endereco_wfm": str(endereco_id),
                        "endereco_normalizado": endereco_normalizado,
                        "candidatos": sorted(
                            str(x)
                            for x in candidatos
                        )
                    }
                )

        else:

            nao_encontrados += 1

            if len(exemplos_nao_encontrados) < 10:

                exemplos_nao_encontrados.append(
                    {
                        "linha": indice_df,
                        "endereco_wfm": str(endereco_id),
                        "endereco_normalizado": endereco_normalizado,
                        "candidatos": []
                    }
                )

    # ========================================================
    # RESULTADO DA REGRA
    # ========================================================

    terminal.info(
        f"Regra 01A - Matrículas vazias antes: "
        f"{total_vazias}"
    )

    terminal.info(
        f"Regra 01A - Matrículas recuperadas: "
        f"{encontrados}"
    )

    terminal.info(
        f"Regra 01A - Endereços ambíguos: "
        f"{ambiguos}"
    )

    terminal.info(
        f"Regra 01A - Não encontradas: "
        f"{nao_encontrados}"
    )

    # ========================================================
    # MOSTRAR DIAGNÓSTICO
    # ========================================================

    if exemplos_nao_encontrados:

        terminal.info(
            "================================================"
        )

        terminal.info(
            "DIAGNÓSTICO - EXEMPLOS NÃO ENCONTRADOS"
        )

        terminal.info(
            "================================================"
        )

        for exemplo in exemplos_nao_encontrados:

            terminal.info(
                f"Linha WFM: {exemplo['linha']}"
            )

            terminal.info(
                f"ENDEREÇO_ID WFM: "
                f"{exemplo['endereco_wfm']}"
            )

            terminal.info(
                f"ENDEREÇO NORMALIZADO: "
                f"{exemplo['endereco_normalizado']}"
            )

            terminal.info(
                "Candidatos encontrados: nenhum"
            )

            terminal.info(
                "------------------------------------------------"
            )

    if exemplos_ambiguos:

        terminal.info(
            "================================================"
        )

        terminal.info(
            "DIAGNÓSTICO - EXEMPLOS AMBÍGUOS"
        )

        terminal.info(
            "================================================"
        )

        for exemplo in exemplos_ambiguos:

            terminal.info(
                f"Linha WFM: {exemplo['linha']}"
            )

            terminal.info(
                f"ENDEREÇO_ID WFM: "
                f"{exemplo['endereco_wfm']}"
            )

            terminal.info(
                f"ENDEREÇO NORMALIZADO: "
                f"{exemplo['endereco_normalizado']}"
            )

            terminal.info(
                "Matrículas candidatas: "
                f"{', '.join(exemplo['candidatos'])}"
            )

            terminal.info(
                "------------------------------------------------"
            )

    return df


# ============================================================
# VALIDAÇÃO
# ============================================================


def validar_matriculas(df):
    """
    Mostra informações sobre matrículas vazias.
    """

    if "MATRICULA" not in df.columns:

        terminal.aviso(
            "Coluna MATRICULA não existe."
        )

        return df

    vazias = (
        df["MATRICULA"].isna()
        |
        (
            df["MATRICULA"]
            .astype(str)
            .str.strip()
            .eq("")
        )
    )

    quantidade = int(
        vazias.sum()
    )

    terminal.info(
        "Matrículas vazias após as etapas automáticas: "
        f"{quantidade}"
    )

    return df


# ============================================================
# TRATAMENTO PRINCIPAL
# ============================================================


def preencher_matricula_notas_fallback(df):
    """Consulta Acatamento e depois Execucao apenas para matriculas ausentes."""
    resultado = df.copy()
    if "MATRICULA" not in resultado.columns:
        resultado["MATRICULA"] = pd.NA
    valores = resultado["MATRICULA"].tolist()
    fontes = (("Notas de Acatamento", "ACATAMENTO"),
              ("Nota Execução/Não Execução", "EXECUCAO"))
    diagnostico = {"ACATAMENTO": 0, "EXECUCAO": 0, "ambiguos": 0}
    for posicao, valor in enumerate(valores):
        if pd.notna(valor) and str(valor).strip():
            continue
        for coluna, origem in fontes:
            if coluna not in resultado.columns:
                continue
            candidatos = analisar_matricula_nota_fallback(
                resultado.iloc[posicao][coluna])
            if len(candidatos) > 1:
                diagnostico["ambiguos"] += 1
                break
            if len(candidatos) == 1:
                valores[posicao] = next(iter(candidatos))
                diagnostico[origem] += 1
                break
    resultado["MATRICULA"] = valores
    resultado.attrs["diagnostico_matricula_notas_fallback"] = diagnostico
    assert len(resultado) == len(df) and resultado.index.equals(df.index)
    return resultado


def adicionar_data_execucao(df):
    """Copia o fim da execucao WFM sem converter ou inventar datas."""
    resultado = df.copy()
    if "Data Fim Execução" in resultado.columns:
        resultado["DATA_EXECUCAO"] = resultado["Data Fim Execução"]
    else:
        resultado["DATA_EXECUCAO"] = pd.NA
    return resultado


def tratar(df):
    """
    Pipeline principal de tratamento da base.

    Ordem atual:

    1. Limpeza básica
    2. Criação do ENDEREÇO_ID
    3. Extração de matrícula das Notas de Acatamento
    4. REGRA 01 - procurar matrícula no campo N/Complemento
    5. Recuperar matricula pela OS nos controles
    6. REGRA 01A - endereco somente apos falha da OS
    7. Fallback pelas notas: Acatamento > Execucao, somente para ausentes
    8. HD: WFM > Comercial > Social > Cliente, escolhendo maior ano
    9. Validacao das matriculas

    As regras 02, 02A e 02B serão adicionadas
    posteriormente.

    IMPORTANTE:
    Não utilizar drop_duplicates() nesta etapa.
    """

    terminal.info(
        "Iniciando tratamento da base..."
    )

    # --------------------------------------------------
    # 1. LIMPEZA BÁSICA
    # --------------------------------------------------

    df = registrar_limpeza(limpar_dados_basicos, df)

    terminal.info(
        "Limpeza básica concluída."
    )

    # --------------------------------------------------
    # 2. CRIAR ENDEREÇO_ID
    # --------------------------------------------------

    df = adicionar_endereco_id(df)

    terminal.info(
        "ENDEREÇO_ID criado."
    )

    # --------------------------------------------------
    # 3. EXTRAIR MATRÍCULA DAS NOTAS
    # --------------------------------------------------

    df = registrar_recuperacao("Matricula pelas Notas de Acatamento (regra original)", preencher_matricula_nota, df)

    terminal.info(
        "Extração de matrícula pelas notas concluída."
    )

    # --------------------------------------------------
    # 4. REGRA 01
    # --------------------------------------------------

    df = registrar_recuperacao("Matricula pelo Complemento", preencher_matricula_coluna_n, df)

    terminal.info(
        "Regra 01 concluída."
    )

    # --------------------------------------------------
    # 5. REGRA 01A
    # --------------------------------------------------

    df = registrar_recuperacao("Matricula pela OS", preencher_matricula_os, df, config.PASTA_CONTROLE)
    df = registrar_recuperacao("Matricula pelo endereco", aplicar_regra_01a, df)
    df = registrar_recuperacao("Matricula pelas notas adicionais", preencher_matricula_notas_fallback, df)

    # HD: somente consultar controle quando o HD do WFM nao for valido.
    df = preencher_hd(df, config.PASTA_CONTROLE)

    # --------------------------------------------------
    # 6. VALIDAÇÃO
    # --------------------------------------------------

    df = validar_matriculas(df)

    # Preservar a data/hora original de conclusao da execucao, sem fallback.
    df = adicionar_data_execucao(df)

    # --------------------------------------------------
    # IMPORTANTE
    # --------------------------------------------------

    # NÃO colocar drop_duplicates() aqui.
    #
    # As duplicidades serão tratadas posteriormente
    # pelas regras:
    #
    # REGRA 02
    # REGRA 02A
    # REGRA 02B

    return df


# ============================================================
# SALVAR EXCEL
# ============================================================


def salvar_excel(df):
    """
    Salva a base tratada em Excel.
    """

    os.makedirs(
        os.path.dirname(config.ARQUIVO_EXCEL),
        exist_ok=True
    )

    df.to_excel(
        config.ARQUIVO_EXCEL,
        index=False
    )

    terminal.info(
        f"Excel salvo em: {config.ARQUIVO_EXCEL}"
    )