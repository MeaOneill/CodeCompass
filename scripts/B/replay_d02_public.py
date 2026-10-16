"""Restore a committed B-D02 checkpoint and verify public artifacts in a fresh clone."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', required=True)
    a = p.parse_args()
    if not a.run_id.replace('-', '').replace('_', '').isalnum():
        p.error('Invalid run-id')
    out = ROOT / 'experiments/B' / a.run_id
    out.mkdir(parents=True, exist_ok=False)
    clone = ROOT / 'tmp' / a.run_id
    if clone.exists():
        raise FileExistsError('Fresh receiver path required')
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    env = dict(os.environ, PYTHONPATH=str(clone / 'src'), PYTHONUTF8='1')
    commands = [
        ('clone', ['git', 'clone', '--no-local', '--single-branch', '--branch', branch, str(ROOT), str(clone)], ROOT, 0),
        ('sha', ['git', 'rev-parse', 'HEAD'], clone, 0),
        ('sample', [sys.executable, '-m', 'app', 'check-sample'], clone, 0),
        ('pytest', [sys.executable, '-m', 'pytest', 'tests/A', 'tests/B', '-q', '--basetemp=tmp/pytest-receiver'], clone, 0),
        ('demo', [sys.executable, 'scripts/B/demo_d02.py', '--run-id', a.run_id + '-demo'], clone, 0),
        ('audit', [sys.executable, 'scripts/B/audit_d02.py', '--run-id', a.run_id + '-audit'], clone, 0),
    ]
    results = []
    for name, cmd, cwd, expected in commands:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True)
        (out / (name + '.stdout.txt')).write_bytes(proc.stdout)
        (out / (name + '.stderr.txt')).write_bytes(proc.stderr)
        match = proc.returncode == expected
        if name == 'sha': match = match and proc.stdout.decode().strip() == head
        results.append({'name': name, 'command': cmd, 'expected_exit_code': expected, 'actual_exit_code': proc.returncode, 'expectation_met': match})
        print(name, proc.returncode, 'expected', expected, flush=True)
        if not match: break
    passed = len(results) == len(commands) and all(r['expectation_met'] for r in results)
    record = {'run_id': a.run_id, 'task_id': 'B-D02', 'code_checkpoint': head, 'branch': branch, 'scope': 'same_machine_public_only_fresh_local_clone_existing_locked_venv', 'private_key_copied': False, 'held_out_answers_replayed': False, 'independent_human_review': 'NOT_REVIEWED', 'engineering_task_gate_passed': passed, 'formal_study_ready': False, 'commands': results, 'exit_code': int(not passed)}
    (out / 'registration.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return record['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
