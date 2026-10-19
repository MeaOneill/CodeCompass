"""Opt-in D06 development integration; untouched D05 collector stays replayable.

Uses original B2 closure/gain/cost rule with completed-material context. No
completed material is inserted into the independent learner ledger.
"""
import copy
import math
from codecompass.learner import mastery_gate, planning_rows
from codecompass.planner.core import validate_request, reverse_closure, ClosureCycle
from codecompass.planner.adaptive import route_audit
from .experiment import Collector


def b2_remaining(request,units,state,config,completed=(),spent=0):
    req=copy.deepcopy(request)
    req['learner_state']=planning_rows(state,req['snapshot_id'],quantile=config['quantile'],allow_simulated=req['is_fixture'])
    by_id=validate_request(req,units,state,config)
    if len(set(completed))!=len(completed) or any(u not in by_id for u in completed):raise ValueError('Bad completed context')
    if type(spent) not in (int,float) or not math.isfinite(spent) or not 0<=spent<=req['budget']:raise ValueError('Bad paid cost')
    concepts={c for u in units for c in u['concept_ids']}|set(req['target_concept_ids'])
    gate=mastery_gate(state,req['snapshot_id'],concepts,threshold=config['threshold'],quantile=config['quantile'],allow_simulated=req['is_fixture'])
    mastered={c for c,g in gate.items() if g['mastered']};selected=list(completed);route=[];cost=0.0
    known=mastered|{c for uid in completed for c in by_id[uid]['concept_ids']};goals=set(req['target_concept_ids'])
    attempts=[]
    while goals-known:
        candidates=[]
        for uid,u in sorted(by_id.items()):
            if uid in selected or not set(u['concept_ids'])&(goals-known):continue
            try:bundle=reverse_closure(uid,by_id,mastered,selected)
            except ClosureCycle:continue
            incremental=sum(by_id[x]['base_cost'] for x in bundle)
            gain=len(({c for x in bundle for c in by_id[x]['concept_ids']}-known)&goals)
            if not gain or spent+cost+incremental>req['budget']+1e-9:continue
            ratio=math.inf if incremental==0 else gain/incremental
            candidates.append(((-ratio,incremental,uid),bundle,incremental))
        attempts.append([dict(root=x[0][2],bundle=x[1],incremental=x[2]) for x in candidates])
        if not candidates:break
        _,bundle,incremental=min(candidates,key=lambda x:x[0]);route.extend(bundle);selected.extend(bundle);cost+=incremental
        known.update(c for uid in bundle for c in by_id[uid]['concept_ids'])
    replay=route_audit(req,units,gate,route,{u['id']:u['base_cost'] for u in units},completed,(),0,spent)
    return dict(status='FEASIBLE' if goals<=known else 'NO_FEASIBLE_FOUND',remaining=route,cost=cost,
                gate=gate,replay=replay,candidate_attempts=attempts,completed=list(completed),
                method='original_closure_gain_cost_rule_with_completed_context',mastery_fabricated=False)


class StudyCollector(Collector):
    """Candidate two-method UI, scheduled quiz atomically after first reading.

    Not formal enrollment: only the existing two dev tasks are executable. The
    eight held-out specs must acquire reviewed planning inputs before any study.
    """
    def create(self,task_id='task_001',method='Ours',participant=None,*,limit_seconds=1500):
        if method not in ('Ours','B2'):raise ValueError('D06开发模式仅Ours/B2；B1_saved不是动态B1')
        return super().create(task_id,method,participant,limit_seconds=limit_seconds)

    def event(self,db,s,kind,payload=None,sample=None):
        payload=copy.deepcopy(payload or {})
        if kind=='reading_complete' and len(s['completed'])>1 and not s['quiz_done']:
            raise ValueError('共同规则：首份材料后必须先完成短测')
        if kind=='final_submit' and not s['quiz_done'] and (s['completed'] or s['route']):
            raise ValueError('共同规则：尚未完成规定阅读/短测，不能最终提交')
        if s['method']=='B2' and kind in ('initial_plan','replan'):
            d=s['data'];result=b2_remaining(d['request'],d['units'],d['state'],d['config'],s['completed'],s['spent'])
            s['route']=result['remaining'];s['planner_status']=result['status'];s['b2_context_result']=result
            payload['after' if kind=='replan' else 'route']=list(s['route']);payload['planner_status']=s['planner_status']
            if s.get('feedback'):s['feedback']['after_route']=list(s['route'])
        super().event(db,s,kind,payload,sample)
        if kind=='reading_complete' and len(s['completed'])==1 and not s['quiz_done']:
            if s['spent']+s['data']['quiz']['cost']>s['data']['request']['budget']:
                s['status']='FAILED';super().event(db,s,'failure',{'reason':'COMMON_QUIZ_UNAFFORDABLE'},sample)
            else:
                s['phase']='quiz';s['quiz_started']=s['elapsed']
                super().event(db,s,'quiz_start',{'item_id':s['data']['quiz']['item_id'],'policy':'automatic_after_exactly_one_material'},sample)

    def view(self,s):
        v=super().view(s)
        v['limitation']='D06开发候选；首份材料后自动短测；仅Ours/B2。留出任务/正式招募/双方审批仍未放行。'
        v['protocol_version']='B-D06-protocol-candidate-1'
        return v
