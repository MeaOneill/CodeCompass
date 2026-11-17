"""B-owned development journey around A's unchanged stable planning interface.

Profiles.ledger is authoritative. Session ledgers are versioned planning copies;
accepting an independent answer updates both within one SQLite transaction.
Cross-project references never silently become current-project mastery evidence.
"""
import copy
import hashlib
import json
import math
import secrets
from datetime import datetime
from pathlib import Path
from scripts.A.relay_d07 import StableRelayCollector
from codecompass.app.experiment import TERMINAL,digest
from codecompass.app.relay_v2 import prepare,registry
from codecompass.app.diagnostics_v2 import score as old_score
from codecompass.graph import read_snapshot,validate_span
from codecompass.learner import initial_state,validate_state,update_evidence,planning_rows,mastery_gate
from codecompass.planner.diagnostics import evidence_for
from codecompass.issues.candidates import match_issues

VERSION='B-D07-development-journey-4'
CROSS_ID='B07_more_chunked'
SOURCE_FILES=('app/B_D07/guide.js','scripts/B/starter_d07.py','src/codecompass/app/journey_d07.py','scripts/B/serve_d07.py','app/B_D07/index.html','app/B_D07/app.js','app/B_D07/style.css',
    'scripts/A/relay_d07.py','src/codecompass/planner/runtime_d07.py','src/codecompass/learner/model.py',
    'benchmarks/B/D07/cross_project.json','benchmarks/B/executable-v2/registry.json',
    'src/codecompass/app/diagnostics_v2.py','src/codecompass/app/diagnostic_items.py','src/codecompass/app/relay_v2.py',
    'src/codecompass/app/experiment.py','src/codecompass/app/study_d06.py')


def source_manifest(root):return {rel:hashlib.sha256((Path(root)/rel).read_bytes()).hexdigest() for rel in SOURCE_FILES}
PRETEST=[
 dict(item_id='B07-base-arithmetic-v1',concept_id='python.basic_arithmetic',prompt='程序打印什么？',code='print(2 + 3 * 4)',choices=['20','14','24'],answer=1),
 dict(item_id='B07-base-mapping-v1',concept_id='python.dict_lookup',prompt='程序打印什么？',code="print({'red': 2, 'blue': 5}['blue'])",choices=['2','5','blue'],answer=1),
 dict(item_id='B07-base-branch-v1',concept_id='python.conditional',prompt='程序打印什么？',code="x = 7\nprint('high' if x > 3 else 'low')",choices=['high','low','7'],answer=0),
 dict(item_id='B07-base-default-v1',concept_id='python.default_argument',prompt='程序打印什么？',code='def add(a, b=3): return a + b\nprint(add(2))',choices=['2','3','5'],answer=2)]
RETEST=dict(item_id='B07-more-counter-v1',concept_id='python.iterator_protocol',prompt='新仓库独立再测：最后打印什么？',
 code='class Counter:\n    def __init__(self): self.n = 0\n    def __iter__(self): return self\n    def __next__(self):\n        self.n += 3\n        return self.n\nc = iter(Counter())\nnext(c)\nprint(next(c))',choices=['3','6','9'],answer=1)


def public_question(q):return {k:q[k] for k in ('item_id','prompt','code','choices')}


def cross_data(root,user,simulated):
    path=Path(root)/'benchmarks/B/D07/cross_project.json';d=json.loads(path.read_text(encoding='utf-8'))
    contents=read_snapshot(Path(root)/d['source_root'],d['snapshot'])
    for u in d['units']:
        for span in u['source_spans']:validate_span(span,d['snapshot'],contents)
    d['state']=initial_state(user,is_simulated=simulated)
    d['request']=dict(schema_version='1.0.0',object_type='PlanningRequest',is_fixture=simulated,request_id='B07-'+secrets.token_hex(12),
        snapshot_id=d['snapshot']['snapshot_id'],task_id=CROSS_ID,learner_state=[],budget=100,cost_unit='proxy_cost',
        config_version=d['config']['version'],target_concept_ids=d['target_concept_ids'],unit_ids=[u['id'] for u in d['units']],prior_plan_id=None)
    return d


class JourneyCollector(StableRelayCollector):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.source_files=source_manifest(self.root);self.source_digest=digest(self.source_files)
        with self.connect() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS profiles (user TEXT PRIMARY KEY, actor TEXT, value TEXT);'
                'CREATE TABLE IF NOT EXISTS profile_events(user TEXT, seq INTEGER, value TEXT, PRIMARY KEY(user,seq));'
                'CREATE TABLE IF NOT EXISTS transfers(user TEXT, target TEXT, value TEXT, PRIMARY KEY(user,target));'
                'CREATE TABLE IF NOT EXISTS answers(user TEXT, item TEXT, value TEXT, PRIMARY KEY(user,item));')

    def _answer_receipt(self,db,user,q,choice,outcome,session_id=None,status='SCORED'):
        value=dict(version=VERSION,user=user,item_id=q['item_id'],choice=choice,outcome=outcome,status=status,
            session_id=session_id,actor=self.actor,timestamp=self.clock.sample()['wall'],source_digest=self.source_digest)
        value['hash']=digest(value)
        db.execute('INSERT INTO answers VALUES (?,?,?)',(user,q['item_id'],json.dumps(value,ensure_ascii=False)))

    def _profile(self,db,user):
        row=db.execute('SELECT actor,value FROM profiles WHERE user=?',(user,)).fetchone()
        if not row or row[0]!=self.actor:raise ValueError('匿名用户不存在或记录来源不同')
        p=json.loads(row[1]);validate_state(p['ledger'],allow_simulated=self.actor!='human_manual')
        if p['ledger']['pseudonymous_user_id']!=user:raise ValueError('Profile identity mismatch')
        if p['source_digest']!=self.source_digest or digest(source_manifest(self.root))!=self.source_digest:raise ValueError('运行源码已变化；保留旧记录后使用独立新版本，不重标历史')
        last=db.execute('SELECT value FROM profile_events WHERE user=? AND seq=?',(user,p['revision'])).fetchone()
        if not last:raise ValueError('Missing authoritative profile event')
        event=json.loads(last[0])
        if event['hash']!=p['last_hash'] or digest({k:v for k,v in event.items() if k!='hash'})!=event['hash'] or event['ledger_sha256']!=digest(p['ledger']):raise ValueError('Authoritative ledger/event mismatch')
        return p

    def _save_profile(self,db,p,kind,detail):
        p['revision']+=1;event=dict(version=VERSION,seq=p['revision'],kind=kind,detail=detail,previous_hash=p['last_hash'],timestamp=self.clock.sample()['wall'],ledger_sha256=digest(p['ledger']),source_digest=self.source_digest)
        event['hash']=digest(event);p['last_hash']=event['hash']
        db.execute('INSERT INTO profile_events VALUES (?,?,?)',(p['user'],p['revision'],json.dumps(event,ensure_ascii=False)))
        db.execute('INSERT INTO profiles VALUES (?,?,?) ON CONFLICT(user) DO UPDATE SET value=excluded.value',
            (p['user'],self.actor,json.dumps(p,ensure_ascii=False)))

    def enroll(self,consent):
        if consent is not True:raise ValueError('先阅读并自愿确认开发预演说明，可随时退出')
        user='p_'+secrets.token_hex(16)
        p=dict(user=user,actor=self.actor,consent_scope='development_pilot_only' if self.actor=='human_manual' else 'LABELLED_AUTOMATED_FIXTURE_ACK',
            formal_participant=False,excluded_from_formal_sample=True,revision=0,last_hash=None,pretest_done=False,
            pretest_started=self.clock.sample(),pretest_timing=None,ledger=initial_state(user,is_simulated=self.actor!='human_manual'),source_digest=self.source_digest)
        with self.connect() as db:self._save_profile(db,p,'enroll',{'scope':p['consent_scope']})
        return dict(participant=user,questions=[public_question(q) for q in PRETEST],source=self.actor,version=VERSION)

    def pretest(self,user,choices):
        if not isinstance(choices,list) or len(choices)!=len(PRETEST):raise ValueError('四道初测均需填写选项或选择跳过')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');p=self._profile(db,user)
            if p['pretest_done']:raise ValueError('初测已保存，不重复增加证据')
            now=self.clock.sample();before=p['pretest_started'];seconds=now['mono']-before['mono']
            valid=now['epoch']==before['epoch'] and math.isfinite(seconds) and seconds>=0
            status='TIMED_OUT' if valid and seconds>600 else ('COMPLETED' if valid else 'TIME_MISSING')
            missing=[]
            for q,choice in zip(PRETEST,choices):
                if choice is not None and (type(choice) is not int or not 0<=choice<len(q['choices'])):raise ValueError('Invalid pretest choice')
                if choice is None or status!='COMPLETED':
                    missing.append(q['item_id']);self._answer_receipt(db,user,q,choice,None,status='MISSING' if choice is None else status);continue
                self._answer_receipt(db,user,q,choice,'pass' if choice==q['answer'] else 'fail')
                e=dict(evidence_id='B07:'+q['item_id'],item_id=q['item_id'],concept_id=q['concept_id'],project='B07-general-python',timestamp=now['wall'],
                    pseudonymous_user_id=user,is_fixture=self.actor!='human_manual',independent=True,evidence_type='independent_quiz',outcome='pass' if choice==q['answer'] else 'fail')
                p['ledger'],_=update_evidence(p['ledger'],e,allow_simulated=self.actor!='human_manual')
            p['pretest_done']=True;p['pretest_timing']=dict(status=status,elapsed_seconds=seconds if valid else None,missing_items=missing)
            self._save_profile(db,p,'pretest',p['pretest_timing'])
        return self.profile(user)

    def event(self,db,s,kind,payload=None,sample=None):
        if kind=='start':
            p=self._profile(db,s['participant'])
            if not p['pretest_done']:raise ValueError('请先完成共同初测；可明确跳过，不把缺失记错')
            sessions=[json.loads(r[0]) for r in db.execute('SELECT value FROM sessions')]
            own=[v for v in sessions if v['participant']==s['participant']]
            if any(v['status'] not in TERMINAL for v in own):raise ValueError('当前已有未结束任务，请先继续或退出')
            if len(own)>=2:raise ValueError('开发预演固定最多两轮，不追加任务追结果')
            if any(e['item_id']==s['data']['quiz']['item_id'] for e in p['ledger']['records']):raise ValueError('同一独立题已作答，不能重复刷证据')
            s['data']['state']=copy.deepcopy(p['ledger']);s['profile_revision']=p['revision']
        return super().event(db,s,kind,dict(payload or {},journey_version=VERSION),sample)

    def create(self,task_id='task_002',method='Ours',participant=None,*,limit_seconds=1500):
        if participant is None or method not in ('Ours','B2','B1'):raise ValueError('先登记匿名用户，选择受支持方法')
        if type(limit_seconds) not in (int,float) or not math.isfinite(limit_seconds) or not 0<limit_seconds<=1500:raise ValueError('Invalid limit')
        d=cross_data(self.root,participant,self.actor!='human_manual') if task_id==CROSS_ID else prepare(self.root,task_id,participant,self.actor!='human_manual')
        now=self.clock.sample();s=dict(id=secrets.token_urlsafe(24),participant=participant,actor=self.actor,task_id=task_id,method=method,
            status='ACTIVE',phase='planning',elapsed=0.,duration_valid=True,missing=[],clock=now,seq=0,last_hash=None,
            limit_seconds=limit_seconds,completed=[],spent=0.,quiz_done=False,quiz_started=None,outcome=None,success=None,
            score_status='NOT_SUBMITTED',response=None,route=[],feedback=None,operation=None,engine_version=VERSION,data=d)
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.event(db,s,'start',{'scope':'development_pilot_not_formal'});self.schedule(db,s,'initial_plan')
        return self.finish_plan(s['id'])

    def load(self,db,sid):
        s=super().load(db,sid)
        if s['engine_version']!=VERSION or s['actor']!=self.actor:raise ValueError('不能跨版本或混用真人/自动数据库')
        if s['status'] not in TERMINAL:
            p=self._profile(db,s['participant'])
            if p['revision']!=s['profile_revision']:raise ValueError('画像修订不匹配，保留检查点后处理；不会静默重算')
            if s['data']['state']!=p['ledger']:raise ValueError('画像缓存与权威证据账本不一致')
        return s

    def action(self,sid,action,payload=None):
        if action!='answer':return super().action(sid,action,payload)
        choice=(payload or {}).get('choice')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');s=self.load(db,sid)
            if s['status'] in TERMINAL:self.save(db,s);return self.view(s)
            if s['status']!='ACTIVE' or s['phase']!='quiz' or s['quiz_done']:raise ValueError('当前不能作答或重复提交')
            if s['task_id']==CROSS_ID:
                if type(choice) is not int or not 0<=choice<len(RETEST['choices']):raise ValueError('请选择一个答案')
                outcome='pass' if choice==RETEST['answer'] else 'fail'
            else:outcome=old_score(s['task_id'],choice)
            d=s['data'];before=copy.deepcopy(d['state']);p=self._profile(db,s['participant'])
            evidence=evidence_for(d['request'],p['ledger'],d['quiz'],outcome,s['clock']['wall'])
            new,decision=update_evidence(p['ledger'],evidence,allow_simulated=d['request']['is_fixture'])
            if decision!='ACCEPTED':raise ValueError('同题或重复证据不再次增加能力')
            self._answer_receipt(db,s['participant'],d['quiz'],choice,outcome,sid)
            p['ledger']=new;self._save_profile(db,p,'independent_quiz',{'evidence':evidence})
            d['state']=copy.deepcopy(new);s['profile_revision']=p['revision'];s['spent']+=1;s['quiz_done']=True;s['outcome']=outcome
            s['feedback']=dict(before=planning_rows(before,d['request']['snapshot_id'],allow_simulated=d['request']['is_fixture']),
                after=planning_rows(new,d['request']['snapshot_id'],allow_simulated=d['request']['is_fixture']),before_route=list(s['route']))
            self.event(db,s,'quiz_submit',{'item_id':evidence['item_id'],'outcome':outcome,'duration_seconds':s['elapsed']-s['quiz_started'] if s['duration_valid'] else None,'scorer':'independent_server_oracle'})
            self.event(db,s,'feedback',{'concept_id':evidence['concept_id'],'outcome':outcome})
            self.schedule(db,s,'replan')
        return self.finish_plan(sid)

    def view(self,s):


        shadow=copy.deepcopy(s)
        if s['task_id']==CROSS_ID:shadow['task_id']='task_002'
        v=super().view(shadow)
        if s['task_id']==CROSS_ID:v['quiz']=public_question(RETEST) if s['phase']=='quiz' else None;v['patch_task']=False
        v['protocol_version']=VERSION;v['limitation']='B-D07开发闭环候选；长期画像与跨项目来源可恢复；非正式实验。更多仓库案例不属于正式题池。'
        return v

    def review_material(self,sid,unit):

        with self.connect() as db:
            row=db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()
        if not row:raise ValueError('学习记录不存在')
        s=json.loads(row[0])
        if s['phase']=='quiz':raise ValueError('独立小题进行中，请先作答或退出')
        if unit not in s['completed']:raise ValueError('这里只能回看已经读过的材料')
        materials=[m for m in s['data']['materials'] if m['unit_id']==unit]
        if not materials:raise ValueError('当前记录没有这份材料')
        return dict(unit_id=unit,materials=materials,review_only=True,mastery_granted=False)

    def tasks(self):
        rows=super().tasks()
        for row in rows:row.update(repo='boltons',formal_task=False)
        rows.append(dict(task_id=CROSS_ID,title='more-itertools · 跨项目再测功能案例',split='functional_demo',patch_task=False,repo='more-itertools',formal_task=False))
        return rows

    def transfer(self,user):
        target=cross_data(self.root,user,self.actor!='human_manual')['request']['snapshot_id']
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');p=self._profile(db,user)
            if any(json.loads(r[0])['participant']==user and json.loads(r[0])['status'] not in TERMINAL for r in db.execute('SELECT value FROM sessions')):
                raise ValueError('先结束当前任务，再登记跨仓库引用')
            old=db.execute('SELECT value FROM transfers WHERE user=? AND target=?',(user,target)).fetchone()
            if old:return json.loads(old[0])
            source=[e for e in p['ledger']['records'] if e['project']=='boltons-4e5faa3d7e40' and e['concept_id']=='python.iterator_protocol']
            row=dict(version=VERSION,concept_id='python.iterator_protocol',source_project='boltons-4e5faa3d7e40',target_project=target,
                source_evidence_ids=[e['evidence_id'] for e in source],source_outcomes=[e['outcome'] for e in source],
                mapping_basis='Both pinned functions consume Python iterators via iter/next; B engineering mapping, not human-reviewed teaching equivalence',
                source_available=bool(source),target_retest_item_id=RETEST['item_id'],target_retest_required=True,
                posterior_copied=False,mastery_granted=False,formal_transfer_effect=False)
            db.execute('INSERT INTO transfers VALUES (?,?,?)',(user,target,json.dumps(row,ensure_ascii=False)))

            self._save_profile(db,p,'cross_project_reference',row)
        return row

    def profile(self,user):
        with self.connect() as db:
            db.execute('BEGIN')
            p=self._profile(db,user);sessions=[json.loads(r[0]) for r in db.execute('SELECT value FROM sessions')]
            sessions=[s for s in sessions if s['participant']==user]
            transfers=[json.loads(r[0]) for r in db.execute('SELECT value FROM transfers WHERE user=?',(user,))]
            events=[json.loads(r[0]) for r in db.execute('SELECT value FROM profile_events WHERE user=? ORDER BY seq',(user,))]
        prev=None
        for i,e in enumerate(events,1):
            if e['seq']!=i or e['previous_hash']!=prev or digest({k:v for k,v in e.items() if k!='hash'})!=e['hash']:raise ValueError('Profile audit chain corrupted')
            prev=e['hash']
        if prev!=p['last_hash'] or len(events)!=p['revision']:raise ValueError('Profile event count mismatch')
        summaries=[dict(project=project,concepts=planning_rows(p['ledger'],project,allow_simulated=self.actor!='human_manual')) for project in sorted({e['project'] for e in p['ledger']['records']})]
        for row in transfers:
            row['target_retest_recorded']=any(e['project']==row['target_project'] and e['item_id']==row['target_retest_item_id'] for e in p['ledger']['records'])
        durations=[s['elapsed'] if s['duration_valid'] else None for s in sessions]
        pt=p['pretest_timing'];total=(pt['elapsed_seconds']+sum(durations)) if pt and pt['elapsed_seconds'] is not None and all(t is not None for t in durations) else None
        now=self.clock.sample();start=p['pretest_started'];wall=(datetime.fromisoformat(now['wall'])-datetime.fromisoformat(start['wall'])).total_seconds()
        wall_valid=now['epoch']==start['epoch'] and math.isfinite(wall) and wall>=0 and abs(wall-(now['mono']-start['mono']))<=5
        wall_seconds=wall if wall_valid else None
        return dict(participant=user,actor=self.actor,pretest_done=p['pretest_done'],pretest_timing=pt,revision=p['revision'],
            evidence_count=len(p['ledger']['records']),history=summaries,transfers=transfers,source_of_truth='profiles.ledger + hashed profile_events; session state is a checked planning copy',
            sessions=[dict(session_id=s['id'],task_id=s['task_id'],method=s['method'],status=s['status'],elapsed_seconds=s['elapsed'] if s['duration_valid'] else None) for s in sessions],
            measured_active_seconds=total,journey_wall_seconds=wall_seconds,
            within_90_minutes=None if total is None or wall_seconds is None else max(total,wall_seconds)<=5400,planned_max_minutes=60,
            actual_two_people_verified=False,formal_participant=False,excluded_from_formal_sample=True,questions=[public_question(q) for q in PRETEST] if not p['pretest_done'] else [])

    def issues(self,sid):
        with self.connect() as db:s=self.load(db,sid);self.save(db,s)
        if s['task_id']==CROSS_ID:return dict(candidates=[],historical=[],no_suitable_reason='第二仓库尚无Issue快照；不使用boltons问题冒充匹配',source_mode='UNAVAILABLE',community_submission=False)
        path=self.root/'benchmarks/B/D07/issues_snapshot.json'
        snap=json.loads(path.read_text(encoding='utf-8'));d=s['data']
        gate=mastery_gate(d['state'],d['request']['snapshot_id'],d['request']['target_concept_ids'],allow_simulated=d['request']['is_fixture'])
        result=match_issues(snap,d['units'],[c for c,g in gate.items() if not g['mastered']])
        result.update(source_mode='FIXED_HISTORICAL_SNAPSHOT',current_issue_state_verified=False,snapshot_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            notice='状态仅截至抓取时间；固定源码版本和Issue状态时间不同。没有向社区提交贡献。')
        return result
