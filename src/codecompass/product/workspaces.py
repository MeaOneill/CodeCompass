"""Persistent repository jobs, once-user self report and recoverable source routes."""
import copy
import io
import json
import secrets
import threading
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from zipfile import ZipFile
from .repositories import acquire, repository_url, FEATURES
from .source_routes import build, solve, ranked_symbols
from .reading_order import optimize_first_order, optimize_remaining_order

BUILD_VERSION = 'product-20261116-r7.1-p1'
LICENSE_LABEL = '仅本地只读静态分析（未作自动许可证裁决与代码再分发）'
DEMO_SOURCE = Path('benchmarks/sources/r5-offline/itsdangerous/benchmarks/sources/imported')
DEMO_COMMIT = '672971d66a2ef9f85151e53283113f33d642dabd'
from .goal_resolution import enrich,resolve,model_resolve
from codecompass.graph import read_snapshot


def stamp(): return datetime.now(timezone.utc).isoformat()
def dump(value): return json.dumps(value,ensure_ascii=False,allow_nan=False)


class Workspaces:
    def __init__(self, service, *, loader=None):
        self.service=service; self.store=service.store; self.loader=loader
        self.root=Path(service.store.path).resolve().parent/'source_workspaces'
        self.root.mkdir(parents=True,exist_ok=True)
        self.slots=threading.BoundedSemaphore(2)
        from .source_issues import SourceIssues
        self.issues=SourceIssues(self)
        with self.store.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS product_repositories(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,request_id TEXT NOT NULL,repository TEXT NOT NULL,status TEXT NOT NULL,message TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(user_id,request_id));
            CREATE TABLE IF NOT EXISTS product_source_routes(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,repository_id TEXT NOT NULL,revision INTEGER NOT NULL,state_json TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS product_source_requests(user_id TEXT NOT NULL,request_id TEXT NOT NULL,payload TEXT NOT NULL,route_id TEXT NOT NULL,PRIMARY KEY(user_id,request_id));
            CREATE TABLE IF NOT EXISTS product_goal_resolutions(user_id TEXT NOT NULL,repository_id TEXT NOT NULL,goal TEXT NOT NULL,result_json TEXT,PRIMARY KEY(user_id,repository_id,goal));
            ''')
            db.execute("UPDATE product_repositories SET status='interrupted',message='服务重启中断了导入，请重新导入；既有路线保留。' WHERE status='importing'")

    def preferences(self, db, uid):
        prefs=json.loads(self.service.user(db,uid)['preferences_json'])
        from .learning_growth import record_read
        for row in db.execute('SELECT id,state_json FROM product_source_routes WHERE user_id=?',(uid,)):
            state=json.loads(row['state_json'])
            for identity in state['completed']:
                record_read(prefs,state['data']['views'][identity],state['repository'],advance=False,route_id=row['id'],unit_id=identity)
        return prefs

    def onboard(self, uid, value, revision):
        if not isinstance(value,dict) or value.get('experience') not in ('new','some','comfortable'):
            raise ValueError('请选择 Python 学习经历')
        familiar=value.get('familiar',[])
        if not isinstance(familiar,list) or len(set(familiar))!=len(familiar) or any(x not in FEATURES for x in familiar):
            raise ValueError('熟悉的主题不受支持')
        if value.get('months') not in ('0','1-6','6-24','24+'):
            raise ValueError('请选择学习时长')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); prefs=self.preferences(db,uid)
            if type(revision) is not int or revision!=prefs.get('revision',0):
                raise ValueError('画像已更新，请刷新后再保存')
            prefs.update(onboarding=dict(experience=value['experience'],months=value['months'],familiar=familiar,
                                         completed_at=stamp(),source='self_report',mastery_evidence=False),revision=revision+1)
            for c in familiar:
                if c in prefs.get('source_feedback',{}): prefs['source_feedback'][c]='familiar'
            db.execute('UPDATE product_users SET preferences_json=? WHERE user_id=?',(dump(prefs),uid))
        return self.service.profile(uid)

    def jobs(self, uid):
        with self.store.connect() as db:
            self.service.user(db,uid)
            return [dict(r) for r in db.execute('SELECT * FROM product_repositories WHERE user_id=? ORDER BY updated_at DESC',(uid,))]

    def demo_available(self):
        return (self.service.root/DEMO_SOURCE/'snapshot.json').is_file()

    def demo(self):
        source=self.service.root/DEMO_SOURCE
        if not self.demo_available():
            raise ValueError('示例暂不可用。可以返回工作台，导入自己的公开仓库。')
        try:
            snapshot=json.loads((source/'snapshot.json').read_text(encoding='utf-8'))
            if snapshot['commit']!=DEMO_COMMIT or snapshot['url']!='https://github.com/pallets/itsdangerous':
                raise ValueError('unexpected demo source')
            files=read_snapshot(source,snapshot)
        except (OSError,ValueError,KeyError) as exc:
            raise ValueError('示例文件不完整，请重新解压运行包后重试。') from exc
        buffer=io.BytesIO()
        with ZipFile(buffer,'w') as archive:
            for name,raw in files.items():
                archive.writestr('itsdangerous/'+name,raw)
        def bundled_loader(url, limit):
            if url.endswith('/commits/HEAD'):
                return dump({'sha':DEMO_COMMIT}).encode()
            if url.endswith('/zipball/'+DEMO_COMMIT):
                return buffer.getvalue()
            raise ValueError('示例源码读取失败，请重试。')
        uid=self.service.profile()['user_id']
        self.onboard(uid,dict(experience='new',months='0',familiar=[]),0)
        job=self.start(uid,snapshot['url'],'bundled-demo',bundled_loader=bundled_loader)
        if job['status']!='ready':
            raise ValueError('示例导入失败，请返回工作台重试。')

        selected=[s['id'] for s in job['symbols']
                  if s['name']=='TimestampSigner.unsign' and s['id']=='src/itsdangerous/timed.py::TimestampSigner.unsign@72']
        if len(selected)!=1:
            raise ValueError('示例源码范围无法确认，请重新解压运行包。')
        route=self.create(uid,job['id'],'理解带时间戳的签名是怎样验证的',selected,budget=None)
        if route['state']['result']['status']!='FEASIBLE':
            raise ValueError('示例路线暂未生成，请返回工作台重试。')
        return dict(profile=self.service.profile(uid),route=route)

    def start(self, uid, url, request_id, *, bundled_loader=None):
        repo=repository_url(url)
        if not isinstance(request_id,str) or not 1<=len(request_id)<=100: raise ValueError('缺少导入请求编号')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE'); prefs=self.preferences(db,uid)
            if not prefs.get('onboarding'): raise ValueError('请先完成一次能力了解')
            old=db.execute('SELECT * FROM product_repositories WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
            if old:
                if old['repository']!=repo: raise ValueError('导入请求编号已经用于另一个仓库')
                return dict(old)
            if not self.slots.acquire(blocking=False): raise ValueError('有仓库正在导入，请稍后重试')
            rid='r_'+secrets.token_hex(16)
            try:
                db.execute('INSERT INTO product_repositories VALUES(?,?,?,?,?,?,?)',(rid,uid,request_id,repo,'importing','正在获取固定提交并分析 Python 源码…',stamp()))
            except Exception:
                self.slots.release(); raise
        if bundled_loader is None:
            threading.Thread(target=self._import,args=(rid,repo),daemon=True).start()
        else:
            self._import(rid,repo,bundled_loader)
        return self.repository(uid,rid)

    def _import(self,rid,repo,bundled_loader=None):
        try:
            loader=bundled_loader or self.loader
            kwargs={'loader':loader} if loader else {}
            acquire(self.service.root,self.root/rid,repo,**kwargs)
            status='ready'; message='源码分析完成，请确认你想理解的函数或类。'
        except HTTPError as e:
            status='failed'; message='GitHub 暂不可访问或请求额度不足，请确认公开仓库链接后重试。' if e.code in (403,404,429) else 'GitHub 下载失败，请稍后重试。'
            if e.code in (403,429) and self.cached_import(rid,repo):status='ready';message='已载入本机保存的源码，可以继续规划。'
        except (URLError,TimeoutError):
            status='failed'; message='网络连接失败，原路线保留，请稍后重新导入。'
            if self.cached_import(rid,repo):status='ready';message='已载入本机保存的源码，可以继续规划。'
        except ValueError as e: status='failed'; message=str(e)
        except Exception: status='failed'; message='源码导入失败；未执行仓库代码，原记录保留，请换较小仓库重试。'
        finally:
            with self.store.connect() as db:
                db.execute('UPDATE product_repositories SET status=?,message=?,updated_at=? WHERE id=?',(status,message,stamp(),rid))
            self.slots.release()

    def cached_import(self,rid,repo):

        roots={self.root,self.service.root/'local_data/product/source_workspaces'}
        for root in roots:
            for manifest in sorted(root.glob('r_*/repository.json'),key=lambda p:p.stat().st_mtime,reverse=True):
                if manifest.parent==self.root/rid:continue
                try:
                    data=json.loads(manifest.read_text(encoding='utf-8'))
                    if data['repository']!=repo:continue
                    contents=read_snapshot(manifest.parent/'benchmarks/sources/imported',data['snapshot'])
                    target=self.root/rid;target.mkdir(parents=True,exist_ok=True)
                    source=target/'benchmarks/sources/imported';source.mkdir(parents=True,exist_ok=True)
                    for name,raw in contents.items():
                        dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
                    (source/'snapshot.json').write_text(dump(data['snapshot']),encoding='utf-8')
                    (target/'schemas').mkdir(exist_ok=True)
                    for name in ('contracts.schema.json','contracts-1.1.schema.json'):shutil.copyfile(self.service.root/'schemas'/name,target/'schemas'/name)
                    shutil.copyfile(manifest.parent/'graph.json',target/'graph.json')
                    data.update(import_mode='cached',cache_loaded_at=stamp())
                    (target/'repository.json').write_text(dump(data),encoding='utf-8')
                    return True
                except (OSError,KeyError,ValueError):continue
        return False

    def repository(self,uid,rid):
        with self.store.connect() as db:
            self.service.user(db,uid)
            r=db.execute('SELECT * FROM product_repositories WHERE id=? AND user_id=?',(rid,uid)).fetchone()
            if not r: raise ValueError('找不到当前学习者的仓库记录')
        result=dict(r)
        if r['status']=='ready':
            repo=self._repo(rid)
            result.update(snapshot=repo['snapshot'],license_status='not_checked',license_status_label=LICENSE_LABEL,
                          symbols=[{k:s[k] for k in ('id','name','path','features','doc','test_source')} for s in repo['symbols']],
                          graph_summary=repo['graph_summary'],parse_manifest=repo['parse_manifest'],import_mode=repo.get('import_mode','online'))
        return result

    def _repo(self,rid):

        return json.loads((self.root/rid/'repository.json').read_text(encoding='utf-8'))

    def routes(self,uid):
        with self.store.connect() as db:
            self.service.user(db,uid)
            return [dict(id=r['id'],repository_id=r['repository_id'],revision=r['revision'],updated_at=r['updated_at'],
                         goal=json.loads(r['state_json'])['goal']) for r in db.execute('SELECT * FROM product_source_routes WHERE user_id=? ORDER BY updated_at DESC',(uid,))]

    def route(self,uid,route_id):
        with self.store.connect() as db:
            self.service.user(db,uid)
            r=db.execute('SELECT * FROM product_source_routes WHERE id=? AND user_id=?',(route_id,uid)).fetchone()
            if not r: raise ValueError('找不到当前学习者的源码路线')
            state=json.loads(r['state_json']); prefs=self.preferences(db,uid)
        from .learning_view import insights
        view=insights(state,prefs)
        view['source_graph']=self._repo(r['repository_id'])['graph_summary']
        if state.get('issue_status') in ('skipped','completed') and not state['result']['remaining'] and state['result']['status']=='FEASIBLE':view['learning_phase']='review'
        return dict(id=r['id'],revision=r['revision'],repository_id=r['repository_id'],state=state,insights=view,
                    build_version=BUILD_VERSION,license_status='not_checked',license_status_label=LICENSE_LABEL,
                    profile_changed=prefs.get('revision',0)!=state['profile_revision'])

    def create(self,uid,rid,goal,selected=None,budget=120,request_id=None):
        self.repository(uid,rid)
        if not isinstance(goal,str) or not 2<=len(goal.strip())<=500: raise ValueError('请输入 2 至 500 字的学习目标')
        if budget is not None and (type(budget) not in (int,float) or not 5<=budget<=10000): raise ValueError('请填写有效的学习容量')
        if request_id is not None and (not isinstance(request_id,str) or not 1<=len(request_id)<=100): raise ValueError('规划请求编号无效')
        payload=dump([rid,goal,selected,budget])
        with self.store.connect() as db:
            cached=db.execute('SELECT * FROM product_source_requests WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
        if cached:
            if cached['payload']!=payload: raise ValueError('规划请求编号已用于其他内容')
            return self.route(uid,cached['route_id'])
        repo=enrich(self.root/rid,self._repo(rid))
        with self.store.connect() as db: prefs=self.preferences(db,uid)
        if not prefs.get('onboarding'): raise ValueError('请先完成一次能力了解')
        intent=resolve(repo,goal,selected)
        if intent is None:
            with self.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                cached_intent=db.execute('SELECT result_json FROM product_goal_resolutions WHERE user_id=? AND repository_id=? AND goal=?',(uid,rid,goal)).fetchone()
                if cached_intent is None:db.execute('INSERT INTO product_goal_resolutions VALUES(?,?,?,NULL)',(uid,rid,goal))
            if cached_intent is None:
                intent=model_resolve(self.service,repo,goal)
                with self.store.connect() as db:db.execute('UPDATE product_goal_resolutions SET result_json=? WHERE user_id=? AND repository_id=? AND goal=?',(dump(intent),uid,rid,goal))
            elif cached_intent['result_json']:intent=json.loads(cached_intent['result_json'])
        data=build(self.root/rid,repo,goal,selected,prefs,uid,self.service.actor!='local_user',intent=intent)
        if data is None:
            return dict(needs_selection=True,needs_clarification=True,candidates=[],message='请描述需要理解的功能，或选择核心流程、完整学习。')
        if budget is None:budget=sum(u['base_cost'] for u in data['units'])*1.5+len(data['units'])+20
        ledger=self.store.evidence.read(uid,simulated=self.service.actor!='local_user')
        result=solve(self.root/rid,data,ledger,budget=budget)
        result=optimize_first_order(data,result)
        for unit, explanation in result.get('reading_order', {}).get('explanations', {}).items():
            data['views'][unit]['order_reason']=explanation['reason']
        route_id='p_'+secrets.token_hex(16)
        state=dict(goal=goal.strip(),repository=repo['repository'],snapshot=repo['snapshot'],data=data,result=result,
                   completed=[],completed_costs={},spent=0,events=[],profile_revision=prefs.get('revision',0),
                   notice='')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cached=db.execute('SELECT * FROM product_source_requests WHERE user_id=? AND request_id=?',(uid,request_id)).fetchone()
            if cached:
                if cached['payload']!=payload: raise ValueError('规划请求编号已用于其他内容')
                return self.route(uid,cached['route_id'])
            if self.preferences(db,uid).get('revision',0)!=state['profile_revision']: raise ValueError('画像已改变，请重新规划')
            db.execute('INSERT INTO product_source_routes VALUES(?,?,?,?,?,?)',(route_id,uid,rid,0,dump(state),stamp()))
            if request_id: db.execute('INSERT INTO product_source_requests VALUES(?,?,?,?)',(uid,request_id,payload,route_id))
        return self.route(uid,route_id)

    def feedback(self,uid,route_id,revision,request_id,action,unit_id=None,preparation=None):
        if action=='begin_learning':return self.begin_learning(uid,route_id,revision,request_id)
        if action in ('skip_issues','finish_issues'):return self.issue_stage(uid,route_id,revision,request_id,action,preparation)
        if action not in ('read','hard','familiar','replan'): raise ValueError('路线操作不受支持')
        if not isinstance(request_id,str) or not 1<=len(request_id)<=100: raise ValueError('缺少操作编号')
        old=self.route(uid,route_id); state=copy.deepcopy(old['state'])
        key=dump([revision,action,unit_id])
        for event in state['events']:
            if event['request_id']==request_id:
                if event['key']!=key: raise ValueError('操作编号已用于其他内容')
                return old
        if type(revision) is not int or revision!=old['revision']: raise ValueError('路线已更新，请刷新后再操作')
        with self.store.connect() as db: prefs=self.preferences(db,uid)
        before_prefs=copy.deepcopy(prefs)
        previous=list(state['result']['remaining']);state.pop('adjustment',None)
        if action!='replan':
            if not state['result']['remaining'] or unit_id!=state['result']['remaining'][0]: raise ValueError('请对当前第一步反馈')
            view=state['data']['views'][unit_id]
            if action=='read':
                cost=state['result']['costs'][unit_id]
                state['completed'].append(unit_id);state['completed_costs'][unit_id]=cost;state['spent']+=cost
                from .learning_growth import record_read
                record_read(prefs,view,state['repository'],route_id=route_id,unit_id=unit_id)
            else:

                repo=enrich(self.root/old['repository_id'],self._repo(old['repository_id'])); span=view['span']
                cs=set(view['concepts']) & set(FEATURES)
                cs.update(c for s in repo['symbols'] if s['span']==span for c in s['features'])
                reports=prefs.setdefault('source_feedback',{})
                for c in cs: reports[c]='hard' if action=='hard' else 'familiar'
                familiar=set(prefs['onboarding']['familiar'])
                if action=='familiar': familiar.update(cs)
                else: familiar.difference_update(cs)
                prefs['onboarding']['familiar']=sorted(familiar); prefs['revision']=prefs.get('revision',0)+1
        repo=enrich(self.root/old['repository_id'],self._repo(old['repository_id']))
        data=build(self.root/old['repository_id'],repo,state['goal'],state['data']['targets'],prefs,uid,self.service.actor!='local_user')
        data['intent']=state['data'].get('intent',data['intent'])

        for unit in state['data']['units']:
            if unit['id'] in state['completed'] and unit['id'] not in {u['id'] for u in data['units']}:
                data['units'].append(unit);data['views'][unit['id']]=state['data']['views'][unit['id']]
        data['request']['unit_ids']=[u['id'] for u in data['units']]
        completed=set(state['completed'])
        current_ids=set(data['request']['unit_ids'])
        known_edges={(edge['before'],edge['after'],edge['path'],edge['line']) for edge in data['verified_order_edges']}
        for edge in state['data']['verified_order_edges']:
            pair={edge['before'],edge['after']}
            key_edge=(edge['before'],edge['after'],edge['path'],edge['line'])
            if pair & completed and pair<=current_ids and key_edge not in known_edges:
                data['verified_order_edges'].append(edge)
                known_edges.add(key_edge)
        reference=[x for x in state['result']['remaining'] if x not in state['completed'] and x in data['views']]
        ledger=self.store.evidence.read(uid,simulated=self.service.actor!='local_user')

        try:
            result=solve(self.root/old['repository_id'],data,ledger,completed=state['completed'],reference=reference,
                         spent=state['spent'],budget=state['result']['budget'])
            result=optimize_remaining_order(data,result,state['completed'],reference)
            for unit, explanation in result['reading_order']['explanations'].items():
                data['views'][unit]['order_reason']=explanation['reason']
            state.update(data=data,result=result,planning_error=None)
            if action in ('hard','familiar'):
                removed=[x for x in previous if x not in result['remaining'] and x not in state['completed']]
                added=[x for x in result['remaining'] if x not in previous]
                if action=='familiar':
                    skipped=state.setdefault('skipped_foundations',{})
                    for x in removed:
                        old_view=old['state']['data']['views'][x]
                        if old_view['kind']=='foundation':skipped[x]=dict(title=old_view['title'],path=old_view['path'])
                state['adjustment']=dict(action=action,topics=sorted(cs),removed=len(removed),added=len(added),before=len(previous),after=len(result['remaining']),
                                         current_skipped=unit_id in removed,from_title=view['title'])
        except Exception:
            state['result']['remaining']=[x for x in state['result']['remaining'] if x not in state['completed']]
            state['planning_error']='反馈已保存，路线更新暂未成功，请重试规划。'
        state['profile_revision']=prefs.get('revision',0)
        state['events'].append(dict(request_id=request_id,key=key,action=action,unit_id=unit_id,timestamp=stamp(),mastery_evidence=False))
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT revision FROM product_source_routes WHERE id=?',(route_id,)).fetchone()
            if current['revision']!=revision or self.preferences(db,uid)!=before_prefs: raise ValueError('学习记录已改变，请刷新后重试')
            db.execute('UPDATE product_users SET preferences_json=? WHERE user_id=?',(dump(prefs),uid))
            db.execute('UPDATE product_source_routes SET revision=?,state_json=?,updated_at=? WHERE id=?',(revision+1,dump(state),stamp(),route_id))
        return self.route(uid,route_id)

    def begin_learning(self,uid,route_id,revision,request_id):
        if not isinstance(request_id,str) or not 1<=len(request_id)<=100:raise ValueError('缺少操作编号')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.service.user(db,uid)
            row=db.execute('SELECT * FROM product_source_routes WHERE id=? AND user_id=?',(route_id,uid)).fetchone()
            if not row:raise ValueError('找不到学习路线')
            state=json.loads(row['state_json'])
            if state.get('learning_started'):return self.route(uid,route_id)
            if type(revision) is not int or row['revision']!=revision:raise ValueError('学习路线已更新，请刷新')
            if state['result']['status']!='FEASIBLE':raise ValueError('请先调整学习范围')
            state['learning_started']=True
            state['events'].append(dict(action='begin_learning',request_id=request_id,key=dump([revision,'begin_learning',None]),timestamp=stamp(),mastery_evidence=False))
            db.execute('UPDATE product_source_routes SET state_json=?,revision=revision+1,updated_at=? WHERE id=?',(dump(state),stamp(),route_id))
        return self.route(uid,route_id)

    def learning_check(self,uid,route_id,unit_id,concept,answer):
        from .learning_growth import CHECKS,topics
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');prefs=self.preferences(db,uid)
            row=db.execute('SELECT * FROM product_source_routes WHERE id=? AND user_id=?',(route_id,uid)).fetchone()
            if not row:raise ValueError('找不到学习路线')
            state=json.loads(row['state_json']);view=state['data']['views'].get(unit_id)
            if unit_id not in state['completed']+state['result']['remaining'] or not view or concept not in topics(view) or concept not in CHECKS:raise ValueError('复核内容不属于当前学习步骤')
            if type(answer) is not int or not 0<=answer<4:raise ValueError('请选择复核答案')
            growth=prefs.setdefault('learning_growth',dict(readings={},checks={},explained=[]));checks=growth['checks']
            if concept in checks:
                if checks[concept]['answer']!=answer:raise ValueError('该主题已保存首次复核结果')
                return self.route(uid,route_id)
            checks[concept]=dict(answer=answer,correct=answer==CHECKS[concept][2],explanation=CHECKS[concept][3],route_id=route_id,unit_id=unit_id,timestamp=stamp())
            prefs['revision']=prefs.get('revision',0)+1
            db.execute('UPDATE product_users SET preferences_json=? WHERE user_id=?',(dump(prefs),uid))
        return self.route(uid,route_id)

    def issue_stage(self,uid,route_id,revision,request_id,action,preparation=None):
        if not isinstance(request_id,str) or not 1<=len(request_id)<=100:raise ValueError('缺少操作编号')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.service.user(db,uid)
            row=db.execute('SELECT * FROM product_source_routes WHERE id=? AND user_id=?',(route_id,uid)).fetchone()
            if not row:raise ValueError('路线不存在')
            state=json.loads(row['state_json']);key=dump([revision,action,None])
            if preparation is not None:key=dump([revision,action,None,preparation])
            for event in state['events']:
                if event['request_id']==request_id:
                    if event['key']!=key:raise ValueError('操作编号已用于其他内容')
                    return self.route(uid,route_id)
            if row['revision']!=revision:raise ValueError('学习记录已更新，请刷新')
            if state['result']['remaining'] or state['result']['status']!='FEASIBLE':raise ValueError('请先完成源码学习')
            if action=='finish_issues':
                if not isinstance(preparation,dict) or type(preparation.get('number')) is not int:raise ValueError('请选择一个推荐问题并完成准备记录')
                if preparation.get('checks')!=[True,True,True]:raise ValueError('请完成三项实践准备')
                note=preparation.get('note')
                if not isinstance(note,str) or not 10<=len(note.strip())<=2000:raise ValueError('请填写10至2000字的复现思路或阅读结论')
                items=self.issues.get(uid,route_id,False)['items']
                chosen=next((i for i in items if i['number']==preparation['number']),None)
                if chosen is None:raise ValueError('推荐问题已更新，请重新选择')
                state['issue_preparation']=dict(number=chosen['number'],title=chosen['title'],url=chosen['url'],state=chosen['state'],note=note.strip(),checks=preparation['checks'],completed_at=stamp())
            state['issue_status']='skipped' if action=='skip_issues' else 'completed'
            state['events'].append(dict(request_id=request_id,key=key,action=action,timestamp=stamp()))
            db.execute('UPDATE product_source_routes SET state_json=?,revision=revision+1,updated_at=? WHERE id=?',(dump(state),stamp(),route_id))
        return self.route(uid,route_id)
