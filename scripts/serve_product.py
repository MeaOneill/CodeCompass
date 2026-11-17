"""Loopback product service. No research collector or paid model execution."""
import argparse,json,secrets,sys,socket
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from codecompass.product.service import Service,Conflict
from codecompass.product.workspaces import BUILD_VERSION

class ProductHTTPServer(ThreadingHTTPServer):

    allow_reuse_address = False
    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()

def make_server(service,port=8789):
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def valid(self):
            origins=[f'http://{h}:{self.server.server_port}' for h in ('127.0.0.1','localhost')]
            return self.headers.get('Host') in [o[7:] for o in origins] and self.headers.get('Origin') in [None,*origins]
        def send(self,status,value,mime='application/json; charset=utf-8'):
            raw=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,allow_nan=False).encode()
            self.send_response(status)
            for k,v in {'Content-Type':mime,'Content-Length':str(len(raw)),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'"}.items():self.send_header(k,v)
            self.end_headers();self.wfile.write(raw)
        def fail(self,status,code,message,data=None): self.send(status,dict(ok=False,error=dict(code=code,message=message,retryable=status in (409,500)),data=data))
        def dispatch(self,post=False):
            if not self.valid() or (post and self.headers.get('X-Session-Token')!=token):


                if post:
                    previous_timeout=self.connection.gettimeout()
                    try:
                        length=int(self.headers.get('Content-Length','0'))
                        if 0<length<=65536:
                            self.connection.settimeout(1);self.rfile.read(length)
                    except (ValueError,OSError):pass
                    finally:self.connection.settimeout(previous_timeout)
                return self.fail(403,'FORBIDDEN','请从本机产品页面重新打开')
            u=urlparse(self.path);q=parse_qs(u.query);arg=lambda k:q.get(k,[''])[0]
            try:
                if post:
                    n=int(self.headers.get('Content-Length','0'))
                    if not 0<n<=4300000: raise ValueError('请求过大或为空')
                    d=json.loads(self.rfile.read(n))
                    if not isinstance(d,dict): raise ValueError('请求需要对象格式')
                else:
                    if u.path in ('/','/app.js','/workspaces.js','/journey.js','/source-map.js','/style.css'):
                        name,mime={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/workspaces.js':('workspaces.js','text/javascript'),'/journey.js':('journey.js','text/javascript'),'/source-map.js':('source-map.js','text/javascript'),'/style.css':('style.css','text/css')}[u.path]
                        return self.send(200,(ROOT/'app/product'/name).read_bytes(),mime+'; charset=utf-8')
                if u.path=='/api/product/health' and not post:
                    with service.store.connect() as db: db.execute('SELECT 1').fetchone()
                    v=dict(version=service.config['version'],build_version=BUILD_VERSION,content_version=service.config['content_version'],database='available')
                elif u.path=='/api/product/bootstrap' and not post:
                    v=dict(token=token,tasks=service.catalog.tasks,assistant_mode=service.assistant.mode(),
                           demo_available=service.workspaces.demo_available(),profile=service.profile(arg('user')) if arg('user') else None)
                elif u.path=='/api/product/demo' and post: v=service.workspaces.demo()
                elif u.path=='/api/product/profile': v=service.profile(d.get('user_id')) if post else service.profile(arg('user')) if arg('user') else None
                elif u.path=='/api/product/onboarding' and post: v=service.workspaces.onboard(d['user_id'],d['value'],d['revision'])
                elif u.path=='/api/product/assessment' and post:
                    v=service.onboarding.submit(d['user_id'],d['attempt_id'],d['answers']) if 'answers' in d else service.onboarding.start(d['user_id'])
                elif u.path=='/api/product/repository':
                    v=service.workspaces.start(d['user_id'],d['url'],d['request_id']) if post else service.workspaces.repository(arg('user'),arg('id'))
                elif u.path=='/api/product/route':
                    v=service.workspaces.create(d['user_id'],d['repository_id'],d['goal'],d.get('selected'),d.get('budget',120),d.get('request_id')) if post else service.workspaces.route(arg('user'),arg('id'))
                elif u.path=='/api/product/source-map' and not post:
                    from codecompass.product.source_map import overview
                    v=overview(service.workspaces,arg('user'),arg('id'))
                elif u.path=='/api/product/route-feedback' and post:
                    v=service.workspaces.feedback(d['user_id'],d['route_id'],d['revision'],d['request_id'],d['action'],d.get('unit_id'),d.get('preparation'))
                elif u.path=='/api/product/source-issues' and not post:
                    v=service.workspaces.issues.get(arg('user'),arg('id'),arg('refresh')=='1')
                elif u.path=='/api/product/learning-check' and post:
                    v=service.workspaces.learning_check(d['user_id'],d['route_id'],d['unit_id'],d['concept'],d['answer'])
                elif u.path=='/api/product/source-assistant':
                    v=service.source_assistant.ask(d['user_id'],d['route_id'],d['unit_id'],d['message'],d['request_id'],d.get('mode','auto')) if post else service.source_assistant.history(arg('user'),arg('route'))
                elif u.path=='/api/product/session': v=service.create(d['user_id'],d['task_id'],d.get('scope','default')) if post else service.get(arg('id'))
                elif u.path=='/api/product/material' and not post: v=service.material(arg('session'),arg('unit'))
                elif u.path=='/api/product/action' and post: v=service.action(d['session_id'],d['request_id'],d['revision'],d['action'],d.get('payload'))
                elif u.path=='/api/product/draft' and post: v=service.draft(d['session_id'],d['request_id'],d['revision'],d.get('kind','practice'),d['content'])
                elif u.path=='/api/product/assistant':
                    v=service.assistant.ask(d['session_id'],d['unit_id'],d['message'],d['request_id'],d.get('mode','auto')) if post else service.assistant.history(arg('session'))
                elif u.path=='/api/product/starter' and not post:
                    from codecompass.product.submissions import starter
                    return self.send(200,starter(ROOT,arg('task')),'application/zip')
                elif u.path=='/api/product/submission' and post:
                    v=service.submissions.submit(d['session_id'],d['request_id'],d['revision'],d.get('package_base64'),d.get('run_checks',False),d.get('note',''),d.get('submission_id'))
                elif u.path=='/api/product/export' and not post:return self.send(200,service.submissions.export(arg('session')),'application/zip')
                elif u.path=='/api/product/transfer' and post:v=service.transfer(d['session_id'],d.get('target_project'),d.get('concept_id','python.iterator_protocol'))
                elif u.path=='/api/product/issues' and not post:v=service.issues.get(arg('session'),arg('refresh')=='1')
                else:return self.fail(404,'NOT_FOUND','找不到这个入口')
                self.send(200,dict(ok=True,data=v))
            except Conflict as e:self.fail(409,'STALE_STATE',str(e),e.data)
            except (KeyError,TypeError,json.JSONDecodeError):self.fail(400,'INVALID_REQUEST','请求格式不正确，请返回页面重新操作')
            except ValueError as e:self.fail(400,'INVALID_REQUEST',str(e))
            except Exception:self.fail(500,'INTERNAL_ERROR','服务暂时无法完成操作，原记录保留，请重试')
        def do_GET(self):self.dispatch()
        def do_POST(self):self.dispatch(True)
    return ProductHTTPServer(('127.0.0.1',port),Handler)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8789);p.add_argument('--database',type=Path,default=ROOT/'local_data/product/product.sqlite3');p.add_argument('--actor',choices=['local_user','agent_demo','test_fixture'],default='local_user');p.add_argument('--assistant-demo',choices=['timeout','error']);a=p.parse_args()
    kwargs={}
    if a.assistant_demo:
        if a.actor!='agent_demo':p.error('Assistant error demonstrations require an explicit demo actor')
        from scripts.B.comparison.b1 import SpendMeter
        def demo_transport(*args):
            if a.assistant_demo=='timeout':raise TimeoutError('explicit automated timeout demonstration')
            raise ValueError('explicit automated transport error demonstration')
        kwargs=dict(transport=demo_transport,meter=SpendMeter(1))
    try: service=Service(ROOT,a.database,a.actor,**kwargs)
    except (OSError,ValueError): sys.exit('产品内容或本地数据初始化失败，请核对源码包、配置及数据目录权限；不会清除已有记录。')
    try: server=make_server(service,a.port)
    except OSError: sys.exit(f'无法启动 http://127.0.0.1:{a.port}，端口可能已占用；请用 -Port 指定其他端口。不会停止其他进程。')
    print(f'CodeCompass http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
