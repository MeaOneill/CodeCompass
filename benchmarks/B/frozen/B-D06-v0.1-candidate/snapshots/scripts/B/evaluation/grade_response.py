"""Independent answer scoring; test-candidate keys must be explicitly supplied.

Keys are never auto-discovered or made available through the application.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def grade_response(task_id, answer_path, key_path, human_review=None):
    catalog = json.loads((ROOT / 'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    task = next((t for t in catalog['tasks'] if t['task_id'] == task_id), None)
    if task is None or task_id in ('task_001', 'task_002'):
        raise ValueError('Unknown response task')
    key_file = Path(key_path).resolve()
    key = json.loads(key_file.read_text(encoding='utf-8'))
    if key.get('record_type') != 'independent_evaluation_keys' or task_id not in key['tasks']:
        raise ValueError('Explicit matching evaluation key required')
    if task['split'] == 'test_candidate' and key.get('access') != 'private_evaluator_only':
        raise ValueError('Test candidate requires private evaluator key')
    if task['split'] == 'test_candidate':
        receipt = json.loads((ROOT / 'benchmarks/B/private_key_manifest.json').read_text(encoding='utf-8'))
        if hashlib.sha256(key_file.read_bytes()).hexdigest() != receipt['sha256']:
            raise ValueError('Private evaluator key hash does not match the registered version')
    answer = json.loads(Path(answer_path).read_text(encoding='utf-8'))
    # JSON-type exactness: bool is not accepted as integer, nor NaN as a value.
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    outputs_passed = canonical(answer.get('outputs')) == canonical(key['tasks'][task_id]['outputs'])
    source_passed = canonical(answer.get('source_spans')) == canonical(task['source_spans'])
    explanation = answer.get('explanation')
    result = {'task_id': task_id, 'evidence_type': 'development_validation', 'answer_sha256': hashlib.sha256(Path(answer_path).read_bytes()).hexdigest(), 'key_sha256': hashlib.sha256(key_file.read_bytes()).hexdigest(), 'outputs_passed': outputs_passed, 'source_passed': source_passed, 'automated_score': (6 if outputs_passed else 0) + (2 if source_passed else 0), 'explanation_present': isinstance(explanation, str) and bool(explanation.strip()), 'human_explanation_score': None, 'total_score': None, 'learner_elapsed_seconds': None, 'success': False if not outputs_passed or not source_passed else None, 'status': 'PENDING_HUMAN_REVIEW' if outputs_passed and source_passed else 'FAILED_AUTOMATED', 'human_review': 'NOT_REVIEWED'}
    if human_review is not None:
        receipt = json.loads(Path(human_review).read_text(encoding='utf-8'))
        if receipt.get('answer_sha256') != result['answer_sha256'] or receipt.get('task_id') != task_id or receipt.get('reviewer_kind') != 'human' or not receipt.get('reviewer') or receipt.get('blind_to_method') is not True:
            raise ValueError('Human receipt must bind exact answer, task, reviewer and blinding')
        score, seconds = receipt.get('explanation_score'), receipt.get('learner_elapsed_seconds')
        if type(score) is not int or score not in (0, 2) or (score == 2 and not result['explanation_present']):
            raise ValueError('Explanation is all-or-nothing and must be present')
        if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0:
            raise ValueError('Finite nonnegative actual learner time required')
        total = result['automated_score'] + score
        result.update(human_explanation_score=score, learner_elapsed_seconds=seconds, human_review=receipt, total_score=total, success=outputs_passed and source_passed and total >= 9 and seconds <= 1500, status='SCORED')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--task', required=True)
    p.add_argument('--answer', required=True)
    p.add_argument('--key', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--human-review')
    a = p.parse_args()
    out = Path(a.output)
    if out.exists():
        raise FileExistsError('Preserve prior evidence')
    result = grade_response(a.task, a.answer, a.key, a.human_review)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('task_id', 'status', 'automated_score', 'success')}))


if __name__ == '__main__':
    main()
