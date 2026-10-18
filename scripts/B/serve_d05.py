"""Loopback-only development experiment UI. No paid model calls."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.experiment import Collector


def make_server(collector, port=8765):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass  # No session capabilities, IPs or identities in logs.

        def send(self,code,body,kind='application/json; charset=utf-8'):
            self.send_response(code)
            self.send_header('Content-Type',kind);self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

        def check_host(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

        def do_GET(self):
            if not self.check_host():return self.send(403,b'{}')
            u=urlparse(self.path)
            if u.path in ('/','/app.js','/style.css'):
                names={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
                name,kind=names[u.path];body=(ROOT/'app/B_D05'/name).read_bytes()
                if name=='index.html':body=body.replace(b'__TOKEN__',token.encode())
                return self.send(200,body,kind+'; charset=utf-8')
            if u.path=='/api/session':
                try:
                    value=collector.get(parse_qs(u.query).get('id',[''])[0])
                    return self.send(200,json.dumps(value,ensure_ascii=False).encode())
                except ValueError as e:return self.send(400,json.dumps({'error':str(e)},ensure_ascii=False).encode())
            self.send(404,b'{}')

        def do_POST(self):
            origin=self.headers.get('Origin')
            if (not self.check_host() or self.headers.get('X-Session-Token')!=token or
                (origin and origin not in (f'http://localhost:{self.server.server_port}',f'http://127.0.0.1:{self.server.server_port}'))):
                return self.send(403,b'{}')
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=65536:raise ValueError('Request size invalid')
                data=json.loads(self.rfile.read(size))
                if self.path=='/api/start':
                    value=collector.create(data.get('task','task_001'),data.get('method','Ours'),data.get('participant'))
                elif self.path=='/api/action':
                    value=collector.action(data['session_id'],data['action'],data.get('payload'))
                else:return self.send(404,b'{}')
                self.send(200,json.dumps(value,ensure_ascii=False).encode())
            except (ValueError,KeyError,TypeError) as e:
                self.send(400,json.dumps({'error':str(e)},ensure_ascii=False).encode())
            except Exception:
                self.send(500,json.dumps({'error':'服务器操作失败，保留此前检查点；请查看本地开发终端。'},ensure_ascii=False).encode())
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8765)
    p.add_argument('--database',type=Path,default=ROOT/'tmp/B-D05-human.sqlite3')
    p.add_argument('--actor',choices=['human_manual','agent_browser','test_fixture'],default='human_manual')
    a=p.parse_args(); db=a.database.resolve()
    if not db.is_relative_to(ROOT/'tmp'):p.error('个人数据库必须位于忽略的 tmp 目录')
    collector=Collector(ROOT,db,actor=a.actor)
    server=make_server(collector,a.port)
    print(f'CodeCompass 开发界面 http://127.0.0.1:{server.server_port} | actor={a.actor} | 仅本机，无付费调用',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
