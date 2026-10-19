import copy
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.B.protocol_d06 import make_schedule,schedule_audit,endpoint
from scripts.B.score_d06 import final_record
from codecompass.app.study_d06 import b2_remaining,StudyCollector
from codecompass.learner import initial_state
from codecompass.planner.core import greedy_plan
from scripts.A.cases_d04 import fixture,unit


@pytest.fixture
def heldout():
    return [t for t in json.loads((ROOT/'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))['tasks'] if t['split']=='test_candidate']


@pytest.mark.parametrize('methods,n',[(('Ours','B1','B2'),12),(('Ours','B1','B2'),18),(('Ours','B2'),6),(('Ours','B2'),10)])
def test_reserved_counterbalancing(heldout,methods,n):
    a=make_schedule(heldout,methods,n);b=make_schedule(heldout,methods,n)
    assert a==b and len(a)==n*len(methods)
    audit=schedule_audit(a,heldout,methods,n)
    assert audit['passed'] and audit['actual_enrolled']==0 and audit['task_method_max_spread']<=1
    assert all(not r['participant_id'] for r in a)


def test_reject_development_in_formal_schedule(heldout):
    heldout[0]['split']='dev'
    with pytest.raises(ValueError):make_schedule(heldout,['Ours','B2'],6)


@pytest.mark.parametrize('status,success,seconds,expected',[
    ('SCORED',True,15,(True,15)),('SCORED',False,15,(False,1500)),('SCORED',True,1501,(False,1500)),
    ('SCORED',True,None,(None,None)),('SCORED',None,12,(None,None)),('TIMEOUT',None,None,(False,1500)),
    ('WITHDRAWN',None,None,(None,None)),('PENDING',None,None,(None,None)),('NOT_STARTED',None,None,(None,None))])
def test_endpoints_no_fake_zero(status,success,seconds,expected):
    r=endpoint(status,success,seconds);assert (r['success'],r['t_cap_seconds'])==expected


@pytest.mark.parametrize('seconds',[-1,float('nan'),True])
def test_invalid_time(seconds):
    with pytest.raises(ValueError):endpoint('SCORED',True,seconds)


def structural():
    case=fixture('B06-completed',[unit('s',['base'],2),unit('a',['x'],12,['s']),unit('b',['y'],4,['s','a'])],['x','y'],25)
    case['state']=initial_state('fixture',is_simulated=True);case['request']['learner_state']=[]
    return case


def test_b2_completed_is_context_not_mastery():
    c=structural();before=copy.deepcopy(c['state'])
    original,_=greedy_plan(c['request'],c['units'],c['state'],c['config'])
    initial=b2_remaining(c['request'],c['units'],c['state'],c['config'])
    assert initial['remaining']==original['ordered_units'] and initial['cost']==original['estimated_cost']
    result=b2_remaining(c['request'],c['units'],c['state'],c['config'],['s'],2)
    assert result['remaining']==['a','b'] and result['cost']==16 and result['replay']['valid']
    assert c['state']==before and not result['gate']['base']['mastered']
    c['request']['budget']=17
    assert b2_remaining(c['request'],c['units'],c['state'],c['config'],['s'],2)['status']=='NO_FEASIBLE_FOUND'


@pytest.mark.parametrize('method',['Ours','B2'])
@pytest.mark.parametrize('tid',['task_001','task_002'])
def test_common_quiz_atomic_and_unskippable(tmp_path,method,tid):
    c=StudyCollector(ROOT,tmp_path/'fixture.sqlite3',actor='test_fixture');s=c.create(tid,method);sid=s['session_id']
    with pytest.raises(ValueError):c.action(sid,'submit',{'response':'skip'})
    s=c.action(sid,'complete_reading');assert s['phase']=='quiz' and len(s['completed'])==1
    with pytest.raises(ValueError):c.action(sid,'complete_reading')
    with pytest.raises(ValueError):c.action(sid,'submit',{'response':'skip quiz'})
    s=c.action(sid,'answer',{'choice':0});assert s['quiz_done'] and s['outcome'] in ('pass','fail')
    assert c.action(sid,'submit',{'response':'fixture'})['success'] is None


def test_static_b1_cannot_impersonate_dynamic(tmp_path):
    c=StudyCollector(ROOT,tmp_path/'fixture.sqlite3',actor='test_fixture')
    with pytest.raises(ValueError):c.create(method='B1_saved')


@pytest.mark.parametrize('scores,expected',[([],None),([2],None),([2,0],None),([2,2],True),([0,0],False)])
def test_blind_score_gate(scores,expected):
    auto=dict(task_id='fixture_only',answer_sha256='fixture_hash',key_sha256='fixture_key_hash',
              outputs_passed=True,source_passed=True,explanation_present=True,automated_score=8)
    reviews=[dict(task_id='fixture_only',answer_sha256='fixture_hash',reviewer_kind='human',reviewer=f'fixture-reviewer-{i}',
                  blind_to_method=True,explanation_score=v) for i,v in enumerate(scores)]
    record=final_record(auto,reviews,dict(elapsed_seconds=20,duration_valid=True,status='SUBMITTED'))
    assert record['success'] is expected and 'fixture-reviewer' not in json.dumps(record)


def test_score_rejects_review_leak_and_repeated_reviewer():
    auto=dict(task_id='f',answer_sha256='h',key_sha256='k',outputs_passed=True,source_passed=True,explanation_present=True,automated_score=8)
    receipt=dict(task_id='f',answer_sha256='h',reviewer_kind='human',reviewer='fixture',blind_to_method=True,explanation_score=2)
    with pytest.raises(ValueError):final_record(auto,[receipt,receipt],{})
    with pytest.raises(ValueError):final_record(auto,[dict(receipt,method='Ours')],{})
