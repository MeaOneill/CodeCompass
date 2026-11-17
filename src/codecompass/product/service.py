import copy
import hashlib
import json
import secrets
from datetime import datetime, timezone, timedelta
from .catalog import Catalog
from .store import ProductStore
from .planning import plan, remaining, scope_budget, CONCEPTS
from .questions import Questions
from codecompass.learner import update_evidence

def now(): return datetime.now(timezone(timedelta(hours=8))).isoformat()
def dump(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,allow_nan=False)
class Conflict(ValueError):
    def __init__(self,message,data): super().__init__(message);self.data=data
class Service:
    def __init__(self,root,path,actor='local_user',*,assistant_config=None,transport=None,meter=None):
        if actor not in ('local_user','agent_demo','test_fixture'): raise ValueError('Invalid actor')
        self.root=root; self.actor=actor;self.catalog=Catalog(root);self.store=ProductStore(path)
        self.config=json.loads((root/'configs/product.json').read_text(encoding='utf-8'))
        self.questions=Questions(root)
        from .assistant import Assistant
        from .submissions import Submissions
        self.assistant=Assistant(self,assistant_config,transport,meter)
        self.submissions=Submissions(self)
        from .issues import Issues
        self.issues=Issues(self)
        from .workspaces import Workspaces
        self.workspaces=Workspaces(self)
        from .source_assistant import SourceAssistant
        self.source_assistant=SourceAssistant(self)
        from .onboarding import Onboarding
        self.onboarding=Onboarding(self)
    def user(self,db,uid):
        r=db.execute('SELECT * FROM product_users WHERE user_id=?',(uid,)).fetchone()
        if not r or r['actor']!=self.actor: raise ValueError('学习者记录不存在，请使用原来的本机入口')
        return r
    def profile(self,uid=None):
        with self.store.connect() as db:
            if uid: self.user(db,uid)
            else:
                uid='u_'+secrets.token_hex(16)
                db.execute('INSERT INTO product_users VALUES(?,?,?,?)',(uid,self.actor,now(),'{}'))
            history=[dict(r) for r in db.execute('SELECT session_id,task_id,status,phase,revision,updated_at FROM product_sessions WHERE user_id=? ORDER BY updated_at DESC',(uid,))]
            preferences=self.workspaces.preferences(db,uid)
        ledger=self.store.evidence.read(uid,simulated=self.actor!='local_user')
        for row in history:
            detail=self.get(row['session_id']);state=detail['state']
            row.update(completed=state['completed'],remaining=state['remaining'],plan_status=state['plan_status'],read_only=detail['read_only'],task=detail['task'],draft_saved=bool(state['draft']))
        from codecompass.learner import mastery_gate
        projects={}
        for task in self.catalog.tasks:
            if task['available']:
                data=self.catalog.source(task['task_id']);project=data['snapshot']['snapshot_id']
                row=projects.setdefault(project,dict(name=task['repository'].rsplit('/',1)[-1],concepts=set()))
                row['concepts'].update(c for u in data['units'] for c in u['concept_ids'])
        knowledge=[]
        for project,info in projects.items():
            gate=mastery_gate(ledger,project,info['concepts'],threshold=self.config['threshold'],quantile=self.config['quantile'],allow_simulated=self.actor!='local_user')
            knowledge.extend(dict(project=project,project_name=info['name'],concept_id=c,title=CONCEPTS.get(c,c),status='尚不了解' if not g['evidence_ids'] else '有练习证据' if g['mastered'] else '建议巩固',evidence_count=len(g['evidence_ids'])) for c,g in gate.items())
        with self.store.connect() as db:refs=[self.reference_view(r) for r in db.execute('SELECT * FROM product_transfers WHERE user_id=? ORDER BY referenced_at',(uid,))]
        from .learning_view import profile_metrics
        return dict(user_id=uid,sessions=history,knowledge=knowledge,transfers=refs,transfer_available=True,preferences=preferences,metrics=profile_metrics(preferences),
                    repositories=self.workspaces.jobs(uid),source_routes=self.workspaces.routes(uid))
    def load(self,db,sid):
        r=db.execute('SELECT * FROM product_sessions WHERE session_id=?',(sid,)).fetchone()
        if not r: raise ValueError('学习记录不存在，请返回任务目录')
        self.user(db,r['user_id'])
        s=dict(r);s['state']=json.loads(s.pop('state_json'))
        for k,v in dict(baseline_done=True,baseline_choices=[None]*4,baseline_feedback=[],feedback=None,checked_units=[],assisted_units=[],current_check=None,submission=None).items():s['state'].setdefault(k,v)
        state=s['state']
        for k,v in dict(default_budget=state['budget'],scope='default',learning_spent=state['spent'],quiz_spent=0,switch_spent=0,completed_costs={},plan_pending=False,missing=[],plan_message='',route_explanations=[],answer_results=[],unit_results={},transfer_reference=None).items():state.setdefault(k,v)
        task=self.catalog.task(s['task_id'])
        s['read_only']=s['schema_version']!=self.config['schema_version'] or not set(state['completed']+state['remaining'])<=set(task['unit_ids']) or state.get('source_version',task['source_version'])!=task['source_version']
        s['compatibility_message']='旧内容无法匹配，记录仅供回看；请从任务目录重新开始，原画像和历史保留。' if s['read_only'] else None
        return s
    def view(self,s):
        v={**s,'state':copy.deepcopy(s['state']),'task':self.catalog.task(s['task_id'])}
        if s['phase']=='baseline':v['baseline_questions']=self.questions.baseline()
        if not s['read_only'] and s['phase']=='check' and s['state']['current_check']:
            uid=s['state']['current_check'];v['question']=self.questions.public(self.questions.unit(s['task_id'],uid))
        if s['phase']=='practice' and v['task']['submission_type']=='answers':v['practice_questions']=[self.questions.public(q) for q in self.questions.practice(s['task_id'])]
        if s['task_id']=='P04_chunked_transfer':
            from codecompass.learner import mastery_gate
            data=self.catalog.source(s['task_id']);ledger=self.store.evidence.read(s['user_id'],simulated=self.actor!='local_user')
            gate=mastery_gate(ledger,data['snapshot']['snapshot_id'],data['request']['target_concept_ids'],threshold=self.config['threshold'],quantile=self.config['quantile'],allow_simulated=self.actor!='local_user')
            v['transfer_summary']=dict(reference=s['state'].get('transfer_reference'),new_result=s['state'].get('unit_results',{}).get('B07_more_chunked'),knowledge_gaps=[CONCEPTS.get(c,c) for c,g in gate.items() if not g['mastered']],mastery_copied=False)
        return v
    def get(self,sid):
        with self.store.connect() as db: return self.view(self.load(db,sid))
    def save(self,db,s):
        db.execute('UPDATE product_sessions SET status=?,phase=?,revision=?,state_json=?,updated_at=? WHERE session_id=?',(s['status'],s['phase'],s['revision'],dump(s['state']),s['updated_at'],s['session_id']))
    def create(self,uid,tid,scope='default'):
        task=self.catalog.task(tid)
        if not task['available']: raise ValueError('这个任务准备中，暂时不能开始')
        with self.store.connect() as db:
            db.execute('BEGIN');self.user(db,uid)
            ledger,ledger_revision=self.store.evidence._load(db,uid,self.actor!='local_user')
            before=[tuple(r) for r in db.execute('SELECT session_id,revision FROM product_sessions WHERE user_id=? ORDER BY session_id',(uid,))]
        quiz_count=sum(q['independent'] for q in self.questions.data[tid].values())+sum(q['independent'] for q in self.questions.practice(tid))
        state=plan(self.root,self.catalog.source(tid,uid,self.actor!='local_user'),ledger,self.config,scope,quiz_count)
        state['source_version']=task['source_version']
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            after=[tuple(r) for r in db.execute('SELECT session_id,revision FROM product_sessions WHERE user_id=? ORDER BY session_id',(uid,))]
            _,current_revision=self.store.evidence._load(db,uid,self.actor!='local_user')
            if after!=before or current_revision!=ledger_revision: raise Conflict('学习记录已更新，请重新打开后再开始',self.profile(uid))
            db.execute("UPDATE product_sessions SET status='paused',revision=revision+1,updated_at=? WHERE user_id=? AND status='active'",(now(),uid))
            preferences=json.loads(self.user(db,uid)['preferences_json'])
            baseline_done=bool(preferences.get('onboarding') or preferences.get('legacy_baseline_done'))

            if not baseline_done:
                baseline_done=any(json.loads(r['state_json']).get('baseline_done') for r in db.execute('SELECT state_json FROM product_sessions WHERE user_id=?',(uid,)))
            state.update(baseline_done=baseline_done,baseline_choices=[None]*4,baseline_feedback=[],feedback=None,checked_units=[],assisted_units=[],current_check=None,submission=None)
            sid='s_'+secrets.token_hex(16)
            db.execute('INSERT INTO product_sessions VALUES(?,?,?,?,?,?,?,?,?,?,?)',(sid,uid,tid,'active','baseline' if state['plan_status']=='FEASIBLE' and not baseline_done else 'learning',0,self.config['schema_version'],self.config['content_version'],self.config['planner_version'],dump(state),now()))
            if tid=='P04_chunked_transfer':
                created=self.load(db,sid);created['state']['transfer_reference']=self._reference(db,created,ledger);self.save(db,created)
            return self.view(self.load(db,sid))
    def _request(self,rid,revision,payload):
        if not isinstance(rid,str) or not 1<=len(rid)<=128:raise ValueError('缺少有效请求编号')
        if type(revision) is not int or not isinstance(payload,dict):raise ValueError('缺少有效记录版本或操作内容')
    def action(self,sid,rid,revision,action,payload=None):
        payload=payload or {};self._request(rid,revision,payload)
        h=hashlib.sha256(dump([revision,action,payload]).encode()).hexdigest()
        with self.store.connect() as db:
            db.execute('BEGIN')
            s=self.load(db,sid)
            cached=db.execute('SELECT * FROM product_actions WHERE session_id=? AND request_id=?',(sid,rid)).fetchone()
            if cached:
                if cached['payload_hash']!=h:raise Conflict('请求编号已用于其他操作',self.view(s))
                return json.loads(cached['response_json'])
            if s['revision']!=revision:raise Conflict('记录已更新，已恢复服务器上的进度',self.view(s))
            ledger,ledger_revision=self.store.evidence._load(db,s['user_id'],self.actor!='local_user')
            exposures=[tuple(r) for r in db.execute('SELECT item_id,assisted,answered FROM product_exposures WHERE user_id=? ORDER BY item_id',(s['user_id'],))]
        state=s['state'];evidence=None;answer=None;exposure_item=None;refresh=None
        extra_answers=[];extra_evidences=[]
        if action not in ('pause','resume','archive','baseline','skip_baseline','read','check','budget','retry_plan','answers'):raise ValueError('当前操作不受支持')
        if s['read_only']:raise ValueError(s['compatibility_message'])
        if state['plan_pending'] and action not in ('retry_plan','budget','pause','resume','archive'):raise ValueError('反馈已保存，请先重试安排')
        if s['status'] in ('archived','completed') and not (action=='retry_plan' and state['plan_pending']):raise ValueError('此记录已结束，可查看成果或重新开始')
        if s['status']=='paused' and action not in ('resume','archive'):raise ValueError('请先恢复学习')
        if action in ('pause','resume','archive'):s['status']={'pause':'paused','resume':'active','archive':'archived'}[action]
        elif action in ('baseline','skip_baseline'):
            if s['phase']!='baseline':raise ValueError('基础了解已结束，不重复提交')
            choices=[None]*4 if action=='skip_baseline' else payload.get('choices')
            if not isinstance(choices,list) or len(choices)!=4:raise ValueError('请保存四题选项，未答项可留空')
            feedback=[]
            for q,c in zip(self.questions.data['baseline'],choices):
                correct=self.questions.score(q,c)
                feedback.append(dict(item_id=q['item_id'],correct=correct,explanation=q['explanation'] if payload.get('finish') or action=='skip_baseline' else None))
            state['baseline_choices']=choices
            if payload.get('finish') or action=='skip_baseline':
                state['baseline_done']=True;state['baseline_feedback']=feedback;s['phase']='learning' if state['remaining'] else 'practice'
        elif action=='read':
            if s['phase']!='learning' or state['plan_status']!='FEASIBLE' or not state['remaining']:raise ValueError('当前没有可完成的阅读单元')
            uid=payload.get('unit_id')
            if uid!=state['remaining'][0]:raise ValueError('请先完成当前单元')
            state['completed'].append(uid);state['remaining'].pop(0)
            cost=state['unit_costs'][uid];state['spent']+=cost;state['learning_spent']+=cost;state['completed_costs'][uid]=cost;state['current_check']=uid
            state['feedback']=None;s['phase']='check'
            from .planning import settings,request_for_state,route_audit
            data=self.catalog.source(s['task_id'],s['user_id'],self.actor!='local_user');req=request_for_state(data['request'],ledger,settings(data,self.config));req['budget']=state['budget']
            gate=state['plan_history'][-1]['result']['gate']
            state['plan_audit']=route_audit(req,data['units'],gate,state['remaining'],state['unit_costs'],state['completed'],state['remaining'],self.config['gamma'],state['spent'])
            if not state['plan_audit']['valid']:raise ValueError('当前安排费用校验失败，请重新安排')
        elif action=='check':
            if s['phase']!='check' or not state['current_check']:raise ValueError('当前没有待作答的小题')
            uid=state['current_check'];q=self.questions.unit(s['task_id'],uid)
            if payload.get('continue'):
                if not state['feedback']:raise ValueError('请先回答或明确选择不会')
                if uid not in state['checked_units']:state['checked_units'].append(uid)
                state['current_check']=None;state['feedback']=None
                s['phase']='learning' if state['remaining'] else 'practice'
            else:
                choice=payload.get('choice');correct=self.questions.score(q,choice)
                prior=next((r for r in exposures if r[0]==q['item_id']),None)
                independent=bool(q['independent'] and correct is not None and not prior and uid not in state['assisted_units'])
                if independent:
                    evidence=dict(evidence_id='product:'+q['item_id'],item_id=q['item_id'],concept_id=q['concept_id'],project=self.catalog.source(s['task_id'])['snapshot']['snapshot_id'],timestamp=now(),pseudonymous_user_id=s['user_id'],is_fixture=self.actor!='local_user',independent=True,source_mode=self.actor,evidence_type='independent_quiz',outcome='pass' if correct else 'fail')
                    ledger,_=update_evidence(ledger,evidence,allow_simulated=self.actor!='local_user')
                    state['spent']+=self.config['quiz_cost'];state['quiz_spent']+=self.config['quiz_cost']
                    refresh='independent_quiz';state['plan_pending']=True
                state['feedback']=dict(correct=correct,independent=independent,explanation=q['explanation'],supplement=q.get('supplement',''),message='尚未确定；不会不记错。' if correct is None else '回答正确。' if correct else '这次还没答对，先看解释，再继续学习。')
                exposure_item=q['item_id']
                state['unit_results'][uid]=dict(item_id=q['item_id'],correct=correct,independent=independent,assisted=uid in state['assisted_units'],explanation=q['explanation'],supplement=q.get('supplement',''))
                answer=dict(item_id=q['item_id'],concept_id=q['concept_id'],project=self.catalog.source(s['task_id'])['snapshot']['snapshot_id'],evidence_id=evidence['evidence_id'] if independent else None,source_mode=self.actor,choice=choice,correct=correct,independent=independent,assisted=uid in state['assisted_units'],timestamp=now())
        elif action=='answers':
            if self.catalog.task(s['task_id'])['submission_type']!='answers' or s['phase']!='practice':raise ValueError('当前不是行为题练习')
            questions=self.questions.practice(s['task_id']);values=payload.get('answers')
            if not isinstance(values,list) or len(values)!=len(questions):raise ValueError('请保存当前任务的全部练习选项')
            reflection=payload.get('reflection','')
            if not isinstance(reflection,str) or len(reflection)>6000:raise ValueError('反思文字过长')
            results=[]
            for q,choice in zip(questions,values):
                correct=self.questions.score(q,choice)
                prior=next((r for r in exposures if r[0]==q['item_id']),None)
                independent=bool(q['independent'] and correct is not None and not prior and not state['assisted_units'])
                record=dict(item_id=q['item_id'],concept_id=q['concept_id'],project=self.catalog.source(s['task_id'])['snapshot']['snapshot_id'],source_mode=self.actor,timestamp=now(),choice=choice,correct=correct,independent=independent,evidence_id=None)
                if independent:
                    ev=dict(evidence_id='product:'+q['item_id'],item_id=q['item_id'],concept_id=q['concept_id'],project=record['project'],timestamp=record['timestamp'],pseudonymous_user_id=s['user_id'],is_fixture=self.actor!='local_user',independent=True,source_mode=self.actor,evidence_type='independent_quiz',outcome='pass' if correct else 'fail')
                    extra_evidences.append(ev);record['evidence_id']=ev['evidence_id']
                    state['spent']+=self.config['quiz_cost'];state['quiz_spent']+=self.config['quiz_cost']
                extra_answers.append(record);results.append(dict(item_id=q['item_id'],correct=correct,independent=independent,explanation=q['explanation']))
            state['answer_results']=results;state['draft']=dict(answers=values,reflection=reflection)
            if all(r['correct'] is True for r in results):s['status']='completed';s['phase']='review'
            if extra_evidences:refresh='independent_behavior';state['plan_pending']=True
        elif action in ('budget','retry_plan'):
            if action=='budget':
                if 'scope' in payload:
                    new=scope_budget(state['default_budget'],payload['scope']);state['scope']=payload['scope']
                else:new=payload.get('budget');state['scope']='custom'
                if type(new) not in (int,float) or not __import__('math').isfinite(new) or new<state['spent'] or new>100000:raise ValueError('学习范围需覆盖已完成工作量，且不超过上限')
                state['budget']=new
            refresh='budget' if action=='budget' else 'retry';state['plan_pending']=True
        s['state']=state;s['revision']+=1;s['updated_at']=now()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');latest=self.load(db,sid)
            old=db.execute('SELECT * FROM product_actions WHERE session_id=? AND request_id=?',(sid,rid)).fetchone()
            if old:
                if old['payload_hash']!=h:raise Conflict('请求编号已用于其他操作',self.view(latest))
                return json.loads(old['response_json'])
            current_exposures=[tuple(r) for r in db.execute('SELECT item_id,assisted,answered FROM product_exposures WHERE user_id=? ORDER BY item_id',(s['user_id'],))]
            _,lr=self.store.evidence._load(db,s['user_id'],self.actor!='local_user')
            if latest['revision']!=revision or lr!=ledger_revision or current_exposures!=exposures:raise Conflict('学习记录已更新，当前进度已保留，请重试',self.view(latest))
            if action=='resume':db.execute("UPDATE product_sessions SET status='paused',revision=revision+1,updated_at=? WHERE user_id=? AND status='active' AND session_id<>?",(now(),s['user_id'],sid))
            if evidence:self.store.evidence.submit_many_in_connection(db,s['user_id'],[evidence],simulated=self.actor!='local_user')
            if answer:
                db.execute('INSERT INTO product_answers(session_id,item_id,value_json) VALUES(?,?,?)',(sid,answer['item_id'],dump(answer)))
                db.execute('INSERT INTO product_exposures VALUES(?,?,0,1) ON CONFLICT(user_id,item_id) DO UPDATE SET answered=1',(s['user_id'],exposure_item))
            if extra_evidences:self.store.evidence.submit_many_in_connection(db,s['user_id'],extra_evidences,simulated=self.actor!='local_user')
            for record in extra_answers:
                db.execute('INSERT INTO product_answers(session_id,item_id,value_json) VALUES(?,?,?)',(sid,record['item_id'],dump(record)))
                db.execute('INSERT INTO product_exposures VALUES(?,?,0,1) ON CONFLICT(user_id,item_id) DO UPDATE SET answered=1',(s['user_id'],record['item_id']))
            self.save(db,s);response=self.view(s)
            db.execute('INSERT INTO product_actions VALUES(?,?,?,?,?)',(sid,rid,h,dump(response),now()))
        return self.refresh_plan(sid,refresh,rid) if refresh else response

    def refresh_plan(self,sid,reason,rid):

        with self.store.connect() as db:
            db.execute('BEGIN');s=self.load(db,sid)
            ledger,lr=self.store.evidence._load(db,s['user_id'],self.actor!='local_user')
        revision=s['revision'];state=copy.deepcopy(s['state'])
        try:state=remaining(self.root,self.catalog.source(s['task_id'],s['user_id'],self.actor!='local_user'),ledger,self.config,state,reason)
        except Exception:
            state=copy.deepcopy(s['state']);state.update(plan_pending=True,plan_status='ERROR',plan_message='反馈已保存，路线暂未更新，可重试安排。')
            state['plan_history'].append(dict(reason=reason,before=list(state['remaining']),after=list(state['remaining']),error='SEARCH_UNAVAILABLE',completed=list(state['completed'])))
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');latest=self.load(db,sid)
            _,current=self.store.evidence._load(db,s['user_id'],self.actor!='local_user')
            if latest['revision']!=revision or current!=lr:return self.view(latest)
            latest['state']=state;latest['revision']+=1;latest['updated_at']=now();self.save(db,latest)
            response=self.view(latest)
            db.execute('UPDATE product_actions SET response_json=? WHERE session_id=? AND request_id=?',(dump(response),sid,rid))
            return response

    def draft(self,sid,rid,revision,kind,content):
        if kind not in ('practice','baseline') or not isinstance(content,dict) or len(dump(content).encode())>20000:raise ValueError('草稿内容过大或格式无效')
        if kind=='baseline':return self.action(sid,rid,revision,'baseline',dict(choices=content.get('choices')))
        self._request(rid,revision,content);h=hashlib.sha256(dump([kind,content,revision]).encode()).hexdigest()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');s=self.load(db,sid)
            old=db.execute('SELECT * FROM product_actions WHERE session_id=? AND request_id=?',(sid,rid)).fetchone()
            if old:
                if old['payload_hash']!=h:raise Conflict('请求编号已用于其他操作',self.view(s))
                return json.loads(old['response_json'])
            if s['revision']!=revision:raise Conflict('记录已更新，请重新读取',self.view(s))
            if s['read_only'] or s['status']!='active' or s['phase']!='practice':raise ValueError('当前不能保存练习草稿')
            s['revision']+=1;s['state']['draft']=content;s['updated_at']=now()
            db.execute('INSERT INTO product_drafts VALUES(?,?,?,?,?) ON CONFLICT(session_id,kind) DO UPDATE SET content_json=excluded.content_json,revision=excluded.revision,updated_at=excluded.updated_at',(sid,kind,dump(content),s['revision'],now()))
            self.save(db,s);response=self.view(s)
            db.execute('INSERT INTO product_actions VALUES(?,?,?,?,?)',(sid,rid,h,dump(response),now()));return response

    @staticmethod
    def reference_view(row):
        return dict(reference_id=row['reference_id'],source_project=row['source_project'],target_project=row['target_project'],concept_id=row['concept_id'],source_evidence_ids=json.loads(row['source_evidence_ids_json']),target_item_id=row['target_item_id'],referenced_at=row['referenced_at'],source_session_ids=json.loads(row['source_sessions_json']),posterior_copied=False,mastery_granted=False)
    def _reference(self,db,s,ledger):
        if s['task_id']!='P04_chunked_transfer':raise ValueError('请选择新仓库分组任务建立关联')
        previous=db.execute('SELECT * FROM product_transfers WHERE session_id=?',(s['session_id'],)).fetchone()
        if previous:return self.reference_view(previous)
        source=self.catalog.source('P02_window_fix')['snapshot']['snapshot_id'];target=self.catalog.source(s['task_id'])['snapshot']['snapshot_id']
        evidences=[e['evidence_id'] for e in ledger['records'] if e['project']==source and e['concept_id']=='python.iterator_protocol']
        sessions=[]
        for row in db.execute("SELECT session_id,state_json FROM product_sessions WHERE user_id=? AND task_id IN ('P02_window_fix','P03_window_debug')",(s['user_id'],)):
            if 'u_iterable' in json.loads(row['state_json'])['completed']:sessions.append(row['session_id'])
        if not evidences and not sessions:return None
        item=self.questions.unit(s['task_id'],'B07_more_chunked')['item_id'];rid='ref_'+secrets.token_hex(16)
        db.execute('INSERT INTO product_transfers VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,s['session_id'],s['user_id'],source,target,'python.iterator_protocol',dump(evidences),item,now(),dump(sessions)))
        return self.reference_view(db.execute('SELECT * FROM product_transfers WHERE reference_id=?',(rid,)).fetchone())
    def transfer(self,sid,target_project=None,concept_id='python.iterator_protocol'):
        if concept_id!='python.iterator_protocol':raise ValueError('当前只支持迭代器协议的跨项目引用')
        if target_project is not None and target_project!=self.catalog.source('P04_chunked_transfer')['snapshot']['snapshot_id']:raise ValueError('目标项目与当前新仓库任务不匹配')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');s=self.load(db,sid)
            if s['read_only']:raise ValueError(s['compatibility_message'])
            ledger,_=self.store.evidence._load(db,s['user_id'],self.actor!='local_user')
            reference=self._reference(db,s,ledger)
            if s['state'].get('transfer_reference')!=reference:
                s['state']['transfer_reference']=reference;s['revision']+=1;s['updated_at']=now();self.save(db,s)
            return dict(reference=reference,session=self.view(s),notice='已有相关记录只作引用，新项目仍需新题确认。' if reference else '没有来源记录；先从这里了解迭代器。')

    def material(self,sid,uid):
        s=self.get(sid);m=self.catalog.material(s['task_id'],uid);m['exercise']=self.questions.public(self.questions.unit(s['task_id'],uid));return m
