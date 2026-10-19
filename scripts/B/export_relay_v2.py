"""Deidentified observations plus separately bound independent assessments."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.B.export_d05 import export,save


def export_assessed(database,out,actor):
    out=Path(out)
    # Single source snapshot: prevent grading or a new session between exports.
    with sqlite3.connect(f'file:{Path(database).resolve().as_posix()}?mode=ro',uri=True) as db:
        db.execute('BEGIN')
        raw=[json.loads(r[0]) for r in db.execute('SELECT value FROM sessions ORDER BY id')]
        # Existing collector uses rollback journal mode. The acquired read lock
        # prevents commits until the matching observation export finishes.
        if db.execute('PRAGMA journal_mode').fetchone()[0].lower() not in ('delete','truncate','persist'):
            raise ValueError('Export requires rollback journal read-lock semantics; take an offline backup for WAL databases')
        counts=export(database,out,actor)
        sessions=json.loads((out/'sessions.json').read_text(encoding='utf-8'))
        raw=[s for s in raw if s['actor']==actor]
        if len(raw)!=len(sessions):raise ValueError('Session set changed during export; discard this bundle and export to a fresh path')
        rows=[]
        for s,anon in zip(raw,sessions):
            response_hash=hashlib.sha256(s['response'].encode()).hexdigest() if s['response'] else None
            if (s['task_id'],s['method'],response_hash)!=(anon['task_id'],anon['method'],anon['response_sha256']):raise ValueError('Source/export snapshot mismatch')
            row=db.execute('SELECT response_hash,value FROM final_assessments WHERE id=?',(s['id'],)).fetchone()
            value=json.loads(row[1]) if row and row[0]==response_hash else None
            rows.append(dict(session_id=anon['session_id'],participant=anon['participant'],task_id=s['task_id'],method=s['method'],
                input_response_sha256=response_hash,assessment=value,assessment_missing=value is None,actor=actor,formal_participant=False))
    save(out/'assessments.json',rows)
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    manifest['files']['assessments.json']=hashlib.sha256((out/'assessments.json').read_bytes()).hexdigest()
    manifest['assessment_policy']='Separate bound independent results; raw session observations are not rewritten. Missing reviews remain pending.'
    save(out/'manifest.json',manifest)
    return dict(**counts,assessment_records=sum(r['assessment'] is not None for r in rows),formal_outcomes=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--actor',choices=['test_fixture','human_manual','agent_browser'],required=True);a=p.parse_args()
    print(json.dumps(export_assessed(a.database,a.output,a.actor)))
