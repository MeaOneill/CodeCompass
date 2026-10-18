"""Budget, evidence and order-sensitive correctness tests, independent permutation oracle."""
import copy
import itertools
import json
import math
from pathlib import Path
import random

import pytest
from codecompass.learner import update_evidence, planning_rows
from codecompass.planner.adaptive import remaining_plan, switch_distance, request_for_state
from codecompass.planner.feedback import start_session, recommend, apply_feedback, complete_next
from codecompass.planner.diagnostics import probability, evidence_for
from scripts.A.cases_d04 import fixture, unit
from scripts.A.cases_d05 import near_gate_case, quiz

ROOT=Path(__file__).resolve().parents[2]
STAMP='2026-10-18T00:00:00+08:00'


def session(case=None, **kwargs):
    f=case or near_gate_case()
    return start_session(ROOT,f['request'],f['units'],f['state'],f['config'],f['quizzes'],**kwargs)


def test_expected_voi_and_feedback_branches():
    f=near_gate_case(); s=session(f)
    d=recommend(ROOT,s); r=d['candidates'][0]
    assert d['selected']=='D05-new-x'
    assert r['branches']['pass']['remaining']==['s','b']
    assert r['branches']['fail']['remaining']==['s','a','b']
    assert r['voi']==pytest.approx(18-(1+.75*6+.25*18))
    assert s['state']==f['state']  # hypothetical branches never mutate actual ledger


@pytest.mark.parametrize('outcome,expected,cost',[('pass',['s','b'],7),('fail',['s','a','b'],19)])
def test_actual_outcomes_charge_cost_and_keep_negative_result(outcome,expected,cost):
    s=apply_feedback(ROOT,session(), 'D05-new-x',outcome,timestamp=STAMP,duration_seconds=3,duration_is_simulated=True)
    assert s['plan']['remaining']==expected
    while s['plan']['remaining']:
        s=complete_next(s,s['plan']['remaining'][0])
    assert s['spent']==cost and s['quiz_count']==1 and s['quiz_duration_seconds']==3
    assert s['completed']==expected and len(s['state']['records'])==6


def test_unknown_duration_is_not_zero():
    s=apply_feedback(ROOT,session(),'D05-new-x','pass',timestamp=STAMP)
    assert s['quiz_duration_seconds'] is None and not s['duration_complete']


def test_duplicate_evidence_and_item_do_not_charge_again():
    s=apply_feedback(ROOT,session(),'D05-new-x','fail',timestamp=STAMP)
    original=copy.deepcopy(s)
    with pytest.raises(ValueError):
        apply_feedback(ROOT,s,'D05-new-x','pass',timestamp=STAMP,scheduled=True)
    assert s==original
    e=copy.deepcopy(s['observed_state']['records'][-1]);e['evidence_id']='different-id'
    new,decision=update_evidence(s['observed_state'],e,allow_simulated=True)
    assert decision=='DUPLICATE_ITEM' and new==s['observed_state']


def test_no_feedback_observation_dedup_but_no_planning_update():
    s=session(strategy='no_feedback'); before=copy.deepcopy(s['state'])
    s=apply_feedback(ROOT,s,'D05-new-x','pass',timestamp=STAMP)
    assert s['state']==before and len(s['observed_state']['records'])==6
    assert s['plan']['remaining']==['s','a','b'] and s['spent']==1
    assert recommend(ROOT,s)['selected'] is None


def test_fixed_uses_same_cap_and_one_opportunity_per_frequency():
    s=session(strategy='fixed',max_quizzes=1)
    s=apply_feedback(ROOT,s,'D05-new-x','fail',timestamp=STAMP)
    assert recommend(ROOT,s)['selected'] is None
    assert s['quiz_spent']==1


@pytest.mark.parametrize('bad',[None,{'kind':'unverified','p_pass':.99}])
def test_no_reliable_probability_falls_back(bad):
    f=near_gate_case();f['quizzes'][0]['probability']=bad
    s=session(f)
    assert recommend(ROOT,s)['selected'] is None
    assert recommend(ROOT,session(f,strategy='fixed'))['selected']=='D05-new-x'


def test_synthetic_probability_never_used_for_real_source():
    f=near_gate_case()
    p,why=probability(ROOT,f['request'],[dict(f['units'][0],is_fixture=False)],f['quizzes'][0])
    assert p is None and 'REJECTED' in why


def test_calibration_is_public_dev_hash_checked_and_never_private(tmp_path):
    f=near_gate_case();q=f['quizzes'][0]
    q['probability']={'kind':'development_calibration','path':'private_evaluation/secret.json','sha256':'a'*64}
    assert probability(tmp_path,f['request'],f['units'],q)[0] is None
    p=tmp_path/'benchmarks/dev/calibration.json';p.parent.mkdir(parents=True)
    data=dict(split='dev',is_simulated=False,concept_id='x',n=20,passes=15,provenance='test-only-artifact')
    p.write_text(json.dumps(data),encoding='utf-8')
    import hashlib
    q['probability'].update(path='benchmarks/dev/calibration.json',sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    assert probability(tmp_path,f['request'],f['units'],q)[0]==.75
    data['n']=2;p.write_text(json.dumps(data),encoding='utf-8')
    assert probability(tmp_path,f['request'],f['units'],q)[0] is None


def test_branch_timeout_keeps_conservative_decision():
    from codecompass.planner.diagnostics import select_diagnostic
    f=near_gate_case();s=session(f)
    d=select_diagnostic(ROOT,f['request'],f['units'],f['state'],f['state'],f['config'],f['quizzes'],s['plan'],options={'time_limit_seconds':0})
    assert d['selected'] is None
    assert d['candidates'][0]['branches']['pass']['status']=='TIMEOUT'


@pytest.mark.parametrize('field,value',[('cost',-1),('cost',float('nan')),('cost_unit','minutes'),('independent',False)])
def test_invalid_quiz_is_rejected(field,value):
    f=near_gate_case();f['quizzes'][0][field]=value
    with pytest.raises(ValueError):session(f)


def test_zero_quiz_cap_and_expensive_diagnostic():
    assert recommend(ROOT,session(max_quizzes=0))['selected'] is None
    f=near_gate_case();f['quizzes'][0]['cost']=100
    assert recommend(ROOT,session(f))['selected'] is None


def test_nearby_only_and_single_pass_must_open_gate():
    f=near_gate_case();f['quizzes']=[quiz('irrelevant',synthetic_probability=True)]
    assert recommend(ROOT,session(f))['selected'] is None
    f=near_gate_case();f['state']['records']=[]
    f['request']=request_for_state(f['request'],f['state'],f['config'])
    assert recommend(ROOT,session(f))['selected'] is None


def test_completed_prefix_preserved_and_new_prerequisite_costed():
    f=near_gate_case()
    e=evidence_for(f['request'],f['state'],dict(f['quizzes'][0],item_id='sixth-history'),'pass',STAMP)
    f['state'],_=update_evidence(f['state'],e,allow_simulated=True)
    f['request']=request_for_state(f['request'],f['state'],f['config'])
    s=session(f,gamma=2)
    assert s['plan']['remaining']==['s','b']
    s=complete_next(s,'s')
    s=apply_feedback(ROOT,s,'D05-new-x','fail',timestamp=STAMP,scheduled=True)
    assert s['completed']==['s'] and s['plan']['remaining']==['a','b']
    assert s['events'][-1]['added_units']==['a'] and s['switch_spent']>0
    assert s['plan']['switch_cost']==0  # paid switching cannot be charged twice
    assert s['spent']==pytest.approx(2+1+s['switch_spent'])


def test_reading_never_becomes_mastery_and_actual_cost_is_frozen():
    s=session(strategy='none',alpha=.5)
    before=copy.deepcopy(s['state']);cost=s['plan']['unit_costs']['s']
    s=complete_next(s,'s')
    assert s['state']==before and s['spent']==cost
    assert s['plan']['objective']==pytest.approx(sum(s['plan']['unit_costs'][u] for u in s['plan']['remaining']))


def test_switch_distance_distinguishes_identical_sets():
    assert switch_distance(['b','a'],['b','a'],2)==0
    assert switch_distance(['b','a'],['a','b'],2)>0
    f=fixture('ordered',[unit('a',['x'],1),unit('b',['y'],1)],['x','y'],10)
    p=remaining_plan(ROOT,f['request'],f['units'],f['state'],f['config'],reference=['b','a'],gamma=3)
    assert p['remaining']==['b','a'] and p['switch_cost']==0
    assert p['certificate'] is None and not p['optimality_claim']


def test_order_search_against_independent_permutation_oracle():
    rng=random.Random(51019)
    for i in range(24):
        units=[unit(chr(97+j),[rng.choice(['x','y','z'])],rng.randint(0,5)) for j in range(4)]
        f=fixture('oracle-'+str(i),units,['x','y'],rng.randint(1,15))
        reference=['d','b','a'];gamma=2
        feasible=[]
        for n in range(5):
            for route in itertools.permutations([u['id'] for u in units],n):
                by={u['id']:u for u in units};coverage={c for u in route for c in by[u]['concept_ids']}
                pos={u:j for j,u in enumerate(reference)};ret=[pos[u] for u in route if u in pos]
                inv=sum(a>b for j,a in enumerate(ret) for b in ret[j+1:]);adds=sum(u not in pos for u in route)
                obj=sum(by[u]['base_cost'] for u in route)+gamma*(inv+adds)/(3+4)
                if {'x','y'}<=coverage and obj<=f['request']['budget']+1e-9:
                    feasible.append((obj,len(route),route))
        p=remaining_plan(ROOT,f['request'],units,f['state'],f['config'],reference=reference,gamma=gamma,
                         options={'beam_width':256,'candidate_limit':50,'max_expansions':10000})
        if feasible:
            assert p['status']=='FEASIBLE' and (p['objective'],len(p['remaining']),tuple(p['remaining']))==min(feasible)
        else:
            assert p['status']=='NO_FEASIBLE_FOUND'


def test_unsafe_input_and_timeout_never_get_old_exact_certificate():
    f=near_gate_case()
    with pytest.raises(ValueError):
        remaining_plan(ROOT,f['request'],f['units'],f['state'],f['config'],completed=['unknown'])
    p=remaining_plan(ROOT,f['request'],f['units'],f['state'],f['config'],options={'time_limit_seconds':0})
    assert p['status']=='TIMEOUT' and p['certificate'] is None


def test_failed_or_wrong_user_response_is_transactional():
    s=session();old=copy.deepcopy(s)
    with pytest.raises(ValueError):apply_feedback(ROOT,s,'D05-new-x','unscored',timestamp=STAMP)
    with pytest.raises(ValueError):apply_feedback(ROOT,s,'D05-new-x','pass',timestamp='naive-time')
    assert s==old


@pytest.mark.parametrize('strategy',['none','fixed','voi','no_feedback'])
@pytest.mark.parametrize('outcome',['pass','fail'])
def test_independent_session_accounting_replay(strategy,outcome):
    from codecompass.planner.adaptive_validator import verify_session
    s=session(strategy=strategy)
    if recommend(ROOT,s)['selected']:
        s=apply_feedback(ROOT,s,'D05-new-x',outcome,timestamp=STAMP)
    while s['plan']['remaining']:
        s=complete_next(s,s['plan']['remaining'][0])
    result=verify_session(ROOT,s)
    assert result['valid'],result['errors']


@pytest.mark.parametrize('kind',['free_quiz','wrong_total','changed_outcome','lost_completion','wrong_voi','bad_branch','extra_mastery','wrong_duration','certificate','duplicate_material'])
def test_independent_replay_rejects_tampering(kind):
    from codecompass.planner.adaptive_validator import verify_session
    s=apply_feedback(ROOT,session(),'D05-new-x','pass',timestamp=STAMP,duration_seconds=3,duration_is_simulated=True)
    s=complete_next(s,'s')
    if kind=='free_quiz':s['events'][0]['quiz_cost']=0
    elif kind=='wrong_total':s['spent']=0
    elif kind=='changed_outcome':s['events'][0]['outcome']='fail'
    elif kind=='lost_completion':s['completed']=[]
    elif kind=='wrong_voi':s['events'][0]['decision']['candidates'][0]['voi']=999
    elif kind=='bad_branch':s['events'][0]['decision']['candidates'][0]['branches']['pass']['objective']=0
    elif kind=='extra_mastery':s['state']['records']=[]
    elif kind=='wrong_duration':s['quiz_duration_seconds']=0
    elif kind=='certificate':s['plan']['certificate']={'pretend':'D04 proof'}
    elif kind=='duplicate_material':s['events'].append(copy.deepcopy(s['events'][-1]))
    assert not verify_session(ROOT,s)['valid']
