"""A-D07 opt-in UI, no paid calls; leaves original B UI and collector unchanged."""
import argparse
from pathlib import Path
import sys
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.A.relay_d07 import StableRelayCollector
from scripts.B.serve_relay_v2 import make_server as original_server


def make_server(collector,port=8771):
    server=original_server(collector,port)
    parent=server.RequestHandlerClass
    class Handler(parent):
        def send(self,status,value,kind='application/json; charset=utf-8'):
            if self.path=='/' and isinstance(value,bytes) and kind.startswith('text/html'):
                snippet=b'<section id="a07-audit" hidden></section><script src="/a07.js"></script>'
                value=value.replace(b'</body>',snippet+b'</body>')
            return super().send(status,value,kind)
        def do_GET(self):
            if urlparse(self.path).path=='/a07.js':
                if not self.valid_host():return self.send(403,{})
                return self.send(200,(ROOT/'app/A_D07/a07.js').read_bytes(),'text/javascript; charset=utf-8')
            return super().do_GET()
    server.RequestHandlerClass=Handler
    return server


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8771)
    p.add_argument('--actor',choices=['test_fixture','human_manual','agent_browser'],default='test_fixture')
    p.add_argument('--database',type=Path,default=ROOT/'tmp/A-D07-development.sqlite3')
    a=p.parse_args();c=StableRelayCollector(ROOT,a.database,actor=a.actor)
    server=make_server(c,a.port)
    print(f'A-D07开发/预演候选 http://127.0.0.1:{server.server_port}; actor={a.actor}; B1未配置，不调用模型；正式G2未放行',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
