"""Complete predeclared development scan; synthetic feedback never claims learning effects."""
import argparse
import copy
import csv
import datetime as dt
import hashlib
import itertools
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from scripts.A.cases_d05 import development_cases
from codecompass.planner.feedback import start_session, recommend, apply_feedback, complete_next
from codecompass.planner.adaptive_validator import verify_session


def save(path,value,compact=False):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,ensure_ascii=False,allow_nan=False,indent=None if compact else 2)+'\n').encode('utf-8'))


def execute(out,run_id):
    scan=json.loads((ROOT/'configs/A/D05_scan.json').read_text(encoding='utf-8'))
    cases=development_cases(); rows=[]; settings=[]
    save(out/'scan_config.json',scan)
    # No empirical calibration is available. Declare this before any comparison.
    save(out/'probability_policy.json',dict(production_voi='DISABLED_NO_REAL_DEV_CALIBRATION',
        fixture_probability='Explicit synthetic prior .75; structural mechanism verification only',
        quiz_cost='1 source-line-equivalent proxy unit by development assumption; no time calibration',
        outcomes='synthetic fixed streams; unavailable to selector API; no final answers read',
        human_profiles=0,formal_study_ready=False))
    for case in cases:
        save(out/'cases'/case['case_id']/'input.json',case)
    grid=itertools.product(scan['thresholds'],scan['beam_widths'],scan['alpha_weights'],scan['switch_weights'])
    for index,(threshold,width,alpha,gamma) in enumerate(grid):
        setting=dict(candidate_id=f'c{index:03d}',threshold=threshold,beam_width=width,alpha=alpha,gamma=gamma)
        settings.append(setting)
        for case in cases:
            cfg=copy.deepcopy(case['config']); cfg['threshold']=threshold
            for strategy in scan['strategies']:
                started=time.perf_counter(); error=None; session=None; decisions=[]; audit=None
                try:
                    session=start_session(ROOT,case['request'],case['units'],case['state'],cfg,case['quizzes'],
                        strategy=strategy,alpha=alpha,gamma=gamma,max_quizzes=scan['max_quizzes'],fixed_interval=scan['fixed_interval'],
                        epsilon=scan['epsilon'],options={'beam_width':width})
                    for step in range(len(case['units'])+scan['max_quizzes']+1):
                        if session['status']!='FEASIBLE' or not session['plan']['remaining']:
                            break
                        choice=recommend(ROOT,session); decisions.append(choice)
                        if choice['selected']:
                            # The outcome stream is consulted strictly after the policy chooses.
                            item=choice['selected']; outcome=case['outcomes'][item]
                            session=apply_feedback(ROOT,session,item,outcome,timestamp='2026-10-18T00:00:00+08:00',
                                                   duration_seconds=None,duration_is_simulated=True)
                        else:
                            session=complete_next(session,session['plan']['remaining'][0])
                    audit=verify_session(ROOT,session)
                    if not audit['valid']:
                        raise ValueError('Independent replay: '+repr(audit['errors']))
                except Exception:
                    error=traceback.format_exc()
                elapsed=time.perf_counter()-started
                relative=Path('runs')/setting['candidate_id']/case['case_id']/(strategy+'.json')
                save(out/relative,dict(setting=setting,case_id=case['case_id'],strategy=strategy,session=session,
                                      decisions=decisions,audit=audit,error=error,processing_seconds=elapsed),compact=True)
                status='ERROR' if error else session['status']
                complete=not error and status=='FEASIBLE' and not session['plan']['remaining']
                rows.append(dict(**setting,case_id=case['case_id'],strategy=strategy,source_kind=case['source_kind'],
                    feedback_is_simulated=True,status=status,material_coverage_complete=complete,
                    total_proxy_cost=None if error else session['spent'],learning_proxy_cost=None if error else session['learning_spent'],
                    quiz_proxy_cost=None if error else session['quiz_spent'],switch_proxy_cost=None if error else session['switch_spent'],
                    quiz_count=None if error else session['quiz_count'],diagnostic_duration_seconds=None if error else session['quiz_duration_seconds'],
                    completed=None if error else session['completed'],processing_seconds=elapsed,raw=relative.as_posix(),
                    human_task_success=None,human_minutes=None,production_voi_calibrated=False))
        print('completed '+setting['candidate_id'],flush=True)
    save(out/'candidates.json',settings)
    counts=dict(candidates=len(settings),cases=len(cases),strategies=len(scan['strategies']),runs=len(rows),
                errors=sum(r['status']=='ERROR' for r in rows),nonfeasible=sum(r['status']!='FEASIBLE' for r in rows))
    save(out/'summary.json',dict(run_id=run_id,task_id='A-D05',comparisons=rows,counts=counts,
        human_profiles=0,formal_study_ready=False,learning_effect='NOT_MEASURED',
        production_voi='DISABLED_NO_REAL_DEV_CALIBRATION',is_simulated=True,
        no_candidate_excluded=True,configuration_selection='NONE; all declared candidates retained'))
    with (out/'comparison.csv').open('w',encoding='utf-8',newline='') as stream:
        fields=[k for k in rows[0] if k!='completed'];writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in rows:
            writer.writerow({k:'NA' if row[k] is None else row[k] for k in fields})
    files=[*sorted((ROOT/'src/codecompass/planner').glob('*.py')),*sorted((ROOT/'src/codecompass/learner').glob('*.py')),
           ROOT/'scripts/A/cases_d05.py',ROOT/'scripts/A/run_d05.py',ROOT/'scripts/A/run_d03.py',
           ROOT/'scripts/A/cases_d04.py',ROOT/'tests/A/test_adaptive_d05.py',ROOT/'configs/A/D05_scan.json',
           ROOT/'schemas/contracts-1.1.schema.json',*sorted((ROOT/'benchmarks/dev/D03').glob('*.json')),
           ROOT/'configs/A/D03_common.json',ROOT/'configs/A/D03_profiles.json',ROOT/'benchmarks/sources/boltons/snapshot.json']
    manifest=[]
    for path in files:
        rel=path.relative_to(ROOT);frozen=out/'code_snapshot'/rel
        frozen.parent.mkdir(parents=True,exist_ok=True);frozen.write_bytes(path.read_bytes())
        manifest.append(dict(path=rel.as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),frozen_copy=frozen.relative_to(ROOT).as_posix()))
    save(out/'input_manifest.json',manifest)
    return counts


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);args=parser.parse_args()
    if not args.run_id.replace('-','').replace('_','').isalnum():parser.error('Unsafe run ID')
    out=ROOT/'experiments/A'/args.run_id;out.mkdir(parents=True,exist_ok=False)
    started=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat();begin=time.perf_counter()
    try:
        counts=execute(out,args.run_id);code=0 if counts['errors']==0 else 1;error=None
    except Exception:
        counts={};code=1;error=traceback.format_exc();(out/'failure.log').write_bytes(error.encode('utf-8'))
    save(out/'registration.json',dict(run_id=args.run_id,task_id='A-D05',owner='成员A',executor='Codex Agent A',machine=platform.node(),
        python=sys.version,interpreter=sys.executable,model_id=None,started_at=started,
        finished_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),elapsed_seconds=time.perf_counter()-begin,
        code_commit=None,base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,encoding='utf-8').strip(),
        dirty_code_note='Exact per-file hash/code snapshot identifies uncommitted run implementation',
        command=[sys.executable,*sys.argv],exit_code=code,error=error,counts=counts,model_api_calls=0,formal_study_ready=False))
    print(json.dumps(dict(exit_code=code,counts=counts,error=error),ensure_ascii=False));return code


if __name__=='__main__':raise SystemExit(main())
