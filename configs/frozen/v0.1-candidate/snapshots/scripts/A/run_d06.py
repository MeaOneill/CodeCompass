"""Small matched development controls; no hidden test answers or new model calls."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
from scripts.A.cases_d05 import development_cases
from codecompass.planner.g2_candidate import episode, VARIANTS, semantic_result


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not args.run_id.replace('-', '').replace('_', '').isalnum():
        parser.error('Unsafe run ID')
    started = dt.datetime.now().astimezone().isoformat()
    out = ROOT / 'experiments/A' / args.run_id
    out.mkdir(exist_ok=False)
    candidate = json.loads((ROOT / 'configs/frozen/v0.1-candidate/candidate.json').read_text(encoding='utf-8'))
    rows = []
    for case in development_cases():
        save(out / 'inputs' / (case['case_id'] + '.json'), case)
        for variant in VARIANTS:
            result = episode(ROOT, case, candidate, variant)
            # Independent accounting identities, not a second call to the solver.
            assert abs(sum(e.get('cost', 0) for e in result['events']) + result['switch_proxy_cost'] - result['total_proxy_cost']) < 1e-9
            assert len(result['completed']) == len(set(result['completed']))
            assert result['total_proxy_cost'] <= result['budget']
            save(out / 'runs' / case['case_id'] / (variant + '.json'), result)
            rows.append(dict(case_id=case['case_id'], source_kind=case['source_kind'], variant=variant,
                             total_proxy_cost=result['total_proxy_cost'], quiz_count=result['quiz_count'],
                             coverage_complete=result['coverage_complete'], status=result['final_plan']['status'],
                             feedback_is_simulated=True, human_task_success=None))
    fields = list(rows[0])
    with (out / 'comparison.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    pairs = []
    for cid in sorted({r['case_id'] for r in rows}):
        path = out / 'runs' / cid
        a = json.loads((path / 'main.json').read_text(encoding='utf-8'))
        b = json.loads((path / 'no_selection.json').read_text(encoding='utf-8'))
        assert semantic_result(a) == semantic_result(b), 'VOI-disabled no-selection control must be semantically identical'
        pairs.append(cid)
    save(out / 'summary.json', dict(run_id=out.name, rows=rows, runs=len(rows), cases=len(pairs),
        no_selection_identical_cases=pairs, diagnostic_selection_effect='NOT_IDENTIFIABLE_VOI_DISABLED',
        formal_study_ready=False, human_n=0, test_answers_read=False, model_api_calls=0))
    source_files = [*sorted((ROOT/'src/codecompass').rglob('*.py')),
                    ROOT/'scripts/A/run_d06.py', ROOT/'scripts/A/cases_d05.py',
                    ROOT/'scripts/A/cases_d04.py', ROOT/'scripts/A/run_d03.py',
                    ROOT/'configs/frozen/v0.1-candidate/candidate.json',
                    ROOT/'configs/A/D03_common.json', ROOT/'configs/A/D03_profiles.json',
                    *sorted((ROOT/'benchmarks/dev/D03').glob('*.json'))]
    for p in source_files:
        dest = out/'code_snapshot'/p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(p.read_bytes())
    save(out/'registration.json', dict(task='A-D06', owner='成员A', executor='Codex Agent A',
        machine=platform.node(), started_at=started, finished_at=dt.datetime.now().astimezone().isoformat(),
        planned_date='2026-10-20', actual_date='2026-10-19', command=[sys.executable,*sys.argv],
        source_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        file_hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        exit_code=0, formal_study_ready=False, outcomes='public synthetic fixed streams, never formal task answers'))
    print(json.dumps(dict(runs=len(rows), no_selection_identical=len(pairs), exit_code=0)))


if __name__ == '__main__':
    main()
