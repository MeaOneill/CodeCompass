"""Public, nonparticipant demonstration for the user's step-by-step self-check."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.B.evaluation.dev_fixtures import create_fixture
from scripts.B.evaluation.grade import grade


def main():
    p = argparse.ArgumentParser(description='B-D02 developer-fixture demo; no private test key or real participant')
    p.add_argument('--run-id', required=True)
    a = p.parse_args()
    if not a.run_id.replace('-', '').replace('_', '').isalnum():
        p.error('Use letters/digits/hyphens/underscores')
    out = ROOT / 'experiments/B' / a.run_id
    out.mkdir(parents=True, exist_ok=False)
    fixtures = ROOT / 'tmp' / a.run_id
    rows = []
    for tid in ('task_001', 'task_002'):
        for label, mutation in [('reference', None), ('original', 'original')]:
            folder = create_fixture(tid, fixtures / (tid + '-' + label), mutation)
            result = grade(tid, folder)
            result.update(is_fixture=True, learner_result=False)
            (out / (tid + '-' + label + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            expected = 'PENDING_HUMAN_REVIEW' if label == 'reference' else 'FAILED_AUTOMATED'
            rows.append({'task_id': tid, 'fixture': label, 'status': result['status'], 'expected_status': expected, 'expectation_met': result['status'] == expected, 'automated_score': result['automated_score'], 'human_score': None, 'success': result['success']})
            print(tid, label, result['status'], 'automated_score=', result['automated_score'], 'success=', result['success'])
    for policy, suffix, expected in [('shared', 'shared', 2), ('source_lines_proposal', 'line-proxy', 0)]:
        command = [sys.executable, 'scripts/B/b0.py', '--budget', '100', '--cost-policy', policy, '--run-id', a.run_id + '-' + suffix]
        proc = subprocess.run(command, cwd=ROOT, env=dict(os.environ, PYTHONUTF8='1'), capture_output=True)
        (out / ('B0-' + suffix + '.stdout.txt')).write_bytes(proc.stdout)
        (out / ('B0-' + suffix + '.stderr.txt')).write_bytes(proc.stderr)
        rows.append({'method': 'B0', 'cost_policy': policy, 'exit_code': proc.returncode, 'expected_exit_code': expected})
        print('B0', policy, 'exit=', proc.returncode, 'expected=', expected)
    (out / 'demo_summary.json').write_text(json.dumps({'record_type': 'developer_fixture_demo_not_human_results', 'rows': rows, 'whole_task_gate_passed': False, 'review': 'NOT_HUMAN_REVIEWED'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Open', str(out / 'demo_summary.json'))
    if any(r.get('exit_code') != r.get('expected_exit_code') for r in rows if 'exit_code' in r):
        return 1
    if any(not r['expectation_met'] for r in rows if 'expectation_met' in r):
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
