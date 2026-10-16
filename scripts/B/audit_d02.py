"""Strict B-D02 audit: technical pass and whole-task approval are separate."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from codecompass.retrieval.samples import contract_validator, load_object
from codecompass.graph import read_snapshot, validate_span
from jsonschema import Draft202012Validator


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', required=True)
    p.add_argument('--evaluation-run', default='B-D02-20261016-evaluation04')
    p.add_argument('--shared-b0-run', default='B-D02-20261016-B0-shared02')
    p.add_argument('--proposal-b0-run', default='B-D02-20261016-B0-lines02')
    a = p.parse_args()
    if any(not v.replace('-', '').replace('_', '').isalnum() for v in vars(a).values()):
        p.error('Invalid run identifier')
    out = ROOT / 'experiments/B' / a.run_id
    out.mkdir(parents=True, exist_ok=False)
    checks = []
    def check(name, condition):
        checks.append({'check': name, 'passed': bool(condition)})
    cat = json.loads((ROOT / 'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    dev = [t for t in cat['tasks'] if t['split'] == 'dev']
    held = [t for t in cat['tasks'] if t['split'] == 'test_candidate']
    check('candidate count 4 dev / 8 module-held-out', len(dev) == 4 and len(held) == 8)
    check('module split disjoint', {t['module'] for t in dev}.isdisjoint({t['module'] for t in held}))
    validator = contract_validator(ROOT)
    spans = 0
    for folder in ('boltons', 'boltons_B_D02'):
        bundle = ROOT / 'benchmarks/sources' / folder
        snap = json.loads((bundle / 'snapshot.json').read_text(encoding='utf-8'))
        validator.validate(snap)
        contents = read_snapshot(bundle, snap)
        for task in cat['tasks']:
            for span in task['source_spans']:
                if span['snapshot_id'] == snap['snapshot_id']:
                    validate_span(span, snap, contents);spans += 1
    check('22 real source spans verified', spans == 22)
    check('BSD license preserved exactly', (ROOT / 'benchmarks/sources/boltons/LICENSE').read_bytes() == (ROOT / 'benchmarks/sources/boltons_B_D02/LICENSE').read_bytes())
    protected = ['src/codecompass/graph', 'src/codecompass/learner', 'src/codecompass/planner', 'schemas', 'benchmarks/dev/task_001.json', 'benchmarks/dev/task_001_units.json', 'benchmarks/sources/boltons', 'experiments/A', 'docs/A', 'report_materials/A']
    diff = subprocess.run(['git', 'diff', '--name-only', '30069ce468a52b68a0d3bfb62bb49b1cce0f2104', '--', *protected], cwd=ROOT, capture_output=True, text=True)
    check('A-owned protected inputs unchanged', diff.returncode == 0 and not diff.stdout.strip())
    tracked = subprocess.check_output(['git', 'ls-files', '--', 'private_evaluation'], cwd=ROOT, text=True)
    ignored = subprocess.run(['git', 'check-ignore', 'private_evaluation/B-D02/keys.json'], cwd=ROOT, capture_output=True)
    check('private key excluded from Git', not tracked.strip() and ignored.returncode == 0)
    denied = False
    try: load_object(ROOT, 'private_evaluation/B-D02/keys.json')
    except ValueError: denied = True
    check('app object reader refuses private path before reading', denied)
    check('app/src imports no evaluator', all('scripts.B.evaluation' not in f.read_text(encoding='utf-8') for directory in ('app', 'src') for f in (ROOT / directory).rglob('*.py')))
    evaluation = json.loads((ROOT / 'experiments/B' / a.evaluation_run / 'registration.json').read_text(encoding='utf-8'))
    stdout = (ROOT / 'experiments/B' / a.evaluation_run / 'pytest.stdout.txt').read_text(encoding='utf-8')
    count = re.search(r'(\d+) passed', stdout)
    check('cumulative regression suite passes', evaluation['pytest_exit_code'] == 0 and count is not None)
    check('14 dev fixture expectations pass, no human success invented', len(evaluation['fixture_checks']) == 14 and all(row['passed'] for row in evaluation['fixture_checks']) and evaluation['human_review'] == 'NOT_REVIEWED')
    key_receipt = json.loads((ROOT / 'benchmarks/B/private_key_manifest.json').read_text(encoding='utf-8'))
    check('held-out fixture used registered private key hash', evaluation['private_key_sha256'] == key_receipt['sha256'])
    unified = json.loads((ROOT / 'configs/B/unified_run.schema.json').read_text(encoding='utf-8'))
    b0 = []
    for run in (a.shared_b0_run, a.proposal_b0_run):
        result = json.loads((ROOT / 'experiments/B' / run / 'result.json').read_text(encoding='utf-8'))
        Draft202012Validator(unified).validate(result)
        check(run + ' preserves no learning-success claim', result['independent_task_success'] is None and result['formal_comparison_eligible'] is False)
        b0.append(result)
    check('shared null-cost input fails explicitly', b0[0]['status'] == 'INPUT_INCOMPLETE' and b0[0]['exit_code'] == 2 and b0[0]['estimated_cost'] is None)
    check('explicit measured line proxy returns fixed route', b0[1]['status'] == 'ROUTE_PREFIX' and b0[1]['estimated_cost'] == 80 and b0[1]['cost_policy'] == 'source_lines_proposal')
    figdir = ROOT / 'report_materials/B/B-D02'
    fm = json.loads((figdir / 'figure_manifest.json').read_text(encoding='utf-8'))
    for row in fm['inputs'] + fm['outputs']:
        check('figure hash ' + row['path'], hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['sha256'])
    for name in ('T01_inventory', 'B0_task001_route'):
        with Image.open(figdir / (name + '.png')) as im:
            check(name + ' PNG 300dpi', all(abs(v - 300) < .1 for v in im.info['dpi']));im.verify()
        svg = ET.parse(figdir / (name + '.svg')).getroot()
        check(name + ' native vector text, no raster embed', bool(svg.findall('{http://www.w3.org/2000/svg}text')) and not svg.findall('.//{http://www.w3.org/2000/svg}image'))
    gates = json.loads((ROOT / 'docs/B/B-D02_review_gates.json').read_text(encoding='utf-8'))
    approved_ids = {t['task_id'] for t in cat['tasks'] if t['human_reviewer'] and t['review_status'] == 'HUMAN_APPROVED'}
    reviews_complete = len(approved_ids & {t['task_id'] for t in dev}) >= 4 and len(approved_ids & {t['task_id'] for t in held}) >= 8 and bool(gates['human_task_review_receipts'])
    blockers = []
    if not reviews_complete or not gates['pilot_receipts']:
        blockers.append('12 candidate specifications are not a human-approved/piloted 4/8 task set; difficulty, concepts and actual timing remain unverified.')
    if not gates['b0_human_review_receipt']:
        blockers.append('B0 fixed-route candidate still lacks an independently human-confirmed route.')
    if not gates['new_task_contract_integration_receipt']:
        blockers.append('New task origins need A contract integration; evaluation specs are not yet planner CodeTask objects.')
    if not gates['common_cost_integration_receipt']:
        blockers.append('Shared costs remain undefined; source_lines_proposal is not an approved common formal-comparison cost.')
    # Registry paths do not themselves authenticate or verify a person's review.
    # Missing receipts fail closed; future receipts require a new explicit audit.
    if any(gates[k] for k in ('human_task_review_receipts', 'pilot_receipts', 'b0_human_review_receipt', 'common_cost_integration_receipt', 'new_task_contract_integration_receipt')):
        blockers.append('New receipt registry entries require explicit artifact/version/person verification before approval; registry text alone is insufficient.')
    technical = all(c['passed'] for c in checks)
    overall = technical and not blockers
    record = {'task_id': 'B-D02', 'evidence_type': 'development_validation', 'audit_type': 'same_Agent_strict_self_audit_not_independent_human_review', 'regression_tests_passed': int(count[1]) if count else None, 'checks': checks, 'technical_checks_passed': technical, 'whole_task_gate_passed': overall, 'next_day_allowed': overall, 'blockers': blockers, 'human_reviewed_tasks': sum(t['human_reviewer'] is not None for t in cat['tasks']), 'pilot_count': 0, 'frozen_tasks': sum(t['frozen'] for t in cat['tasks']), 'formal_experiments': 0, 'exit_code': 0 if overall else 2 if technical else 1}
    (out / 'audit.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'technical_checks_passed': technical, 'tests': record['regression_tests_passed'], 'whole_task_gate_passed': overall, 'next_day_allowed': overall, 'exit_code': record['exit_code']}))
    return record['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
