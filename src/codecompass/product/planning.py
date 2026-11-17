"""Accounting around the unchanged adaptive search and independent replay."""
import math
from codecompass.planner.adaptive import remaining_plan, request_for_state, personalized_costs, route_audit
SCOPES={'short':.6,'default':1,'wide':1.2}
CONCEPTS={'python.iterator_protocol':'逐个取数据','python.tee':'多个迭代视角','python.keyword_presence':'填充参数是否提供','python.type_validation':'参数类型检查','python.hash_set':'集合去重','python.key_function':'按key判断重复','python.generator_laziness':'按需生成','source.function.iterutils.unique_iter':'保序去重函数','source.function.more_itertools.chunked':'新仓库分组函数'}
def settings(data,config):return {**data['config'],'threshold':config['threshold'],'quantile':config['quantile']}
def scope_budget(default,scope):
    if scope not in SCOPES:raise ValueError('学习范围不受支持')
    return math.ceil(default*SCOPES[scope])
def explanations(data,completed,route,gate):
    rows=[]
    for u in data['units']:
        concepts='、'.join(CONCEPTS.get(c,c) for c in u['concept_ids'])
        deps=[e['unit_id'] for e in u['prerequisites'] if e['hard']]
        needed=[v['id'] for v in data['units'] if any(e['hard'] and e['unit_id']==u['id'] for e in v['prerequisites'])]
        reason='已学习，保留材料覆盖；阅读不等于掌握。' if u['id'] in completed else '为当前任务补充'+concepts+'。'+('先完成关联先修材料。' if deps else '没有额外硬性先修。') if u['id'] in route else '当前路线不需要此单元，由概念证据与任务目标共同核对。'
        rows.append(dict(unit_id=u['id'],concepts=concepts,dependencies=deps,needed_by=needed,reason=reason))
    return rows
def plan(root,data,ledger,config,scope='default',quiz_count=1):
    cfg=settings(data,config);req=request_for_state(data['request'],ledger,cfg)
    costs=personalized_costs(req,data['units'],ledger,cfg,config['alpha'])
    default=math.ceil(sum(costs.values())+config['gamma']+quiz_count*config['quiz_cost'])
    state=dict(completed=[],remaining=[],plan_status='PENDING',plan_history=[],spent=0,learning_spent=0,quiz_spent=0,switch_spent=0,completed_costs={},draft=None,budget=scope_budget(default,scope),default_budget=default,scope=scope,quiz_reserve=quiz_count*config['quiz_cost'],unit_costs=costs,active_seconds=None,timing_status='unknown',plan_pending=True)
    return remaining(root,data,ledger,config,state,'initial')
def remaining(root,data,ledger,config,state,reason):
    cfg=settings(data,config);req=request_for_state(data['request'],ledger,cfg);req['budget']=state['budget']
    old=list(state['remaining'])
    result=remaining_plan(root,req,data['units'],ledger,cfg,completed=state['completed'],reference=old,spent=state['spent'],alpha=config['alpha'],gamma=config['gamma'],options=config['search'])
    audit=route_audit(req,data['units'],result['gate'],result['remaining'],result['unit_costs'],state['completed'],old,config['gamma'],state['spent'])
    if not audit['valid']:raise ValueError('剩余路线验证失败')
    adopted=result['status']=='FEASIBLE';paid=result['switch_cost'] if adopted else 0
    if adopted:
        state['spent']+=paid;state['switch_spent']+=paid
        state['remaining']=result['remaining'];state['unit_costs']=result['unit_costs']
        state['plan_audit']=route_audit(req,data['units'],result['gate'],state['remaining'],result['unit_costs'],state['completed'],state['remaining'],config['gamma'],state['spent'])
        if not state['plan_audit']['valid']:raise ValueError('采用路线后费用验证失败')
    elif result['status']=='NO_FEASIBLE_FOUND':
        state['remaining']=result['remaining'];state['unit_costs']=result['unit_costs'];state['plan_audit']=audit
    state['plan_status']=result['status'];state['plan_pending']=result['status']=='TIMEOUT'
    state['plan_message']='反馈已保存，路线暂未更新，可重试安排。' if result['status']=='TIMEOUT' else '当前范围内未找到完整路线。' if not adopted else '当前安排仍适合。' if old==result['remaining'] and reason!='initial' else '已根据当前证据与范围更新安排。'
    state['missing']=result['missing'];state['route_explanations']=explanations(data,state['completed'],state['remaining'],result['gate'])
    state['plan_history'].append(dict(reason=reason,before=old,after=list(state['remaining']),completed=list(state['completed']),added=[u for u in state['remaining'] if u not in old],retained=[u for u in state['remaining'] if u in old],removed=[u for u in old if u not in state['remaining']],paid_switch_cost=paid,result=result))
    return state
