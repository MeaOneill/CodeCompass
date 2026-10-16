"""Capture actual checks, outputs and input hashes in a fresh run directory."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', required=True)
    args = p.parse_args()
    if not args.run_id.replace('-', '').replace('_', '').isalnum():
        p.error('run-id must be alphanumeric with hyphens/underscores')
    out = ROOT / 'experiments/B' / args.run_id
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1')
    commands = [
        ('help', [sys.executable, '-m', 'app', '--help']),
        ('imports', [sys.executable, '-c', 'import codecompass,codecompass.retrieval,codecompass.issues,app; print("imports OK")']),
        ('sample', [sys.executable, '-m', 'app', 'check-sample']),
        ('a_contract_review', [sys.executable, 'scripts/A/validate_d01.py', '--output', f'experiments/B/{args.run_id}/a_contract_review.json']),
        ('pytest', [sys.executable, '-m', 'pytest', 'tests/B', '-q', '--basetemp', str(ROOT / 'tmp' / ('pytest-' + args.run_id))]),
        ('pip_check', [sys.executable, '-m', 'pip', 'check']),
    ]
    inputs = []
    for directory in ('app', 'src/codecompass', 'tests/B', 'schemas', 'benchmarks', 'scripts/B', 'docs/B'):
        for f in sorted((ROOT / directory).rglob('*')):
            if f.is_file() and '__pycache__' not in f.parts:
                inputs.append({'path': f.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()})
    (out / 'input_manifest.json').write_text(json.dumps(inputs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest_hash = hashlib.sha256((out / 'input_manifest.json').read_bytes()).hexdigest()
    results = []
    for name, command in commands:
        start = datetime.datetime.now(datetime.timezone.utc).isoformat()
        t = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        elapsed = time.perf_counter() - t
        (out / f'{name}.stdout.txt').write_text(result.stdout, encoding='utf-8')
        (out / f'{name}.stderr.txt').write_text(result.stderr, encoding='utf-8')
        results.append({'name': name, 'command': command, 'started_at': start, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'exit_code': result.returncode, 'elapsed_seconds': elapsed, 'stdout': f'{name}.stdout.txt', 'stderr': f'{name}.stderr.txt'})
        print(name, 'exit=', result.returncode)
    record = {'run_id': args.run_id, 'task_id': 'B-D01', 'actor': 'Codex Agent B', 'owner': 'member B / local Git identity', 'machine': platform.node(), 'python': sys.version, 'python_executable': sys.executable, 'code_commit': None, 'dependency_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'worktree_content_manifest': 'input_manifest.json', 'data_hash': manifest_hash, 'evidence_type': 'development_validation', 'formal_experiment': False, 'model_id': None, 'seed': None, 'metrics': None, 'cost': None, 'checks': results, 'exit_code': int(any(r['exit_code'] for r in results)), 'independent_human_review': 'NOT_REVIEWED'}
    (out / 'registration.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return record['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
