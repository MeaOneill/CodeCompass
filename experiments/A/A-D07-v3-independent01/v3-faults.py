import json
from pathlib import Path
from unittest.mock import patch
from codecompass.app.pilot_d07_v3 import Pilot
from scripts.A.cases_d07 import Clock
root=Path('C:/CodeCompass/CodeCompass-A-D05');out=Path('tmp/independent-audit');rows=[]
def stored(p,sid):
    with p.connect() as db:return json.loads(db.execute('select value from cases where id=?',(sid,)).fetchone()[0])
for stage in ['history','diagnosis']:
    p=Pilot(root,out/('v3-fault-'+stage+'.db'),actor='test_fixture',clock=Clock());v=p.create(True)
    choices=[q['answer'] for q in p.items[:5]]
    if stage=='diagnosis':v=p.action(v['id'],'history',dict(read=True,choices=choices))
    action_payload=dict(read=True,choices=choices) if stage=='history' else dict(choice=p.items[5]['answer'])
    with patch('codecompass.app.pilot_d07_v3.safe_remaining',return_value=dict(status='TIMEOUT')):
        try:p.action(v['id'],stage,action_payload)
        except Exception as exc:error=type(exc).__name__+': '+str(exc)
    s=stored(p,v['id'])
    count_after_failed=len(s['answers']);status_after_failed=s['status'];stage_after_failed=s['stage']
    if stage=='history':retry=p.action(v['id'],stage,dict(read=True,choices=[None]*5))
    else:retry=p.action(v['id'],stage,dict(choice=None))
    final=stored(p,v['id'])
    rows.append(dict(stage=stage,error=error,status_after_failed=status_after_failed,stage_after_failed=stage_after_failed,
        answers_after_failed=count_after_failed,retry_status=retry['status'],retry_answers=len(final['answers']),retry_missing=[a['missing'] for a in final['answers']]))
assert rows[0]['answers_after_failed']==0 and rows[0]['retry_status']=='ACTIVE'
assert rows[1]['answers_after_failed']==5 and rows[1]['retry_status']=='DONE'
(out/'v3-faults.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(rows,ensure_ascii=False,indent=2))
