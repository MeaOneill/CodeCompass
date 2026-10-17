"""Replay and byte/denominator audit for B's saved exploratory comparison."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
from PIL import Image
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from scripts.B.comparison.adapters import public_packet
from scripts.B.comparison.b1 import digest, cost_policy, parse_route
from scripts.B.comparison.metrics import evaluate,aggregate
from scripts.B.run_d04 import save


def load(p):return json.loads(p.read_text(encoding='utf-8'))


def audit_rows(root,rows,case_map):
    schema=Draft202012Validator(load(root/'report_materials/B/T02_data.schema.json'))
    for row in rows:
        schema.validate(row);case=case_map[row['case_id']]
        context,gate,source,_=public_packet(root,case)
        assert row['context_hash']==digest(context),'context hash'
        if row['plan'] is not None:
            measured=evaluate(case['request'],case['units'],gate,row['plan'],source)
            assert measured==row['metrics'],'independent metric mismatch'
            assert row['execution_status'] != 'FEASIBLE' or measured['legal'],'illegal success'
        else:
            assert row['metrics'] is None,'missing plan with metrics'
        if not row['attempted']:
            assert row['execution_status'] in ('NOT_CONFIGURED','BUDGET_NOT_RUN','INPUT_LIMIT_NOT_RUN'),'invalid not-run'


def audit_live_calls(rows,case_map,config,prompt):
    """Saved responses only: no transport/model execution during audit."""
    currency,prices=cost_policy(config['b1']);total=0;cost=0;unknown_cost=False
    for row in rows:
        if row['method']!='B1' or not row['attempted']:continue
        assert row['B1_trace']['transport_is_fixture'] is False,'mock transport in live result'
        context,_,_,_=public_packet(ROOT,case_map[row['case_id']])
        expected_input=prompt+'\nCONTEXT_JSON\n'+json.dumps(context,ensure_ascii=False,sort_keys=True)
        assert len(row['calls'])<=2,'too many repairs'
        for i,call in enumerate(row['calls']):
            total+=1
            assert call['request_hash']==digest(call['request']),'request hash mismatch'
            assert call['request']['input']==expected_input,'different context or repair help'
            assert call['kind']==('initial' if i==0 else 'format_repair'),'repair record'
            if 'response' not in call:
                assert row['plan'] is None and row['execution_status'] not in ('FEASIBLE','ALGORITHM_INVALID','NO_FEASIBLE_FOUND'),'missing response scored'
                assert call['estimated_cost_'+currency.lower()] is None,'unknown fee filled in'
                unknown_cost=True
                continue
            assert call.get('quarantined') is False,'quarantined response cannot be scored'
            raw=call['response']
            assert hashlib.sha256(json.dumps(raw,ensure_ascii=False).encode()).hexdigest()==call['raw_sha256'],'response hash mismatch'
            assert raw.get('model')==call['model_returned'],'recorded model mismatch'
            assert call['usage']==raw['usage'],'usage changed'
            if not isinstance(raw.get('usage'),dict):
                assert row['plan'] is None and call['estimated_cost_'+currency.lower()] is None,'missing usage scored'
                unknown_cost=True
                continue
            estimate=(raw['usage']['input_tokens']*prices['input']+raw['usage']['output_tokens']*prices['output'])/1e6
            assert call['estimated_cost_'+currency.lower()]==estimate,'fee mismatch'
            cost+=estimate
            text=''.join(p['text'] for item in raw['output'] if item.get('type')=='message' for p in item.get('content',[]) if p.get('type')=='output_text')
            expected_input=expected_input+'\nFORMAT_ONLY_REPAIR: Return {"ordered_units": [string,...]} only. Preserve the intended order. Prior output:\n'+text
        if row['execution_status'] in ('FEASIBLE','ALGORITHM_INVALID','NO_FEASIBLE_FOUND'):
            assert raw['model']==config['b1']['model'],'different model scored'
            assert parse_route(text)==row['plan']['ordered_units'],'recorded route differs from actual model text'
            assert raw['status']=='completed','incomplete response scored'
        estimates=[c['estimated_cost_'+currency.lower()] for c in row['calls']]
        assert row['api_cost_'+currency.lower()]==(None if any(v is None for v in estimates) else sum(estimates)),'row fee mismatch'
    return {'calls':total,'currency':currency,'conservative_token_cost':None if unknown_cost else cost,'known_cost_subtotal':cost,'billing_cost':None}


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--figures',type=Path,required=True);p.add_argument('--fixtures',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.exists():p.error('Do not overwrite audit')
    checks=[]
    def check(name,value):
        checks.append({'check':name,'passed':bool(value)})
        assert value,name
    try:
        source=a.source;summary=load(source/'summary.json');rows=summary['rows']
        for f in load(source/'input_manifest.json'):
            for key in ('path','frozen_copy'):
                check('exact bytes '+f[key],hashlib.sha256((ROOT/f[key]).read_bytes()).hexdigest()==f['sha256'])
        cases={folder.name:load(folder/'input.json') for folder in (source/'cases').iterdir()}
        audit_rows(ROOT,rows,cases);check('24 rows / six cases / four methods',len(rows)==24 and len(cases)==6)
        for case_id,case in cases.items():
            group=[r for r in rows if r['case_id']==case_id]
            check('one result per method '+case_id,sorted(r['method'] for r in group)==['B0','B1','B2','beam'])
            check('same public info '+case_id,len({r['context_hash'] for r in group})==1)
            check('saved public info '+case_id,digest(load(source/'cases'/case_id/'public_context.json'))==group[0]['context_hash'])
        for method in ['B0','B1','B2','beam']:
            check('failure denominator '+method,summary['aggregates'][method]==aggregate([r for r in rows if r['method']==method]))
        config=load(source/'config.json')
        if not config['b1']['enabled']:
            check('B1 not invented',summary['B1_live_calls']==0 and summary['aggregates']['B1']['attempted']==0 and summary['aggregates']['B1']['failure_rate'] is None)
        elif summary['B1_live_calls']:
            fees=audit_live_calls(rows,cases,config,(source/'prompt.txt').read_text(encoding='utf-8'))
            check('real response/usage/route/input/fees replay',fees['calls']==summary['B1_live_calls'])
        with (source/'T02.csv').open(encoding='utf-8',newline='') as f:table=list(csv.DictReader(f))
        check('T02 retains all scheduled rows',len(table)==len(rows))
        indexed={(r['case_id'],r['method']):r for r in rows}
        for row in table:
            original=indexed[(row['case_id'],row['method'])]
            flat={**original,**(original['metrics'] or {})}
            check('CSV metrics equal raw JSON '+row['case_id']+' '+row['method'],
                  all(value==('NA' if flat.get(key) is None else str(flat[key])) for key,value in row.items()))
            if row['execution_status']=='NOT_CONFIGURED':check('NA is not zero '+row['case_id'],row['coverage_ratio']==row['replayed_proxy_cost']=='NA')
        fixture=load(a.fixtures/'summary.json');check('fixture transport not a real model result',fixture['is_fixture'] and fixture['real_api_calls']==0 and fixture['passed'])
        hand=load(a.fixtures/'hand_count.json')
        check('hand-derived independent counts',all(hand['actual'][k]==v for k,v in hand['manual_expected'].items()))
        check('real-source comparison is exploratory',not summary['formal_study_ready'] and summary['human_profiles']==0 and summary['learning_effect']=='NOT_MEASURED')
        for figure in load(a.figures/'figure_manifest.json'):
            check('figure belongs to audited run',figure['run_id']==summary['run_id'])
            for row in figure['files']:check('figure/input '+row['path'],hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256'])
            with Image.open(ROOT/figure['png']) as im:check('300dpi '+figure['figure_id'],all(abs(d-300)<.1 for d in im.info['dpi']))
            svg=ET.parse(ROOT/figure['svg']).getroot();check('native SVG '+figure['figure_id'],bool(svg.findall('{http://www.w3.org/2000/svg}text')) and not svg.findall('.//{http://www.w3.org/2000/svg}image'))
        result={'engineering_passed':True,'checks':checks,'B1_live_comparison':'NOT_RUN' if not config['b1']['enabled'] else 'SEE_RAW_CALLS',
                'formal_study_ready':False,'independent_human_review':'NOT_REVIEWED','exit_code':0}
    except Exception as e:
        result={'engineering_passed':False,'checks':checks,'error':repr(e),'exit_code':1}
    save(a.output,result);print(json.dumps({k:v for k,v in result.items() if k!='checks'},ensure_ascii=False))
    return result['exit_code']


if __name__=='__main__':raise SystemExit(main())
