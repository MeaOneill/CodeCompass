"""Versioned format-only submission hints; original runtime and UI remain intact."""
import argparse
from pathlib import Path
import sys
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.A.serve_d07 import make_server as parent_server
from scripts.A.relay_d07 import StableRelayCollector

UI_VERSION='A-D07-submission-ui-v1'

def make_server(collector,port=8773):
    server=parent_server(collector,port)
    parent=server.RequestHandlerClass
    class Handler(parent):
        def send(self,status,value,kind='application/json; charset=utf-8'):
            if self.path=='/' and isinstance(value,bytes) and kind.startswith('text/html'):
                value=value.replace(b'</body>',b'<script src="/submission-v1.js"></script></body>')
            if isinstance(value,dict) and 'runtime_version' in value:
                value=dict(value,submission_ui_version=UI_VERSION)
            return super().send(status,value,kind)
        def do_GET(self):
            if urlparse(self.path).path=='/submission-v1.js':
                if not self.valid_host():return self.send(403,{})
                return self.send(200,(ROOT/'app/A_D07_submission_v1/submission.js').read_bytes(),'text/javascript; charset=utf-8')
            return super().do_GET()
    server.RequestHandlerClass=Handler
    return server

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8773)
    p.add_argument('--actor',choices=['human_manual','test_fixture','agent_browser'],default='test_fixture')
    p.add_argument('--database',type=Path,required=True)
    a=p.parse_args();server=make_server(StableRelayCollector(ROOT,a.database,actor=a.actor),a.port)
    print(f'{UI_VERSION} http://127.0.0.1:{server.server_port}; actor={a.actor}; no paid B1 calls',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
