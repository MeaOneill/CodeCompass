import copy
import itertools
from pathlib import Path

import pytest

from codecompass.planner.adaptive import remaining_plan, route_audit
from codecompass.planner.g2_gate_control import mean_plan, mean_gate
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
