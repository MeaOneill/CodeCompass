"""Tamper checks on isolated candidate copies. Originals and private keys untouched."""
import argparse
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.B.audit_d06 import audit


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    scratch=ROOT/'tmp/B-D06-challenges01';scratch.mkdir(parents=True,exist_ok=False)
    rel='benchmarks/B/frozen/B-D06-v0.1-candidate/manifest.json'
    manifest=json.loads((ROOT/rel).read_text(encoding='utf-8'));paths={rel}
    for e in manifest['files']:paths.update((e['path'],e['snapshot']))
    results=[]
    for name,target in [('catalog','benchmarks/B/task_catalog.json'),('snapshot',manifest['files'][0]['snapshot']),('protocol','docs/protocol/B-D06-v0.1-candidate/protocol.md')]:
        folder=scratch/name
        for path in paths:
            dst=folder/path;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,dst)
        with (folder/target).open('ab') as f:f.write(b'\n') # Semantically harmless whitespace must still break the byte seal.
        report=audit(folder);results.append(dict(case=name,rejected=not report['candidate_checks_passed'],errors=report['errors']))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(dict(cases=results,passed=all(r['rejected'] for r in results),private_answers_copied=False),f,indent=2)
    print(json.dumps(results));raise SystemExit(0 if all(r['rejected'] for r in results) else 1)
