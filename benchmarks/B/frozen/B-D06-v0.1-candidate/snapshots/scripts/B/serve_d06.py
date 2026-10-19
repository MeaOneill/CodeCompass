"""D06 candidate development UI; never starts a formal enrolled study."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.B.serve_d05 import make_server
from codecompass.app.study_d06 import StudyCollector


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8767);a=p.parse_args()
    c=StudyCollector(ROOT,ROOT/'tmp/B-D06-development.sqlite3',actor='test_fixture')
    server=make_server(c,a.port,ROOT/'app/B_D06')
    print(f'候选开发界面 http://127.0.0.1:{server.server_port}；非正式实验，无API费用',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
