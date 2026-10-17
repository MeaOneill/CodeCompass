"""Batch B0/B1/B2/beam, one public input and one independent replay policy."""
import argparse
from datetime import datetime, timezone
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src')); sys.path.insert(0, str(ROOT))
from scripts.B.comparison.adapters import invoke
from scripts.B.comparison.b1 import SpendMeter
from scripts.B.comparison.metrics import aggregate


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def cases():
    source = ROOT/'experiments/A/A-D04-mechanism01/cases'
    for name in ['task_001-sim_unknown', 'task_001-sim_evidence', 'task_002-sim_unknown', 'task_002-sim_evidence', 'shared', 'cost_gap']:
        case = json.loads((source/name/'input.json').read_text(encoding='utf-8'))
        if not case.get('real_source_task'):
            # Explicit fixture document order, fixed independently of result/optimum.
            case['config']['routes'] = {case['request']['task_id']: ['s','a','b'] if name=='shared' else ['a','b','c']}
        yield case


def main():
    p = argparse.ArgumentParser(description='B-D04统一比较；默认不调用API，B1未配置记未运行，保留失败。')
    p.add_argument('--run-id', required=True)
    p.add_argument('--config', type=Path, default=ROOT/'configs/B/D04_comparison.json')
    a = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', a.run_id): p.error('Invalid run ID')
    config = json.loads(a.config.read_text(encoding='utf-8'))
    if config['methods'] != ['B0','B1','B2','beam']: p.error('D04 method set is fixed')
    out = ROOT/'experiments/B'/a.run_id
    if out.exists(): p.error('Do not overwrite evidence; choose a new run ID')
    out.mkdir(parents=True)
    prompt_path = ROOT/'configs/B/B1_direct_v1.txt'; prompt = prompt_path.read_text(encoding='utf-8')
    meter = SpendMeter(config['b1']['budget_usd'] or 0); rows = []
    for case in cases():
        hashes = set()
        save(out/'cases'/case['case_id']/'input.json', case)
        for method in config['methods']:
            row, context = invoke(ROOT, case, method, config, prompt, meter)
            rows.append(row); hashes.add(row['context_hash'])
            save(out/'cases'/case['case_id']/(method+'.json'), row)
            save(out/'cases'/case['case_id']/'public_context.json', context)
            print(case['case_id'], method, row['execution_status'],
                  'cost='+str(row['metrics']['replayed_proxy_cost'] if row['metrics'] else None))
        assert len(hashes)==1, 'Methods received different public information'
    totals = {m: aggregate([r for r in rows if r['method']==m]) for m in config['methods']}
    summary = {'run_id': a.run_id, 'kind': 'exploratory_development_comparison', 'rows': rows,
               'aggregates': totals, 'B1_live_calls': sum(len(r['calls']) for r in rows),
               'reserved_api_usd': meter.reserved, 'formal_study_ready': False,
               'human_profiles': 0, 'learning_effect': 'NOT_MEASURED', 'independent_relevance_labels': 0}
    save(out/'summary.json', summary); save(out/'config.json', config)
    (out/'prompt.txt').write_text(prompt, encoding='utf-8', newline='\n')
    fields = ['case_id','method','source_kind','profile_is_simulated','attempted','execution_status','context_hash',
              'coverage_tp','required_concepts','coverage_ratio','hard_violations','hard_relations_checked',
              'prerequisite_violation_rate','source_spans_valid','source_spans_checked','source_reference_validity',
              'replayed_proxy_cost','elapsed_seconds','api_cost_usd','format_repairs','human_task_success']
    with (out/'T02.csv').open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n'); w.writeheader()
        for row in rows:
            flat = {**row, **(row['metrics'] or {})}
            w.writerow({k: 'NA' if flat.get(k) is None else flat[k] for k in fields})
    paths = [*sorted((ROOT/'scripts/B/comparison').glob('*.py')), Path(__file__),
             ROOT/'configs/B/D04_comparison.json', prompt_path,
             *sorted((ROOT/'src/codecompass/planner').glob('*.py')),
             *sorted((ROOT/'src/codecompass/learner').glob('*.py')),
             ROOT/'scripts/B/b0.py', ROOT/'scripts/A/run_d03.py', ROOT/'schemas/contracts-1.1.schema.json',
             *sorted((ROOT/'benchmarks/dev/D03').glob('*.json')),
             ROOT/'benchmarks/sources/boltons/snapshot.json']
    manifest = []
    for path in paths:
        rel = path.relative_to(ROOT); frozen = out/'code_snapshot'/rel
        frozen.parent.mkdir(parents=True, exist_ok=True); frozen.write_bytes(path.read_bytes())
        manifest.append({'path': rel.as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'frozen_copy': frozen.relative_to(ROOT).as_posix()})
    save(out/'input_manifest.json', manifest)
    save(out/'registration.json', {'task': 'B-D04', 'owner': '成员B / 糯糯', 'executor': 'Codex Agent B',
         'machine': platform.node(), 'model_id': None, 'actual_time': datetime.now(timezone.utc).isoformat(),
         'planned_day': '2026-10-18', 'command': sys.argv, 'exit_code': 0,
         'base': '722b9c46676d05b7492f7250b58a9d61c60d5124',
         'source_head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'B1': 'NOT_CONFIGURED' if not config['b1']['enabled'] else 'SEE_CALL_LOGS',
         'independent_human_review': 'NOT_REVIEWED', 'formal_study_ready': False})
    print('开发比较完成；B1状态与调用费用见summary；未运行不填失败率0。', out)
    return 0


if __name__ == '__main__': raise SystemExit(main())
