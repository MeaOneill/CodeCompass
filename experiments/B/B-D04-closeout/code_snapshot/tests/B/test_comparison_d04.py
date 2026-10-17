import copy
import json
from pathlib import Path
from urllib.error import URLError
import pytest

from scripts.A.cases_d04 import mechanism_cases
from scripts.B.run_d04 import cases
from scripts.B.comparison.adapters import public_packet, invoke
from scripts.B.comparison.b1 import SpendMeter, run_b1, parse_route, inspect_raw
from scripts.B.comparison.metrics import evaluate, aggregate

ROOT = Path(__file__).resolve().parents[2]


def config():
    c = json.loads((ROOT/'configs/B/D04_comparison.json').read_text(encoding='utf-8'))
    c['b1'].update(enabled=True, model='fixture-model-snapshot', budget_usd=1,
                   per_call_reservation_usd=.1, input_usd_per_million=1,
                   output_usd_per_million=2, price_source='EXPLICIT_TEST_RATE_NOT_A_REAL_PRICE')
    return c


def response(text, **kw):
    return {'model': 'fixture-model-snapshot', 'status': 'completed',
            'usage': {'input_tokens': 100, 'output_tokens': 20},
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': text}]}], **kw}


def fixture(name):
    f = next(c for c in mechanism_cases() if c['case_id']==name)
    f['config']['routes'] = {name: [u['id'] for u in f['units']]}
    return f


def test_hand_count_shared_and_zero_denominators():
    f = fixture('shared'); context, gate, source, _ = public_packet(ROOT, f)
    # Hand count: [a,s,b] covers x,y (TP2/FN0); a before s violates 1 of 2 relations.
    plan = {'ordered_units': ['a','s','b'], 'status': 'FEASIBLE', 'estimated_cost': 5,
            'unmet_constraints': [], 'coverage': {'required_concept_ids':['x','y'], 'covered_concept_ids':['x','y'], 'ratio':1}}
    r = evaluate(f['request'], f['units'], gate, plan)
    assert (r['coverage_tp'], r['coverage_fn'], r['coverage_ratio']) == (2,0,1)
    assert (r['hard_violations'], r['hard_relations_checked'], r['prerequisite_violation_rate']) == (1,2,.5)
    assert r['source_reference_validity'] is None and not r['legal']
    plan['ordered_units'] = ['s','a','b']
    assert evaluate(f['request'], f['units'], gate, plan)['prerequisite_violation_rate'] == 0
    f = fixture('empty_goal')
    plan = {'ordered_units': [], 'status':'FEASIBLE','estimated_cost':0,'unmet_constraints':[],
            'coverage':{'required_concept_ids':[],'covered_concept_ids':[],'ratio':None}}
    r = evaluate(f['request'],f['units'],{},plan)
    assert r['coverage_ratio'] is r['prerequisite_violation_rate'] is r['source_reference_validity'] is None


def test_partial_coverage_duplicates_unknown_budget_and_claims():
    f = fixture('cost_gap')
    plan = {'ordered_units':['a'], 'status':'NO_FEASIBLE_FOUND','estimated_cost':2,
            'coverage':{'required_concept_ids':['x','y'],'covered_concept_ids':['x'],'ratio':.5}}
    r = evaluate(f['request'], f['units'], {}, plan)
    assert (r['coverage_tp'],r['coverage_fn'],r['coverage_ratio']) == (1,1,.5)
    for route in [['unknown'],['a','a'],['a','b','c']]:
        bad={**plan,'ordered_units':route}
        assert not evaluate(f['request'],f['units'],{},bad)['legal']


def test_failure_denominator_includes_format_timeout_invalid_not_unconfigured():
    rows=[{'attempted':True,'execution_status':s} for s in ['FEASIBLE','TIMEOUT','FORMAT_ERROR','ALGORITHM_INVALID']]
    rows.append({'attempted':False,'execution_status':'NOT_CONFIGURED'})
    r=aggregate(rows)
    assert (r['scheduled'],r['attempted'],r['failed'],r['failure_rate'],r['not_run'])==(5,4,3,.75,1)
    assert aggregate(rows[-1:])['failure_rate'] is None


def test_all_methods_same_public_context_and_no_answer_payload():
    c=config(); f=next(cases()); hashes=set()
    for method in ['B0','B1','B2','beam']:
        row, context=invoke(ROOT,f,method,c,'fixture prompt',SpendMeter(1),transport=lambda *args:response('{"ordered_units": []}'))
        hashes.add(row['context_hash'])
        assert context['source_materials'] and context['learner_gate']
        assert not set(context['task']) & {'rubric','answer','evaluation_key','solution'}
        assert not set(context['config']) & {'routes'}
    assert len(hashes)==1
    bad=copy.deepcopy(f); bad['request']['task_id']='../../private_evaluation/keys'
    with pytest.raises(ValueError,match='public development'):
        public_packet(ROOT,bad)


def test_real_source_counts_and_tampered_span_rejected():
    f=next(cases()); c=config()
    row,_=invoke(ROOT,f,'B0',c,'fixture',SpendMeter(0))
    assert row['metrics']['source_spans_valid']==row['metrics']['source_spans_checked']==3
    assert row['metrics']['source_reference_validity']==1
    assert row['metrics']['prerequisite_violation_rate'] is None
    _,gate,source,_=public_packet(ROOT,f)
    bad=copy.deepcopy(f['units']);bad[0]['source_spans'][0]['content_hash']='0'*64
    m=evaluate(f['request'],bad,gate,row['plan'],source)
    assert not m['legal'] and m['source_spans_valid']==2


def test_b1_one_format_repair_logs_original_and_all_costs():
    outputs=iter([response('not JSON'),response('{"ordered_units": ["s", "a", "b"]}')])
    c=config()['b1']; result=run_b1({'x':1},c,'fixture',SpendMeter(1),transport=lambda *a:next(outputs))
    assert result['status']=='PARSED' and len(result['calls'])==2 and result['transport_is_fixture']
    assert result['calls'][0]['response']['output'][0]['content'][0]['text']=='not JSON'
    assert sum(x['estimated_cost_usd'] for x in result['calls'])==pytest.approx(.00028)
    assert 'FORMAT_ONLY_REPAIR' in result['calls'][1]['request']['input']
    assert all(c['elapsed_seconds']>=0 and c['billing_cost_usd'] is None for c in result['calls'])


@pytest.mark.parametrize('text', ['[]','{"ordered_units": "a"}','{"ordered_units":[],"extra":true}'])
def test_bad_format_stops_after_one_repair(text):
    result=run_b1({},config()['b1'],'fixture',SpendMeter(1),transport=lambda *a:response(text))
    assert result['status']=='FORMAT_ERROR' and len(result['calls'])==2


def test_semantically_illegal_b1_gets_no_repair_and_is_retained():
    row,_=invoke(ROOT,fixture('shared'),'B1',config(),'fixture',SpendMeter(1),transport=lambda *a:response('{"ordered_units":["a","s","b"]}'))
    assert row['execution_status']=='ALGORITHM_INVALID' and row['format_repairs']==0
    assert row['metrics']['hard_violations']==1 and row['plan']['ordered_units']==['a','s','b']


@pytest.mark.parametrize('error', [TimeoutError(), URLError(TimeoutError())])
def test_timeout_keeps_call_and_unknown_billing(error):
    def fail(*a):raise error
    r=run_b1({},config()['b1'],'fixture',SpendMeter(1),transport=fail)
    assert r['status']=='TIMEOUT' and r['attempted'] and len(r['calls'])==1
    assert r['calls'][0]['estimated_cost_usd'] is None


def test_no_configuration_no_call_and_batch_budget_reservation():
    def forbidden(*a):raise AssertionError('must not call')
    c=config()['b1']; c['enabled']=False
    r=run_b1({},c,'fixture',SpendMeter(1),transport=forbidden)
    assert not r['attempted'] and r['status']=='NOT_CONFIGURED'
    c['enabled']=True;meter=SpendMeter(.1)
    r=run_b1({},c,'fixture',meter,transport=lambda *a:response('bad format'))
    assert r['status']=='BUDGET_EXHAUSTED' and len(r['calls'])==1
    r=run_b1({},c,'fixture',meter,transport=forbidden)
    assert r['status']=='BUDGET_NOT_RUN' and not r['attempted']


@pytest.mark.parametrize('raw,status',[(response('{"ordered_units":[]}',model='other-model'),'MODEL_MISMATCH'),
    (response('x',usage=None),'USAGE_MISSING'),(response('x',status='incomplete'),'API_INCOMPLETE')])
def test_unknown_usage_model_and_incomplete_not_success(raw,status):
    r=run_b1({},config()['b1'],'fixture',SpendMeter(1),transport=lambda *a:raw)
    assert r['status']==status and len(r['calls'])==1


def test_privacy_quarantine_no_raw_secret_export():
    r=run_b1({},config()['b1'],'fixture',SpendMeter(1),transport=lambda *a:response('email: person@example.com'))
    assert r['status']=='PRIVACY_QUARANTINED'
    assert 'person@example.com' not in json.dumps(r)


def test_saved_metric_tamper_rejected():
    from scripts.B.audit_d04 import audit_rows
    f=fixture('shared');row,_=invoke(ROOT,f,'B2',config(),'fixture',SpendMeter(0))
    audit_rows(ROOT,[row],{'shared':f})
    for key,value in [('coverage_ratio',0),('hard_relations_checked',0),('source_spans_checked',100),('replayed_proxy_cost',0)]:
        bad=copy.deepcopy(row);bad['metrics'][key]=value
        with pytest.raises(AssertionError,match='metric'):
            audit_rows(ROOT,[bad],{'shared':f})
