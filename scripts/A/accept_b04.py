"""Offline A reception of B-D04; records commands and never starts a model launcher."""
import argparse
import datetime as dt
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.run_id):
        parser.error('Use a simple unique run id')
    out = ROOT / 'experiments/A' / args.run_id
    out.mkdir(exist_ok=False)
    temp = ROOT / 'tmp' / args.run_id
    temp.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    for key in list(env):
        if any(word in key.upper() for word in ('API_KEY', 'TOKEN', 'SECRET', 'PASSWORD')):
            env.pop(key)
    env.update(PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1', PYTHONIOENCODING='utf-8', TEMP=str(temp), TMP=str(temp))
    def git(*arguments):
        return subprocess.check_output(['git', *arguments], cwd=ROOT, encoding='utf-8').strip()
    record = dict(run_id=args.run_id, task='A-D05 prerequisites / receive B-D04', owner='成员A',
                  executor='Codex Agent A', model_id=None, machine=platform.node(),
                  platform=platform.platform(), python=sys.version, interpreter=sys.executable,
                  root=str(ROOT), branch=git('branch', '--show-current'), code_commit=git('rev-parse', 'HEAD'),
                  received_B_commit=git('rev-parse', 'origin/codex/B-D04-baselines'),
                  started_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),
                  verification_kind='same-machine isolated-worktree reception', model_api_calls=0,
                  independent_human_review='NOT_REVIEWED', formal_study_ready=False, commands=[])
    commands = [
        ('pip-check', [sys.executable, '-m', 'pip', 'check']),
        ('pip-freeze', [sys.executable, '-m', 'pip', 'freeze']),
        ('pytest', [sys.executable, '-m', 'pytest', '-q', '--basetemp=' + str(temp / 'pytest')]),
        ('B04-live-audit', [sys.executable, 'scripts/B/audit_d04.py', '--source', 'experiments/B/B-D04-deepseek-live01', '--figures', 'report_materials/B/B-D04-deepseek-live01', '--fixtures', 'experiments/B/B-D04-fixtures01', '--output', str(out / 'B04-live-audit.json')]),
        ('A04-mechanism-audit', [sys.executable, 'scripts/A/audit_d04.py', '--run-id', 'A-D04-mechanism01', '--output', str(out / 'A04-mechanism-audit.json')]),
        ('demo-A04', [sys.executable, 'scripts/A/demo_d04.py']),
        ('sample', [sys.executable, '-m', 'app', 'check-sample']),
    ]
    for name, command in commands:
        started = time.perf_counter()
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
        (out / (name + '.stdout.log')).write_bytes(result.stdout)
        (out / (name + '.stderr.log')).write_bytes(result.stderr)
        record['commands'].append(dict(name=name, argv=command, exit_code=result.returncode,
                                       seconds=time.perf_counter() - started,
                                       stdout=name + '.stdout.log', stderr=name + '.stderr.log'))
        (out / 'registration.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
        print(f'{name}: exit {result.returncode}', flush=True)
    record['finished_at'] = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()
    record['engineering_passed'] = all(c['exit_code'] == 0 for c in record['commands'])
    for path in out.glob('*.json'):
        path.write_text(path.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    record['files'] = [dict(path=str(p.relative_to(ROOT)).replace('\\', '/'), sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(out.iterdir()) if p.name != 'registration.json']
    record['reception_script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out / 'registration.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    return 0 if record['engineering_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
