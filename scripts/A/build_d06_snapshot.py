"""One-time candidate snapshot. Formal freeze and tag creation are deliberately absent."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT/'configs/frozen/freeze_manifest.json'


def build():
    if MANIFEST.exists():
        raise SystemExit('Existing version is immutable; create a new version with affected_run_ids')
    files = set()
    for folder, pattern in [('src/codecompass','*.py'), ('schemas','*.json'),
                            ('benchmarks/dev/D03','*.json'), ('benchmarks/sources/boltons','*')]:
        files.update(p for p in (ROOT/folder).rglob(pattern) if p.is_file() and '__pycache__' not in p.parts)
    for rel in [
        'configs/frozen/v0.1-candidate/candidate.json', 'configs/A/D03_common.json',
        'configs/A/D03_profiles.json', 'configs/A/D05_scan.json',
        'scripts/A/run_d06.py', 'scripts/A/audit_d06.py', 'scripts/A/build_d06_snapshot.py',
        'scripts/A/draw_d06.py', 'tests/A/test_g2_d06.py',
        'scripts/A/cases_d05.py', 'scripts/A/cases_d04.py', 'scripts/A/run_d03.py',
        'scripts/A/requirements_d05_figures.hashes.txt',
        'scripts/B/requirements-d01-win-py312.hashes.txt',
        'experiments/B/B-D04-deepseek-live01/prompt.txt',
        'experiments/B/B-D04-deepseek-live01/config.json',
        'experiments/B/B-D04-deepseek-live01/registration.json',
        'experiments/A/A-D05-development01/summary.json',
        'experiments/A/A-D05-development01/comparison.csv',
        'experiments/A/A-D05-development01/input_manifest.json',
        'experiments/A/A-D06-controls03/summary.json',
        'experiments/A/A-D06-controls03/comparison.csv',
        'experiments/A/A-D06-controls03/registration.json',
        'docs/B/measurement_rules.md', 'docs/related_work.md',
        'docs/references/A-D02-source_provenance.json',
        'CodeCompass计划/refine-logs/EXPERIMENT_PLAN.md',
    ]:
        files.add(ROOT/rel)
    files.update((ROOT/'experiments/A/A-D06-controls03/inputs').glob('*.json'))
    files.update((ROOT/'experiments/A/A-D06-controls03/runs').rglob('*.json'))
    entries = []
    for p in sorted(files):
        rel = p.relative_to(ROOT)
        dest = ROOT/'configs/frozen/v0.1-candidate/snapshots'/rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(p.read_bytes())
        entries.append(dict(path=rel.as_posix(), snapshot=dest.relative_to(ROOT).as_posix(),
                            sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    result = dict(version='v0.1-candidate', status='CANDIDATE_ONLY_G2_NOT_PASSED',
        owner='成员A', executor='Codex Agent A', machine='糯糯',
        planned_date='2026-10-20', actual_date='2026-10-19',
        source_base_sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        code_version='base SHA plus exact per-file hashes and byte snapshots; final Git checkpoint in sync receipt',
        selection_data_split='dev', test_answers_used=False, formal_test_data_hash=None,
        formal_evaluator_hash=None, formal_study_ready=False, tag_created=False,
        provider_model_revision=None, model_revision_note='historical deepseek-flash alias, exact provider revision unknown; no new calls',
        seed=0, randomness='deterministic lexical ordering; historical fixture random tests have their own seeds',
        evaluator='development route/accounting audits only; independent final scoring unavailable',
        development_run_ids=['A-D04-mechanism01','A-D05-development01','A-D06-controls03'],
        g2_blockers=['B-D06 formal protocol/task split/scoring versions not delivered',
                     'dynamic fair B1 not integrated; B1_saved only',
                     'D06 controlled quiz timing not integrated into B development UI',
                     'independent human source/teaching-edge review and A/B confirmations absent',
                     'main not integrated/confirmed; no formal milestone tag'],
        change_policy=dict(new_version_required=True, affected_run_ids_required=True,
                           affected_run_ids=['A-D06-controls03'], test_answer_tuning_forbidden=True,
                           existing_version_overwrite_forbidden=True),
        independent_human_review='NOT_REVIEWED', files=entries)
    MANIFEST.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(candidate_files=len(entries), formal_freeze=False)))


if __name__ == '__main__':
    build()
