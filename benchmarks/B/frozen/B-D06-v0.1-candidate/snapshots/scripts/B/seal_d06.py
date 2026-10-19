"""Seal a new B protocol candidate without touching A's frozen candidate or tags."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--version',default='B-D06-v0.1-candidate');a=p.parse_args()
    if a.version!='B-D06-v0.1-candidate':p.error('Register a new source/output list for a new version')
    out=ROOT/'benchmarks/B/frozen'/a.version;out.mkdir(parents=True,exist_ok=False)
    sources=[*sorted((ROOT/'docs/protocol/B-D06-v0.1-candidate').glob('*')),
        *sorted((ROOT/'app/B_D06').glob('*')),ROOT/'benchmarks/B/task_catalog.json',ROOT/'benchmarks/B/private_key_manifest.json',
        ROOT/'benchmarks/sources/boltons_B_D02/snapshot.json',ROOT/'benchmarks/sources/boltons_B_D02/boltons/strutils.py',
        ROOT/'benchmarks/sources/boltons/snapshot.json',ROOT/'scripts/B/protocol_d06.py',ROOT/'scripts/B/score_d06.py',
        ROOT/'scripts/B/serve_d06.py',ROOT/'scripts/B/serve_d05.py',ROOT/'scripts/B/seal_d06.py',ROOT/'scripts/B/audit_d06.py',
        ROOT/'src/codecompass/app/study_d06.py',ROOT/'tests/B/test_protocol_d06.py',
        *sorted((ROOT/'scripts/B/evaluation').glob('*.py'))]
    files=[]
    for path in sources:
        rel=path.relative_to(ROOT);raw=path.read_bytes();dst=out/'snapshots'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
        files.append(dict(path=rel.as_posix(),snapshot=dst.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest()))
    manifest=dict(version=a.version,record_type='candidate_content_seal_not_formal_freeze',source_base='72c0922369d5ef31c4803974dda8965761ca72dd',
        formal_freeze=False,formal_tasks=0,task_specs=12,private_answers_in_git=False,
        A_candidate_preserved=True,A_tag=None,files=files,change_policy='No overwrite. New content requires new version, reason and affected runs before formal outcomes.')
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(files=len(files),formal_freeze=False,output=out.relative_to(ROOT).as_posix())))
