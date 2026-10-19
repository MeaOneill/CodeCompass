"""Evaluator-only, blind-to-method response scoring. No app imports this module."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.B.evaluation.grade_response import grade_response
from scripts.B.protocol_d06 import endpoint


def final_record(automated,reviews,measurement):
    """Two real blind reviews required; conflicts are preserved, never averaged."""
    if len(reviews)>2:raise ValueError('Disagreements need a separately registered adjudication receipt, not extra votes')
    answer_hash=automated['answer_sha256'];tid=automated['task_id'];seen=set();scores=[]
    for r in reviews:
        if (r.get('task_id')!=tid or r.get('answer_sha256')!=answer_hash or r.get('reviewer_kind')!='human'
            or not r.get('reviewer') or r.get('blind_to_method') is not True or 'method' in r):
            raise ValueError('Need exact answer-bound method-blind human review')
        if r['reviewer'] in seen:raise ValueError('Distinct reviewers required')
        seen.add(r['reviewer']);v=r.get('explanation_score')
        if type(v) is not int or v not in (0,2):raise ValueError('Explanation score is 0 or 2')
        if v==2 and not automated['explanation_present']:raise ValueError('No explanation to score')
        scores.append(v)
    status='PENDING';success=None;total=None;reason='TWO_BLIND_HUMAN_REVIEWS_REQUIRED'
    if not automated['outputs_passed'] or not automated['source_passed']:
        status='SCORED';success=False;reason='FAILED_INDEPENDENT_AUTOMATED_CRITERIA'
    elif len(scores)>=2 and len(set(scores))>1:
        reason='HUMAN_SCORING_DISAGREEMENT_NEEDS_PREDECLARED_ADJUDICATION'
    elif len(scores)==2:
        total=automated['automated_score']+scores[0];success=total>=9;status='SCORED';reason=None
    seconds=measurement.get('elapsed_seconds') if measurement.get('duration_valid') is True else None
    if measurement.get('status')=='TIMED_OUT':status='TIMEOUT';success=False;reason='DEADLINE'
    elif measurement.get('status')=='WITHDRAWN':status='WITHDRAWN';success=None;reason='WITHDRAWN'
    elif measurement.get('status')!='SUBMITTED':status='PENDING';success=None;reason='FINAL_SUBMISSION_NOT_RECORDED'
    end=endpoint(status,success,seconds)
    return dict(task_id=tid,evaluator_version='B-D06-independent-response-1',answer_sha256=answer_hash,
        key_sha256=automated['key_sha256'],automated_score=automated['automated_score'],total_score=total,
        review_count=len(scores),review_disagreement=len(set(scores))>1,status=status,reason=reason,
        **end,raw_reviewer_identities_exported=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--task',required=True);p.add_argument('--answer',type=Path,required=True)
    p.add_argument('--private-key',type=Path,required=True);p.add_argument('--measurement',type=Path,required=True)
    p.add_argument('--review',action='append',type=Path,default=[]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=grade_response(a.task,a.answer,a.private_key)
    record=final_record(result,[json.loads(f.read_text(encoding='utf-8')) for f in a.review],json.loads(a.measurement.read_text(encoding='utf-8')))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps({k:record[k] for k in ('task_id','status','success','reason')}))
