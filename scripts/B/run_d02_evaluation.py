"""Reproducible B-D02 dev-fixture audit; participant results are never fabricated."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from scripts.B.evaluation.dev_fixtures import create_fixture
from scripts.B.evaluation.grade import grade
from scripts.B.evaluation.grade_response import grade_response
from codecompass.graph import read_snapshot, validate_span


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', required=True)
    p.add_argument('--private-key', required=True)
    a = p.parse_args()
    if not a.run_id.replace('-', '').replace('_', '').isalnum():
        p.error('Invalid run-id')
    out = ROOT / 'experiments/B' / a.run_id
    out.mkdir(parents=True, exist_ok=False)
    fixtures = ROOT / 'tmp' / a.run_id
    fixtures.mkdir(parents=True, exist_ok=False)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    t0 = time.perf_counter()
    catalog = json.loads((ROOT / 'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    snapshots = {}
    for folder in ['boltons', 'boltons_B_D02']:
        bundle = ROOT / 'benchmarks/sources' / folder
        snap = json.loads((bundle / 'snapshot.json').read_text(encoding='utf-8'))
        snapshots[snap['snapshot_id']] = (snap, read_snapshot(bundle, snap))
    spans = 0
    for task in catalog['tasks']:
        for span in task['source_spans']:
            snap, contents = snapshots[span['snapshot_id']]
            validate_span(span, snap, contents)
            spans += 1
    results = []
    for tid in ('task_001', 'task_002'):
        for label, mutation in [('reference', None), ('original', 'original')]:
            folder = create_fixture(tid, fixtures / (tid + '-' + label), mutation)
            result = grade(tid, folder)
            result.update(is_fixture=True, fixture_kind=label, learner_result=False)
            (out / f'{tid}-{label}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            expected = 'PENDING_HUMAN_REVIEW' if label == 'reference' else 'FAILED_AUTOMATED'
            results.append({'task_id': tid, 'fixture': label, 'expected_status': expected, 'actual_status': result['status'], 'passed': result['status'] == expected})
    keys = json.loads((ROOT / 'benchmarks/B/dev_response_keys.json').read_text(encoding='utf-8'))['tasks']
    private_key = Path(a.private_key).resolve()
    private_data = json.loads(private_key.read_text(encoding='utf-8'))
    keys.update(private_data['tasks'])
    # Held-out fixture answers stay outside Git and outside application sources.
    hidden = ROOT / 'private_evaluation/B-D02' / a.run_id
    hidden.mkdir(parents=True, exist_ok=False)
    for task in catalog['tasks'][2:]:
        tid = task['task_id']
        path = (fixtures if task['split'] == 'dev' else hidden) / (tid + '.json')
        path.write_text(json.dumps({'outputs': keys[tid]['outputs'], 'source_spans': task['source_spans'], 'explanation': 'Developer fixture; not a human response.'}, ensure_ascii=False, indent=2), encoding='utf-8')
        kpath = ROOT / 'benchmarks/B/dev_response_keys.json' if task['split'] == 'dev' else private_key
        result = grade_response(tid, path, kpath)
        result.update(is_fixture=True, learner_result=False)
        # Result contains hashes and pass flags, never answer outputs or keys.
        (out / f'{tid}-response-fixture.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        results.append({'task_id': tid, 'fixture': 'response_key', 'actual_status': result['status'], 'passed': result['status'] == 'PENDING_HUMAN_REVIEW'})
    env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONUTF8='1')
    command = [sys.executable, '-m', 'pytest', 'tests/A', 'tests/B', '-q', '--basetemp', str(ROOT / 'tmp' / ('pytest-' + a.run_id))]
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    (out / 'pytest.stdout.txt').write_bytes(proc.stdout)
    (out / 'pytest.stderr.txt').write_bytes(proc.stderr)
    inputs = []
    for pattern in ['scripts/B/**/*.py', 'tests/B/*.py', 'src/codecompass/retrieval/*.py', 'benchmarks/B/*', 'configs/B/*']:
        for f in sorted(ROOT.glob(pattern)):
            if f.is_file():
                inputs.append({'path': f.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()})
    for f in [ROOT / 'pytest.ini', ROOT / '.gitattributes', ROOT / '.gitignore']:
        inputs.append({'path': f.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()})
    (out / 'input_manifest.json').write_text(json.dumps(inputs, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    record = {'run_id': a.run_id, 'task_id': 'B-D02', 'actor': 'Codex Agent B', 'owner': '成员B / 糯糯', 'machine': os.environ.get('COMPUTERNAME'), 'model_id': None, 'code_commit': None, 'dependency_commit': '30069ce468a52b68a0d3bfb62bb49b1cce0f2104', 'evidence_type': 'development_validation', 'started_at': started, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'elapsed_seconds': time.perf_counter() - t0, 'private_key_sha256': hashlib.sha256(private_key.read_bytes()).hexdigest(), 'source_spans_verified': spans, 'fixture_checks': results, 'pytest_command': command, 'pytest_exit_code': proc.returncode, 'metrics': None, 'api_cost': None, 'formal_experiments': 0, 'human_review': 'NOT_REVIEWED', 'exit_code': int(proc.returncode != 0 or not all(r['passed'] for r in results))}
    (out / 'registration.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('source spans:', spans, 'fixture checks:', sum(r['passed'] for r in results), '/', len(results), 'pytest exit:', proc.returncode)
    return record['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
