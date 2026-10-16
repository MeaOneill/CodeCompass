"""Capture actual G1 verification commands, including expected input failures."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(); p.add_argument('--run-id', required=True)
    a = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', a.run_id): p.error('Invalid run-id')
    out = ROOT/'experiments/B'/a.run_id; out.mkdir(parents=True, exist_ok=False)
    commands = [
        ('pytest', ['-m', 'pytest', '-q'], 0),
        ('A-demo', ['scripts/A/demo_d03.py'], 0),
        ('A-audit', ['scripts/A/audit_d03.py', '--source-run', 'A-D03-short-tests04', '--run-id', a.run_id+'-A-replay'], 0),
        ('B-demo', ['scripts/B/demo_d03.py', '--run-id', a.run_id+'-demo'], 0),
        ('B-audit', ['scripts/B/audit_d03.py', '--source', 'experiments/B/B-D03-integration02', '--figures', 'report_materials/B/B-D03-final', '--output', str((out/'audit.json').relative_to(ROOT))], 0),
        ('Issue-prepare', ['scripts/B/issues_d03.py', 'prepare', '--snapshot', 'experiments/B/B-D03-issues01/snapshot.json', '--output', str((out/'issue_prepare.json').relative_to(ROOT))], 0),
        ('B-help', ['scripts/B/demo_d03.py', '--help'], 0),
        ('Issue-help', ['scripts/B/issues_d03.py', '--help'], 0),
        ('invalid-run-id', ['scripts/B/demo_d03.py', '--run-id', '../escape'], 2),
        ('missing-snapshot', ['scripts/B/issues_d03.py', 'prepare', '--snapshot', 'tmp/never-existed-snapshot.json', '--output', str((out/'must_not_exist.json').relative_to(ROOT))], 2),
    ]
    records = []
    for name, argv, expected in commands:
        result = subprocess.run([sys.executable, *argv], cwd=ROOT,
                                env={**os.environ, 'PYTHONPATH': str(ROOT/'src'), 'PYTHONUTF8': '1'},
                                capture_output=True, encoding='utf-8', errors='strict', timeout=180)
        (out/(name+'.stdout.txt')).write_text(result.stdout, encoding='utf-8', newline='\n')
        (out/(name+'.stderr.txt')).write_text(result.stderr, encoding='utf-8', newline='\n')
        records.append({'name': name, 'command': [sys.executable, *argv], 'exit_code': result.returncode,
                        'expected_exit': expected, 'passed': result.returncode == expected,
                        'stdout': (out/(name+'.stdout.txt')).relative_to(ROOT).as_posix(),
                        'stderr': (out/(name+'.stderr.txt')).relative_to(ROOT).as_posix()})
        print(name+': '+str(result.returncode)+' expected '+str(expected), flush=True)
    passed = all(r['passed'] for r in records) and not (out/'must_not_exist.json').exists()
    registration = {'task': 'B-D03', 'run_id': a.run_id, 'time': datetime.now(timezone.utc).isoformat(),
                    'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    'commands': records, 'engineering_passed': passed, 'exit_code': 0 if passed else 1,
                    'independent_human_review': 'NOT_REVIEWED', 'formal_study_ready': False}
    (out/'registration.json').write_text(json.dumps(registration, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    return registration['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
