"""Independent counts from route, source bytes and predeclared concepts.

Coverage is concept presence, not task success. Hard-edge checks are local
ordered relation occurrences; zero applicable relations means None, not zero.
"""
import math
from codecompass.graph import validate_span


def evaluate(request, units, gate, result, source_context=None):
    by_id = {u['id']: u for u in units}
    goals = set(request['target_concept_ids'])
    known = {c for c, g in gate.items() if g['mastered']}
    seen = set(); costs = []; issues = []
    violations = relations = source_total = source_ok = 0
    for uid in result['ordered_units']:
        if uid not in by_id:
            issues.append('unknown unit: '+uid); continue
        if uid in seen:
            issues.append('duplicate unit: '+uid)
        unit = by_id[uid]
        for edge in unit['prerequisites']:
            if not edge['hard']: continue
            relations += 1
            prerequisite = by_id.get(edge['unit_id'])
            if prerequisite is None or (edge['unit_id'] not in seen and not set(prerequisite['concept_ids']) <= known):
                violations += 1
        for span in unit['source_spans']:
            source_total += 1
            try:
                if source_context is None: raise ValueError('No independently loaded source snapshot')
                snapshot, contents = source_context
                if span['snapshot_id'] != request['snapshot_id']: raise ValueError('Wrong snapshot')
                validate_span(span, snapshot, contents)
                source_ok += 1
            except (ValueError, KeyError, TypeError):
                pass
        costs.append(unit['base_cost']); seen.add(uid); known.update(unit['concept_ids'])
    tp = len(goals & known); fn = len(goals-known); cost = math.fsum(costs)
    if violations: issues.append('hard prerequisite violation')
    if source_ok != source_total: issues.append('invalid source reference')
    if cost > request['budget']+1e-9: issues.append('over budget')
    claimed = result.get('estimated_cost')
    if type(claimed) not in (int, float) or not math.isfinite(claimed) or not math.isclose(cost, claimed, abs_tol=1e-9, rel_tol=1e-12):
        issues.append('reported cost mismatch')
    expected = {'required_concept_ids': sorted(goals), 'covered_concept_ids': sorted(goals & known),
                'ratio': tp/len(goals) if goals else None}
    if result.get('coverage') != expected: issues.append('reported coverage mismatch')
    if result.get('status') == 'FEASIBLE' and (fn or result.get('unmet_constraints')): issues.append('false feasible')
    if result.get('status') == 'NO_FEASIBLE_FOUND' and not fn: issues.append('false incomplete')
    return {'required_concepts': len(goals), 'coverage_tp': tp, 'coverage_fn': fn,
            'coverage_ratio': tp/len(goals) if goals else None,
            'hard_relations_checked': relations, 'hard_violations': violations,
            'prerequisite_violation_rate': violations/relations if relations else None,
            'source_spans_checked': source_total, 'source_spans_valid': source_ok,
            'source_reference_validity': source_ok/source_total if source_total else None,
            'replayed_proxy_cost': cost, 'legal': not issues, 'violations': issues,
            'human_task_success': None}


def aggregate(rows):
    attempted = [r for r in rows if r['attempted']]
    failures = [r for r in attempted if r['execution_status'] != 'FEASIBLE']
    return {'scheduled': len(rows), 'attempted': len(attempted),
            'not_run': len(rows)-len(attempted), 'failed': len(failures),
            'failure_rate': len(failures)/len(attempted) if attempted else None,
            'failure_definition': 'attempted outcome other than independently legal FEASIBLE; includes timeout/format/algorithm/API errors',
            'human_task_success': None}
