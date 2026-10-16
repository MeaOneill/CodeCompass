"""Acquire an immutable held-out module without changing A's source bundle."""
import datetime
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d'


def main():
    folder = ROOT / 'benchmarks/sources/boltons_B_D02'
    folder.mkdir(parents=True, exist_ok=False)
    records = []
    for name in ['LICENSE', 'boltons/strutils.py', 'tests/test_strutils.py']:
        url = f'https://raw.githubusercontent.com/mahmoud/boltons/{COMMIT}/{name}'
        content = urllib.request.urlopen(url, timeout=40).read()
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        records.append({'path': name, 'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content), 'git_blob': hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()})
    records.sort(key=lambda r: r['path'])
    snap = {'schema_version': '1.0.0', 'object_type': 'RepoSnapshot', 'is_fixture': False, 'snapshot_id': 'boltons-d02-strutils-' + COMMIT[:12], 'url': 'https://github.com/mahmoud/boltons', 'commit': COMMIT, 'license': 'BSD-3-Clause', 'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'hash': hashlib.sha256(json.dumps(records, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'hash_scope': 'selected_files_manifest_sha256', 'files': records, 'license_path': 'LICENSE', 'snapshot_scope': 'partial_source_bundle', 'complete_checkout_included': False}
    (folder / 'snapshot.json').write_text(json.dumps(snap, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(snap['snapshot_id'], snap['hash'])


if __name__ == '__main__':
    main()
