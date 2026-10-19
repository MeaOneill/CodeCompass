"""Read-only candidate version integrity, never a formal G2 or tag approval."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
REL='configs/frozen/A-D07-runtime-v1/manifest.json'


def audit(root=ROOT):
    root=Path(root).resolve();m=json.loads((root/REL).read_text(encoding='utf-8'));errors=[];checked=0
    for entry in m['files']:
        for rel in (entry['path'],entry['snapshot']):
            p=(root/rel).resolve();checked+=1
            if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:
                errors.append('HASH_OR_SCOPE:'+rel)
    for rel,digest in m['protected_parent_files'].items():
        p=(root/rel).resolve();checked+=1
        if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:
            errors.append('PARENT_CHANGED:'+rel)
    if m['formal_g2_passed'] is not False or m['formal_study_allowed'] is not False or m['formal_tag_created'] is not False:
        errors.append('FORMAL_APPROVAL_FORBIDDEN')
    if m['parameters_changed'] is not False or m['actual_recruitment'] is not None or m['actual_pretesters'] is not None:
        errors.append('UNRECORDED_PROTOCOL_CHANGE')
    if not m['affected_run_scope'] or not m['parent_commit']:
        errors.append('MISSING_LINEAGE')
    return dict(passed=not errors,errors=errors,checked_files=checked,runtime_version=m['runtime_version'],
                formal_g2_passed=False,formal_study_allowed=False,formal_tag_created=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=audit()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result));raise SystemExit(0 if result['passed'] else 1)
