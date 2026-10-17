"""Identical public context and legality policy for all D04 methods."""
import copy
from pathlib import Path
import json
import time
from jsonschema import Draft202012Validator, FormatChecker
from codecompass.graph import read_snapshot, validate_span
from codecompass.learner import mastery_gate
from codecompass.planner.core import validate_request
from codecompass.planner.search_service import solve_request
from codecompass.planner.comparison_validator import verify_result
from scripts.A.run_d03 import b0_adapter
from .b1 import run_b1, digest
from .metrics import evaluate


def public_packet(root, case):
    request, units, state, config = [copy.deepcopy(case[k]) for k in ('request', 'units', 'state', 'config')]
    validate_request(request, units, state, config)
    validator = Draft202012Validator(json.loads((root/'schemas/contracts-1.1.schema.json').read_text(encoding='utf-8')), format_checker=FormatChecker())
    validator.validate(request)
    for unit in units: validator.validate(unit)
    gate = mastery_gate(state, request['snapshot_id'], {c for u in units for c in u['concept_ids']}|set(request['target_concept_ids']),
                        threshold=config['threshold'], quantile=config['quantile'], allow_simulated=request['is_fixture'])
    source = None; materials = []
    real = any(not u['is_fixture'] for u in units)
    if real:
        matches = []
        for path in (root/'benchmarks/sources').glob('*/snapshot.json'):
            snapshot = json.loads(path.read_text(encoding='utf-8'))
            if snapshot['snapshot_id'] == request['snapshot_id']: matches.append((path.parent, snapshot))
        if len(matches) != 1: raise ValueError('Unique fixed snapshot required')
        folder, snapshot = matches[0]; contents = read_snapshot(folder, snapshot); source = (snapshot, contents)
        for unit in units:
            for span in unit['source_spans']:
                validate_span(span, snapshot, contents)
                materials.append({'unit_id': unit['id'], 'source_span': span,
                                  'text': '\n'.join(contents[span['path']].decode('utf-8').splitlines()[span['start_line']-1:span['end_line']])})
        if request['task_id'] not in ('task_001', 'task_002'):
            raise ValueError('D04 prompt allows only the two reviewed public development tasks')
        task = json.loads((root/'benchmarks/dev/D03'/f'{request["task_id"]}.json').read_text(encoding='utf-8'))
        if set(request['target_concept_ids']) != set(task['required_concept_ids']):
            raise ValueError('Task goals differ from reviewed public specification')
        public_task = {k: task[k] for k in ('task_id', 'title', 'goal', 'requirements', 'repo_commit', 'source_spans')}
    else:
        public_task = {'task_id': request['task_id'], 'kind': 'EXPLICIT_SYNTHETIC_MECHANISM_FIXTURE'}
    context = {'request': request, 'units': units, 'learner_ledger': state,
               'learner_gate': gate, 'config': {k: config[k] for k in ('version', 'threshold', 'quantile')},
               'task': public_task, 'source_materials': materials}
    # No rubric keys, evaluator code, expected routes, exact certificates or responses.
    return context, gate, source, validator


def invoke(root, case, method, comparison_config, prompt, meter, *, transport=None):
    started = time.perf_counter()
    context, gate, source, validator = public_packet(root, case)
    request, units, state, config = [context[k] for k in ('request', 'units', 'learner_ledger', 'config')]
    row = {'method': method, 'case_id': case['case_id'], 'context_hash': digest(context),
           'attempted': True, 'execution_status': None, 'plan': None, 'metrics': None,
           'source_kind': 'fixed_real_task' if source else 'synthetic_structure',
           'profile_is_simulated': state['is_simulated'], 'human_task_success': None,
           'calls': [], 'model_id': None, 'api_cost_usd': None, 'format_repairs': 0}
    try:
        if method == 'B1':
            raw = run_b1(context, comparison_config['b1'], prompt, meter, transport=transport)
            row['B1_trace'] = raw; row['calls'] = raw['calls']; row['attempted'] = raw['attempted']
            row['model_id'] = raw['model_requested']; row['format_repairs'] = sum(c['kind']=='format_repair' for c in raw['calls'])
            estimates = [c['estimated_cost_usd'] for c in raw['calls']]
            row['api_cost_usd'] = sum(estimates) if estimates and all(v is not None for v in estimates) else None
            if raw['status'] != 'PARSED':
                row['execution_status'] = raw['status']; return row, context
            route = raw['route']; by_id = {u['id']:u for u in units}
            known = {c for c,g in gate.items() if g['mastered']}|{c for uid in route if uid in by_id for c in by_id[uid]['concept_ids']}
            goals = set(request['target_concept_ids']); missing = sorted(goals-known)
            plan = {'schema_version': '1.0.0', 'object_type': 'PlanResult', 'is_fixture': request['is_fixture'],
                    'plan_id': request['request_id']+'-B1', 'request_id': request['request_id'],
                    'status': 'FEASIBLE' if not missing else 'NO_FEASIBLE_FOUND', 'ordered_units': route,
                    'coverage': {'required_concept_ids': sorted(goals), 'covered_concept_ids': sorted(goals&known), 'ratio': len(goals&known)/len(goals) if goals else None},
                    'estimated_cost': sum(by_id[u]['base_cost'] for u in route if u in by_id), 'cost_unit': request['cost_unit'],
                    'unmet_constraints': ['uncovered target: '+c for c in missing], 'reason_trace': [], 'proof_path': None}
            detail = {'certificate': None}
        elif method == 'B0':
            plan, detail = b0_adapter(request, units, case['config']['routes'][request['task_id']], gate)
        elif method in ('B2', 'beam'):
            plan, detail = solve_request(root, request, units, state, config, method=method,
                                          options=comparison_config['beam_options'] if method=='beam' else None)
        else: raise ValueError('Unknown method')
        row['plan'] = plan; row['details'] = detail; validator.validate(plan)
        metrics = evaluate(request, units, gate, plan, source)
        replay = verify_result(request, units, plan, gate, detail.get('certificate'))
        row['metrics'] = metrics; row['independent_replay'] = replay
        row['execution_status'] = plan['status'] if metrics['legal'] and replay['valid'] else 'ALGORITHM_INVALID'
        return row, context
    except Exception as e:
        row['execution_status'] = 'ADAPTER_ERROR'; row['error_type'] = type(e).__name__
        row['error_message'] = str(e)[:300]
        return row, locals().get('context')
    finally:
        row['elapsed_seconds'] = time.perf_counter()-started
