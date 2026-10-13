> **Cópia preparada com dados fictícios.** As planilhas em ENTRADA são exemplos inventados, gerados por `gerar_demo.py`; nenhum dado operacional foi copiado. Consulte [origem dos dados](docs/DADOS_FICTICIOS.md) e [validação desta cópia](VALIDACAO.md). O projeto interno permanece separado.

## Executar os exemplos incluídos

As entradas sintéticas já estão incluídas. Instale `requirements.txt` e execute `python -X utf8 main.py` na raiz. Para Água e Obra, use `$env:EXECUCAO_AGENTE = "1"` antes de executar para dispensar interação. `gerar_demo.py` documenta e reproduz a criação das entradas, mas recusa sobrescrevê-las; use uma cópia vazia para regenerar.

# ETL Base de Obras — SABESP Guarujá

Consolida planilhas de ligações de água, identifica adesões/matrículas e hidrômetros e gera Excel e SQLite para análise e consultas. A organização estrutural preserva o comportamento aprovado: nenhum cruzamento multiplica linhas e não há remoção de duplicatas de origem.

Autor: Mateus Crudo de Barros. Projeto de automação, estudo e portfólio profissional.

## Fontes

- `ENTRADA/WFM/`: arquivos `.xlsx` e `.xls`; a consolidação lê suas abas e acrescenta `ARQUIVO` e `ABA` para rastreabilidade.
- `ENTRADA/SHAREPOINT/`: controles usados na recuperação de matrícula pela OS, no endereço e no HD.
- O HD do controle usa `GERAL` e as abas de clientes validadas: `Dados cliente deep`, `Dados de cliente deep`, `Dados clientes deep` e `Dados dos clientes` (comparação sem diferença de caixa/espaços externos).
- A leitura otimizada dos controles determina a última linha com dados de cadastro. Não usa limite fixo nem termina na primeira lacuna; conteúdo isolado fora do cadastro não infla a leitura.

## Estrutura

```text
ETL_OBRA/
├── main.py                         # entry point, exportação e ciclo do log
├── config.py                       # fontes, saída, logs e colunas SQLite
├── etl.py                          # consolidação e tratamento
├── regex_utils.py                  # reconhecimento de matrícula nas notas
├── matricula_os.py                 # recuperação de matrícula pela OS
├── endereco_utils.py               # chave normalizada de endereço
├── controle_utils.py               # leitura e índice de endereço dos controles
├── controle_leitura.py             # determinação do intervalo real de cadastro
├── hd_utils.py                     # reconhecimento e prioridade das fontes de HD
├── database.py                     # exportação SQLite e índices
├── logger.py                       # logging, console e métricas
├── terminal.py                     # mensagens coloridas
├── uitls.py                        # cronômetros; nome original preservado
├── testes/
│   ├── __init__.py
│   ├── test_*.py                    # testes automatizados
├── saida/                          # gerada ao executar; não incluída
├── logs/                           # novos logs e históricos preservados
├── ENTRADA/                        # fontes preservadas
├── work/                           # arquivos temporários dos testes
├── pytest.ini
├── requirements.txt
└── README.md
```

As pastas antigas `database_excel/` e `database_SQL/` e os arquivos externos de saída existentes foram preservados; não são mais os destinos configurados. Nenhuma base antiga foi copiada para `saida/` como se fosse uma nova exportação.

## Fluxo de execução

1. Consolidar as abas WFM.
2. Remover apenas linhas completamente vazias nos campos originais.
3. Criar a chave de endereço.
4. Aplicar a extração original das Notas de Acatamento e o reconhecimento no Complemento.
5. Recuperar matrícula pela OS.
6. Aplicar endereço como fallback após a OS não recuperar matrícula.
7. Para os registros ainda sem matrícula, aplicar o reconhecimento adicional: Acatamento antes de Execução.
8. Resolver HD com as fontes aprovadas.
9. Acrescentar `DATA_EXECUCAO` a partir de `Data Fim Execução`.
10. Exportar Excel, depois SQLite, e registrar o resultado da execução.

## Limpeza e integridade

`ARQUIVO` e `ABA` são metadados e não tornam uma linha vazia preenchida. Valores `0` e `False` contam como dados. Após essa limpeza, os tratamentos preservam quantidade e índices das linhas, incluindo índices repetidos. Registros duplicados existentes na origem são preservados.

Números de endereço equivalentes como `123`, `123.0` e `"123.0"` geram a mesma chave. Conteúdo adicional, complementos, intervalos e sufixos não são descartados automaticamente.

## ADESÃO/MATRÍCULA

Os formatos-base aprovados são:

- 2 ou 3 letras seguidas de 4, 5 ou 6 números;
- 4 números, hífen e 2 ou 3 letras, incluindo `2146-CGN`.

A extração original das Notas de Acatamento exige identificação explícita por matrícula/adesão. A regra existente do Complemento permanece intacta.

### Recuperação pela OS

Somente para matrícula ausente, consultar a OS nas abas de controle com campos correspondentes. Uma ou várias ocorrências que indiquem uma única matrícula distinta válida permitem preencher. Matrículas distintas para a mesma OS não geram escolha automática.

Normalizar apenas diferenças de representação, como `123456`, `"123456"` e `123456.0`. Não remover zeros à esquerda nem alterar hífens ou conteúdo lógico.

### Fallback por endereço

Consultar o endereço apenas se a OS não recuperar matrícula. Preencher somente com correspondência única e válida; endereço ambíguo permanece sem escolha automática.

### Reconhecimento adicional nas notas

Aplicado somente aos registros que continuam sem matrícula após as regras anteriores:

1. `Notas de Acatamento`;
2. `Nota Execução/Não Execução`, quando Acatamento não fornecer candidato. Uma ambiguidade no Acatamento bloqueia a escolha automática pela fonte inferior.

Identificar o código escrito, tolerando diferenças de apresentação:

- `PMN 101629` → `PMN101629`;
- `0018 - CGN` → `0018-CGN`;
- `PMN7745HIDROMETRO` → `PMN7745`;
- `AR5267ANEXO` → `AR5267`;
- código de formato aprovado em texto irregular, como `ADESÕA: PMN7742`.

Os espaços internos de apresentação são retirados sem mudar o conteúdo lógico. Não corrigir semanticamente, truncar ou derivar códigos. As palavras adjacentes reconhecidas foram confirmadas nos dados: `HIDROMETRO`, `ANEXO` e `AREGULARIZACAO`; outros sufixos não são cortados.

O sufixo `A` faz parte da adesão: `PMN9902A` permanece `PMN9902A`, e nunca vira `PMN9902`. Candidatos distintos ou delimitação ambígua impedem preenchimento. O texto `VN1281AREGULARIZAÇÃO ... ADESÃO VN1281A` permanece pendente sem exceção específica por OS.

## HD

Código válido: `A` ou `Y`, 2 dígitos do ano, série opcional aprovada e numeração.

```regex
^[AY]\d{2}(?:LM|SG|TL|F|G|K|N|T|X|Z|L|S)?\d+$
```

Série vazia ou `F, G, K, N, T, X, Z, L, S, LM, SG, TL`.

Prioridade: **WFM > COMERCIAL > SOCIAL > CLIENTE**. Uma fonte inferior não substitui HD válido de uma fonte superior. Comercial vazio/sem código válido permite consultar Social; `MANTER HM` não é condição obrigatória. Cliente é consultado quando as fontes anteriores não resolvem, utilizando a matrícula exata.

Dentro da fonte aplicável, escolher o maior ano presente no código. HDs distintos empatados no maior ano resultam em `CONFLITO`, sem escolha automática. A lógica de HD por OS foi removida; OS recupera matrícula e não é fonte de HD.

Não cortar sufixos nem converter códigos fora do padrão, como `Y25LM0258888B`, `Y20T425376D0002` ou valores somente numéricos.

Preservar `HD_WFM`, `HD` e `ORIGEM_HD` em ambos os arquivos. Origens permitidas: `WFM`, `COMERCIAL`, `SOCIAL`, `CLIENTE`, `CONFLITO` ou vazio; nunca `OS`.

## Saídas

- `saida/base_obra.xlsx`: base tratada completa, sem índice do DataFrame.
- `saida/base_obra.db`: tabela `adesoes`, com a seleção existente `COLUNAS_SQLITE`, incluindo `HD_WFM`, `HD`, `ORIGEM_HD` e `DATA_EXECUCAO`. Mantidos índices de OS, PDE e matrícula.

`DATA_EXECUCAO` copia `Data Fim Execução` do WFM sem conversão ou fallback na transformação. Se a coluna de origem não existir, o valor fica ausente. Na gravação SQLite, objetos date/datetime/Timestamp em colunas de tipo object são serializados em formato ISO; valores ausentes viram NULL.

Excel é exportado antes do SQLite. A tabela SQLite é substituída diretamente, sem banco temporário ou promoção conjunta das duas saídas; não há verificação `integrity_check` nesse fluxo.

Os destinos são resolvidos a partir de `Path(__file__).resolve().parent` em `config.py`, independentemente do diretório atual do terminal. A organização não modifica as colunas ou dados exportados.

## Logs

Cada execução cria `logs/etl_obra_YYYY-MM-DD_HH-MM-SS.txt`. Execuções no mesmo segundo recebem um sufixo para evitar sobrescrita. Os logs históricos foram preservados.

O módulo padrão `logging` registra início, fontes WFM e controles disponíveis, consolidação, linhas vazias removidas, recuperação por etapa, totais de matrícula/HD, origens, conflitos, diagnósticos, caminhos de saída, tempos, warnings, exceções e status de sucesso/falha.

As mensagens do console são mantidas; stdout/stderr são também registrados no arquivo. Se ocorrer exceção, o log registra `STATUS=FALHA`, traceback e tempo até a interrupção. A exceção continua sendo propagada; não há nova tentativa automática, mudança de destino ou contorno de arquivo bloqueado. Uma falha de leitura de arquivo WFM é reportada pelo consolidar, que continua com os demais arquivos; se nenhum dado válido for obtido, a execução falha. Portanto, sucesso não garante que todos os arquivos WFM foram lidos.

**`STATUS=SUCESSO` também não garante atualização do SQLite.** Se a confirmação interativa for recusada ou faltarem colunas de `COLUNAS_SQLITE`, `criar_sqlite()` retorna sem gravar e o fluxo pode terminar com sucesso. Conferir `sqlite_atualizado=True` no log, além dos warnings. Esse indicador compara existência, tamanho e data de modificação antes/depois; não é uma comparação integral do conteúdo do banco.

## Instalação e execução

Python 3.14 foi utilizado na validação desta organização. Recomenda-se ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -B main.py
```

Para execução sem a confirmação interativa do SQLite:

```powershell
$env:EXECUCAO_AGENTE = "1"
python -B main.py
```

Também é possível executar `python -B "caminho/do/projeto/main.py"` a partir de outro diretório. Importar `main` não executa o ETL. Para uso programático, a execução explícita é `main.executar()`.

Não é necessário instalar SQLite separadamente: o módulo `sqlite3` faz parte do Python. A leitura de `.xls` requer `xlrd`; arquivos `.xlsx` utilizam openpyxl. A exportação Excel utiliza os engines existentes do pandas.

## Testes

A partir da raiz:

```powershell
python -B -m unittest discover -s testes -t . -p "test_*.py"
```

Na revisão estática de 13/10/2026 foram encontrados 118 métodos de teste nos demais módulos e 7 no módulo estrutural (125 no total). Essa contagem descreve o código presente, não uma execução aprovada da suíte nesta revisão. Os estruturais validam caminhos, importação sem execução, execução de outro diretório, log no console/arquivo, warnings, fechamento e não sobrescrita dos logs, exportação temporária de fixture e falha controlada.

O entry point é exercitado apenas com dados sintéticos e destinos temporários dentro de `work/`; não usa WFM/controles reais nem sobrescreve saídas de produção. Os 5 diagnósticos internos de `testes/manuais/` não foram copiados. Foi acrescentado `testes/test_demo.py`, totalizando 126 testes aprovados nesta preparação.

O `pytest.ini` permite opcionalmente `python -m pytest` após instalar pytest. A validação oficial desta organização utilizou unittest, que não exige pytest.

## Baseline aprovado

| Indicador | Referência |
| --- | ---: |
| Registros finais | 20.428 |
| Com matrícula | 19.993 |
| Sem matrícula | 435 |
| HD WFM | 12.624 |
| HD COMERCIAL | 908 |
| HD SOCIAL | 5.484 |
| HD CLIENTE | 898 |
| CONFLITO | 8 |
| Com HD válido | 19.914 |
| Sem HD | 514 |
| ORIGEM_HD = OS | 0 |

`19.914 + 514 = 20.428`. O reconhecimento adicional das notas recupera, na simulação aprovada, 168 pelo Acatamento e 28 pela Execução, totalizando 196; existe 1 ambiguidade conhecida.

Esses números são referência aprovada, não valores forçados pelo código. Nesta organização não foi executada a produção nem revalidado o baseline com as fontes reais. A última tentativa anterior parou por PermissionError na gravação do antigo Excel. Registros sem evidência suficiente permanecem vazios, em vez de receber preenchimento especulativo.

## Arquivo legado e pendências

`obsoleto/EXCEL_TO_SQL_02.py` é um conversor independente da base de esgoto, com fonte própria hardcoded. Não é importado nem chamado por `main.py`, seus módulos transitivos ou pelos testes. Foi movido intacto e não deve ser usado como entry point deste ETL; eventual uso externo/agendado precisa de revisão manual.

`testes/manuais/Teste.py` conserva uma fonte antiga hardcoded; revise-a antes de executar esse diagnóstico. Não alteramos fontes originais. As pastas antigas de saída, `work/` e caches foram preservados. Não foi encontrado `readme.log` na raiz; as informações úteis do README anterior foram incorporadas, corrigindo sua descrição antiga de remoção de duplicatas.

## Revisão documental em 13/10/2026

Documentados DATA_EXECUCAO, comportamento de exportação e limites do status de sucesso; atualizada a contagem estática de testes. Não foram executados os testes, o ETL ou as bases de produção nesta revisão. Nenhum código de processamento foi alterado.

Nesta cópia preparada, `obsoleto/` e `testes/manuais/` citados na descrição histórica não foram incluídos. As referências a esses arquivos e backups descrevem a instalação interna de origem. Nenhum arquivo já existente no GitHub será apagado sem aprovação específica.
