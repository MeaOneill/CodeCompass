"""Labelled B1 transport fixtures and independent hand-count checks; no API."""
import argparse
import copy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from scripts.A.cases_d04 import mechanism_cases
from scripts.B.run_d04 import save
from scripts.B.comparison.adapters import invoke,public_packet
from scripts.B.comparison.metrics import evaluate,aggregate
from scripts.B.comparison.b1 import SpendMeter
import json


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
    if not a.run_id.replace('-','').replace('_','').isalnum():p.error('Invalid run ID')
    out=ROOT/'experiments/B'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    c=json.loads((ROOT/'configs/B/D04_comparison.json').read_text(encoding='utf-8'))
    c['b1'].update(enabled=True,model='fixture-model-snapshot',budget_usd=1,per_call_reservation_usd=.1,
                   input_usd_per_million=1,output_usd_per_million=2,price_source='FIXTURE_NOT_REAL_PRICE')
    f=next(x for x in mechanism_cases() if x['case_id']=='shared');f['config']['routes']={'shared':['s','a','b']}
    def response(text,**kw):
        return {'model':'fixture-model-snapshot','status':'completed','usage':{'input_tokens':100,'output_tokens':20},
                'output':[{'type':'message','content':[{'type':'output_text','text':text}]}],**kw}
    valid=response('{"ordered_units":["s","a","b"]}')
    specs=[('one_repair','FEASIBLE',[response('bad JSON'),valid]),
           ('format_exhausted','FORMAT_ERROR',[response('bad JSON')]*2),
           ('illegal_order','ALGORITHM_INVALID',[response('{"ordered_units":["a","s","b"]}')]),
           ('unknown_unit','ALGORITHM_INVALID',[response('{"ordered_units":["invented"]}')]),
           ('timeout','TIMEOUT',[TimeoutError()]),
           ('missing_usage','USAGE_MISSING',[response('x',usage=None)]),
           ('privacy_quarantine','PRIVACY_QUARANTINED',[response('fixture-contact@example.com')])]
    rows=[]
    for name,expected,outputs in specs:
        queue=iter(outputs)
        def transport(*args):
            value=next(queue)
            if isinstance(value,Exception):raise value
            return value
        row,context=invoke(ROOT,f,'B1',c,'EXPLICIT_FIXTURE_TRANSPORT_NOT_A_MODEL',SpendMeter(1),transport=transport)
        assert row['execution_status']==expected,(name,row)
        row.update(challenge=name,is_fixture=True,real_api_calls=0,expected_status=expected)
        save(out/(name+'.json'),row);rows.append(row)
    _,gate,_,_=public_packet(ROOT,f)
    plan={'ordered_units':['a','s','b'],'status':'FEASIBLE','estimated_cost':5,'unmet_constraints':[],
          'coverage':{'required_concept_ids':['x','y'],'covered_concept_ids':['x','y'],'ratio':1}}
    hand=evaluate(f['request'],f['units'],gate,plan)
    assert hand['coverage_tp']==2 and hand['coverage_fn']==0 and hand['hard_violations']==1 and hand['hard_relations_checked']==2
    save(out/'hand_count.json',{'is_fixture':True,'manual_expected':{'coverage_tp':2,'coverage_fn':0,'hard_violations':1,'hard_relations_checked':2,'prerequisite_violation_rate':.5,'source_reference_validity':None},'explanation':'Shared graph s->a and s->b, route a,s,b: a misses s; b has s. Both target concepts present; illegal order remains illegal. No source spans => NA.','actual':hand})
    save(out/'summary.json',{'task':'B-D04','is_fixture':True,'real_api_calls':0,'role':'transport/failure-path verification only; not a model baseline score',
                           'checks':len(rows)+1,'passed':True,'aggregate':aggregate(rows),'exit_code':0})
    print('7个明确夹具调用场景+1个手算检查通过；真实API调用0。')
    return 0


if __name__=='__main__':raise SystemExit(main())
