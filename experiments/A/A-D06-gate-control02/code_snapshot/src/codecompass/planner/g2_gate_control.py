"""Supplemental gate ablation, with an explicit gate and original-input replay.

The ordered-prefix engine is copied from adaptive.remaining_plan at 42689bb.
Only the gate-policy argument/selection and version metadata differ. This copy
preserves the frozen D05 source; it is not a new algorithm contribution. Neither
learner records, unit concepts, source spans nor prerequisite edges are rewritten.
"""
import math
import time

from codecompass.learner import mastery_gate, planning_rows
from .adaptive import (EPS, validate_input, nonnegative, personalized_costs,
                       switch_distance, route_audit, search_options)

VERSION = 'D06-gate-control-v1.1'


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


def gate_plan(root, request, units, state, config, *, completed=(), reference=(), spent=0,
                   alpha=0, gamma=0, options=None, clock=time.monotonic, gate_policy='lower'):
    """Full ordered prefix states; FEASIBLE is legal, never a global optimum claim."""
    if gate_policy not in ('lower', 'mean'):
        raise ValueError('Unknown gate policy')
    validate_input(root, request, units, state, config)
    nonnegative(spent, 'spent'); nonnegative(gamma, 'gamma')
    if spent > request['budget'] + EPS:
        raise ValueError('Already spent beyond total budget')
    by_id = {u['id']: u for u in units}
    completed = tuple(completed); reference = tuple(reference)
    if len(set(completed)) != len(completed) or any(u not in by_id for u in completed):
        raise ValueError('Invalid completed history')
    if len(set(reference)) != len(reference) or any(u not in by_id or u in completed for u in reference):
        raise ValueError('Invalid reference suffix')
    costs = personalized_costs(request, units, state, config, alpha)
    concepts = {c for u in units for c in u['concept_ids']} | set(request['target_concept_ids'])
    gate = (mean_gate(state, request, units, config) if gate_policy == 'mean' else
            mastery_gate(state, request['snapshot_id'], concepts, threshold=config['threshold'],
                         quantile=config['quantile'], allow_simulated=request['is_fixture']))
    opt = search_options(options)
    initial = {c for c, row in gate.items() if row['mastered']} | {c for u in completed for c in by_id[u]['concept_ids']}
    goals = set(request['target_concept_ids'])
    start = clock(); deadline = start + opt['time_limit_seconds']
    def known(route):
        return initial | {c for u in route for c in by_id[u]['concept_ids']}
    def objective(route):
        return math.fsum(costs[u] for u in route) + gamma*switch_distance(reference, route, len(units))
    def rank(route):
        return (len(goals-known(route)), objective(route), len(route), route)
    frontier = [()]; incumbent = None; partial = (); events = []; expansions = 0
    timeout = False; limited = False; truncated = False
    for depth in range(len(units)-len(completed)+1):
        pool = set()
        for route in sorted(frontier, key=rank):
            if clock() >= deadline:
                timeout = True; break
            if rank(route) < rank(partial):
                partial = route
            if goals <= known(route):
                if incumbent is None or (objective(route), len(route), route) < (objective(incumbent), len(incumbent), incumbent):
                    incumbent = route
                continue
            selected = set(completed) | set(route); available = known(route)
            candidates = []
            for uid, unit in sorted(by_id.items()):
                if uid in selected:
                    continue
                if any(e['hard'] and e['unit_id'] not in selected and not set(by_id[e['unit_id']]['concept_ids']) <= available for e in unit['prerequisites']):
                    continue
                new = route + (uid,)
                if spent+objective(new) <= request['budget']+EPS:
                    candidates.append(new)
            candidates.sort(key=rank)
            dropped = candidates[opt['candidate_limit']:]
            truncated |= bool(dropped)
            events.append(dict(depth=depth, prefix=list(route), dropped_candidates=[list(x) for x in dropped]))
            for new in candidates[:opt['candidate_limit']]:
                if clock() >= deadline:
                    timeout = True; break
                if expansions >= opt['max_expansions']:
                    limited = True; break
                expansions += 1; pool.add(new)  # tuple, never frozenset: order is objective-relevant
                if rank(new) < rank(partial):
                    partial = new
                if goals <= known(new) and (incumbent is None or (objective(new),len(new),new) < (objective(incumbent),len(incumbent),incumbent)):
                    incumbent = new
            if timeout or limited:
                break
        if timeout or limited:
            break
        ordered = sorted(pool, key=rank)
        truncated |= len(ordered) > opt['beam_width']
        events.append(dict(depth=depth, retained=[list(x) for x in ordered[:opt['beam_width']]], dropped_prefixes=[list(x) for x in ordered[opt['beam_width']:]]))
        frontier = ordered[:opt['beam_width']]
        if not frontier:
            break
    route = incumbent if incumbent is not None else partial
    audit = route_audit(request, units, gate, route, costs, completed, reference, gamma, spent)
    if not audit['valid']:
        raise ValueError('Remaining route failed independent replay: '+repr(audit))
    status = 'TIMEOUT' if timeout else ('FEASIBLE' if incumbent is not None else 'NO_FEASIBLE_FOUND')
    return dict(version=VERSION, gate_policy=gate_policy, status=status, completed=list(completed), remaining=list(route),
                unit_costs=costs, gate=gate, reference=list(reference), spent_before=spent, alpha=alpha, gamma=gamma,
                **{k: audit[k] for k in ('learning_cost','switch_cost','objective','missing','total_if_executed')},
                replay=audit, options=opt, expansions=expansions, truncated=truncated or limited,
                termination='WALL_CLOCK_TIMEOUT' if timeout else ('EXPANSION_LIMIT' if limited else 'BOUNDED_SEARCH_FINISHED'),
                events=events, elapsed_seconds=clock()-start, optimality_claim=False, certificate=None,
                state_key='full ordered remaining prefix; completed context fixed')


def mean_plan(root, request, units, state, config, *, options=None):
    return gate_plan(root, request, units, state, config, alpha=0, gamma=0,
                     options=options, gate_policy='mean')
