"""Versioned executable study candidate: twelve tasks and true dynamic B1.

The source-only registry, UI and planners never import private evaluation keys.
Planning runs outside SQLite write transactions; pending operations do not auto
retry on restart. Final submissions remain unscored until evaluator-only replay.
"""
import copy
import hashlib
import json
import math
from pathlib import Path
import secrets
import threading

from codecompass.graph import read_snapshot,validate_span,make_span
from codecompass.learner import initial_state,planning_rows,mastery_gate,update_evidence
from codecompass.planner.adaptive import remaining_plan,request_for_state,route_audit
from codecompass.planner.diagnostics import evidence_for
from .experiment import Collector,TERMINAL,digest
from .diagnostics_v2 import ITEMS,public_item,score
from .study_d06 import b2_remaining
from scripts.B.comparison.b1 import run_b1

VERSION='B-D06-executable-candidate-2'
PROMPT='''Plan a remaining source-reading route using ONLY the public context.
Return exactly {"ordered_units":["unit_id",...]} with no additional keys.
Preserve completed materials: never return a completed unit, repeat a unit,
invent IDs, exceed remaining proxy budget or violate hard prerequisites.
Cover remaining goals using supplied independent mastery gate and completed
coverage. You receive the same source, feedback, budget and help as other
methods. No final answers, final tests or other methods' routes are provided.
'''


def registry(root):
    path=Path(root)/'benchmarks/B/executable-v2/registry.json';raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=path.with_suffix('.sha256').read_text().strip():raise ValueError('Registry bytes changed')
    return json.loads(raw)


def prepare(root,tid,participant,simulated):
    entries=registry(root)['records'];matches=[r for r in entries if r['task_id']==tid]
    if len(matches)!=1:raise ValueError('Unknown registered task')
    d=copy.deepcopy(matches[0]);allowed=('benchmarks/sources/boltons','benchmarks/sources/boltons_B_D02')
    if d['source_root'] not in allowed:raise ValueError('Source root outside fixed snapshots')
    contents=read_snapshot(Path(root)/d['source_root'],d['snapshot'])
    for unit in d['units']:
        for span in unit['source_spans']:validate_span(span,d['snapshot'],contents)
    d['state']=initial_state(participant,is_simulated=simulated)
    d['request']=dict(schema_version='1.0.0',object_type='PlanningRequest',is_fixture=simulated,request_id='R-v2-'+secrets.token_hex(12),
        snapshot_id=d['snapshot']['snapshot_id'],task_id=tid,learner_state=[],budget=100,cost_unit='proxy_cost',
        config_version=d['config']['version'],target_concept_ids=d['target_concept_ids'],unit_ids=[u['id'] for u in d['units']],prior_plan_id=None)
    return d


def packet(s):
    d=s['data'];req=d['request'];concepts={c for u in d['units'] for c in u['concept_ids']}|set(req['target_concept_ids'])
    gate=mastery_gate(d['state'],req['snapshot_id'],concepts,threshold=.7,quantile=.1,allow_simulated=req['is_fixture'])

    ledger=[{k:e[k] for k in ('concept_id','item_id','outcome','project','evidence_type','independent','is_fixture')} for e in d['state']['records']]
    return dict(task=d['task'],snapshot_id=req['snapshot_id'],target_concept_ids=req['target_concept_ids'],
        units=d['units'],source_materials=d['materials'],source_context=d['source_context'],
        learner_evidence=ledger,learner_gate=gate,completed=list(s['completed']),spent_proxy=s['spent'],
        budget_proxy=100,remaining_proxy=100-s['spent'],feedback=s['outcome'],
        policy=dict(threshold=.7,quantile=.1,alpha=0,gamma=0,max_quizzes=1,quiz_cost=1))


class RelayCollector(Collector):
    def __init__(self,*args,b1_config=None,meter=None,transport=None,**kwargs):
        super().__init__(*args,**kwargs);self.b1_config=b1_config or {'enabled':False};self.meter=meter;self.transport=transport
        self._locks={};self._locks_guard=threading.Lock()
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS planner_traces(id TEXT, op TEXT PRIMARY KEY, value TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS final_assessments(id TEXT PRIMARY KEY, response_hash TEXT, value TEXT)')

    def lock(self,sid):
        with self._locks_guard:return self._locks.setdefault(sid,threading.RLock())

    def event(self,db,s,kind,payload=None,sample=None):
        super().event(db,s,kind,dict(payload or {},engine_version=VERSION),sample)

    def tasks(self):
        return [dict(task_id=r['task_id'],title=r['task']['title'],split=r['split'],patch_task=r['task_id'] in ('task_001','task_002')) for r in registry(self.root)['records']]

    def load(self,db,sid):
        row=db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()
        if not row:raise ValueError('会话不存在')
        s=json.loads(row[0]);self.tick(db,s)
        if s.get('operation') and s['operation']['owner']!=self.clock.epoch and s['status'] not in TERMINAL:
            s['status']='FAILED';self.event(db,s,'failure',{'reason':'PLANNING_INTERRUPTED_NO_AUTO_RETRY'})
            s['operation']=None
        return s

    def schedule(self,db,s,kind):
        s['phase']='planning';s['operation']=dict(id=secrets.token_hex(16),owner=self.clock.epoch,kind=kind)
        self.event(db,s,'planning_start',{'kind':kind,'context_hash':digest(packet(s))})
        self.save(db,s)

    def create(self,task_id='task_001',method='Ours',participant=None,*,limit_seconds=1500):
        if method not in ('Ours','B2','B1') or type(limit_seconds) not in (int,float) or not math.isfinite(limit_seconds) or not 0<limit_seconds<=1500:raise ValueError('Invalid method/time limit')
        if participant is not None and (len(participant)!=34 or not participant.startswith('p_') or any(c not in '0123456789abcdef' for c in participant[2:])):raise ValueError('Bad anonymous ID')
        participant=participant or 'p_'+secrets.token_hex(16);now=self.clock.sample()
        s=dict(id=secrets.token_urlsafe(24),participant=participant,actor=self.actor,task_id=task_id,method=method,
            status='ACTIVE',phase='planning',elapsed=0.,duration_valid=True,missing=[],clock=now,seq=0,last_hash=None,
            limit_seconds=limit_seconds,completed=[],spent=0.,quiz_done=False,quiz_started=None,outcome=None,success=None,
            score_status='NOT_SUBMITTED',response=None,route=[],feedback=None,operation=None,engine_version=VERSION,
            data=prepare(self.root,task_id,participant,self.actor!='human_manual'))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');self.event(db,s,'start',{'scope':'development_or_pilot_not_formal'})
            self.schedule(db,s,'initial_plan')
        return self.finish_plan(s['id'])

    def calculate(self,s):
        d=s['data'];p=packet(s);req=request_for_state(d['request'],d['state'],d['config'])
        if s['method']=='Ours':
            result=remaining_plan(self.root,req,d['units'],d['state'],d['config'],completed=s['completed'],reference=s['route'],spent=s['spent'],alpha=0,gamma=0)
            return dict(status=result['status'],route=result['remaining'],cost=result['learning_cost'],context=p,details=result)
        if s['method']=='B2':
            result=b2_remaining(req,d['units'],d['state'],d['config'],s['completed'],s['spent'])
            return dict(status=result['status'],route=result['remaining'],cost=result['cost'],context=p,details=result)
        covered={c for u in d['units'] if u['id'] in s['completed'] for c in u['concept_ids']}|{c for c,g in p['learner_gate'].items() if g['mastered']}
        if set(req['target_concept_ids'])<=covered:
            trace=dict(status='NO_ACTION_NEEDED',calls=[],attempted=False,route=[],transport_is_fixture=self.transport is not None)
        else:trace=run_b1(p,self.b1_config,PROMPT,self.meter,transport=self.transport)
        if trace['status'] not in ('PARSED','NO_ACTION_NEEDED'):
            return dict(status=trace['status'],route=[],cost=None,context=p,details=trace)
        route=trace['route'];by_id={u['id']:u for u in d['units']}
        if len(route)!=len(set(route)) or any(uid not in by_id or uid in s['completed'] for uid in route):
            return dict(status='ALGORITHM_INVALID',route=route,cost=None,context=p,details=trace)
        audit=route_audit(req,d['units'],p['learner_gate'],route,{u['id']:u['base_cost'] for u in d['units']},s['completed'],(),0,s['spent'])
        return dict(status='FEASIBLE' if audit['valid'] else 'ALGORITHM_INVALID',route=route,
            cost=sum(by_id[u]['base_cost'] for u in route),context=p,details=trace,independent_replay=audit)

    def finish_plan(self,sid):
        with self.lock(sid):
            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE');s=self.load(db,sid);op=s.get('operation');self.save(db,s)
            if not op or s['status']!='ACTIVE':return self.view(s)
            try:result=self.calculate(copy.deepcopy(s))
            except Exception as e:result=dict(status='PLANNING_ERROR',route=[],cost=None,error_type=type(e).__name__,context=packet(s))

            with self.connect() as db:
                db.execute('BEGIN IMMEDIATE');latest=self.load(db,sid)
                db.execute('INSERT INTO planner_traces VALUES (?,?,?)',(sid,op['id'],json.dumps(result,ensure_ascii=False)))
                if not latest.get('operation') or latest['operation']['id']!=op['id'] or latest['status']!='ACTIVE':
                    self.save(db,latest);return self.view(latest)
                s=latest;s['route']=result['route'];s['planner_status']=result['status'];s['operation']=None
                s['phase']='reading' if op['kind']=='initial_plan' else 'feedback'
                if s['feedback']:s['feedback']['after_route']=list(s['route'])
                self.event(db,s,op['kind'],{'route':s['route'],'planner_status':result['status'],'context_hash':digest(result['context'])})
                if result['status']!='FEASIBLE':
                    s['status']='FAILED';self.event(db,s,'failure',{'reason':result['status']})
                elif op['kind']=='initial_plan' and s['route']:self.event(db,s,'read',{'unit_id':s['route'][0]})
                self.save(db,s);return self.view(s)

    def action(self,sid,action,payload=None):
        payload=payload or {};needs_plan=False
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE');s=self.load(db,sid)
            if action=='poll' or s['status'] in TERMINAL:self.save(db,s);return self.view(s)
            if action=='withdraw':s['status']='WITHDRAWN';self.event(db,s,'withdraw');s['operation']=None
            elif s.get('operation'):raise ValueError('规划进行中，正在计时；不会重复发起调用')
            elif action=='resume':
                if s['status']!='PAUSED':raise ValueError('当前未暂停')
                s['status']='ACTIVE';self.event(db,s,'resume')
            elif s['status']!='ACTIVE':self.save(db,s);return self.view(s)
            elif action=='pause':s['status']='PAUSED';self.event(db,s,'pause')
            elif action=='read':
                if not s['route']:raise ValueError('没有剩余材料')
                if s['phase']!='quiz':s['phase']='reading'
                self.event(db,s,'read',{'unit_id':s['route'][0]})
            elif action=='complete_reading':
                if not s['route'] or s['phase']=='quiz':raise ValueError('请先完成规定短测')
                uid=s['route'][0];cost=next(u['base_cost'] for u in s['data']['units'] if u['id']==uid)
                if s['spent']+cost>100:raise ValueError('代理预算不足')
                s['spent']+=cost;s['completed'].append(uid);s['route'].pop(0)
                self.event(db,s,'reading_complete',{'unit_id':uid,'mastery_updated':False})
                if len(s['completed'])==1:
                    if s['spent']+1>100:s['status']='FAILED';self.event(db,s,'failure',{'reason':'COMMON_QUIZ_UNAFFORDABLE'})
                    else:
                        s['phase']='quiz';s['quiz_started']=s['elapsed']
                        self.event(db,s,'quiz_start',{'item_id':s['data']['quiz']['item_id'],'policy':'automatic_after_exactly_one_material'})
            elif action=='answer':
                if s['phase']!='quiz' or s['quiz_done']:raise ValueError('短测不可重复提交')
                outcome=score(s['task_id'],payload.get('choice'));d=s['data'];before=copy.deepcopy(d['state'])
                evidence=evidence_for(d['request'],d['state'],d['quiz'],outcome,s['clock']['wall'])
                new,accepted=update_evidence(d['state'],evidence,allow_simulated=d['request']['is_fixture'])
                if accepted!='ACCEPTED':raise ValueError('重复证据')
                s['spent']+=1;d['state']=new;s['quiz_done']=True;s['outcome']=outcome
                duration=s['elapsed']-s['quiz_started'] if s['duration_valid'] else None
                s['feedback']=dict(before=planning_rows(before,d['request']['snapshot_id'],allow_simulated=d['request']['is_fixture']),
                    after=planning_rows(new,d['request']['snapshot_id'],allow_simulated=d['request']['is_fixture']),before_route=list(s['route']))
                self.event(db,s,'quiz_submit',{'item_id':d['quiz']['item_id'],'outcome':outcome,'duration_seconds':duration,'scorer':'independent_parallel_python_snippet_v2'})
                self.event(db,s,'feedback',{'concept_id':d['quiz']['concept_id'],'outcome':outcome})
                self.schedule(db,s,'replan');needs_plan=True
            elif action=='submit':
                if not s['quiz_done'] and (s['completed'] or s['route']):raise ValueError('尚未完成规定短测')
                response=payload.get('response')
                if not isinstance(response,str) or not response.strip() or len(response.encode('utf-8'))>450000:raise ValueError('提交内容缺失或过大')
                s['response']=response;s['status']='SUBMITTED';s['score_status']='PENDING_INDEPENDENT_FINAL_SCORING'
                self.event(db,s,'final_submit',{'response_sha256':hashlib.sha256(response.encode()).hexdigest(),'success':None,'score_status':s['score_status']})
            else:raise ValueError('Unknown action')
            self.save(db,s)
        return self.finish_plan(sid) if needs_plan else self.view(s)

    def view(self,s):
        d=s['data'];uid=s['route'][0] if s['route'] else None
        with self.connect() as db:
            row=db.execute('SELECT response_hash,value FROM final_assessments WHERE id=?',(s['id'],)).fetchone()
        assessment=json.loads(row[1]) if row and s['response'] and row[0]==hashlib.sha256(s['response'].encode()).hexdigest() else None
        return dict(session_id=s['id'],participant=s['participant'],task=d['task'],method=s['method'],actor=s['actor'],
            status=s['status'],phase=s['phase'],elapsed_seconds=s['elapsed'] if s['duration_valid'] else None,observed_seconds=s['elapsed'],
            missing=list(s['missing']),limit_seconds=s['limit_seconds'],route=list(s['route']),completed=list(s['completed']),spent=s['spent'],
            quiz_done=s['quiz_done'],quiz=public_item(s['task_id']) if s['phase']=='quiz' else None,
            materials=[m for m in d['materials'] if m['unit_id']==uid],source_context=d['source_context'],feedback=s['feedback'],
            outcome=s['outcome'],score_status=s['score_status'],success=s['success'],events=s['seq'],patch_task=s['task_id'] in ('task_001','task_002'),
            assessment=assessment,protocol_version=VERSION,limitation='12题与三方法技术联调候选；真人同意、题目/方案人工批准尚未完成，非正式实验。')

    def traces(self,sid):
        with self.connect() as db:return [json.loads(row[0]) for row in db.execute('SELECT value FROM planner_traces WHERE id=? ORDER BY rowid',(sid,))]

    def submission_spans(self,tid,references):
        row=next(r for r in registry(self.root)['records'] if r['task_id']==tid)
        contents=read_snapshot(self.root/row['source_root'],row['snapshot']);spans=[]
        for ref in references:
            path,start,end=ref['path'],ref['start_line'],ref['end_line']
            if path not in contents or type(start) is not int or type(end) is not int:raise ValueError('Invalid source citation')
            spans.append(make_span(row['snapshot']['snapshot_id'],path,contents[path].decode('utf-8'),start,end))
        return spans
