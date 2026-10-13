"""Cria planilhas fictícias WFM e de controle, sem consultar origens externas."""
from pathlib import Path
import pandas as pd

def gerar_demo():
    root=Path(__file__).resolve().parent/'ENTRADA'
    w=root/'WFM'/'WFM_FICTICIO.xlsx';c=root/'SHAREPOINT'/'CONTROLE_FICTICIO.xlsx'
    if w.exists() or c.exists():raise FileExistsError('Amostras já existem.')
    w.parent.mkdir(parents=True,exist_ok=True);c.parent.mkdir(parents=True,exist_ok=True)
    rows=[]
    for i in range(1,4):
        rows.append({'Número OS':900000+i,'Notas de Acatamento':f'ADESAO DEM100{i}',
            'PDE':f'PDE-DEMO-{i}','Endereço':f'Rua Fictícia {i}','Número':10*i,
            'Complemento':'Casa fictícia','Bairro':'Bairro Exemplo',
            'Nota Execução/Não Execução':f'Instalado A26LM90000{i}',
            'Data Fim Execução':f'0{i}/10/2026 10:00'})
    pd.DataFrame(rows).to_excel(w,sheet_name='WFM_DEMO',index=False)
    pd.DataFrame({'ADESAO':['DEM1001','DEM1002','DEM1003'],
                  'OS / FORNECIMENTO':[900001,900002,900003],
                  'Endereco':['Rua Fictícia 1','Rua Fictícia 2','Rua Fictícia 3'],
                  'Hidrômetro Comercial':['A26LM900001','A26LM900002','A26LM900003'],
                  'Hidrômetro Social':[None,None,None]}).to_excel(c,sheet_name='GERAL',index=False)
    print('Entradas fictícias de Obra criadas.')

if __name__=='__main__':gerar_demo()
