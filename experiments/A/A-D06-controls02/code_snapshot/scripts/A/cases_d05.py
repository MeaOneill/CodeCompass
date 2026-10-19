"""Public dev inputs and explicitly synthetic outcomes, never private answer keys."""
import copy
from codecompass.learner import initial_state, update_evidence, planning_rows
from scripts.A.cases_d04 import unit, fixture
from scripts.A.run_d03 import load, make_profile, make_request


def quiz(concept, *, synthetic_probability=False):
    return dict(item_id='D05-new-'+concept, concept_id=concept, independent=True,
                source='public development concept; outcome stream is synthetic, not a learner measurement',
                cost=1.0, cost_unit='proxy_cost',
                cost_basis='fixed development source-line-equivalent proxy assumption; not seconds or calibrated time',
                probability=dict(kind='synthetic_prior',p_pass=.75,source='declared structural-test prior; not empirical calibration') if synthetic_probability else None)


def near_gate_case(outcome='pass'):
    case = fixture('diagnostic-'+outcome,
        [unit('s',['prerequisite'],2),unit('a',['x'],12,['s']),unit('b',['y'],4,['s','a'])], ['x','y'],25)
    state = initial_state('D05-synthetic-learner',is_simulated=True)
    for i in range(5):
        e=dict(evidence_id='history-'+str(i),item_id='history-'+str(i),concept_id='x',outcome='pass',
               timestamp='2026-10-17T00:00:00+08:00',project=case['request']['snapshot_id'],
               pseudonymous_user_id=state['pseudonymous_user_id'],is_fixture=True,independent=True,evidence_type='independent_quiz')
        state,_=update_evidence(state,e,allow_simulated=True)
    case['state']=state; case['request']['learner_state']=planning_rows(state,case['request']['snapshot_id'],allow_simulated=True)
    case.update(quizzes=[quiz('x',synthetic_probability=True)],outcomes={'D05-new-x':outcome},
                source_kind='synthetic_structure',feedback_kind='synthetic_fixed_outcome_stream')
    return case


def development_cases():
    cases=[near_gate_case('pass'),near_gate_case('fail')]
    common=load('configs/A/D03_common.json')
    for tid in ('task_001','task_002'):
        task=load('benchmarks/dev/D03/'+tid+'.json')
        units=[u for u in load('benchmarks/dev/D03/units.json') if u['id'] in task['learning_unit_ids']]
        for profile in load('configs/A/D03_profiles.json')['profiles']:
            state=make_profile(profile,task['snapshot_id'])
            name=tid+'-'+profile['id']
            request=make_request(task,units,state,common,'D05-'+name,budget=160)
            qs=[quiz(c) for c in request['target_concept_ids']]
            cases.append(dict(case_id=name,request=request,units=units,state=state,config=copy.deepcopy(common),
                quizzes=qs,outcomes={q['item_id']:('pass' if i%2==0 else 'fail') for i,q in enumerate(qs)},
                source_kind='fixed_real_source_task',feedback_kind='synthetic_fixed_outcome_stream',is_simulated=True))
    return cases
