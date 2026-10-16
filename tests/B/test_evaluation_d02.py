import hashlib
import json
from pathlib import Path

import pytest

from scripts.B.evaluation.dev_fixtures import create_fixture
from scripts.B.evaluation.grade import grade

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('task_id', ['task_001', 'task_002'])
def test_reference_is_automated_only(tmp_path, task_id):
    f = create_fixture(task_id, tmp_path / task_id)
    r = grade(task_id, f)
    assert r['status'] == 'PENDING_HUMAN_REVIEW'
    assert r['automated_score'] == 7
    assert r['total_score'] is None and r['success'] is None
    assert r['human_review'] == 'NOT_REVIEWED'


@pytest.mark.parametrize('task_id', ['task_001', 'task_002'])
def test_original_is_expected_failure(tmp_path, task_id):
    r = grade(task_id, create_fixture(task_id, tmp_path / task_id, 'original'))
    assert r['status'] == 'FAILED_AUTOMATED' and r['success'] is False


def test_overconsumption_caught(tmp_path):
    r = grade('task_001', create_fixture('task_001', tmp_path / 'bad', 'overconsume'))
    assert r['status'] == 'FAILED_AUTOMATED'
    assert r['criteria']['R2']['passed'] is False


def test_timeout_is_failure(tmp_path):
    r = grade('task_001', create_fixture('task_001', tmp_path / 'hang', 'hang'), timeout=1)
    assert r['status'] == 'TIMEOUT' and r['success'] is False


def test_outside_scope_rejected(tmp_path):
    r = grade('task_001', create_fixture('task_001', tmp_path / 'outside', 'outside_scope'))
    assert r['status'] == 'INVALID_SUBMISSION'


def test_missing_submission_not_success(tmp_path):
    assert grade('task_001', tmp_path)['status'] == 'INVALID_SUBMISSION'


def test_fake_or_replayed_human_review_rejected(tmp_path):
    folder = create_fixture('task_001', tmp_path / 'good')
    receipt = tmp_path / 'fake.json'
    receipt.write_text(json.dumps({'task_id': 'task_001', 'submission_hash': 'wrong', 'reviewer': 'fixture', 'reviewer_kind': 'human', 'blind_to_method': True}), encoding='utf-8')
    with pytest.raises(ValueError, match='Human review'):
        grade('task_001', folder, review=receipt)


def test_rejects_nonfinite_timeout(tmp_path):
    with pytest.raises(ValueError):
        grade('task_001', tmp_path, timeout=float('nan'))


def test_noncritical_r4_failure_does_not_override_original_rubric(tmp_path):
    folder = create_fixture('task_001', tmp_path / 'bool-bug')
    p = folder / 'candidate.py'
    p.write_text(p.read_text(encoding='utf-8').replace('if type(count) is not int:', 'if not isinstance(count, int):'), encoding='utf-8')
    result = grade('task_001', folder)
    assert result['criteria']['R4']['passed'] is False
    assert result['automated_score'] == 6
    assert result['status'] == 'PENDING_HUMAN_REVIEW'


def test_candidate_import_exception_is_execution_error(tmp_path):
    folder = create_fixture('task_001', tmp_path / 'import-failure')
    p = folder / 'candidate.py'
    p.write_text(p.read_text(encoding='utf-8').replace('def chunked_iter(src, size, count=None, **kw):', 'def chunked_iter(src, size, count=(1/0), **kw):'), encoding='utf-8')
    result = grade('task_001', folder)
    assert result['status'] == 'EXECUTION_ERROR' and result['success'] is False
