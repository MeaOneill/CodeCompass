import copy,json
from pathlib import Path
from unittest.mock import patch
import codecompass.app.pilot_d07_v3 as module
from scripts.A.cases_d07 import Clock
root=Path('C:/CodeCompass/CodeCompass-A-D05');out=Path('tmp/independent-audit');rows=[]
def stored(p,sid):
    with p.connect() as db:return json.loads(db.execute('select value from cases where id=?',(sid,)).fetchone()[0])
for stage,fault in [('history','TIMEOUT'),('history','exception'),('diagnosis','TIMEOUT'),('diagnosis','exception'),('no_feedback','TIMEOUT')]:
    p=module.Pilot(root,out/('v3-final-'+stage+'-'+fault+'.db'),actor='test_fixture',clock=Clock());v=p.create(True)
    choices=[q['answer'] for q in p.items[:5]]
    if stage!='history':v=p.action(v['id'],'history',dict(read=True,choices=choices))
    real_remaining=module.safe_remaining;calls=[0]
    def broken(*args,**kwargs):
        calls[0]+=1
        if stage=='no_feedback' and calls[0]==1:return real_remaining(*args,**kwargs)
        p.clock.t+=3
        if fault=='exception':raise OSError('independent technical failure')
        return dict(status='TIMEOUT')
    action='history' if stage=='history' else 'diagnosis'
    payload=dict(read=True,choices=choices) if stage=='history' else dict(choice=p.items[5]['answer'])
    with patch('codecompass.app.pilot_d07_v3.safe_remaining',side_effect=broken):view=p.action(v['id'],action,payload)
    saved=stored(p,v['id']);accepted=5 if stage=='history' else 6
    assert view['status']=='FAILED' and len(saved['answers'])==accepted and len(saved['data']['state']['records'])==accepted
    assert saved['spent']==5+accepted and saved['completed']==['u_positive_int'] and saved['elapsed']==3
    assert all(a['outcome']=='pass' and not a['missing'] for a in saved['answers'])
    assert saved['events'][-1]['kind']=='planning_failure'
    p.action(v['id'],action,dict(read=True,choices=[None]*5,choice=None))
    unchanged=stored(p,v['id'])==saved
    assert unchanged
    rows.append(dict(stage=stage,fault=fault,status=view['status'],answers_retained=accepted,ledger_retained=len(saved['data']['state']['records']),spent=saved['spent'],elapsed=saved['elapsed'],completed=saved['completed'],last_event=saved['events'][-1]['kind'],changed_retry_rejected=unchanged,source_hashes=saved['provenance']['source_hashes']))
(out/'v3-faults-final.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=True,scenarios=len(rows),all_answers_retained=True,changed_retries_rejected=True),ensure_ascii=False))
