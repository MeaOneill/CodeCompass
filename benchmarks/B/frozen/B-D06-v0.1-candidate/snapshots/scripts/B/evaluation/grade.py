"""Evaluate dev patches independently; human explanations cannot be auto-passed."""
import argparse
import ast
import datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package_hash(folder):
    names = ['candidate.py', 'explanation.md', 'regression_tests.py', 'patch.diff', 'commands_and_elapsed.json']
    rows = {n: sha(Path(folder) / n) if (Path(folder) / n).is_file() else None for n in names}
    return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(), rows


def scope_unchanged(candidate, allowed):
    original = ROOT / 'benchmarks/sources/boltons/boltons/iterutils.py'
    def body(path):
        return [ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text(encoding='utf-8')).body if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) or n.name not in allowed]
    return body(original) == body(candidate)


def grade(task_id, submission, timeout=5, review=None):
    if task_id not in ('task_001', 'task_002'):
        raise ValueError('Only implemented dev patch tasks are accepted here')
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('timeout must be positive and finite')
    folder = Path(submission).resolve()
    candidate = folder / 'candidate.py'
    content_hash, files = package_hash(folder)
    result = {'task_id': task_id, 'evidence_type': 'development_validation', 'submission_hash': content_hash, 'files': files, 'status': None, 'criteria': {}, 'total_score': None, 'automated_score': 0, 'success': None, 'human_review': 'NOT_REVIEWED', 'elapsed_seconds': None, 'error': None}
    if not candidate.is_file():
        result.update(status='INVALID_SUBMISSION', success=False, error='candidate.py missing')
        return result
    weights = {'R1': 2, 'R2': 2, 'R3': 2, 'R4': 1} if task_id == 'task_001' else {'R1': 3, 'R2': 2, 'R3': 2}
    try:
        allowed = {'chunked_iter'} if task_id == 'task_001' else {'windowed_iter'}
        if not scope_unchanged(candidate, allowed):
            result.update(status='INVALID_SUBMISSION', success=False, error='Changed code outside the permitted function')
            return result
    except (SyntaxError, UnicodeError) as exc:
        result.update(status='INVALID_SUBMISSION', success=False, error=str(exc))
        return result
    (ROOT / 'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='B-grade-', dir=ROOT / 'tmp') as td:
        raw = Path(td) / 'worker.json'
        command = [sys.executable, '-I', str(Path(__file__).with_name('worker.py')), '--task', task_id, '--candidate', str(candidate), '--output', str(raw)]
        started = time.perf_counter()
        try:
            proc = subprocess.run(command, cwd=td, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
            result['worker_exit_code'] = proc.returncode
            result['worker_stdout'] = proc.stdout
            result['worker_stderr'] = proc.stderr
            if proc.returncode or not raw.is_file():
                result.update(status='EXECUTION_ERROR', success=False, error='Worker failed or no output')
                return result
            worker = json.loads(raw.read_text(encoding='utf-8'))
            result['worker_result'] = worker
        except subprocess.TimeoutExpired:
            result.update(status='TIMEOUT', success=False, error='Evaluator wall-clock timeout; not a learner task-time measurement')
            return result
        finally:
            result['elapsed_seconds'] = time.perf_counter() - started
    if worker['import_error']:
        result.update(status='EXECUTION_ERROR', success=False, error=worker['import_error'])
        return result
    for rid, points in weights.items():
        passed = worker['criteria'].get(rid, {}).get('passed', False)
        result['criteria'][rid] = {'score': points if passed else 0, 'max_score': points, 'passed': passed}
    result['automated_score'] = sum(v['score'] for v in result['criteria'].values())
    human_id = 'R5' if task_id == 'task_001' else 'R4'
    result['criteria'][human_id] = {'score': None, 'max_score': 2, 'passed': None, 'owner': 'independent human blind to method'}
    result['criteria']['R6'] = {'score': None, 'max_score': 1, 'passed': None, 'owner': 'independent human checks regression tests and command log'}
    critical = ('R1', 'R2', 'R3')
    if any(not result['criteria'][rid]['passed'] for rid in critical):
        result.update(status='FAILED_AUTOMATED', success=False)
        return result
    result['status'] = 'PENDING_HUMAN_REVIEW'
    if review is not None:
        receipt = json.loads(Path(review).read_text(encoding='utf-8'))
        if receipt.get('submission_hash') != content_hash or receipt.get('task_id') != task_id or receipt.get('reviewer_kind') != 'human' or receipt.get('blind_to_method') is not True or not receipt.get('reviewer'):
            raise ValueError('Human review must identify task, exact submission, reviewer and blinding')
        seconds = receipt.get('learner_elapsed_seconds')
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Human timing must be finite nonnegative seconds')
        for rid, maximum in [(human_id, 2), ('R6', 1)]:
            value = receipt['scores'][rid]
            if type(value) is not int or value not in (0, maximum):
                raise ValueError('All-or-nothing rubric score required')
            if not all(files[n] for n in files):
                raise ValueError('Human review requires every submission artifact')
            result['criteria'][rid].update(score=value, passed=value == maximum)
        result['human_review'] = receipt
        total = result['automated_score'] + sum(result['criteria'][rid]['score'] for rid in (human_id, 'R6'))
        result.update(total_score=total, success=seconds <= 1500 and total >= 9 and result['criteria'][human_id]['passed'], status='SCORED')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--task', required=True)
    p.add_argument('--submission', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--timeout', type=float, default=5)
    p.add_argument('--human-review')
    a = p.parse_args()
    out = Path(a.output)
    if out.exists():
        raise FileExistsError('Use a fresh output path')
    r = grade(a.task, a.submission, a.timeout, a.human_review)
    r['recorded_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: r[k] for k in ['task_id', 'status', 'automated_score', 'total_score', 'success']}, ensure_ascii=False))
    return 0 if r['status'] in ('PENDING_HUMAN_REVIEW', 'SCORED', 'FAILED_AUTOMATED', 'TIMEOUT', 'INVALID_SUBMISSION', 'EXECUTION_ERROR') else 1


if __name__ == '__main__':
    raise SystemExit(main())
