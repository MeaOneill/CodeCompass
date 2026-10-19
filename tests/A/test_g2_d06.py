"""Meaningful isolation, budget and freeze tamper checks for D06 controls."""
import copy
import json
from pathlib import Path
import shutil

import pytest

from codecompass.planner.g2_candidate import episode, VARIANTS, semantic_result
from scripts.A.cases_d05 import near_gate_case, development_cases
from scripts.A.audit_d06 import audit

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = json.loads((ROOT/'configs/frozen/v0.1-candidate/candidate.json').read_text(encoding='utf-8'))


@pytest.mark.parametrize('outcome,expected', [('pass', 7), ('fail', 19)])
def test_feedback_value_and_negative_result(outcome, expected):
    case = near_gate_case(outcome)
    old = copy.deepcopy(case)
    main = episode(ROOT, case, CANDIDATE, 'main')
    nf = episode(ROOT, case, CANDIDATE, 'no_feedback')
    assert main['total_proxy_cost'] == expected
    assert nf['total_proxy_cost'] == 19
    assert case == old
    assert main['completed'][0] == nf['completed'][0] == 's'
    assert len(main['observed_state']['records']) == 6
    assert len(nf['planning_state']['records']) == 5
    assert nf['quiz_proxy_cost'] == main['quiz_proxy_cost'] == 1


@pytest.mark.parametrize('case', development_cases(), ids=lambda c: c['case_id'])
def test_no_selection_is_not_identifiable(case):
    a = episode(ROOT, case, CANDIDATE, 'main')
    b = episode(ROOT, case, CANDIDATE, 'no_selection')
    assert semantic_result(a) == semantic_result(b)


def test_timing_not_a_policy_effect():
    a = {'variant': 'main', 'plan': {'elapsed_seconds': .001, 'status': 'FEASIBLE'}}
    b = {'variant': 'no_selection', 'plan': {'elapsed_seconds': .002, 'status': 'FEASIBLE'}}
    assert semantic_result(a) == semantic_result(b)
    assert a['plan']['elapsed_seconds'] == .001
    b['plan']['status'] = 'TIMEOUT'
    assert semantic_result(a) != semantic_result(b)


def test_no_gate_disables_skipping_not_observation():
    r = episode(ROOT, near_gate_case('pass'), CANDIDATE, 'no_gate')
    assert r['total_proxy_cost'] == 19
    assert r['planning_state']['records'] == []
    assert len(r['observed_state']['records']) == 6
    assert not any(row['mastered'] for row in r['final_plan']['gate'].values())


@pytest.mark.parametrize('variant', VARIANTS)
def test_budget_stop_is_not_success(variant):
    candidate = {**CANDIDATE, 'budget': 1}
    r = episode(ROOT, near_gate_case(), candidate, variant)
    assert not r['coverage_complete']
    assert r['total_proxy_cost'] == 0


def test_foreign_quiz_units_rejected():
    case = near_gate_case()
    case['quizzes'][0]['cost_unit'] = 'minutes'
    with pytest.raises(ValueError):
        episode(ROOT, case, CANDIDATE, 'main')


def test_frozen_candidate_integrity():
    assert audit(ROOT)['candidate_integrity_passed']
    assert not audit(ROOT)['freeze_tag_allowed']


@pytest.mark.parametrize('attack', ['config', 'test_selection', 'formal', 'missing_source', 'path_escape'])
def test_freeze_tamper_rejected(tmp_path, attack):
    manifest_path = ROOT/'configs/frozen/freeze_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for entry in manifest['files']:
        for key in ('path', 'snapshot'):
            dest = tmp_path/entry[key]; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/entry[key], dest)
    if attack == 'config':
        (tmp_path/'configs/frozen/v0.1-candidate/candidate.json').write_text('{}', encoding='utf-8')
    elif attack == 'test_selection':
        manifest['test_answers_used'] = True
    elif attack == 'formal':
        manifest['formal_study_ready'] = True
    elif attack == 'missing_source':
        manifest['files'] = [e for e in manifest['files'] if e['path'] != 'src/codecompass/planner/adaptive.py']
    else:
        manifest['files'][0]['path'] = '../escape'
    target = tmp_path/'configs/frozen/freeze_manifest.json'; target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest), encoding='utf-8')
    assert not audit(tmp_path)['candidate_integrity_passed']
