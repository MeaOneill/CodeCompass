"""Explicit mechanism fixtures; no human responses or upstream gold answers."""
from codecompass.learner import initial_state,planning_rows,update_evidence
CONFIG={'version':'D04-mechanism-v1','threshold':.7,'quantile':.1}

def unit(uid,concepts,cost=1,deps=()):
    return {'schema_version':'1.0.0','object_type':'LearningUnit','is_fixture':True,'id':uid,'concept_ids':list(concepts),'source_spans':[],'base_cost':cost,'cost_unit':'proxy_cost','cost_basis':'explicit structural fixture proxy; not minutes','provenance':{'kind':'fixture','evidence':['fixture-only:mechanism'],'proposed_by':'Codex Agent A','review_status':'pending','reviewer':None,'confidence':None},'prerequisites':[{'unit_id':p,'relation_type':'teaching_prerequisite','hard':True,'provenance':{'kind':'fixture','review_status':'approved','reviewer':'SYNTHETIC_REVIEW_NOT_A_PERSON','proposed_by':'Codex Agent A','confidence':None,'evidence':['fixture-only:structural-constraint']}} for p in deps]}

def fixture(name,units,goals,budget=100,mastered=()):
    state=initial_state('simulation-D04',is_simulated=True)
    for c in mastered:
        for i in range(10):
            e={'evidence_id':f'{c}:{i}','item_id':f'{c}:{i}','concept_id':c,'timestamp':'2026-10-16T00:00:00+08:00','project':'synthetic-D04','pseudonymous_user_id':state['pseudonymous_user_id'],'is_fixture':True,'independent':True,'evidence_type':'independent_quiz','outcome':'pass'}
            state,_=update_evidence(state,e,allow_simulated=True)
    request={'schema_version':'1.0.0','object_type':'PlanningRequest','is_fixture':True,'request_id':name,'snapshot_id':'synthetic-D04','task_id':name,'learner_state':planning_rows(state,'synthetic-D04',allow_simulated=True),'budget':budget,'cost_unit':'proxy_cost','config_version':CONFIG['version'],'target_concept_ids':list(goals),'unit_ids':[u['id'] for u in units],'prior_plan_id':None}
    return {'case_id':name,'is_simulated':True,'units':units,'request':request,'state':state,'config':CONFIG.copy()}

def mechanism_cases():
    counter=[unit('a',['x'],2),unit('b',['x','y'],5),unit('c',['y'],4)]
    return [
      fixture('shared',[unit('s',['p']),unit('a',['x'],2,['s']),unit('b',['y'],2,['s'])],['x','y'],5),
      fixture('greedy_failure',counter,['x','y'],5),fixture('cost_gap',counter,['x','y'],10),
      fixture('unique_chain',[unit('s',['p']),unit('a',['x'],2,['s'])],['x'],3),
      fixture('cycle',[unit('a',['x'],1,['b']),unit('b',['p'],1,['a'])],['x'],10),
      fixture('cycle_escape',[unit('a',['x'],1,['b']),unit('b',['p'],1,['a']),unit('z',['p'])],['x'],2),
      fixture('budget_short',[unit('a',['x'],2)],['x'],1),fixture('unreachable',[unit('a',['x'])],['missing'],10),
      fixture('mastered',[unit('s',['p'],5),unit('a',['x'],2,['s'])],['x'],2,['p']),
      fixture('zero_cost',[unit('a',['x'],0),unit('b',['y'],0,['a'])],['x','y'],0),
      fixture('fractional',[unit('a',['x'],.1),unit('b',['y'],.2)],['x','y'],.3),
      fixture('ties',[unit('a',['x']),unit('b',['x'])],['x'],1),
      fixture('twelve_units',[unit(f'u{i:02d}',[f'c{i:02d}']) for i in range(12)],[f'c{i:02d}' for i in range(12)],12),
      fixture('empty_goal',[unit('a',['x'])],[],0),
    ]
