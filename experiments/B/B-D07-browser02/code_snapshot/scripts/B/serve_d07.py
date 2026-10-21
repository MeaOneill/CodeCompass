"""One loopback entry for the B-D07 development journey; no paid model by default."""
import argparse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from codecompass.app.journey_d07 import JourneyCollector


def make_server(c,port=8780):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def valid_host(self):return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def send(self,status,value,mime='application/json; charset=utf-8'):
            raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not self.valid_host():return self.send(403,{})
            u=urlparse(self.path);q=parse_qs(u.query)
            try:
                if u.path in ('/','/app.js','/style.css'):
                    name,mime={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}[u.path]
                    return self.send(200,(ROOT/'app/B_D07'/name).read_bytes().replace(b'__TOKEN__',token.encode()),mime+'; charset=utf-8')
                if u.path=='/api/tasks':return self.send(200,c.tasks())
                if u.path=='/api/session':return self.send(200,c.get(q.get('id',[''])[0]))
                if u.path=='/api/profile':return self.send(200,c.profile(q.get('user',[''])[0]))
                if u.path=='/api/issues':return self.send(200,c.issues(q.get('id',[''])[0]))
                return self.send(404,{})
            except (ValueError,KeyError,TypeError):return self.send(400,{'error':'记录不存在、来源不匹配或校验失败；请保留当前匿名编号与检查点。'})
            except Exception:return self.send(500,{'error':'读取失败，未修改原始记录；请保留检查点。'})
        def do_POST(self):
            if not self.valid_host() or self.headers.get('X-Session-Token')!=token or self.headers.get('Origin') not in (None,f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
                return self.send(403,{})
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=500000:raise ValueError('请求过大或缺失')
                d=json.loads(self.rfile.read(length))
                if not isinstance(d,dict):raise ValueError('JSON object required')
                if self.path=='/api/enroll':v=c.enroll(d.get('consent'))
                elif self.path=='/api/pretest':v=c.pretest(d['participant'],d['choices'])
                elif self.path=='/api/start':v=c.create(d.get('task','task_002'),d.get('method','Ours'),d.get('participant'))
                elif self.path=='/api/action':v=c.action(d['session_id'],d['action'],d.get('payload'))
                elif self.path=='/api/transfer':v=c.transfer(d['participant'])
                else:return self.send(404,{})
                self.send(200,v)
            except (ValueError,KeyError,TypeError) as e:self.send(400,{'error':str(e)})
            except Exception:self.send(500,{'error':'操作失败，检查点已保留；不会自动重试模型或伪造作答。'})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8780)
    p.add_argument('--actor',choices=['test_fixture','agent_browser','human_manual'],default='test_fixture');p.add_argument('--database',type=Path);a=p.parse_args()
    database=a.database or ROOT/f'tmp/B-D07-{a.actor}.sqlite3'
    c=JourneyCollector(ROOT,database,actor=a.actor);server=make_server(c,a.port)
    print(f'B-D07完整开发闭环 http://127.0.0.1:{server.server_port} actor={a.actor}; 默认不付费；非正式研究',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
