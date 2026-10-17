"""Capture verification with expected exits; no configured paid model calls."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from scripts.B.run_d04 import save


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
    if not a.run_id.replace('-','').replace('_','').isalnum():p.error('Invalid run ID')
    out=ROOT/'experiments/B'/a.run_id;out.mkdir(parents=True,exist_ok=False)
    commands=[
        ('pytest',['-m','pytest','-q'],0),
        ('batch',['scripts/B/run_d04.py','--run-id',a.run_id+'-batch'],0),
        ('fixtures',['scripts/B/challenge_d04.py','--run-id',a.run_id+'-fixtures'],0),
        ('B-audit',['scripts/B/audit_d04.py','--source','experiments/B/B-D04-comparison03','--figures','report_materials/B/B-D04-final','--fixtures','experiments/B/B-D04-fixtures01','--output',str((out/'audit.json').relative_to(ROOT))],0),
        ('A04-audit',['scripts/A/audit_d04.py','--run-id','A-D04-mechanism01','--output','experiments/A/'+a.run_id+'-A04.json'],0),
        ('B03-audit',['scripts/B/audit_d03.py','--source','experiments/B/B-D03-integration02','--figures','report_materials/B/B-D03-final','--output',str((out/'B03-audit.json').relative_to(ROOT))],0),
        ('help',['scripts/B/run_d04.py','--help'],0),
        ('invalid-run',['scripts/B/run_d04.py','--run-id','../escape'],2),
        ('pip-check',['-m','pip','check'],0)]
    records=[]
    for label,args,expected in commands:
        started=datetime.now(timezone.utc)
        result=subprocess.run([sys.executable,*args],cwd=ROOT,env={**os.environ,'PYTHONUTF8':'1','PYTHONPATH':str(ROOT/'src')},capture_output=True,encoding='utf-8',timeout=180)
        for stream in ('stdout','stderr'):(out/(label+'.'+stream+'.txt')).write_text(getattr(result,stream),encoding='utf-8',newline='\n')
        records.append({'name':label,'command':[sys.executable,*args],'exit_code':result.returncode,'expected':expected,'passed':result.returncode==expected,'started':started.isoformat(),'elapsed_seconds':(datetime.now(timezone.utc)-started).total_seconds()})
        print(label,result.returncode,'expected',expected,flush=True)
        if label=='A04-audit' and result.returncode==0:
            # A explicitly confines its output to its own folder. B archives only
            # this newly generated, uniquely named file; A inputs stay unchanged.
            (ROOT/'experiments/A'/(a.run_id+'-A04.json')).rename(out/'A04-audit.json')
    passed=all(r['passed'] for r in records)
    save(out/'registration.json',{'task':'B-D04','run_id':a.run_id,'commands':records,'engineering_passed':passed,
         'source_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'B1_live_calls':0,'formal_study_ready':False,'independent_human_review':'NOT_REVIEWED','exit_code':0 if passed else 1})
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
