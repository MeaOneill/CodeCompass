"""B G1 review: replay stored evidence and independent fixed-source validation."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from codecompass.graph import read_snapshot, validate_span
from codecompass.learner import initial_state, update_evidence, planning_rows, beta_quantile
from codecompass.planner import check_plan
from codecompass.issues.candidates import match_issues
from jsonschema import Draft202012Validator, FormatChecker


def load(p):
    return json.loads(p.read_text(encoding='utf-8'))


def audit(source, figures=None):
    checks = []
    def check(name, condition):
        checks.append({'check': name, 'passed': bool(condition)})
        if not condition:
            raise AssertionError(name)
    manifest = load(source/'input_manifest.json')
    for row in manifest:
        check('current bytes '+row['path'], hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest() == row['sha256'])
        check('frozen bytes '+row['path'], hashlib.sha256((ROOT/row['frozen_copy']).read_bytes()).hexdigest() == row['sha256'])
    capability = load(source/'capability.json')
    events = load(source/'events.json')
    check('no invented human evidence', events['is_simulated'] and events['human_answers'] == 0)
    state = initial_state('sim-anon-B03-01', is_simulated=True)
    validator = Draft202012Validator(load(ROOT/'schemas/contracts-1.1.schema.json'), format_checker=FormatChecker())
    for row in events['events']:
        validator.validate(row['evidence'])
        state, decision = update_evidence(state, row['evidence'], allow_simulated=True)
        check('pure A evidence replay '+row['evidence']['evidence_id'], decision == row['decision'])
    check('process restore exactly equals replay', json.loads(load(source/'restart_process.json')['stdout']) == state)
    check('fresh process exited zero', load(source/'restart_process.json')['exit_code'] == 0)
    stages = {r['stage']: r for r in capability['stages']}
    check('initial prior unknown', stages['initial']['unknown'] and stages['initial']['a'] == stages['initial']['b'] == 1)
    check('correct a increments', stages['correct']['a'] == 2 and stages['correct']['b'] == 1)
    check('incorrect b increments', stages['incorrect']['a'] == stages['incorrect']['b'] == 2)
    check('duplicate and reading no inflation', stages['incorrect']['a'] == stages['duplicate_and_reading']['a'] and stages['incorrect']['b'] == stages['duplicate_and_reading']['b'])
    for row in capability['stages']:
        check('probability/uncertainty '+row['stage'], row['mean'] == row['a']/(row['a']+row['b']) and
              row['lower_q10'] == beta_quantile(row['a'], row['b'], .1) and row['upper_q90'] == beta_quantile(row['a'], row['b'], .9))
    snap = load(ROOT/'benchmarks/sources/boltons/snapshot.json')
    contents = read_snapshot(ROOT/'benchmarks/sources/boltons', snap)
    units = load(ROOT/'benchmarks/dev/D03/units.json')
    for unit in units:
        for span in unit['source_spans']:
            validate_span(span, snap, contents)
        check('real source '+unit['id'], not unit['is_fixture'] and len(unit['source_spans']) > 0)
        check('soft teaching edges '+unit['id'], not any(e['hard'] for e in unit['prerequisites']))
    routes = load(source/'routes.json')
    subset = [u for u in units if u['id'] in load(ROOT/'benchmarks/dev/D03/task_001.json')['learning_unit_ids']]
    for case in routes:
        folder = source/'stages'/case['stage']
        req = load(folder/'request.json'); ledger = load(folder/'ledger.json')
        check('request uses persisted ledger '+case['stage'], req['learner_state'] == planning_rows(ledger, req['snapshot_id'], allow_simulated=True))
        gate = load(folder/'detail.json')['gate']
        check('route legal '+case['stage'], check_plan(req, subset, case['plan'], gate)['structurally_valid'])
        check('B0 legal '+case['stage'], check_plan(req, subset, case['B0'], gate)['structurally_valid'])
    check('distinct simulated evidence changes actual route', routes[0]['plan']['ordered_units'] != routes[-1]['plan']['ordered_units'])
    check('B0 fixed across states', len({tuple(r['B0']['ordered_units']) for r in routes}) == 1)
    snapshot = load(source/'issue_snapshot.json')
    check('real Issues with capture time and partial query boundary', snapshot['is_fixture'] is False and snapshot['http_status'] == 200 and not snapshot['pagination']['complete_repository'])
    gaps = [r['concept_id'] for r in load(source/'stages/distinct_simulated_items/summary.json') if r['lower_q10'] < .7]
    matches = match_issues(snapshot, subset, gaps)
    check('Issue match replay', matches == load(source/'issue_matches.json'))
    check('no recommendation accuracy invented', matches['recommendation_accuracy'] is None and matches['independent_relevance_labels'] == 0)
    for issue in matches['historical']:
        check('historical closed excluded #'+str(issue['number']), issue['disposition'] == 'HISTORICAL_CLOSED_NOT_ACTIONABLE')
    if figures:
        from PIL import Image
        fm = load(figures/'figure_manifest.json')
        for figure in fm:
            for row in figure['files']:
                check('figure/source bytes '+row['path'], hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest() == row['sha256'])
            with Image.open(ROOT/figure['png']) as im:
                check('300dpi '+figure['figure_id'], all(abs(d-300) < .1 for d in im.info['dpi']))
            if figure.get('svg'):
                root = ET.parse(ROOT/figure['svg']).getroot()
                check('native SVG '+figure['figure_id'], bool(root.findall('.//{http://www.w3.org/2000/svg}text')) and not root.findall('.//{http://www.w3.org/2000/svg}image'))
    return {'task': 'B-D03', 'engineering_passed': True, 'checks': checks,
            'independent_human_review': 'NOT_REVIEWED', 'formal_study_ready': False,
            'real_participants': 0, 'scope': 'G1 engineering feasibility only', 'exit_code': 0}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--figures', type=Path)
    a = p.parse_args()
    if a.output.exists(): p.error('Do not overwrite audit evidence')
    try:
        result = audit(a.source, a.figures)
    except Exception as e:
        result = {'engineering_passed': False, 'error': repr(e), 'exit_code': 1}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'checks'}, ensure_ascii=False))
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
