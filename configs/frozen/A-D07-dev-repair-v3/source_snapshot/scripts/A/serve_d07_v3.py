"""Loopback-only v0.3 development pilot; no API model or final-answer access."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from codecompass.app.pilot_d07_v3 import Pilot

def make_server(pilot,port=8774):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*a):pass
        def valid_host(self):return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def send(self,status,value,kind='application/json; charset=utf-8'):
            raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status)
            for k,v in [('Content-Type',kind),('Content-Length',str(len(raw))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")]:self.send_header(k,v)
            self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not self.valid_host():return self.send(403,{})
            u=urlparse(self.path)
            try:
                if u.path in ('/','/app.js','/style.css'):
                    name,kind={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}[u.path]
                    rel='app/A_D07_v3/'+name;raw=(ROOT/rel).read_bytes()
                    if hashlib.sha256(raw).hexdigest()!=pilot.provenance['source_hashes'][rel]:raise ValueError('界面源版本已变化，请停止本轮')
                    return self.send(200,raw.replace(b'__TOKEN__',token.encode()),kind+'; charset=utf-8')
                if u.path=='/api/view':return self.send(200,pilot.get(parse_qs(u.query).get('id',[''])[0]))
                return self.send(404,{})
            except (ValueError,KeyError):return self.send(400,{'error':'记录不存在或来源/版本已变化；原记录保留，请联系组织者。'})
        def do_POST(self):
            origin=self.headers.get('Origin');base=f'http://127.0.0.1:{self.server.server_port}'
            if not self.valid_host() or self.headers.get('X-Session-Token')!=token or origin not in (None,base,base.replace('127.0.0.1','localhost')):return self.send(403,{})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=12000:raise ValueError('提交大小错误')
                d=json.loads(self.rfile.read(size))
                if not isinstance(d,dict):raise ValueError('提交格式错误')
                if self.path=='/api/start':result=pilot.create(d.get('consent'))
                elif self.path=='/api/action':result=pilot.action(d['id'],d['action'],d.get('payload',{}))
                else:return self.send(404,{})
                return self.send(200,result)
            except (ValueError,KeyError,TypeError):return self.send(400,{'error':'当前步骤不接受此提交。请选择每题答案或“不会/跳过”，确认已读；暂停时请先恢复。原输入保留。'})
            except Exception:return self.send(500,{'error':'操作未完成，原记录保留；请暂停并联系组织者，不要重复开始。'})
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--port',type=int,default=8774)
    p.add_argument('--actor',choices=['human_manual','test_fixture','agent_browser'],default='test_fixture');a=p.parse_args()
    s=make_server(Pilot(ROOT,a.database,actor=a.actor),a.port)
    print(f'v0.3开发机制验证 http://127.0.0.1:{s.server_port}; actor={a.actor}; 无模型调用',flush=True)
    try:s.serve_forever()
    except KeyboardInterrupt:pass
    finally:s.server_close()
