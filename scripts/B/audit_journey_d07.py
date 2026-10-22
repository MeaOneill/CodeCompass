"""Independent receipt/ledger/event checks; no planner execution or gold access."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from codecompass.app.experiment import digest
from codecompass.app.journey_d07 import PRETEST,RETEST,VERSION,source_manifest
from codecompass.app.diagnostics_v2 import ITEMS
from codecompass.learner import validate_state


def audit(database,actor):
    errors=[];checks=0
    def check(ok,label):
        nonlocal checks
        checks+=1
        if not ok:errors.append(label)
    bank={q['item_id']:q for q in [*PRETEST,RETEST,*ITEMS.values()]}
    expected_source=digest(source_manifest(ROOT))
    with sqlite3.connect(f'file:{Path(database).resolve().as_posix()}?mode=ro',uri=True) as db:
        db.execute('BEGIN')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'profiles','profile_events','answers','sessions','events','transfers'}<=tables:
            return dict(passed=False,checks=1,errors=['LEGACY_STORAGE_SCHEMA_WITHOUT_ORIGINAL_CHOICE_RECEIPTS'],actor=actor,
                actual_human_people_verified=False,answers_exported=False,formal_G2_passed=False)
        profiles=[json.loads(r[0]) for r in db.execute('SELECT value FROM profiles WHERE actor=?',(actor,))]
        check(bool(profiles),'no records for the requested actor; empty data is not acceptance')
        for p in profiles:
            user=p['user'];ledger=p['ledger'];validate_state(ledger,allow_simulated=actor!='human_manual')
            check(p['source_digest']==expected_source,'source version');check(p['formal_participant'] is False and p['excluded_from_formal_sample'] is True,'pilot exclusion')
            events=[json.loads(r[0]) for r in db.execute('SELECT value FROM profile_events WHERE user=? ORDER BY seq',(user,))];prev=None
            for i,e in enumerate(events,1):
                check(e['seq']==i and e['previous_hash']==prev,'profile event order');check(digest({k:v for k,v in e.items() if k!='hash'})==e['hash'],'profile event hash');prev=e['hash']
            check(bool(events) and events[-1]['hash']==p['last_hash'] and len(events)==p['revision'],'profile tail')
            check(bool(events) and events[-1]['ledger_sha256']==digest(ledger),'ledger binding')
            answers=[json.loads(r[0]) for r in db.execute('SELECT value FROM answers WHERE user=?',(user,))]
            for a in answers:
                check(a['user']==user and a['actor']==actor and a['source_digest']==p['source_digest'],'answer association')
                check(a['hash']==digest({k:v for k,v in a.items() if k!='hash'}),'answer hash')
                q=bank.get(a['item_id']);check(q is not None,'registered independent question')
                if q and a['status']=='SCORED':
                    choice=a['choice'];check(type(choice) is int and 0<=choice<len(q['choices']),'raw choice')
                    expected='pass' if choice==q['answer'] else 'fail';check(expected==a['outcome'],'independent oracle replay')
                elif a['status']!='SCORED':check(a['outcome'] is None,'missing is not failure')
            for e in ledger['records']:
                matches=[a for a in answers if a['item_id']==e['item_id'] and a['status']=='SCORED']
                check(len(matches)==1 and matches[0]['outcome']==e['outcome'],'accepted ledger has exact independent original choice')
            rows=[json.loads(r[0]) for r in db.execute('SELECT value FROM sessions')];sessions=[s for s in rows if s['participant']==user]
            check(len(sessions)<=2,'two-round cap')
            for s in sessions:
                es=[json.loads(r[0]) for r in db.execute('SELECT value FROM events WHERE id=? ORDER BY seq',(s['id'],))];prev=None
                for i,e in enumerate(es,1):
                    check(e['seq']==i and e['previous_hash']==prev and e['hash']==digest({k:v for k,v in e.items() if k!='hash'}),'task event chain')
                    check(e['participant']==user and e['task_id']==s['task_id'] and e['actor']==actor,'task event association');prev=e['hash']
                check(s['last_hash']==prev and s['seq']==len(es),'task tail')
                check(s['spent']<=100 and s['elapsed']>=0,'cost and nonnegative time')
                check(s['success'] is None,'click or quiz is not final success')
            for (raw,) in db.execute('SELECT value FROM transfers WHERE user=?',(user,)):
                t=json.loads(raw);check(t['posterior_copied'] is False and t['mastery_granted'] is False,'no copied mastery')
                source={e['evidence_id'] for e in ledger['records'] if e['project']==t['source_project'] and e['concept_id']==t['concept_id']}
                check(set(t['source_evidence_ids'])<=source,'retained source evidence')
                target=[e for e in ledger['records'] if e['project']==t['target_project']]
                check(all(e['item_id']==t['target_retest_item_id'] and e['evidence_id'] not in source for e in target),'target evidence requires a different retest')
    return dict(passed=not errors,checks=checks,errors=errors,actor=actor,version=VERSION,
        profiles=len(profiles) if actor!='human_manual' else None,actual_human_people_verified=False,
        formal_participants=0,answers_exported=False,private_final_keys_read=False,formal_G2_passed=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--actor',choices=['test_fixture','agent_browser','human_manual'],required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.actor=='human_manual' and not any(a.output.resolve().is_relative_to((ROOT/rel).resolve()) for rel in ('experiments/B/B-D07-human-live01','experiments/B/B-D07-human-guided-v4')):raise ValueError('Human receipt audit stays in the ignored local pilot archive')
    result=audit(a.database,a.actor);a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:result[k] for k in ('passed','checks','errors','actor','actual_human_people_verified')}));raise SystemExit(0 if result['passed'] else 1)
