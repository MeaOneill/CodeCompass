"""Audit every D05 configuration, response transaction and result row without search."""
import argparse
import copy
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from codecompass.planner.adaptive_validator import verify_session
from scripts.A.run_d05 import save


def execute(source):
    def load(path):return json.loads(path.read_text(encoding='utf-8'))
    summary=load(source/'summary.json');candidates=load(source/'candidates.json');scan=load(source/'scan_config.json')
    checks=[]
    def check(name,condition):
        checks.append(dict(check=name,passed=bool(condition)))
        if not condition:raise ValueError(name)
    check('no model or learning-effect claim',summary['human_profiles']==0 and not summary['formal_study_ready'] and summary['learning_effect']=='NOT_MEASURED')
    policy=load(source/'probability_policy.json')
    check('uncalibrated production VOI disabled',policy['production_voi']=='DISABLED_NO_REAL_DEV_CALIBRATION')
    for record in load(source/'input_manifest.json'):
        for key in ('path','frozen_copy'):
            check('input/code byte hash '+record[key],hashlib.sha256((ROOT/record[key]).read_bytes()).hexdigest()==record['sha256'])
    grid=list(itertools.product(scan['thresholds'],scan['beam_widths'],scan['alpha_weights'],scan['switch_weights']))
    check('all declared candidate configurations',len(candidates)==len(grid)==32)
    check('candidate values exact',[(c['threshold'],c['beam_width'],c['alpha'],c['gamma']) for c in candidates]==grid)
    case_map={p.parent.name:load(p) for p in (source/'cases').glob('*/input.json')}
    expected={(c['candidate_id'],case,strategy) for c in candidates for case in case_map for strategy in scan['strategies']}
    rows=summary['comparisons'];actual=[(r['candidate_id'],r['case_id'],r['strategy']) for r in rows]
    check('no missing or repeated method/config/case',len(actual)==len(set(actual)) and set(actual)==expected)
    negative=0;cost_rows={};total_events=0
    for row in rows:
        record=load(source/row['raw']);case=case_map[row['case_id']];s=record['session']
        check('no hidden engineering error '+row['raw'],record['error'] is None)
        check('settings retained '+row['raw'],all(record['setting'][k]==row[k] for k in record['setting']))
        check('initial input ledger and materials '+row['raw'],s['initial_request']==case['request'] and s['initial_state']==case['state'] and s['units']==case['units'] and s['quizzes']==case['quizzes'])
        expected_config={**case['config'],'threshold':row['threshold']}
        check('only declared parameter changes '+row['raw'],s['config']==expected_config and s['alpha']==row['alpha'] and s['gamma']==row['gamma'] and s['options']=={'beam_width':row['beam_width']})
        check('same quiz cap/cost/opportunities '+row['raw'],s['max_quizzes']==scan['max_quizzes'] and s['fixed_interval']==scan['fixed_interval'])
        audit=verify_session(ROOT,s);check('independent session replay '+row['raw'],audit['valid'])
        check('summary status and cost '+row['raw'],row['status']==s['status'] and row['total_proxy_cost']==s['spent'] and row['quiz_count']==s['quiz_count'])
        check('summary complete flag '+row['raw'],row['material_coverage_complete']==(s['status']=='FEASIBLE' and not s['plan']['remaining']))
        total_events+=len(s['events'])
        cost_rows[(row['candidate_id'],row['case_id'],row['strategy'])]=row['total_proxy_cost']
        for e in s['events']:
            if e['type']=='diagnostic':
                check('actual outcome only from declared synthetic stream',e['outcome']==case['outcomes'][e['item_id']])
                if case['source_kind']=='fixed_real_source_task' and row['strategy'] in ('voi','no_feedback'):
                    raise ValueError('Uncalibrated production VOI used on real-source case')
    for c,case,strategy in expected:
        if strategy in ('voi','fixed','no_feedback'):
            negative+=cost_rows[(c,case,strategy)]>cost_rows[(c,case,'none')]+1e-9
    with (source/'comparison.csv').open(encoding='utf-8',newline='') as f:table=list(csv.DictReader(f))
    check('CSV retains all rows',len(table)==len(rows))
    for csvrow,row in zip(table,rows):
        check('CSV equals raw row',all(v==('NA' if row[k] is None else str(row[k])) for k,v in csvrow.items()))
    # Outcome-pair policies must choose before their different outcomes are visible.
    for candidate in candidates:
        for strategy in scan['strategies']:
            pair=[load(source/'runs'/candidate['candidate_id']/('diagnostic-'+outcome)/(strategy+'.json')) for outcome in ('pass','fail')]
            check('first selection same before outcome',pair[0]['decisions'][:1]==pair[1]['decisions'][:1])
    # Preserve and reject several concrete accounting/evidence forgeries.
    example=next(load(source/r['raw'])['session'] for r in rows if r['case_id']=='diagnostic-pass' and r['strategy']=='voi' and r['threshold']==.7 and r['quiz_count']==1)
    challenges=[]
    for kind in ('free_quiz','wrong_total','outcome','voi','branch','duration','evidence','completion','certificate','switch'):
        changed=copy.deepcopy(example);event=next(e for e in changed['events'] if e['type']=='diagnostic')
        if kind=='free_quiz':event['quiz_cost']=0
        elif kind=='wrong_total':changed['spent']=0
        elif kind=='outcome':event['outcome']='fail'
        elif kind=='voi':event['decision']['candidates'][0]['voi']=999
        elif kind=='branch':event['decision']['candidates'][0]['branches']['pass']['objective']=0
        elif kind=='duration':changed['quiz_duration_seconds']=0
        elif kind=='evidence':changed['state']['records']=[]
        elif kind=='completion':changed['completed']=[]
        elif kind=='certificate':changed['plan']['certificate']={'old_D04':'invalid'}
        elif kind=='switch':event['paid_switch_cost']+=1
        audit=verify_session(ROOT,changed);challenges.append(dict(kind=kind,rejected=not audit['valid'],errors=audit['errors']))
    check('all accounting/evidence tamper challenges rejected',all(c['rejected'] for c in challenges))
    return dict(engineering_passed=True,checks=checks,runs=len(rows),events=total_events,
                negative_cost_comparisons_retained=negative,tamper_challenges=challenges,
                formal_study_ready=False,independent_human_review='NOT_REVIEWED',model_api_calls=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.run_id.replace('-','').replace('_','').isalnum():p.error('Unsafe run ID')
    output=a.output.resolve()
    if not output.is_relative_to((ROOT/'experiments/A').resolve()) or output.exists():p.error('Unique output inside experiments/A required')
    try:
        result=execute(ROOT/'experiments/A'/a.run_id);result['exit_code']=0
    except Exception as error:
        result=dict(engineering_passed=False,error=repr(error),exit_code=1)
    result['audit_script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save(output,result);print(json.dumps({k:v for k,v in result.items() if k not in ('checks','tamper_challenges')},ensure_ascii=False))
    return result['exit_code']


if __name__=='__main__':raise SystemExit(main())
