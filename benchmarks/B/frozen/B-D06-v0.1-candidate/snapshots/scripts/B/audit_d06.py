"""Read-only B-D06 candidate audit. Formal G2 gates remain explicit, never invented."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.B.protocol_d06 import make_schedule,schedule_audit


def audit(root=ROOT):
    root=Path(root);errors=[];checks=0
    def check(ok,message):
        nonlocal checks
        checks+=1
        if not ok:errors.append(message)
    folder=root/'docs/protocol/B-D06-v0.1-candidate'
    manifest=json.loads((root/'benchmarks/B/frozen/B-D06-v0.1-candidate/manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        for key in ('path','snapshot'):
            path=(root/entry[key]).resolve()
            if not path.is_relative_to(root.resolve()):check(False,'unsafe path');continue
            check(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],'hash mismatch: '+entry[key])
    check(manifest['formal_freeze'] is False and manifest['private_answers_in_git'] is False,'unjustified formal seal')
    catalog=json.loads((root/'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    tasks=catalog['tasks'];heldout=[t for t in tasks if t['split']=='test_candidate']
    inventories=json.loads((folder/'inventory.json').read_text(encoding='utf-8'))
    check(inventories['actual_specs']==len(tasks)==12,'inventory specs')
    check(len(heldout)==8 and sum(t['split']=='dev' for t in tasks)==4,'4/8 split')
    check(inventories['formal_tasks']==0,'formal task count')
    check(not set(t['module'] for t in tasks if t['split']=='dev')&{t['module'] for t in heldout},'module split leak')
    schedule_reports=[]
    import csv
    for name,n,methods in [('three_12',12,['Ours','B1','B2']),('three_18',18,['Ours','B1','B2']),('two_6',6,['Ours','B2']),('two_10',10,['Ours','B2'])]:
        with (folder/(name+'.csv')).open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        for row in rows:row['period']=int(row['period']);row['seed']=int(row['seed'])
        check(rows==make_schedule(heldout,methods,n),'schedule reproducibility '+name)
        result=schedule_audit(rows,heldout,methods,n);check(result['passed'],'schedule invariants '+name)
        check(result['task_method_max_spread']<=1,'task/method balance '+name);schedule_reports.append(result)
    recruitment=json.loads((folder/'recruitment_status.json').read_text(encoding='utf-8'))
    check(recruitment['confirmed_count'] is None and recruitment['consent_records']==0,'unexpected enrollment evidence')
    seal=json.loads((folder/'seal_manifest.json').read_text(encoding='utf-8'))
    check(not seal['human_reviews'] and seal['disagreement_status'].startswith('NOT_REVIEWED'),'fabricated human agreement')
    private=root/'private_evaluation/B-D06/v0.1-candidate/keys.json'
    private_hash_matches=private.is_file() and hashlib.sha256(private.read_bytes()).hexdigest()==seal['private_key']['sha256']
    blockers=['正式参与人数/自愿同意未确认；预演者排除需实际核对',
        '12规格尚无人类题目/独立rubric与源码教学关系批准；正式题0',
        '8留出候选未接入经审核规划/诊断材料；当前界面仅2道dev题',
        '三方法分支缺动态B1；两方法分支需人数证据和事前双方方案确认',
        'A/B协议批准、main集成及v0.1-protocol-freeze标签尚未完成']
    return dict(candidate_checks_passed=not errors,checks=checks,errors=errors,
        sealed_task_specs=12,formal_tasks=0,formal_reviewers=0,actual_enrollment=recruitment['confirmed_count'],
        private_key_matches_on_this_machine=private_hash_matches,private_key_new_clone_policy='missing key blocks evaluator; protocol/code audit remains replayable',
        schedule_reports=schedule_reports,joint_g2_passed=False,formal_study_allowed=False,freeze_tag_allowed=False,
        software_handoff_ready=not errors,blockers=blockers,independent_human_review='NOT_REVIEWED',model_api_calls=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=audit();a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:result[k] for k in ('candidate_checks_passed','checks','errors','joint_g2_passed','software_handoff_ready','formal_study_allowed')},ensure_ascii=False))
    raise SystemExit(0 if result['candidate_checks_passed'] else 1)
