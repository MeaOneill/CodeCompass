"""Verify this separately authorized development candidate, not a formal freeze."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.A.audit_d07_version import audit as parent_audit

def audit(root=ROOT):
    root=Path(root).resolve();m=json.loads((root/'configs/frozen/A-D07-dev-repair-v3/manifest.json').read_text(encoding='utf-8'));errors=[];checked=0
    for row in m['files']:
        for rel in (row['path'],row['snapshot']):
            p=(root/rel).resolve();checked+=1
            if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:errors.append('SOURCE_OR_SNAPSHOT:'+rel)
    for rel,sha in m['protected_parent_files'].items():
        checked+=1;p=(root/rel).resolve()
        if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:errors.append('PARENT_CHANGED:'+rel)
    cfg=json.loads((root/'configs/A/D07_v3_development.json').read_text(encoding='utf-8'))
    if (cfg['threshold'],cfg['quantile'],cfg['budget'],cfg['alpha'],cfg['gamma'],cfg['history_items'],cfg['new_diagnoses'],cfg['total_item_cap'])!=(.7,.1,100,0,0,5,1,6):errors.append('PROTOCOL_CONSTANT_CHANGED')
    if m['formal_G2_passed'] is not False or m['formal_study_allowed'] is not False or m['protocol_extension_authorized'] is not True:errors.append('APPROVAL_FLAG')
    parent=parent_audit(root)
    if not parent['passed']:errors.append('OLD_FREEZE_CHANGED')
    return dict(passed=not errors,errors=errors,checked_source_snapshot_parent_files=checked,old_runtime_audit=parent,version=m['version'],formal_G2_passed=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=audit();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(r));raise SystemExit(0 if r['passed'] else 1)
