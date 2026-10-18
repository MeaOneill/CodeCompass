"""Deidentified export with participant grouping; no response text or identities."""
import argparse
import csv
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.experiment import digest, VERSION


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')


def export(database,out,actor):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    db=sqlite3.connect(f'file:{Path(database).resolve().as_posix()}?mode=ro',uri=True)
    salt=secrets.token_bytes(32)  # Consistent within bundle; unlinkable across independent exports.
    anon=lambda value:hmac.new(salt,value.encode(),hashlib.sha256).hexdigest()[:24]
    sessions=[];events=[]
    try:
        db.execute('BEGIN') # Single SQLite read snapshot, including event chains.
        for (raw,) in db.execute('SELECT value FROM sessions ORDER BY id'):
            s=json.loads(raw)
            if s['actor']!=actor:continue
            raw_events=[json.loads(r[0]) for r in db.execute('SELECT value FROM events WHERE id=? ORDER BY seq',(s['id'],))]
            previous=None
            for i,e in enumerate(raw_events,1):
                signed={k:v for k,v in e.items() if k!='hash'}
                if e['hash']!=digest(signed) or e['previous_hash']!=previous or e['seq']!=i:
                    raise ValueError('Stored event chain corrupted')
                if any(e[k]!=s[k if k!='session_id' else 'id'] for k in ('session_id','participant','task_id','method','actor')):
                    raise ValueError('Event association mismatch')
                previous=e['hash']
            if previous!=s['last_hash'] or len(raw_events)!=s['seq']:raise ValueError('Incomplete event chain')
            sid=anon(s['id']);pid=anon(s['participant'])
            # Active export is an observation through the last server checkpoint, never a completed duration.
            elapsed=s['elapsed'] if s['duration_valid'] and s['status'] in ('SUBMITTED','TIMED_OUT','WITHDRAWN','FAILED') else None
            missing=list(s['missing'])
            if s['status'] in ('ACTIVE','PAUSED'):missing.append('SESSION_UNFINISHED')
            if s['score_status']!='SCORED':missing.append('FINAL_SCORE_MISSING')
            row=dict(session_id=sid,participant=pid,task_id=s['task_id'],method=s['method'],actor=actor,
                status=s['status'],duration_seconds=elapsed,observed_seconds=s['elapsed'],duration_valid=s['duration_valid'],
                limit_seconds=s['limit_seconds'],success=None,score_status=s['score_status'],missing=missing,
                # Not a success-time endpoint: cannot infer final success from an in-page concept quiz.
                t_cap_seconds=s['limit_seconds'] if s['status']=='TIMED_OUT' and s['duration_valid'] else None,
                quiz_outcome=s['outcome'],response_sha256=hashlib.sha256(s['response'].encode()).hexdigest() if s['response'] else None,
                event_count=len(raw_events),source_commit=s['data']['task']['repo_commit'])
            sessions.append(row);prev=None
            for e in raw_events:
                item=dict(session_id=sid,participant=pid,task_id=s['task_id'],method=s['method'],actor=actor,
                    seq=e['seq'],kind=e['kind'],elapsed_observed=e['elapsed_observed'],duration_valid=e['duration_valid'],
                    status=e['status'],payload=e['payload'],previous_hash=prev)
                item['hash']=digest(item);prev=item['hash'];events.append(item)
        db.rollback()
    finally:db.close()
    if not sessions:raise ValueError('No sessions for requested provenance; empty export not accepted')
    groups=[]
    for pid in sorted({s['participant'] for s in sessions}):
        rows=[s for s in sessions if s['participant']==pid]
        groups.append(dict(participant=pid,sessions=len(rows),methods=sorted({s['method'] for s in rows}),
            completed_submissions=sum(s['status']=='SUBMITTED' for s in rows),scored=0,success_rate=None,
            missing_duration=sum(s['duration_seconds'] is None for s in rows),formal_participant=False))
    save(out/'sessions.json',sessions);save(out/'events.json',events);save(out/'participants.json',groups)
    with (out/'sessions.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(sessions[0]));writer.writeheader()
        for row in sessions:writer.writerow({k:'NA' if v is None else json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in row.items()})
    save(out/'manifest.json',dict(version=VERSION,actor=actor,scope='development_only',clock_source='server UTC + process monotonic',
        pii_removed=['local participant/session token','absolute time','free response','database path'],
        grouping='HMAC pseudonyms stable within this export only; do not combine bundles as new participants',
        formal_study_ready=False,files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file()}))
    return dict(sessions=len(sessions),participants=len(groups),actor=actor)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--actor',choices=['human_manual','agent_browser','test_fixture'],required=True)
    a=p.parse_args();out=a.output.resolve()
    expected={'human_manual':'manual','agent_browser':'agent_browser','test_fixture':'fixtures'}[a.actor]
    if not out.is_relative_to(ROOT/'experiments/B') or expected not in out.parts:p.error('Use experiments/B/<run>/'+expected+'/<unique-export>')
    print(json.dumps(export(a.database,out,a.actor)));return 0


if __name__=='__main__':raise SystemExit(main())
