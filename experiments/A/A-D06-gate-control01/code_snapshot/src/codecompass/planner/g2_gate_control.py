"""Supplemental mean-gate ablation; D05 search and frozen candidate stay unchanged.

The mean policy reduces only goals and hard edges already satisfied by its
independent evidence gate. It does not manufacture learner records. Costs stay
static (alpha=0), and an original-input route replay checks the reduced problem.
"""
import copy

from codecompass.learner import mastery_gate, planning_rows
from .adaptive import remaining_plan, route_audit, validate_input


def mean_gate(state, request, units, config):
    concepts = {c for u in units for c in u['concept_ids']} | set(request['target_concept_ids'])
    gate = mastery_gate(state, request['snapshot_id'], concepts, threshold=config['threshold'],
                        quantile=config['quantile'], allow_simulated=request['is_fixture'])
    rows = planning_rows(state, request['snapshot_id'], quantile=config['quantile'],
                         allow_simulated=request['is_fixture'])
    for row in rows:
        if row['concept_id'] in gate:
            g = gate[row['concept_id']]
            g.update(posterior_mean=row['alpha']/(row['alpha']+row['beta']))
            g['mastered'] = g['posterior_mean'] >= config['threshold']
            g['reason'] = 'MEAN_ABLATION: independent current-project posterior mean threshold'
    return gate


def mean_plan(root, request, units, state, config, *, options=None):
    validate_input(root, request, units, state, config)
    gate = mean_gate(state, request, units, config)
    known = {c for c, g in gate.items() if g['mastered']}
    # Lower-bound known concepts must remain a subset; otherwise this reduction
    # is not equivalent to replacing the gate and must fail rather than guess.
    lower = mastery_gate(state, request['snapshot_id'], gate, threshold=config['threshold'],
                         quantile=config['quantile'], allow_simulated=request['is_fixture'])
    if not {c for c,g in lower.items() if g['mastered']} <= known:
        raise ValueError('Unsupported lower/mean gate relationship')
    transformed = copy.deepcopy(units)
    by_id = {u['id']: u for u in units}
    removed = []
    for unit in transformed:
        kept = []
        for edge in unit['prerequisites']:
            if edge['hard'] and set(by_id[edge['unit_id']]['concept_ids']) <= known:
                removed.append([unit['id'], edge['unit_id']])
            else:
                kept.append(edge)
        unit['prerequisites'] = kept
    reduced = copy.deepcopy(request)
    reduced['target_concept_ids'] = [c for c in request['target_concept_ids'] if c not in known]
    result = remaining_plan(root, reduced, transformed, state, config, alpha=0, gamma=0, options=options)
    replay = route_audit(request, units, gate, result['remaining'], result['unit_costs'])
    if not replay['valid']:
        raise ValueError('Mean ablation failed original-input replay')
    if result['status'] == 'FEASIBLE' and not replay['goal_complete']:
        raise ValueError('Reduced problem incorrectly claimed full original goal coverage')
    result.update(gate=gate, replay=replay, gate_policy='posterior_mean',
                  adapter=dict(known_from_independent_evidence=sorted(known), removed_hard_edges=removed,
                               removed_goals=sorted(set(request['target_concept_ids'])-set(reduced['target_concept_ids'])),
                               original_ledger_unchanged=True),
                  **{k:replay[k] for k in ('learning_cost','switch_cost','objective','missing','total_if_executed')})
    return result
