"""Fixed reading order, compiled before Ours exists; no graph/planner imports."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from codecompass.retrieval.samples import load_dev_bundle


def fixed_order(units, order, budget, cost_unit):
    if type(budget) not in (int, float) or not __import__('math').isfinite(budget) or budget < 0 or cost_unit != 'proxy_cost':
        raise ValueError('Finite nonnegative proxy_cost budget required')
    by_id = {u['id']: u for u in units}
    if len(by_id) != len(units) or len(set(order)) != len(order) or set(order) - set(by_id):
        raise ValueError('Invalid fixed-route unit IDs')
    if any(by_id[uid]['base_cost'] is None for uid in order):
        return {'status': 'INPUT_INCOMPLETE', 'ordered_units': [], 'reading_order_only': order, 'estimated_cost': None, 'unmet_constraints': ['base_cost missing; no budget-feasible claim'], 'cost_unit': cost_unit}
    total = 0
    chosen = []
    for uid in order:
        cost = by_id[uid]['base_cost']
        if type(cost) not in (int, float) or not __import__('math').isfinite(cost) or cost < 0 or by_id[uid]['cost_unit'] != cost_unit:
            raise ValueError('Invalid unit cost')
        if total + cost > budget:
            break  # B0 truncates a fixed prefix; never reorders or cherry-picks.
        total += cost
        chosen.append(uid)
    return {'status': 'ROUTE_PREFIX', 'ordered_units': chosen, 'reading_order_only': order, 'estimated_cost': total, 'unmet_constraints': [] if len(chosen) == len(order) else ['fixed route truncated by budget'], 'cost_unit': cost_unit}


def main():
    p = argparse.ArgumentParser(description='B0 fixed reading-order baseline. Missing costs are explicit failures, never zero.')
    p.add_argument('--task', default='task_001', choices=['task_001'])
    p.add_argument('--budget', type=float, required=True)
    p.add_argument('--run-id', required=True)
    p.add_argument('--cost-policy', choices=['shared', 'source_lines_proposal'], default='shared', help='Explicit B-only static proxy proposal; never changes shared units or implies human minutes')
    a = p.parse_args()
    if not a.run_id.replace('-', '').replace('_', '').isalnum():
        p.error('Invalid run-id')
    out = ROOT / 'experiments/B' / a.run_id
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    b = load_dev_bundle(ROOT)
    (out / 'input_units.json').write_bytes((ROOT / 'benchmarks/dev/task_001_units.json').read_bytes())
    (out / 'config.json').write_bytes((ROOT / 'configs/B/B0_fixed.json').read_bytes())
    config = json.loads((ROOT / 'configs/B/B0_fixed.json').read_text(encoding='utf-8'))
    costs = None
    if a.cost_policy == 'source_lines_proposal':
        # Measure fixed source ranges; this is a new declared proxy, not filling
        # missing shared base_cost with zero or a claimed learned estimator.
        costs = {u['id']: sum(s['end_line'] - s['start_line'] + 1 for s in u['source_spans']) for u in b['units']}
        b['units'] = [dict(u, base_cost=costs[u['id']]) for u in b['units']]
    result = fixed_order(b['units'], config['routes'][a.task], a.budget, 'proxy_cost')
    result.update(method='B0', task_id=a.task, run_id=a.run_id, schema='B-unified-run-0.1', evidence_type='development_validation', is_fixture=False, requested_budget=a.budget, config_version=config['version'], config_hash=hashlib.sha256((ROOT / 'configs/B/B0_fixed.json').read_bytes()).hexdigest(), data_hash=hashlib.sha256((ROOT / 'benchmarks/dev/task_001_units.json').read_bytes()).hexdigest(), code_commit=None, elapsed_seconds=time.perf_counter() - started, independent_task_success=None, model_id=None, seed=None, api_cost=None, reason_trace=config['rationale'], exit_code=2 if result['status'] == 'INPUT_INCOMPLETE' else 0)
    result.update(cost_policy=a.cost_policy, measured_static_proxy_costs=costs, shared_cost_policy_approved=False, formal_comparison_eligible=False)
    if costs is not None:
        result['reason_trace'] = result['reason_trace'] + ['本次显式使用B的source_lines_proposal：固定源码行数代理，非共享成本验收、非分钟或学习效果。']
    (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
