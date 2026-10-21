"""Fetch a small public, pinned second-repository source bundle; no credentials."""
import hashlib
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[2]


def fetch(url):
    with urlopen(Request(url,headers={'User-Agent':'CodeCompass-B-D07-source-cache'}),timeout=30) as r:
        if r.geturl().split('/')[2] not in ('api.github.com','raw.githubusercontent.com'):raise ValueError('Unexpected source host')
        raw=r.read(1_000_001)
    if len(raw)>1_000_000:raise ValueError('Source size limit')
    return raw


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit');a=p.parse_args()
    repo='more-itertools/more-itertools';out=ROOT/'benchmarks/sources/more_itertools_B_D07_v2'
    if out.exists():raise FileExistsError('Preserve fixed source bundle')
    commit=a.commit or json.loads(fetch(f'https://api.github.com/repos/{repo}/commits/HEAD'))['sha']
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):raise ValueError('Fixed commit SHA required')
    files=[];cache={}
    for path in ('LICENSE','more_itertools/more.py','more_itertools/recipes.py'):
        raw=fetch(f'https://raw.githubusercontent.com/{repo}/{commit}/{path}');cache[path]=raw
        files.append(dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()))
    if b'MIT' not in cache['LICENSE'] or b'Permission is hereby granted' not in cache['LICENSE']:raise ValueError('License must be reviewed')
    out.mkdir(parents=True)
    for path,raw in cache.items():
        target=out/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    manifest=dict(schema_version='1.0.0',object_type='RepoSnapshot',is_fixture=False,snapshot_id='more-itertools-'+commit[:12]+'-v2',
        url=f'https://github.com/{repo}',commit=commit,license='MIT',retrieved_at=datetime.now(timezone.utc).isoformat(),
        hash=hashlib.sha256(json.dumps(sorted(files,key=lambda x:x['path']),sort_keys=True,separators=(',',':')).encode()).hexdigest(),hash_scope='selected_files_manifest_sha256',
        files=files,license_path='LICENSE',snapshot_scope='partial_source_bundle',complete_checkout_included=False)
    (out/'snapshot.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(snapshot_id=manifest['snapshot_id'],commit=commit,files=len(files),license='MIT')))
