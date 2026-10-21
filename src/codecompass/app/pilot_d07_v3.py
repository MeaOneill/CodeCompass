"""Costed development-only 5-history + 1-diagnosis pilot; no changed planner."""
import copy
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import threading

from codecompass.app.experiment import Clock,digest
from codecompass.app.relay_v2 import prepare
from codecompass.app.study_d06 import b2_remaining
from codecompass.learner import update_evidence
from codecompass.planner.adaptive import request_for_state
from codecompass.planner.runtime_d07 import safe_remaining,validate_method_result

VERSION='A-D07-dev-repair-v3'
SOURCE_FILES=['src/codecompass/app/pilot_d07_v3.py','scripts/A/serve_d07_v3.py',
              'app/A_D07_v3/index.html','app/A_D07_v3/app.js','app/A_D07_v3/style.css',
              'benchmarks/dev/A_D07_v3/bank.json']

def bank(root):
    p=Path(root)/'benchmarks/dev/A_D07_v3/bank.json';raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=p.with_suffix('.sha256').read_text().strip():raise ValueError('题库版本不一致')
    value=json.loads(raw)
    assert value['cap']==6 and value['history_count']==5 and len(value['items'])==6
    assert len({q['item_id'] for q in value['items']})==6
    return value

def public_item(q):return {k:q[k] for k in ('item_id','facet','code','choices')}

def validate_choices(values,count):
    if not isinstance(values,list) or len(values)!=count:raise ValueError('请为每题选择一个答案或“不会/跳过”')
    if any(v is not None and (type(v) is not int or not 0<=v<4) for v in values):raise ValueError('选项不合法')

def add_answer(data,q,choice,timestamp):
    validate_choices([choice],1)
    if choice is None:return dict(item_id=q['item_id'],choice=None,outcome=None,missing=True)
    outcome='pass' if choice==q['answer'] else 'fail'
    e=dict(evidence_id='v3:'+q['item_id'],item_id=q['item_id'],concept_id=q['concept_id'],
           project=data['request']['snapshot_id'],timestamp=timestamp,pseudonymous_user_id=data['state']['pseudonymous_user_id'],
           is_fixture=data['request']['is_fixture'],independent=True,evidence_type='independent_quiz',outcome=outcome)
    state,accepted=update_evidence(data['state'],e,allow_simulated=data['request']['is_fixture'])
    if accepted!='ACCEPTED':raise ValueError('重复证据不能再次计入')
    data['state']=state
    return dict(item_id=q['item_id'],choice=choice,outcome=outcome,missing=choice is None)

def plans(root,data,completed,spent):
    req=request_for_state(data['request'],data['state'],data['config'])
    ours=safe_remaining(root,req,data['units'],data['state'],data['config'],completed=completed,spent=spent)
    b2=b2_remaining(req,data['units'],data['state'],data['config'],completed,spent)
    s=dict(data=data,completed=completed,spent=spent)
    checked=validate_method_result(root,s,dict(status=b2['status'],route=b2['remaining'],cost=b2['cost']))
    if ours['status']!='FEASIBLE' or checked['status']!='FEASIBLE':raise ValueError('规划未找到完整合法路线，记录不得当成成功')
    return dict(Ours=dict(route=ours['remaining'],gate=ours['gate'],audit=ours['replay'],cost=ours['learning_cost'],explanations=ours['route_explanations']),
                B2=dict(route=b2['remaining'],gate=b2['gate'],audit=checked['acceptance_replay'],cost=b2['cost']))

class Pilot:
    def __init__(self,root,database,*,actor='human_manual',clock=None):
        if actor not in ('human_manual','test_fixture','agent_browser'):raise ValueError('明确记录执行来源')
        self.root=Path(root);self.database=Path(database);self.database.parent.mkdir(parents=True,exist_ok=True)
        self.actor=actor;self.clock=clock or Clock();self.lock=threading.RLock();self.items=bank(root)['items']
        self.provenance=dict(protocol_version=VERSION,ui_version=VERSION,source_hashes={p:hashlib.sha256((self.root/p).read_bytes()).hexdigest() for p in SOURCE_FILES})
        with self.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY,value TEXT NOT NULL)')
    def connect(self):return sqlite3.connect(self.database,timeout=10)
    def event(self,s,kind,payload=None):
        e=dict(seq=len(s['events'])+1,kind=kind,status=s['status'],stage=s['stage'],elapsed=s['elapsed'],
               spent=s['spent'],version=VERSION,ui_version=VERSION,source_digest=digest(self.provenance),
               payload=payload or {},previous_hash=s['events'][-1]['hash'] if s['events'] else None)
        e['hash']=digest(e);s['events'].append(e)
    def save(self,db,s):db.execute('INSERT OR REPLACE INTO cases VALUES(?,?)',(s['id'],json.dumps(s,ensure_ascii=False,allow_nan=False)))
    def tick(self,s):
        if s['status'] not in ('ACTIVE','PAUSED'):return
        now=self.clock.sample();previous=s['clock'];s['clock']=now
        if now['epoch']!=previous['epoch'] or now['mono']<previous['mono']:
            s['status']='FAILED';s['duration_valid']=False;self.event(s,'clock_failure');return
        if s['status']=='ACTIVE':s['elapsed']+=now['mono']-previous['mono']
        if s['elapsed']>=1500:s['status']='TIMED_OUT';self.event(s,'timeout')
    def load(self,db,sid):
        row=db.execute('SELECT value FROM cases WHERE id=?',(sid,)).fetchone()
        if not row:raise ValueError('会话不存在')
        s=json.loads(row[0])
        if s['actor']!=self.actor or s['provenance']!=self.provenance:raise ValueError('来源或代码版本不同，不能沿用旧会话')
        if any(hashlib.sha256((self.root/p).read_bytes()).hexdigest()!=sha for p,sha in self.provenance['source_hashes'].items()):raise ValueError('运行中源文件变化，不能沿用旧版本')
        self.tick(s);return s
    def create(self,consent):
        if consent is not True:raise ValueError('需要本人自愿参加')
        with self.lock,self.connect() as db:
            if db.execute('SELECT count(*) FROM cases').fetchone()[0]:raise ValueError('本入口固定一次，不重复刷题；请保留原记录')
            user='p_'+secrets.token_hex(16);d=prepare(self.root,'task_002',user,self.actor!='human_manual')
            if (d['config']['threshold'],d['config']['quantile'])!=(.7,.1):raise ValueError('冻结门槛不一致')
            s=dict(id=secrets.token_urlsafe(24),actor=self.actor,provenance=copy.deepcopy(self.provenance),consent=True,
                   status='ACTIVE',stage='history',data=d,completed=[],spent=0.,history_cost=0,diagnosis_cost=0,
                   elapsed=0.,duration_valid=True,clock=self.clock.sample(),events=[],answers=[],before=None,after=None,
                   no_feedback=None,sixth_presented=False,formal_sample=False)
            self.event(s,'start',dict(task='task_002',limit_seconds=1500,history_cap=5,diagnosis_cap=1))
            self.save(db,s);return self.view(s)
    def get(self,sid):
        with self.lock,self.connect() as db:s=self.load(db,sid);self.save(db,s);return self.view(s)
    def plan_failure(self,db,s,exc):
        # Accepted answers are irrevocable even when search/IO fails afterwards.
        self.tick(s)
        if s['status']=='ACTIVE':
            s['status']='FAILED';self.event(s,'planning_failure',dict(error_type=type(exc).__name__,answers_retained=len(s['answers'])))
        self.save(db,s)
        return self.view(s)
    def action(self,sid,action,payload):
        if not isinstance(payload,dict):raise ValueError('提交格式错误')
        with self.lock,self.connect() as db:
            s=self.load(db,sid)
            if s['status'] not in ('ACTIVE','PAUSED'):self.save(db,s);return self.view(s)
            if action=='withdraw':s['status']='WITHDRAWN';self.event(s,'withdraw')
            elif action=='pause' and s['status']=='ACTIVE':s['status']='PAUSED';self.event(s,'pause')
            elif action=='resume' and s['status']=='PAUSED':s['status']='ACTIVE';self.event(s,'resume')
            elif s['status']!='ACTIVE':raise ValueError('请先恢复；暂停期间不能提交')
            elif action=='history':
                if s['stage']!='history' or payload.get('read') is not True:raise ValueError('需先阅读材料；不得重复提交历史')
                choices=payload.get('choices');validate_choices(choices,5)
                s['completed']=['u_positive_int'];s['spent']=5.;self.event(s,'reading_complete',dict(unit='u_positive_int',mastery_updated=False,arrangement='fixed protocol prefix, not planner-selected'))
                for q,choice in zip(self.items[:5],choices):
                    a=add_answer(s['data'],q,choice,s['clock']['wall']);s['answers'].append(a);s['spent']+=1;s['history_cost']+=1;self.event(s,'history_evidence',a)
                try:s['before']=plans(self.root,s['data'],s['completed'],s['spent'])
                except Exception as exc:return self.plan_failure(db,s,exc)
                self.tick(s)
                if s['status']!='ACTIVE':self.save(db,s);return self.view(s)
                s['state_before']=copy.deepcopy(s['data']['state'])
                self.event(s,'before_plan_sealed',dict(plans_digest=digest(s['before']),state_digest=digest(s['state_before']),completed=list(s['completed'])))
                s['stage']='diagnosis';s['sixth_presented']=True;s['diagnosis_started']=s['elapsed'];self.event(s,'diagnosis_presented',dict(item_id=self.items[5]['item_id']))
            elif action=='diagnosis':
                if s['stage']!='diagnosis' or len(s['answers'])!=5:raise ValueError('先完成固定历史，不能重复诊断')
                if 'choice' not in payload:raise ValueError('请选择答案或明确选择不会/跳过')
                q=self.items[5];choice=payload.get('choice');validate_choices([choice],1)
                s['diagnosis_duration_seconds']=s['elapsed']-s['diagnosis_started'] if s['duration_valid'] else None
                a=add_answer(s['data'],q,choice,s['clock']['wall']);s['answers'].append(a);s['spent']+=1;s['diagnosis_cost']=1;self.event(s,'diagnosis_missing' if a['missing'] else 'diagnosis_evidence',a)
                try:
                    s['after']=plans(self.root,s['data'],s['completed'],s['spent'])
                    counter=copy.deepcopy(s['data']);counter['state']=s['state_before'];s['no_feedback']=plans(self.root,counter,s['completed'],s['spent'])
                except Exception as exc:return self.plan_failure(db,s,exc)
                s['diagnosis_metrics']=dict(count=1,seconds=s['diagnosis_duration_seconds'],quiz_cost=1,switch_cost=0,
                    added_units=sorted(set(s['after']['Ours']['route'])-set(s['before']['Ours']['route'])),
                    removed_units=sorted(set(s['before']['Ours']['route'])-set(s['after']['Ours']['route'])))
                self.tick(s)
                if s['status']=='ACTIVE':s['status']='DONE';s['stage']='done';self.event(s,'finished',dict(changed=s['before']['Ours']['route']!=s['after']['Ours']['route'],completed=list(s['completed'])))
            else:raise ValueError('当前步骤不接受此操作')
            self.tick(s);self.save(db,s);return self.view(s)
    def view(self,s):
        material=[m for m in s['data']['materials'] if m['unit_id']=='u_positive_int']
        def summary(value):
            return None if value is None else {method:{'route':p['route'],'cost':p['cost'],'goal_complete':p['audit']['goal_complete']} for method,p in value.items()}
        result=dict(id=s['id'],actor=s['actor'],status=s['status'],stage=s['stage'],version=VERSION,provenance=s['provenance'],
                    elapsed=s['elapsed'] if s['duration_valid'] else None,completed=s['completed'],spent=s['spent'],budget=100,
                    history_cost=s['history_cost'],diagnosis_cost=s['diagnosis_cost'],source_commit=s['data']['task']['repo_commit'],
                    material=material,items=[public_item(q) for q in self.items[:5]] if s['stage']=='history' else ([public_item(self.items[5])] if s['stage']=='diagnosis' else []),
                    before=summary(s['before']),after=summary(s['after']),no_feedback=summary(s['no_feedback']),event_count=len(s['events']),formal_sample=False)
        if s['after']:result['route_changed']=s['before']['Ours']['route']!=s['after']['Ours']['route']
        return result
