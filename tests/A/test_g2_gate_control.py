import copy
import itertools
import random
from pathlib import Path

import pytest

from codecompass.planner.adaptive import remaining_plan, route_audit
from codecompass.planner.g2_gate_control import mean_plan, mean_gate, gate_plan
from codecompass.learner import update_evidence, planning_rows
from codecompass.planner.g2_candidate import semantic_result
from scripts.A.cases_d04 import fixture,unit
from scripts.A.cases_d05 import development_cases,near_gate_case

ROOT=Path(__file__).resolve().parents[2]


def test_mean_gate_really_differs_before_new_feedback():
    case=near_gate_case('pass');before=copy.deepcopy(case)
    args=[ROOT,*[case[k] for k in ('request','units','state','config')]]
    lower=remaining_plan(*args)
    mean=mean_plan(*args)
    assert not lower['gate']['x']['mastered']
    assert mean['gate']['x']['mastered']
    assert lower['objective']==18 and mean['objective']==6
    assert mean['remaining']==['s','b']
    assert case==before
    assert mean['replay']['goal_complete']


def test_no_evidence_is_not_mastery_even_below_prior_mean():
    case=fixture('unknown',[unit('x',['x'],1)],['x'])
    case['config']['threshold']=.3
    gate=mean_gate(case['state'],case['request'],case['units'],case['config'])
    assert not gate['x']['mastered']


@pytest.mark.parametrize('case',development_cases(),ids=lambda c:c['case_id'])
def test_original_input_oracle_not_reduced_input(case):
    r=mean_plan(ROOT,*[case[k] for k in ('request','units','state','config')])
    costs={u['id']:u['base_cost'] for u in case['units']}
    best=None
    for n in range(len(case['units'])+1):
        for route in itertools.permutations(costs,n):
            audit=route_audit(case['request'],case['units'],r['gate'],route,costs)
            if audit['valid'] and audit['goal_complete']:
                value=(audit['objective'],len(route),route)
                best=value if best is None or value<best else best
    assert best is not None
    assert (r['objective'],len(r['remaining']),tuple(r['remaining']))==best


def test_all_mastered_can_return_empty_route():
    case=fixture('known',[unit('x',['x'],5)],['x'],10,['x'])
    r=mean_plan(ROOT,*[case[k] for k in ('request','units','state','config')])
    assert r['remaining']==[] and r['objective']==0 and r['replay']['goal_complete']


def test_partly_known_multiconcept_prerequisite():
    case=near_gate_case()
    case['units']=[unit('p',['x','y'],100),unit('a',['y'],1),unit('b',['z'],1,['p'])]
    case['request'].update(unit_ids=['p','a','b'],target_concept_ids=['z'],budget=5)
    r=mean_plan(ROOT,*[case[k] for k in ('request','units','state','config')])
    assert r['status']=='FEASIBLE' and r['remaining']==['a','b'] and r['objective']==2


@pytest.mark.parametrize('case',development_cases(),ids=lambda c:c['case_id'])
def test_lower_policy_matches_unchanged_frozen_solver(case):
    args=[ROOT,*[case[k] for k in ('request','units','state','config')]]
    a=semantic_result(remaining_plan(*args));b=semantic_result(gate_plan(*args,gate_policy='lower'))
    a.pop('version');b.pop('version');b.pop('gate_policy')
    assert a==b


def test_random_mixed_gates_against_exhaustive_original_inputs():
    rng=random.Random(61220)
    for index in range(24):
        units=[unit(str(i),rng.sample(['x','y','z'],rng.randint(1,3)),rng.randint(0,6),
                    [str(j) for j in range(i) if rng.random()<.3]) for i in range(4)]
        case=fixture('random-'+str(index),units,rng.sample(['x','y','z'],rng.randint(1,3)),rng.randint(0,12))
        state=case['state']
        for c in ['x','y','z']:
            for j in range(rng.randint(0,7)):
                e=dict(evidence_id=c+str(j),item_id=c+str(j),concept_id=c,outcome=rng.choice(['pass','pass','fail']),
                       timestamp='2026-10-19T00:00:00+08:00',project=case['request']['snapshot_id'],
                       pseudonymous_user_id=state['pseudonymous_user_id'],is_fixture=True,independent=True,
                       evidence_type='independent_quiz')
                state,_=update_evidence(state,e,allow_simulated=True)
        case['state']=state
        case['request']['learner_state']=planning_rows(state,case['request']['snapshot_id'],allow_simulated=True)
        r=mean_plan(ROOT,*[case[k] for k in ('request','units','state','config')],options={'beam_width':256})
        costs={u['id']:u['base_cost'] for u in units};best=None
        for n in range(5):
            for route in itertools.permutations(costs,n):
                replay=route_audit(case['request'],units,r['gate'],route,costs)
                if replay['valid'] and replay['goal_complete']:
                    value=(replay['objective'],len(route),route)
                    best=value if best is None or value<best else best
        if best is None:
            assert r['status']!='FEASIBLE'
        else:
            assert (r['objective'],len(r['remaining']),tuple(r['remaining']))==best
