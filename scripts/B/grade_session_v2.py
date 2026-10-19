"""Offline evaluator bridge. Never imported by the web app; never runs code there.

Inputs are actual submitted sessions, not fabricated elapsed times. Response keys
must be explicitly provided. Local jobs may contain answers and must stay ignored.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.relay_v2 import RelayCollector
from scripts.B.evaluation.grade_response import grade_response
from scripts.B.evaluation.grade import grade
from scripts.B.score_d06 import final_record
from scripts.B.protocol_d06 import endpoint


def assess(database,sid,job,*,key=None,reviews=()):
    job=Path(job).resolve()
    # Raw submissions and reviewer receipts are local evaluator artifacts only.
    if not job.is_relative_to((ROOT/'tmp').resolve()):raise ValueError('Evaluator jobs must stay under ignored tmp/')
    with sqlite3.connect(f'file:{Path(database).resolve().as_posix()}?mode=ro',uri=True) as db:
        row=db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()
    if not row:raise ValueError('Unknown session')
    s=json.loads(row[0])
    if s['status']!='SUBMITTED' or not s['response']:raise ValueError('A recorded final submission is required')
    job.mkdir(parents=True,exist_ok=False);payload=json.loads(s['response']);tid=s['task_id']
    measurement=dict(status=s['status'],duration_valid=s['duration_valid'],elapsed_seconds=s['elapsed'] if s['duration_valid'] else None)
    if tid in ('task_001','task_002'):
        allowed={'candidate.py','explanation.md','regression_tests.py','patch.diff','commands_and_elapsed.json'}
        files=payload.get('files',{})
        if not isinstance(files,dict) or set(files)-allowed or not all(isinstance(v,str) for v in files.values()):raise ValueError('Invalid patch submission filenames/content')
        folder=job/'submission';folder.mkdir()
        for name,value in files.items():(folder/name).write_text(value,encoding='utf-8',newline='\n')
        auto=grade(tid,folder)
        # Existing rubric checks explanation and reproducibility; independent
        # human receipts bind the exact package, not an agent's own judgment.
        if len(reviews)>2:raise ValueError('Register adjudication separately; no extra votes')
        judgments=[];seen=set()
        for i,review in enumerate(reviews):
            if 'method' in review or review.get('reviewer') in seen:raise ValueError('Distinct method-blind patch reviewers required')
            seen.add(review.get('reviewer'))
            receipt=dict(review,learner_elapsed_seconds=s['elapsed'])
            path=job/f'review-{i}.json';path.write_text(json.dumps(receipt,ensure_ascii=False),encoding='utf-8')
            judged=grade(tid,folder,review=path)
            # Invalid automated submissions do not reach grade() receipt checks.
            if review.get('task_id')!=tid or review.get('submission_hash')!=auto['submission_hash'] or review.get('reviewer_kind')!='human' or not review.get('reviewer') or review.get('blind_to_method') is not True:
                raise ValueError('Exact package-bound human blind review required')
            judgments.append(judged)
        status='SCORED' if auto['success'] is False else 'PENDING';success=auto['success'];reason=auto['status']
        disagree=len(judgments)==2 and judgments[0]['total_score']!=judgments[1]['total_score']
        if auto['success'] is not False and len(judgments)==2:
            if disagree:reason='HUMAN_SCORING_DISAGREEMENT_NEEDS_PREDECLARED_ADJUDICATION'
            elif measurement['elapsed_seconds'] is not None:
                status='SCORED';success=judgments[0]['success'];reason=None
        result=dict(task_id=tid,status=status,reason=reason,automated_score=auto['automated_score'],
            review_count=len(reviews),review_disagreement=disagree,**endpoint(status,success,measurement['elapsed_seconds']))
    else:
        if key is None:raise ValueError('Explicit independent evaluator key required')
        c=RelayCollector(ROOT,database,actor=s['actor'])
        answer=dict(outputs=payload.get('outputs'),source_spans=c.submission_spans(tid,payload.get('references',[])),explanation=payload.get('explanation'))
        path=job/'answer.json';path.write_text(json.dumps(answer,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        auto=grade_response(tid,path,key)
        result=final_record(auto,list(reviews),measurement)
    result.update(evaluator_version='B-D06-session-evaluator-2',input_response_sha256=hashlib.sha256(s['response'].encode()).hexdigest(),
        fixture=s['actor']!='human_manual',formal_participant=False,source_time='server_event_collector',
        elapsed_seconds=measurement['elapsed_seconds'])
    (job/'automated.json').write_text(json.dumps(auto,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (job/'assessment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # No answer text, expected outputs, reviewer identities or method in payload.
    public={k:v for k,v in result.items() if k not in ('key_sha256',)}
    with sqlite3.connect(database) as db:
        db.execute('BEGIN IMMEDIATE')
        current=json.loads(db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()[0])
        if current['response']!=s['response'] or current['status']!='SUBMITTED':raise ValueError('Submission changed while evaluating')
        db.execute('INSERT INTO final_assessments VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET response_hash=excluded.response_hash,value=excluded.value',
            (sid,result['input_response_sha256'],json.dumps(public,ensure_ascii=False)))
    return public


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True)
    p.add_argument('--session',required=True);p.add_argument('--job',type=Path,required=True);p.add_argument('--key',type=Path)
    p.add_argument('--review',action='append',type=Path,default=[]);a=p.parse_args()
    r=assess(a.database,a.session,a.job,key=a.key,reviews=[json.loads(f.read_text(encoding='utf-8')) for f in a.review])
    print(json.dumps({k:r[k] for k in ('task_id','status','success','reason')},ensure_ascii=False))
