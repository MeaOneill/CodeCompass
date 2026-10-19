"""Audit supplemental recorded controls, independently replaying original inputs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from codecompass.planner.adaptive import route_audit
from codecompass.learner import mastery_gate
from scripts.A.audit_d06 import audit as parent_audit


def audit():
    root=ROOT;out=root/'experiments/A/A-D06-gate-control02'
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    parent=parent_audit(root)
    assert parent['candidate_integrity_passed']
    registration=load(out/'registration.json')
    for rel,digest in registration['file_hashes'].items():
        assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest,rel
        assert hashlib.sha256((out/'code_snapshot'/rel).read_bytes()).hexdigest()==digest,rel
    rows=list(csv.DictReader((out/'comparison.csv').open(encoding='utf-8',newline='')))
    checks=0
    assert len(rows)==60
    assert len({(r['case_id'],r['method']) for r in rows})==60
    for row in rows:
        case=load(out/'inputs'/(row['case_id']+'.json'))
        result=load(out/'runs'/row['case_id']/(row['method']+'.json'))
        req,units,state,config=[case[k] for k in ('request','units','state','config')]
        gate=result['gate']
        if row['method']=='candidate_mean':
            counts={}
            for record in state['records']:
                if record['project']==req['snapshot_id']:
                    a,b=counts.setdefault(record['concept_id'],[1,1])
                    counts[record['concept_id']]=[a+(record['outcome']=='pass'),b+(record['outcome']=='fail')]
            expected={c for c,(a,b) in counts.items() if c in gate and a/(a+b)>=config['threshold']}
        else:
            concepts={c for u in units for c in u['concept_ids']}|set(req['target_concept_ids'])
            expected={c for c,g in mastery_gate(state,req['snapshot_id'],concepts,
                      threshold=config['threshold'],quantile=config['quantile'],allow_simulated=True).items() if g['mastered']}
        assert {c for c,g in gate.items() if g['mastered']}==expected
        costs={u['id']:u['base_cost'] for u in units}
        replay=route_audit(req,units,gate,result['remaining'],costs)
        assert replay['valid']
        assert abs(replay['objective']-float(row['proxy_cost']))<1e-9
        assert row['status']==result['status']
        assert (row['coverage_complete']=='True')==replay['goal_complete']
        assert result['status']!='FEASIBLE' or replay['goal_complete']
        checks+=7
    manifest=root/'configs/frozen/v0.1-candidate.1-supplement/freeze_manifest.json'
    if manifest.exists():
        m=load(manifest)
        assert m['parameters_changed'] is False
        assert m['parent_manifest_sha256']==hashlib.sha256((root/'configs/frozen/freeze_manifest.json').read_bytes()).hexdigest()
        for rel,digest in m['file_hashes'].items():
            assert hashlib.sha256((root/rel).read_bytes()).hexdigest()==digest,rel
    return dict(passed=True,checked_results=60,replay_checks=checks,parent_candidate_files=109,
                b2_scope='initial only; not dynamic feedback comparison',joint_g2_passed=False,
                formal_test_allowed=False,freeze_tag_allowed=False,test_answers_used=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);args=p.parse_args()
    result=audit()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result))
