"""A-D05 release checks with immutable command logs; offline, no model launcher."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--source-run',default='A-D05-development01');a=parser.parse_args()
    if not all(v.replace('-','').replace('_','').isalnum() for v in (a.run_id,a.source_run)):parser.error('Unsafe run ID')
    out=ROOT/'experiments/A'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    temp=ROOT/'tmp'/a.run_id;temp.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ)
    for key in list(env):
        if any(word in key.upper() for word in ('API_KEY','SECRET','TOKEN','PASSWORD')):env.pop(key)
    env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONPATH=str(ROOT/'src'),TEMP=str(temp),TMP=str(temp))
    py=sys.executable
    commands=[
        ('pip-check',[py,'-m','pip','check'],0),
        ('pytest',[py,'-m','pytest','-q','--basetemp='+str(temp/'pytest')],0),
        ('adaptive-audit',[py,'scripts/A/audit_d05.py','--run-id',a.source_run,'--output',str(out/'adaptive-audit.json')],0),
        ('A04-audit',[py,'scripts/A/audit_d04.py','--run-id','A-D04-mechanism01','--output',str(out/'A04-audit.json')],0),
        ('B04-audit',[py,'scripts/B/audit_d04.py','--source','experiments/B/B-D04-deepseek-live01','--figures','report_materials/B/B-D04-deepseek-live01','--fixtures','experiments/B/B-D04-fixtures01','--output',str(out/'B04-audit.json')],0),
        ('demo-pass',[py,'scripts/A/demo_d05.py','--outcome','pass'],0),
        ('demo-fail',[py,'scripts/A/demo_d05.py','--outcome','fail'],0),
        ('demo-none',[py,'scripts/A/demo_d05.py','--strategy','none'],0),
        ('demo-fixed',[py,'scripts/A/demo_d05.py','--strategy','fixed'],0),
        ('demo-no-feedback',[py,'scripts/A/demo_d05.py','--strategy','no_feedback'],0),
        ('demo-no-probability',[py,'scripts/A/demo_d05.py','--no-probability'],0),
        ('demo-timeout',[py,'scripts/A/demo_d05.py','--time-limit','0'],0),
        ('reject-negative-cost-weight',[py,'scripts/A/demo_d05.py','--alpha','-1'],2),
    ]
    registration=dict(task_id='A-D05',run_id=a.run_id,source_run=a.source_run,machine=platform.node(),owner='成员A',executor='Codex Agent A',
        interpreter=py,python=sys.version,model_id=None,commands=[],
        started_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
        base_or_checkpoint=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,encoding='utf-8').strip(),
        model_api_calls=0,formal_study_ready=False,independent_human_review='NOT_REVIEWED')
    def write():
        (out/'registration.json').write_bytes((json.dumps(registration,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    for name,argv,expected in commands:
        begin=time.perf_counter();result=subprocess.run(argv,cwd=ROOT,env=env,capture_output=True)
        (out/(name+'.stdout.log')).write_bytes(result.stdout);(out/(name+'.stderr.log')).write_bytes(result.stderr)
        registration['commands'].append(dict(name=name,argv=argv,exit_code=result.returncode,expected_exit=expected,
            passed=result.returncode==expected,elapsed_seconds=time.perf_counter()-begin,stdout=name+'.stdout.log',stderr=name+'.stderr.log'))
        write();print(name+': '+str(result.returncode),flush=True)
    registration['engineering_passed']=all(c['passed'] for c in registration['commands'])
    registration['finished_at']=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
    registration['command_logs']=[dict(path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.glob('*.log'))]
    write();return 0 if registration['engineering_passed'] else 1


if __name__=='__main__':raise SystemExit(main())
