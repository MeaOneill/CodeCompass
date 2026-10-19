"""Deterministic protocol preparation; no enrollment, answer reads or API calls."""
import argparse
from collections import Counter
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[2]
VERSION='B-D06-protocol-candidate-1'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def csv_file(path,rows,fields=None):
    with Path(path).open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)


def make_schedule(tasks,methods,n,seed=17):
    """Reserved slots, not people. Shuffle method permutations in full blocks.

    Greedy task assignment penalizes imbalance, rejects shared task concepts and
    functions within one participant. Never consumes scores or task outcomes.
    """
    if len(methods) not in (2,3) or len(set(methods))!=len(methods) or type(n) is not int or n<1:
        raise ValueError('Two/three distinct methods and positive planned slots required')
    if any(t['split']!='test_candidate' for t in tasks):raise ValueError('Use held-out candidate pool only')
    rng=random.Random(seed);orders=list(itertools.permutations(methods));sequence=[]
    while len(sequence)<n:
        block=list(orders);rng.shuffle(block);sequence.extend(block)
    combos=[]
    for combo in itertools.permutations(tasks,len(methods)):
        concepts=[set(t['required_concept_ids']) for t in combo];functions=[set(t['functions']) for t in combo]
        if all(not(concepts[i]&concepts[j] or functions[i]&functions[j]) for i in range(len(combo)) for j in range(i)):
            combos.append(combo)
    if not combos:raise ValueError('Insufficient nonoverlapping task candidates')
    rng.shuffle(combos);method_task=Counter();task_position=Counter();total=Counter();rows=[]
    for i,order in enumerate(sequence[:n]):
        def imbalance(combo):
            # Increment in sum of squared counts. No difficulty/performance tuning.
            return sum(4*(2*method_task[(m,t['task_id'])]+1)+
                (2*task_position[(p,t['task_id'])]+1)+(2*total[t['task_id']]+1)
                for p,(m,t) in enumerate(zip(order,combo)))
        chosen=min(combos,key=imbalance)
        for p,(m,t) in enumerate(zip(order,chosen),1):
            method_task[(m,t['task_id'])]+=1;task_position[(p-1,t['task_id'])]+=1;total[t['task_id']]+=1
            rows.append(dict(slot_id=f'SLOT-{i+1:03d}',participant_id='',pair_id=f'PAIR-{i+1:03d}',
                period=p,method=m,task_id=t['task_id'],split='test_candidate',assignment_status='RESERVED_NOT_ENROLLED',seed=seed))
    return rows


def schedule_audit(rows,tasks,methods,n):
    by_id={t['task_id']:t for t in tasks};errors=[];k=len(methods)
    counts=Counter((r['period'],r['method']) for r in rows)
    for i in range(1,n+1):
        rs=[r for r in rows if r['slot_id']==f'SLOT-{i:03d}']
        if len(rs)!=k or {r['method'] for r in rs}!=set(methods) or len({r['task_id'] for r in rs})!=k:
            errors.append('participant route/method coverage')
        if any(r['participant_id'] or r['assignment_status']!='RESERVED_NOT_ENROLLED' for r in rs):errors.append('fabricated enrollment')
        for a,b in itertools.combinations(rs,2):
            if set(by_id[a['task_id']]['required_concept_ids'])&set(by_id[b['task_id']]['required_concept_ids']):errors.append('concept overlap')
            if set(by_id[a['task_id']]['functions'])&set(by_id[b['task_id']]['functions']):errors.append('function overlap')
    spread=max(counts.values())-min(counts.get((p,m),0) for p in range(1,k+1) for m in methods)
    if spread>1:errors.append('method period imbalance')
    task_method=[dict(task_id=t['task_id'],**{m:sum(r['task_id']==t['task_id'] and r['method']==m for r in rows) for m in methods}) for t in tasks]
    return dict(passed=not errors,errors=errors,planned_slots=n,actual_enrolled=0,method_period_counts={f'{p}:{m}':counts[(p,m)] for p in range(1,k+1) for m in methods},
        task_method_counts=task_method,task_method_max_spread=max(max(t[m] for m in methods)-min(t[m] for m in methods) for t in task_method),
        parallel_difficulty='NOT_HUMAN_CALIBRATED',shared_generic_python_transfer='POSSIBLE_DESPITE_DISJOINT_LISTED_CONCEPTS')


def endpoint(status,success,elapsed,limit=1500):
    """Prespecified endpoint semantics; missing/withdrawn is never zero seconds."""
    if status not in ('SCORED','TIMEOUT','WITHDRAWN','PENDING','NOT_STARTED'):raise ValueError('Unknown result status')
    if success is not None and type(success) is not bool:raise ValueError('Boolean or unknown success required')
    if elapsed is not None and (type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0):raise ValueError('Invalid measured time')
    if status in ('PENDING','WITHDRAWN','NOT_STARTED'):return dict(success=None,t_cap_seconds=None,missing_reason=status)
    if status=='TIMEOUT':return dict(success=False,t_cap_seconds=limit,missing_reason=None)
    if success is None or elapsed is None:return dict(success=None,t_cap_seconds=None,missing_reason='SCORING_OR_TIME_MISSING')
    actual_success=success and elapsed<=limit
    return dict(success=actual_success,t_cap_seconds=min(elapsed,limit) if actual_success else limit,missing_reason=None)


def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    catalog=json.loads((ROOT/'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    tasks=catalog['tasks'];test=[t for t in tasks if t['split']=='test_candidate']
    for n,methods,name in [(12,['Ours','B1','B2'],'three_12'),(18,['Ours','B1','B2'],'three_18'),(6,['Ours','B2'],'two_6'),(10,['Ours','B2'],'two_10')]:
        rows=make_schedule(test,methods,n);csv_file(out/(name+'.csv'),rows)
        save(out/(name+'_audit.json'),schedule_audit(rows,test,methods,n))
    inventory=[]
    for split,module,planned in [('dev','iterutils',8),('test_candidate','strutils',16)]:
        ts=[t for t in tasks if t['split']==split]
        inventory.append(dict(split=split,module=module,planned=planned,actual_specs=len(ts),
            human_reviewed=sum(bool(t.get('human_reviewer')) for t in ts),pilot_validated=0,formally_frozen=0,
            patch_tasks=sum(t['task_type']=='local_modification' for t in ts),task_types=dict(Counter(t['task_type'] for t in ts))))
    save(out/'inventory.json',dict(version=VERSION,repository_count=len({t['repo_url'] for t in tasks}),rows=inventory,
        actual_specs=len(tasks),planned_specs=24,formal_tasks=0,scope='one repository, iterutils dev / strutils held-out candidates; not cross-repo generalization'))
    csv_file(out/'inventory.csv',[{k:json.dumps(v,ensure_ascii=False) if isinstance(v,dict) else v for k,v in row.items()} for row in inventory])
    specs=[{k:t[k] for k in ('task_id','split','repo_url','repo_commit','module','functions','task_type','required_concept_ids','time_limit_minutes','success_rule','review_status')} for t in tasks]
    save(out/'task_specifications.json',specs)
    key=ROOT/'private_evaluation/B-D02/keys.json';receipt=json.loads((ROOT/'benchmarks/B/private_key_manifest.json').read_text(encoding='utf-8'))
    key_matches=key.is_file() and sha(key)==receipt['sha256']
    private=ROOT/'private_evaluation/B-D06/v0.1-candidate'
    private.mkdir(parents=True,exist_ok=False)
    if key_matches:
        (private/'keys.json').write_bytes(key.read_bytes()) # Byte copy only; never parse answers or expose them.
        (private/'rubric_catalog.json').write_bytes((ROOT/'benchmarks/B/task_catalog.json').read_bytes())
    public_files=['benchmarks/B/task_catalog.json','benchmarks/B/private_key_manifest.json','scripts/B/evaluation/grade.py',
        'scripts/B/evaluation/grade_response.py','scripts/B/evaluation/worker.py','src/codecompass/app/diagnostic_items.py',
        'benchmarks/sources/boltons_B_D02/snapshot.json']
    # Some historical snapshot names differ; use the real source receipt only.
    public_files=[p for p in public_files if (ROOT/p).is_file()]
    save(out/'seal_manifest.json',dict(version=VERSION,formal_freeze=False,status='SEALED_CANDIDATE_NOT_FORMAL',
        source_base_sha='72c0922369d5ef31c4803974dda8965761ca72dd',files=[dict(path=p,sha256=sha(ROOT/p)) for p in public_files],
        private_key=dict(sha256=receipt['sha256'],verified_local=key_matches,task_ids=receipt['task_ids'],
            shared_storage=False,storage='ignored private_evaluation/B-D06/v0.1-candidate; B evaluator only; explicit restricted transfer not configured'),
        human_reviews=[],scoring_disagreements=[],disagreement_status='NOT_REVIEWED; empty list is not agreement',
        source_module_review='NOT_HUMAN_REVIEWED',freeze_tag=None))
    return dict(specs=len(tasks),dev=sum(t['split']=='dev' for t in tasks),test_candidates=len(test),private_key_hash_matches=key_matches,
        schedules=4,actual_enrollment=None,formal_freeze=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    print(json.dumps(build(a.output),ensure_ascii=False))
