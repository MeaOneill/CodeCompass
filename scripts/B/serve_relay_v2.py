"""Loopback UI for all twelve tasks; B1 live mode requires explicit local config."""
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.relay_v2 import RelayCollector
from scripts.B.comparison.b1 import PersistentSpendMeter


def make_server(c,port=8768):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def send(self,status,value,kind='application/json; charset=utf-8'):
            raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
            self.send_response(status);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(raw)
        def valid_host(self):return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def do_GET(self):
            if not self.valid_host():return self.send(403,{})
            u=urlparse(self.path)
            if u.path in ('/','/app.js','/style.css'):
                name,kind={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}[u.path]
                body=(ROOT/'app/B_D06_v2'/name).read_bytes().replace(b'__TOKEN__',token.encode())
                return self.send(200,body,kind+'; charset=utf-8')
            try:
                if u.path=='/api/tasks':return self.send(200,c.tasks())
                if u.path=='/api/session':return self.send(200,c.get(parse_qs(u.query).get('id',[''])[0]))
                return self.send(404,{})
            except ValueError as e:return self.send(400,{'error':str(e)})
        def do_POST(self):
            origin=self.headers.get('Origin')
            if not self.valid_host() or self.headers.get('X-Session-Token')!=token or origin not in (None,f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
                return self.send(403,{})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=500000:raise ValueError('请求内容过大或缺失')
                d=json.loads(self.rfile.read(size))
                if self.path=='/api/start':value=c.create(d.get('task','task_001'),d.get('method','Ours'),d.get('participant'))
                elif self.path=='/api/action':value=c.action(d['session_id'],d['action'],d.get('payload'))
                else:return self.send(404,{})
                self.send(200,value)
            except (ValueError,KeyError,TypeError) as e:self.send(400,{'error':str(e)})
            except Exception:self.send(500,{'error':'操作失败，已保留原有检查点。不会自动重试付费调用。'})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8768)
    p.add_argument('--enable-b1',action='store_true');p.add_argument('--actor',choices=['test_fixture','human_manual','agent_browser'],default='test_fixture');a=p.parse_args()
    config=json.loads((ROOT/'configs/B/D06_v2_deepseek.json').read_text(encoding='utf-8'))['b1'] if a.enable_b1 else None
    meter=PersistentSpendMeter(ROOT/config['budget_state_path'],5,'CNY') if config else None
    c=RelayCollector(ROOT,ROOT/f'tmp/B-D06-v2-{a.actor}.sqlite3',actor=a.actor,b1_config=config,meter=meter)
    server=make_server(c,a.port);print(f'12题联调候选 http://127.0.0.1:{server.server_port}；非正式实验；B1实时调用={a.enable_b1}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
