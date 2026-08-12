import os

PASTA_DADOS = r"C:\Users\MateusCrudodeBarros\DEEPESSOAS\PROJETOS - SABESP - PERFORMANCE GUARUJÁ\PERFORMANCE_GUARUJA_AGUA\EXECUÇÃO\BACKOFFICE\CONFERENCIA\Reconferencia\Ligações de água"

arquivos = [f for f in os.listdir(PASTA_DADOS)
            if f.endswith(".xlsx") or f.endswith(".xls")]

print(arquivos)