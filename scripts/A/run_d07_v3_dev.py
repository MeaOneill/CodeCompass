"""Nine preregistered technical outcomes; all explicitly synthetic, no human bank."""
import argparse,csv,copy,datetime,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from codecompass.app.pilot_d07_v3 import Pilot
from scripts.A.audit_d07_v3 import audit_case
from scripts.A.cases_d07 import Clock

def run(run_id):
    if not run_id.replace('-','').isalnum():raise ValueError('Explicit safe run ID')
    out=ROOT/'experiments/A'/run_id;out.mkdir(exist_ok=False)
    tmp=ROOT/'tmp'/run_id;tmp.mkdir(exist_ok=False)
    rows=[];patterns=[('all_pass',None)]+[('wrong_'+str(i),i) for i in range(6)]+[('all_fail','all'),('all_skip','skip')]
    for name,wrong in patterns:
        c=Pilot(ROOT,tmp/(name+'.sqlite3'),actor='test_fixture',clock=Clock());v=c.create(True);answers=[q['answer'] for q in c.items]
        if type(wrong) is int:answers[wrong]=(answers[wrong]+1)%4
        elif wrong=='all':answers=[(a+1)%4 for a in answers]
        elif wrong=='skip':answers=[None]*6
        c.clock.t+=10;v=c.action(v['id'],'history',dict(read=True,choices=answers[:5]));c.clock.t+=7;v=c.action(v['id'],'diagnosis',dict(choice=answers[5]))
        with c.connect() as db:s=json.loads(db.execute('select value from cases').fetchone()[0])
        a=audit_case(s);assert a['passed'] and a['observed_route_change']==(name=='all_pass')
        (out/(name+'.json')).write_text(json.dumps(dict(case=s,audit=a,is_fixture=True),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        rows.append(dict(case=name,status=s['status'],actor=s['actor'],changed=a['observed_route_change'],spent=s['spent'],audit_checks=a['checks'],raw=name+'.json'))
    # Meaningful tampering challenges of the independent accounting audit.
    good=json.loads((out/'all_pass.json').read_text(encoding='utf-8'))['case'];challenges=[]
    for change in ('control_budget','ledger_scope','completed_prefix'):
        bad=copy.deepcopy(good)
        if change=='control_budget':bad['no_feedback']['Ours']['audit']['total_if_executed']-=1
        elif change=='ledger_scope':bad['data']['state']['records'][-1]['project']='other-project'
        else:bad['completed']=[]
        rejected=False
        try:audit_case(bad)
        except (ValueError,AssertionError):rejected=True
        assert rejected;challenges.append(dict(challenge=change,rejected=True))
    with (out/'outcomes.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/'summary.json').write_text(json.dumps(dict(run_id=run_id,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_kind='dirty-source hashes are persisted in every synthetic case; no real participant claims',finished_at=datetime.datetime.now().astimezone().isoformat(),cases=len(rows),changed=sum(r['changed'] for r in rows),unchanged=sum(not r['changed'] for r in rows),checks=sum(r['audit_checks'] for r in rows),challenges=challenges,real_humans=0,new_model_calls=0,formal_G2_passed=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(rows),checks=sum(r['audit_checks'] for r in rows),tamper_rejected=len(challenges))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);run(p.parse_args().run_id)
