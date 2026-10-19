"""Fail-closed candidate integrity and G2 readiness audit; never creates a tag."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def audit(root=ROOT):
    root = Path(root)
    manifest = json.loads((root/'configs/frozen/freeze_manifest.json').read_text(encoding='utf-8'))
    errors = []
    entries = manifest['files']
    for entry in entries:
        rel = Path(entry['path'])
        snapshot = Path(entry['snapshot'])
        if rel.is_absolute() or snapshot.is_absolute() or '..' in rel.parts or '..' in snapshot.parts:
            errors.append('UNSAFE_PATH'); continue
        for p in (root/rel, root/snapshot):
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != entry['sha256']:
                errors.append('HASH_MISMATCH:' + p.relative_to(root).as_posix())
    if len({e['path'] for e in entries}) != len(entries) or not entries:
        errors.append('DUPLICATE_OR_EMPTY_FILES')
    if manifest['selection_data_split'] != 'dev' or manifest['test_answers_used'] is not False:
        errors.append('TEST_SELECTION_FORBIDDEN')
    if manifest['status'] != 'CANDIDATE_ONLY_G2_NOT_PASSED' or manifest['formal_study_ready'] is not False:
        errors.append('UNSUPPORTED_FORMAL_FREEZE')
    if not manifest['g2_blockers'] or manifest['tag_created'] is not False:
        errors.append('MISSING_BLOCKERS_OR_UNAUTHORIZED_TAG')
    required = {'configs/frozen/v0.1-candidate/candidate.json',
                'src/codecompass/planner/g2_candidate.py',
                'src/codecompass/planner/adaptive.py',
                'src/codecompass/learner/model.py',
                'experiments/A/A-D06-controls03/comparison.csv',
                'experiments/B/B-D04-deepseek-live01/prompt.txt'}
    if not required <= {e['path'] for e in entries}:
        errors.append('MISSING_CRITICAL_INPUT')
    if not manifest['change_policy'].get('new_version_required') or not manifest['change_policy'].get('affected_run_ids_required'):
        errors.append('MISSING_CHANGE_POLICY')
    return dict(candidate_integrity_passed=not errors, errors=errors, checked_files=len(entries),
                g2_passed=False, formal_study_ready=False, freeze_tag_allowed=False,
                blockers=manifest['g2_blockers'], independent_human_review='NOT_REVIEWED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes((json.dumps(result, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result['candidate_integrity_passed'] else 1)
