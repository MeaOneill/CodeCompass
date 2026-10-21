"""Read-only B-D07 delivery seal audit. No human data, API calls or fake gates."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.A.audit_d07_v3_version import audit as parent_audit
from codecompass.app.journey_d07 import source_manifest
from codecompass.app.experiment import digest


def audit(root=ROOT):
    root=Path(root);m=json.loads((root/'configs/B/B-D07-development-seal/manifest.json').read_text(encoding='utf-8'));errors=[]
    for row in m['files']:
        p=(root/row['path']).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:errors.append('FILE_MISMATCH:'+row['path'])
    if digest(source_manifest(root))!=m['runtime_source_digest']:errors.append('RUNTIME_SOURCE_DIGEST')
    parent=parent_audit(root)
    if not parent['passed']:errors.append('A_PARENT_FREEZE_CHANGED')
    for key in ('formal_G2_passed','formal_study_allowed','formal_freeze'):
        if m[key] is not False:errors.append('UNJUSTIFIED_FORMAL_APPROVAL:'+key)
    return dict(passed=not errors,errors=errors,checked_files=len(m['files']),parent_new_checks=parent['checked_source_snapshot_parent_files'],
        parent_old_checks=parent['old_runtime_audit']['checked_files'],runtime_source_digest=m['runtime_source_digest'],
        technical_delivery_ready=not errors,human_rehearsal_evaluated=False,other_machine_evaluated=False,
        whole_B07_day_passed=None,formal_G2_passed=False,formal_study_allowed=False,
        conclusion='Engineering integrity only; actual pilot/other-machine receipts and cross-review remain separate')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit()
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
    print(json.dumps(r));raise SystemExit(0 if r['passed'] else 1)
