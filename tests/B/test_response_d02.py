import copy
import json
from pathlib import Path

import pytest

from codecompass.retrieval.samples import load_object
from scripts.B.evaluation.grade_response import grade_response

ROOT = Path(__file__).resolve().parents[2]


def answer(tmp_path, task_id='task_003'):
    catalog = json.loads((ROOT / 'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    task = next(t for t in catalog['tasks'] if t['task_id'] == task_id)
    key = json.loads((ROOT / 'benchmarks/B/dev_response_keys.json').read_text(encoding='utf-8'))
    p = tmp_path / 'answer.json'
    p.write_text(json.dumps({'outputs': key['tasks'][task_id]['outputs'], 'source_spans': task['source_spans'], 'explanation': 'fixture; no human grade'}), encoding='utf-8')
    return p


def test_dev_response_pending_human(tmp_path):
    r = grade_response('task_003', answer(tmp_path), ROOT / 'benchmarks/B/dev_response_keys.json')
    assert r['automated_score'] == 8 and r['success'] is None
    assert r['human_explanation_score'] is None


def test_wrong_answer_not_success(tmp_path):
    p = answer(tmp_path)
    d = json.loads(p.read_text());d['outputs']['plain'] = []
    p.write_text(json.dumps(d), encoding='utf-8')
    assert grade_response('task_003', p, ROOT / 'benchmarks/B/dev_response_keys.json')['success'] is False


def test_source_line_tamper_fails(tmp_path):
    p = answer(tmp_path)
    d = json.loads(p.read_text());d['source_spans'][0]['start_line'] += 1
    p.write_text(json.dumps(d), encoding='utf-8')
    assert grade_response('task_003', p, ROOT / 'benchmarks/B/dev_response_keys.json')['source_passed'] is False


def test_missing_private_key_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        grade_response('task_005', answer(tmp_path), tmp_path / 'absent.json')


def test_unregistered_private_key_rejected(tmp_path):
    p = tmp_path / 'wrong-key.json'
    p.write_text(json.dumps({'record_type': 'independent_evaluation_keys', 'access': 'private_evaluator_only', 'tasks': {'task_005': {'outputs': {}}}}), encoding='utf-8')
    with pytest.raises(ValueError, match='key hash'):
        grade_response('task_005', answer(tmp_path), p)


def test_response_replayed_human_receipt_rejected(tmp_path):
    p = answer(tmp_path)
    receipt = tmp_path / 'review.json'
    receipt.write_text(json.dumps({'task_id': 'task_003', 'answer_sha256': 'stale', 'reviewer_kind': 'human', 'reviewer': 'fixture', 'blind_to_method': True}), encoding='utf-8')
    with pytest.raises(ValueError, match='exact answer'):
        grade_response('task_003', p, ROOT / 'benchmarks/B/dev_response_keys.json', receipt)


def test_response_testdouble_receipt_time_gate(tmp_path):
    # Only a unit-test double in tmp, never a real review/participant record.
    import hashlib
    p = answer(tmp_path)
    receipt = tmp_path / 'review.json'
    data = {'task_id': 'task_003', 'answer_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'reviewer_kind': 'human', 'reviewer': 'unit-test-double-not-a-real-review', 'blind_to_method': True, 'explanation_score': 2, 'learner_elapsed_seconds': 1501}
    receipt.write_text(json.dumps(data), encoding='utf-8')
    result = grade_response('task_003', p, ROOT / 'benchmarks/B/dev_response_keys.json', receipt)
    assert result['total_score'] == 10 and result['success'] is False
    data['learner_elapsed_seconds'] = float('nan')
    receipt.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='Finite'):
        grade_response('task_003', p, ROOT / 'benchmarks/B/dev_response_keys.json', receipt)


@pytest.mark.parametrize('relative', ['private_evaluation/B-D02/keys.json', 'benchmarks/B/dev_response_keys.json', 'scripts/B/evaluation/worker.py'])
def test_application_cannot_read_evaluator_keys(relative):
    with pytest.raises(ValueError, match='application-readable'):
        load_object(ROOT, relative)


def test_split_and_provenance():
    cat = json.loads((ROOT / 'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    dev = [t for t in cat['tasks'] if t['split'] == 'dev']
    held = [t for t in cat['tasks'] if t['split'] == 'test_candidate']
    assert len(dev) == 4 and len(held) == 8
    assert {t['module'] for t in dev}.isdisjoint({t['module'] for t in held})
    assert not any(t['frozen'] or t['human_reviewer'] for t in cat['tasks'])
    for task in cat['tasks']:
        assert sum(g['points'] for g in task['rubric']) == task['max_score'] == 10
