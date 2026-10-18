"""B-D05 local acceptance capture. No paid model launcher or identity export."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);a=p.parse_args()
    if not a.run_id.replace('-','').replace('_','').isalnum():p.error('safe ID required')
    out=ROOT/'experiments/B'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PYTHONUTF8='1',PYTHONPATH=str(ROOT/'src'),NO_PROXY='127.0.0.1,localhost')
    py=sys.executable;commands=[
        [py,'-m','pytest','-q','--basetemp=tmp/pytest-'+a.run_id],
        [py,'scripts/A/audit_d05.py','--run-id','A-D05-development01','--output','experiments/A/'+a.run_id+'-accept-A.json'],
        [py,'scripts/B/audit_d04.py','--source','experiments/B/B-D04-deepseek-live01','--figures','report_materials/B/B-D04-deepseek-live01','--fixtures','experiments/B/B-D04-fixtures01','--output',str(out/'B04-audit.json')],
        [py,'scripts/B/demo_d05.py','--run-id',a.run_id+'-fixtures'],
        [py,'-m','pip','check'],
    ]
    records=[]
    for i,cmd in enumerate(commands):
        start=datetime.now(timezone.utc).isoformat()
        result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        filename=f'command-{i:02}.txt';(out/filename).write_bytes(result.stdout)
        records.append(dict(command=cmd,exit_code=result.returncode,started_at=start,raw=filename))
        print(f'{i}: exit={result.returncode}',flush=True)
    sources=[*ROOT.glob('src/codecompass/app/*.py'),*ROOT.glob('app/B_D05/*'),*ROOT.glob('scripts/B/*d05.py'),ROOT/'tests/B/test_interface_d05.py']
    files=[]
    for src in sources:
        rel=src.relative_to(ROOT);dst=out/'source_snapshot'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
        files.append(dict(path=rel.as_posix(),sha256=hashlib.sha256(src.read_bytes()).hexdigest()))
    report=dict(run_id=a.run_id,task_id='B-D05',owner='成员B',executor='Codex Agent B',machine=platform.node(),
        actual_date='2026-10-18',planned_date='2026-10-19',code_parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        source_files=files,commands=records,passed=all(r['exit_code']==0 for r in records),
        human_manual_acceptance='SEPARATE_REQUIRED',independent_human_review='NOT_REVIEWED',model_api_calls=0)
    (out/'registration.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
