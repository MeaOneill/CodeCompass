import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import ValidationError
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from app.events import validate_event
from codecompass.retrieval.samples import load_dev_bundle, load_object, safe_path

ROOT = Path(__file__).resolve().parents[2]


def test_real_bundle_is_read_only():
    inputs = [p for folder in ('schemas', 'benchmarks') for p in (ROOT / folder).rglob('*') if p.is_file()]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    b = load_dev_bundle(ROOT)
    assert b['snapshot']['commit'] == '4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d'
    assert all(u['base_cost'] is None for u in b['units'])
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}


@pytest.mark.parametrize('path', ['../secret', '/absolute', 'C:/absolute', 'a\\b'])
def test_unsafe_paths_rejected(path):
    with pytest.raises(ValueError):
        safe_path(ROOT, path)


def test_fixture_marker_preserved():
    assert load_object(ROOT, 'schemas/examples/plan_result.json')['is_fixture'] is True


def test_tamper_detected(tmp_path):
    for folder in ('schemas', 'benchmarks'):
        shutil.copytree(ROOT / folder, tmp_path / folder)
    source = tmp_path / 'benchmarks/sources/boltons/boltons/iterutils.py'
    source.write_bytes(source.read_bytes() + b'\n# tamper\n')
    with pytest.raises(ValueError, match='hash mismatch'):
        load_dev_bundle(tmp_path)


def events():
    return json.loads((ROOT / 'docs/B/event_examples.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('index', range(5))
def test_event_examples(index):
    validate_event(ROOT, events()[index])


@pytest.mark.parametrize('kind,code,error,checkpoint', [('succeeded', 1, None, None), ('failed', 0, None, None), ('paused', None, None, None), ('resumed', None, None, None)])
def test_event_semantic_failure(kind, code, error, checkpoint):
    e = copy.deepcopy(events()[0])
    e['event_type'] = kind
    e['payload'].update(exit_code=code, error=error, resume_from=checkpoint)
    with pytest.raises(ValueError):
        validate_event(ROOT, e)


def test_invalid_time_rejected():
    e = copy.deepcopy(events()[0])
    e['timestamp'] = 'yesterday'
    with pytest.raises(ValidationError):
        validate_event(ROOT, e)


def test_session_profile_schema():
    profile = json.loads((ROOT / 'docs/B/session_event.schema.json').read_text(encoding='utf-8'))
    contract = json.loads((ROOT / 'schemas/contracts.schema.json').read_text(encoding='utf-8'))
    uri = (ROOT / 'schemas/contracts.schema.json').as_uri()
    profile['$id'] = (ROOT / 'docs/B/session_event.schema.json').as_uri()
    registry = Registry().with_resource(uri, Resource.from_contents(contract))
    validator = Draft202012Validator(profile, registry=registry)
    for event in events():
        validator.validate(event)
    bad = copy.deepcopy(events()[1])
    bad['payload']['resume_from'] = None
    assert not validator.is_valid(bad)
