"""Local Git receiver rehearsal plus offline dependency reinstall; not a second PC."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    out = ROOT / 'experiments/B/B-D01-20261016-local-replay'
    out.mkdir(parents=True, exist_ok=False)
    clone = ROOT / 'tmp/B-D01-receiver'
    venv = ROOT / 'tmp/B-D01-receiver-venv'
    if clone.exists() or venv.exists():
        raise FileExistsError('Receiver paths already exist; preserve them and use a new rehearsal ID')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    py = venv / 'Scripts/python.exe'
    env = dict(os.environ, PYTHONPATH=str(clone / 'src'), PYTHONUTF8='1')
    commands = [
        ('clone', ['git', 'clone', '--no-local', '--single-branch', '--branch', branch, str(ROOT), str(clone)], ROOT),
        ('receiver_sha', ['git', 'rev-parse', 'HEAD'], clone),
        ('venv', [sys.executable, '-m', 'venv', str(venv)], ROOT),
        ('offline_install', [str(py), '-m', 'pip', 'install', '--no-index', '--require-hashes', '--find-links', str(ROOT / 'tmp/B-D01-wheels'), '-r', 'scripts/B/requirements-d01-win-py312.hashes.txt'], clone),
        ('pip_check', [str(py), '-m', 'pip', 'check'], clone),
        ('help', [str(py), '-m', 'app', '--help'], clone),
        ('sample', [str(py), '-m', 'app', 'check-sample'], clone),
        ('pytest', [str(py), '-m', 'pytest', 'tests/B', '-q', '--basetemp', str(clone / 'tmp/pytest-receiver')], clone),
    ]
    records = []
    for name, command, cwd in commands:
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        t = time.perf_counter()
        r = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        (out / f'{name}.stdout.txt').write_text(r.stdout, encoding='utf-8')
        (out / f'{name}.stderr.txt').write_text(r.stderr, encoding='utf-8')
        code = r.returncode
        if name == 'receiver_sha' and r.stdout.strip() != head:
            code = 1
        records.append({'name': name, 'command': command, 'cwd': str(cwd), 'started_at': started, 'elapsed_seconds': time.perf_counter() - t, 'exit_code': code})
        print(name, code, flush=True)
        if code:
            break
    result = {'task_id': 'B-D01', 'evidence_type': 'development_validation', 'source_checkpoint': head, 'branch': branch, 'receiver_same_machine': True, 'remote_used': False, 'offline_install_network_disabled_by_pip': True, 'wheel_hashes': [{'name': f.name, 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted((ROOT / 'tmp/B-D01-wheels').glob('*.whl'))], 'commands': records, 'exit_code': int(len(records) != len(commands) or any(r['exit_code'] for r in records)), 'independent_human_review': 'NOT_REVIEWED'}
    (out / 'registration.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
