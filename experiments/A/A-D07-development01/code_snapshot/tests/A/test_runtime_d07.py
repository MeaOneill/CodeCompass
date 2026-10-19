import copy
from pathlib import Path

import pytest

from codecompass.app.relay_v2 import RelayCollector
from codecompass.planner.runtime_d07 import safe_remaining,validate_method_result
from codecompass.planner.feedback import start_session,complete_next,apply_feedback
from scripts.A.cases_d07 import (Clock,stored,b1_config,fixture_transport,empty_transport,
                                development_case,add_history)
from scripts.A.relay_d07 import StableRelayCollector
from scripts.B.comparison.b1 import SpendMeter

ROOT=Path(__file__).resolve().parents[2]


def plan(d,**kw):return safe_remaining(ROOT,d['request'],d['units'],d['state'],d['config'],**kw)


def test_cold_start_evidence_source_and_foreign_project():
    d=development_case(ROOT)
    a=plan(d)
    assert a['feasible'] and a['learning_cost']==80
    assert all(r['source_versions'][0]['commit']==d['task']['repo_commit'] for r in a['route_explanations'])
    assert all(r['source_spans'] for r in a['route_explanations'])
    foreign=add_history(d,['python.iterator_protocol'],10,project='other-project-similar-name')
    same=add_history(d,['python.iterator_protocol'],10)
    similar=add_history(d,['python.iterator_protocol.v2'],10)
    assert plan(foreign)['learning_cost']==plan(similar)['learning_cost']==80
    assert plan(same)['learning_cost']==64


@pytest.mark.parametrize('fault',['wrong_user','duplicate','bad_counts','bad_snapshot','bad_budget'])
def test_invalid_inputs_are_not_feasible(fault):
    d=add_history(development_case(ROOT),['python.iterator_protocol'],1)
    if fault=='wrong_user':d['state']['records'][0]['pseudonymous_user_id']='someone-else'
    elif fault=='duplicate':d['state']['records'].append(copy.deepcopy(d['state']['records'][0]))
    elif fault=='bad_counts':d['request']['learner_state'][0]['alpha']=1000
    elif fault=='bad_snapshot':d['request']['snapshot_id']='other-snapshot'
    else:d['request']['budget']=-1
    result=plan(d)
    assert not result['feasible'] and result['status']=='INVALID_INPUT'
    assert result['human_task_success'] is None


def test_insufficient_budget_and_timeout_are_distinct():
    d=development_case(ROOT);d['request']['budget']=1
    assert plan(d)['status']=='NO_FEASIBLE_FOUND'
    d['request']['budget']=100
    result=plan(d,options={'time_limit_seconds':0})
    assert result['status']=='TIMEOUT' and not result['feasible'] and result['certificate'] is None


@pytest.mark.parametrize('method',['Ours','B2','B1'])
def test_same_complete_goal_guard_for_all_methods(method):
    d=development_case(ROOT)
    session=dict(data=d,method=method,completed=[],spent=0)
    result=validate_method_result(ROOT,session,dict(status='FEASIBLE',route=[],context={}))
    assert result['status']=='ALGORITHM_INCOMPLETE'
    assert not result['acceptance_replay']['goal_complete']


def test_real_defect_empty_B1_not_retried_or_called_success(tmp_path):
    legacy=RelayCollector(ROOT,tmp_path/'old.db',actor='test_fixture',clock=Clock(),
                          b1_config=b1_config(ROOT),meter=SpendMeter(5),transport=empty_transport)
    old=legacy.create(method='B1')
    assert old['status']=='ACTIVE' and legacy.traces(old['session_id'])[0]['status']=='FEASIBLE'
    stable=StableRelayCollector(ROOT,tmp_path/'new.db',actor='test_fixture',clock=Clock(),
                          b1_config=b1_config(ROOT),meter=SpendMeter(5),transport=empty_transport)
    new=stable.create(method='B1');trace=stable.traces(new['session_id'])[0]
    assert new['status']=='FAILED' and trace['status']=='ALGORITHM_INCOMPLETE'
    assert len(trace['details']['calls'])==1 and stable.meter.reserved==.25
    assert new['success'] is None


def test_failed_evidence_repairs_remaining_prefix_without_retuning():
    d=development_case(ROOT)
    concepts=next(u['concept_ids'] for u in d['units'] if u['id']=='u_chunked_iter')
    d=add_history(d,concepts,6)
    s=start_session(ROOT,d['request'],d['units'],d['state'],d['config'],[d['quiz']],strategy='none',max_quizzes=1)
    assert 'u_chunked_iter' not in s['plan']['remaining']
    s=complete_next(s,s['plan']['remaining'][0]);completed=list(s['completed']);before=list(s['plan']['remaining'])
    after=apply_feedback(ROOT,s,d['quiz']['item_id'],'fail',timestamp='2026-10-19T01:00:00+08:00',scheduled=True)
    assert after['completed']==completed and set(after['completed']).isdisjoint(after['plan']['remaining'])
    assert 'u_chunked_iter' in after['plan']['remaining'] and after['plan']['remaining']!=before
    assert after['spent']==s['spent']+1


@pytest.mark.parametrize('method',['Ours','B2','B1'])
def test_same_information_prefix_failure_and_resume(tmp_path,method):
    c=StableRelayCollector(ROOT,tmp_path/'db',actor='test_fixture',clock=Clock(),
                          b1_config=b1_config(ROOT),meter=SpendMeter(5),transport=fixture_transport)
    s=c.create(method=method);sid=s['session_id']
    s=c.action(sid,'complete_reading');prefix=s['completed']
    from codecompass.app.diagnostics_v2 import ITEMS
    wrong=(ITEMS['task_001']['answer']+1)%len(ITEMS['task_001']['choices'])
    s=c.action(sid,'answer',{'choice':wrong})
    assert s['status']=='ACTIVE' and s['outcome']=='fail' and s['completed']==prefix
    assert len(stored(c,sid)['data']['state']['records'])==1
    c.action(sid,'pause')
    resumed=StableRelayCollector(ROOT,c.database,actor='test_fixture',clock=c.clock,
                          b1_config=b1_config(ROOT),meter=c.meter,transport=fixture_transport)
    assert resumed.action(sid,'resume')['completed']==prefix
    assert not set(s['route'])&set(prefix)
    assert c.traces(sid)[1]['acceptance_replay']['goal_complete']


def test_timeout_and_input_rejection_preserve_completed(tmp_path):
    with pytest.raises(ValueError):
        StableRelayCollector(ROOT,tmp_path/'bad',actor='human_manual',test_search_options={'time_limit_seconds':0})
    c=StableRelayCollector(ROOT,tmp_path/'db',actor='test_fixture',test_search_options={'time_limit_seconds':0})
    s=c.create();assert s['status']=='FAILED' and c.traces(s['session_id'])[0]['status']=='TIMEOUT'
    d=development_case(ROOT);d['request']['budget']=-1
    assert plan(d,completed=['u_iterable'])['completed']==['u_iterable']
