"""B-D05 transactional collector. Local development only; no model API calls."""
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import secrets
import sqlite3
import time
import uuid

from codecompass.learner import initial_state, mastery_gate, planning_rows, update_evidence
from codecompass.graph import read_snapshot, validate_span
from codecompass.planner.feedback import start_session, apply_feedback, complete_next
from codecompass.planner.diagnostics import evidence_for
from codecompass.planner.search_service import solve_request
from .diagnostic_items import ITEMS, public_item, score

METHODS = ('B0', 'B1_saved', 'B2', 'Ours')
TERMINAL = ('SUBMITTED', 'TIMED_OUT', 'WITHDRAWN', 'FAILED')
VERSION = 'B-D05-collector-1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class Clock:
    def __init__(self):
        self.epoch = uuid.uuid4().hex

    def sample(self):
        return dict(wall=datetime.now(timezone.utc).isoformat(), mono=time.monotonic(), epoch=self.epoch)


def load(root, path):
    return json.loads((root/path).read_text(encoding='utf-8'))


def inputs(root, tid, participant, simulated):
    if tid not in ITEMS:
        raise ValueError('仅开放两道开发任务，终测未接入')
    task = load(root, f'benchmarks/dev/D03/{tid}.json')
    units = [u for u in load(root, 'benchmarks/dev/D03/units.json') if u['id'] in task['learning_unit_ids']]
    config = load(root, 'configs/A/D03_common.json')
    state = initial_state(participant, is_simulated=simulated)
    req = dict(schema_version='1.0.0', object_type='PlanningRequest', is_fixture=simulated,
        request_id='B05-'+uuid.uuid4().hex, snapshot_id=task['snapshot_id'], task_id=tid,
        learner_state=[], budget=100, cost_unit='proxy_cost', config_version=config['version'],
        target_concept_ids=task['required_concept_ids'], unit_ids=[u['id'] for u in units], prior_plan_id=None)
    snapshot = load(root, 'benchmarks/sources/boltons/snapshot.json')
    contents = read_snapshot(root/'benchmarks/sources/boltons', snapshot)
    materials = []
    for u in units:
        for span in u['source_spans']:
            validate_span(span, snapshot, contents)
            lines = contents[span['path']].decode('utf-8').splitlines()
            materials.append(dict(unit_id=u['id'], source_span=span,
                text='\n'.join(f'{i+1:4}  {lines[i]}' for i in range(span['start_line']-1, span['end_line']))))
    q = ITEMS[tid]
    quiz = dict(item_id=q['item_id'], concept_id=q['concept_id'], independent=True,
        source=q['basis'], cost=1.0, cost_unit='proxy_cost', probability=None)
    public_task = {k: task[k] for k in ('task_id', 'title', 'goal', 'requirements', 'repo_commit')}
    return dict(task=public_task, units=units, config=config, state=state, request=req,
                materials=materials, quiz=quiz)


def plan(root, s):
    d = s['data']; method = s['method']
    if method == 'Ours':
        if not s.get('adaptive'):
            s['adaptive'] = start_session(root, d['request'], d['units'], d['state'], d['config'],
                [d['quiz']], strategy='voi', max_quizzes=1, alpha=0, gamma=0)
        s['route'] = list(s['adaptive']['plan']['remaining'])
        s['planner_status'] = s['adaptive']['status']
    elif method == 'B0':
        s['route'] = [u for u in d['config']['routes'][s['task_id']] if u not in s['completed']]
        s['planner_status'] = 'FEASIBLE'
    elif method == 'B1_saved':
        rows = load(root, 'experiments/B/B-D04-deepseek-live01/summary.json')['rows']
        row = next(r for r in rows if r['method']=='B1' and r['case_id']==s['task_id']+'-sim_unknown')
        s['route'] = [u for u in row['plan']['ordered_units'] if u not in s['completed']]
        s['planner_status'] = row['execution_status']
    else:

        req = copy.deepcopy(d['request']); covered = {c for u in d['units'] if u['id'] in s['completed'] for c in u['concept_ids']}
        req['target_concept_ids'] = [c for c in req['target_concept_ids'] if c not in covered]
        req['budget'] -= s['spent']
        req['learner_state'] = planning_rows(d['state'], req['snapshot_id'], allow_simulated=req['is_fixture'])
        if not req['target_concept_ids']:
            s['route'] = []; s['planner_status'] = 'FEASIBLE'
        else:
            result, _ = solve_request(root, req, d['units'], d['state'], d['config'], method='B2')
            s['route'] = [u for u in result['ordered_units'] if u not in s['completed']]
            s['planner_status'] = result['status']


class Collector:
    def __init__(self, root, database, *, clock=None, actor='human_manual'):
        self.root = Path(root); self.database = Path(database); self.clock = clock or Clock()
        if actor not in ('human_manual', 'agent_browser', 'test_fixture'):
            raise ValueError('Explicit provenance required')
        self.actor = actor
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, value TEXT NOT NULL);'
                             'CREATE TABLE IF NOT EXISTS events (id TEXT, seq INTEGER, value TEXT, PRIMARY KEY(id,seq));')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.database, timeout=30)
        try:
            with db:
                yield db
        finally:
            db.close()

    def event(self, db, s, kind, payload=None, sample=None):
        sample = sample or self.clock.sample()
        s['seq'] += 1
        e = dict(version=VERSION, session_id=s['id'], participant=s['participant'], task_id=s['task_id'],
            method=s['method'], actor=s['actor'], seq=s['seq'], kind=kind, clock=sample,
            elapsed_observed=s['elapsed'], duration_valid=s['duration_valid'], status=s['status'],
            payload=payload or {}, previous_hash=s['last_hash'])
        e['hash'] = digest(e); s['last_hash'] = e['hash']
        db.execute('INSERT INTO events VALUES (?,?,?)', (s['id'], s['seq'], json.dumps(e, ensure_ascii=False)))

    def save(self, db, s):
        db.execute('INSERT OR REPLACE INTO sessions VALUES (?,?)', (s['id'], json.dumps(s, ensure_ascii=False)))

    def tick(self, db, s):
        now = self.clock.sample(); last = s['clock']
        if s['status'] in TERMINAL:
            return
        wall_delta = (datetime.fromisoformat(now['wall'])-datetime.fromisoformat(last['wall'])).total_seconds()
        if now['epoch'] != last['epoch']:
            if s['status'] == 'ACTIVE':
                s['duration_valid'] = False; s['missing'].append('ACTIVE_RESTART_GAP')
                s['status'] = 'PAUSED'
            self.event(db, s, 'restart', {'active_gap_unknown': not s['duration_valid']}, now)
        else:
            delta = now['mono']-last['mono']
            if not math.isfinite(delta) or delta < 0 or wall_delta < -1 or abs(wall_delta-delta) > 5:
                s['duration_valid'] = False; s['missing'].append('CLOCK_DISCONTINUITY'); s['status'] = 'PAUSED'
                self.event(db, s, 'clock_anomaly', {}, now)
            elif s['status'] == 'ACTIVE':
                s['elapsed'] += delta
        s['clock'] = now
        if s['status'] == 'ACTIVE' and s['elapsed'] >= s['limit_seconds']:
            s['status'] = 'TIMED_OUT'
            self.event(db, s, 'timeout', {'limit_seconds': s['limit_seconds']}, now)

    def create(self, task_id='task_001', method='Ours', participant=None, *, limit_seconds=1500):
        if method not in METHODS or type(limit_seconds) not in (int,float) or not 0 < limit_seconds <= 1500:
            raise ValueError('Invalid method/time limit')

        if participant is not None and (len(participant)!=34 or not participant.startswith('p_') or
                any(c not in '0123456789abcdef' for c in participant[2:])):
            raise ValueError('匿名编码无效')
        participant = participant or 'p_'+secrets.token_hex(16)
        now = self.clock.sample()
        s = dict(id=secrets.token_urlsafe(24), participant=participant, actor=self.actor, task_id=task_id,
            method=method, status='ACTIVE', phase='reading', elapsed=0.0, duration_valid=True, missing=[],
            clock=now, seq=0, last_hash=None, limit_seconds=limit_seconds, completed=[], spent=0.0,
            quiz_done=False, quiz_started=None, outcome=None, success=None, score_status='NOT_SUBMITTED',
            response=None, route=[], feedback=None, data=inputs(self.root,task_id,participant,self.actor!='human_manual'))
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            self.event(db,s,'start', {'scope':'development_only', 'method_variant':'saved_static' if method=='B1_saved' else 'development'})
            plan(self.root,s); self.tick(db,s)
            self.event(db,s,'initial_plan',{'route':s['route'], 'planner_status':s['planner_status']})
            if s['planner_status']!='FEASIBLE':
                s['status']='FAILED';self.event(db,s,'failure',{'reason':s['planner_status']})
            elif s['status']=='ACTIVE' and s['route']: self.event(db,s,'read',{'unit_id':s['route'][0]})
            self.save(db,s)
        return self.view(s)

    def get(self, sid):
        return self.action(sid, 'poll')

    def action(self, sid, action, payload=None):
        payload = payload or {}
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()
            if not row: raise ValueError('会话不存在，请开始新开发会话')
            s = json.loads(row[0]); self.tick(db,s)
            if action == 'poll' or s['status'] in TERMINAL:
                self.save(db,s); return self.view(s)
            if action == 'resume':
                if s['status'] != 'PAUSED': raise ValueError('当前未暂停')
                s['status']='ACTIVE'; self.event(db,s,'resume')
            elif action == 'withdraw':
                s['status']='WITHDRAWN'; self.event(db,s,'withdraw')
            elif s['status'] != 'ACTIVE':
                self.save(db,s)

                return self.view(s)
            elif action == 'pause':
                s['status']='PAUSED'; self.event(db,s,'pause')
            elif action == 'read':
                if not s['route']: raise ValueError('没有下一材料')
                s['phase']='quiz' if s['quiz_started'] is not None and not s['quiz_done'] else 'reading'
                self.event(db,s,'read', {'unit_id':s['route'][0]})
            elif action == 'complete_reading':
                if not s['route']: raise ValueError('没有下一材料')
                uid=s['route'][0]
                if s['method']=='Ours':
                    s['adaptive']=complete_next(s['adaptive'],uid); s['spent']=s['adaptive']['spent']
                else:
                    cost=next(u['base_cost'] for u in s['data']['units'] if u['id']==uid)
                    if s['spent']+cost>100: raise ValueError('代理预算不足')
                    s['spent']+=cost
                s['completed'].append(uid); s['route'].pop(0)
                self.event(db,s,'reading_complete', {'unit_id':uid, 'mastery_updated':False})
            elif action == 'quiz':
                if s['quiz_done'] or s['quiz_started'] is not None: raise ValueError('每轮仅一次独立短测')
                if not s['completed']: raise ValueError('请先完成一份阅读材料')
                s['phase']='quiz'; s['quiz_started']=s['elapsed']
                self.event(db,s,'quiz_start', {'item_id':s['data']['quiz']['item_id']})
            elif action == 'answer':
                if s['phase']!='quiz' or s['quiz_done']: raise ValueError('短测不可重复提交')
                outcome=score(s['task_id'],payload.get('choice'))
                duration=s['elapsed']-s['quiz_started'] if s['duration_valid'] else None
                d=s['data']; before=copy.deepcopy(d['state']); before_route=list(s['route'])
                if s['method']=='Ours':
                    s['adaptive']=apply_feedback(self.root,s['adaptive'],d['quiz']['item_id'],outcome,
                        timestamp=s['clock']['wall'],duration_seconds=duration,scheduled=True)
                    d['state']=s['adaptive']['state']; s['spent']=s['adaptive']['spent']
                else:
                    if s['spent']+1>100: raise ValueError('测验代理预算不足')
                    evidence=evidence_for(d['request'],d['state'],d['quiz'],outcome,s['clock']['wall'])
                    d['state'], accepted=update_evidence(d['state'],evidence,allow_simulated=d['request']['is_fixture'])
                    if accepted!='ACCEPTED': raise ValueError('重复证据')
                    s['spent']+=1
                s['quiz_done']=True; s['outcome']=outcome
                self.event(db,s,'quiz_submit', {'item_id':d['quiz']['item_id'], 'outcome':outcome,
                    'duration_seconds':duration,'scorer':'independent_python_semantics_v1'})
                s['feedback']={'before':planning_rows(before,d['request']['snapshot_id'],allow_simulated=d['request']['is_fixture']),
                    'after':planning_rows(d['state'],d['request']['snapshot_id'],allow_simulated=d['request']['is_fixture']),
                    'before_route':before_route}
                self.event(db,s,'feedback', {'concept_id':d['quiz']['concept_id'],'outcome':outcome})
                plan(self.root,s); self.tick(db,s)
                s['feedback']['after_route']=list(s['route']); s['phase']='feedback'
                self.event(db,s,'replan', {'before':before_route,'after':s['route'],
                    'policy':'static_route_retained' if s['method'] in ('B0','B1_saved') else 'evidence_replan',
                    'planner_status':s['planner_status']})
                if s['planner_status']!='FEASIBLE' and s['status']=='ACTIVE':
                    s['status']='FAILED';self.event(db,s,'failure',{'reason':s['planner_status']})
            elif action == 'submit':
                response=payload.get('response')
                if not isinstance(response,str) or not response.strip() or len(response)>12000:
                    raise ValueError('请填写开发提交说明（最多12000字），不要填写身份信息')
                s['response']=response; s['status']='SUBMITTED'; s['score_status']='PENDING_INDEPENDENT_FINAL_SCORING'
                self.event(db,s,'final_submit', {'response_sha256':hashlib.sha256(response.encode()).hexdigest(),
                    'success':None, 'score_status':s['score_status']})
            else: raise ValueError('Unknown action')
            self.save(db,s)
            return self.view(s)

    def view(self,s):

        d=s['data']; uid=s['route'][0] if s['route'] else None
        return dict(session_id=s['id'],participant=s['participant'],task=d['task'],method=s['method'],actor=s['actor'],
            status=s['status'],phase=s['phase'],elapsed_seconds=s['elapsed'] if s['duration_valid'] else None,
            observed_seconds=s['elapsed'],missing=list(s['missing']),limit_seconds=s['limit_seconds'],
            route=s['route'],completed=s['completed'],spent=s['spent'],quiz_done=s['quiz_done'],
            quiz=public_item(s['task_id']) if s['phase']=='quiz' and not s['quiz_done'] else None,
            materials=[m for m in d['materials'] if m['unit_id']==uid], feedback=s['feedback'],
            outcome=s['outcome'],score_status=s['score_status'],success=s['success'],events=s['seq'],
            limitation='开发测试；B1为D04静态保存路线；各方法同一短测。生产VOI未校准，终测评分未接入。')
