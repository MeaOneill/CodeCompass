import copy,json,sqlite3
from pathlib import Path
from scripts.A.audit_d07_v3 import audit_case
out=Path('tmp/independent-audit');rows=[];good=None;skip=None
for path in sorted((out/'v3-missing-final').rglob('db.sqlite3')):
    if 'current' in path.parent.name:continue
    with sqlite3.connect(path) as db:
        records=[json.loads(r[0]) for r in db.execute('select value from cases')]
    for s in records:
        if s['actor']!='test_fixture':continue
        result=audit_case(s)
        rows.append(dict(test_directory=path.parent.name,result=result))
        if s['status']=='DONE' and all(a['outcome']=='pass' for a in s['answers']):good=s
        if s['status']=='DONE' and len(s['answers'])==6 and all(a['missing'] for a in s['answers']):skip=s
assert good is not None and skip is not None
assert skip['data']['state']['records']==[] and skip['spent']==11 and all(a['outcome'] is None for a in skip['answers'])
challenges=[]
for change in ['control_budget','ledger_scope','completed_prefix']:
    s=copy.deepcopy(good)
    if change=='control_budget':s['no_feedback']['Ours']['audit']['total_if_executed']-=1
    elif change=='ledger_scope':s['data']['state']['records'][-1]['project']='other-project'
    else:s['completed']=[]
    rejected=False
    try:audit_case(s)
    except ValueError:rejected=True
    assert rejected;challenges.append(dict(change=change,rejected=True))
result=dict(passed=True,cases=len(rows),all_skip_zero_ledger=True,all_skip_spent=11,rows=rows,tamper_rejected=challenges)
(out/'v3-audit-ready-final.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(passed=True,cases=len(rows),all_skip_zero_ledger=True,tamper_rejected=len(challenges))))
