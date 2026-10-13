DB_PATH='saida/base_obra.db'
EXPECTED={'adesoes': 3}
QUERY='SELECT MATRICULA, HD FROM adesoes ORDER BY MATRICULA'
ROWS=[('DEM1001', 'A26LM900001'), ('DEM1002', 'A26LM900002'), ('DEM1003', 'A26LM900003')]

from contextlib import closing
from pathlib import Path
import os,shutil,sqlite3,subprocess,sys,tempfile,unittest

class DemoTests(unittest.TestCase):
    def test_execucao_com_entradas_sinteticas(self):
        root=Path(__file__).resolve().parents[1]
        temp_root=root/'work'/'integration';temp_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as folder:
            demo=Path(folder)
            for p in root.rglob('*.py'):
                rel=p.relative_to(root)
                if any(x in {'work','__pycache__','tests','testes'} for x in rel.parts):continue
                dest=demo/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
            env=os.environ.copy();env['EXECUCAO_AGENTE']='1';env['PYTHONIOENCODING']='utf-8'
            for script in ['gerar_demo.py','main.py']:
                run=subprocess.run([sys.executable,'-X','utf8',script],cwd=demo,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60)
                self.assertEqual(run.returncode,0,run.stdout+'\n'+run.stderr)
            with closing(sqlite3.connect(demo/DB_PATH)) as con:
                self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                for table,count in EXPECTED.items():
                    self.assertEqual(con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0],count)
                rows=con.execute(QUERY).fetchall()
                self.assertEqual(rows,ROWS)

if __name__=='__main__':unittest.main()
