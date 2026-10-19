"""D05 order-preserving remaining-route search; no D04 certificate reuse."""
import copy
import json
import math
from pathlib import Path
import time

from jsonschema import Draft202012Validator
from codecompass.graph import read_snapshot, validate_span
from codecompass.learner import mastery_gate, planning_rows
from codecompass.retrieval.samples import contract_validator
from .core import validate_request
from .beam import search_options

EPS = 1e-9
VERSION = 'D05-adaptive-v1'


def nonnegative(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(name + ' must be finite and nonnegative')
    return value


def validate_input(root, request, units, state, config):
    root = Path(root)
    validator = Draft202012Validator(json.loads((root/'schemas/contracts-1.1.schema.json').read_text(encoding='utf-8')),
                                    format_checker=contract_validator(root).format_checker)
    validator.validate(request)
    for unit in units:
        validator.validate(unit)
    validate_request(request, units, state, config)
    real = [u for u in units if not u['is_fixture']]
    if real:
        snapshots = []
        for path in (root/'benchmarks/sources').glob('*/snapshot.json'):
            snapshot = json.loads(path.read_text(encoding='utf-8'))
            if snapshot['snapshot_id'] == request['snapshot_id']:
                snapshots.append((path.parent, snapshot))
        if len(snapshots) != 1:
            raise ValueError('Unique fixed source snapshot required')
        folder, snapshot = snapshots[0]
        contents = read_snapshot(folder, snapshot)
        for unit in real:
            for span in unit['source_spans']:
                validate_span(span, snapshot, contents)


def personalized_costs(request, units, state, config, alpha):
    nonnegative(alpha, 'alpha')
    rows = planning_rows(state, request['snapshot_id'], quantile=config['quantile'], allow_simulated=request['is_fixture'])
    means = {r['concept_id']: r['alpha']/(r['alpha']+r['beta']) for r in rows}
    return {u['id']: u['base_cost'] * (1 + alpha * math.fsum(1-means.get(c, .5) for c in u['concept_ids'])/len(u['concept_ids'])) for u in units}


def switch_distance(reference, route, universe_size):
    """Fixed denominator makes prefix penalties monotone; no deletion charge."""
    if not reference:
        return 0.0
    positions = {uid: i for i, uid in enumerate(reference)}
    retained = [positions[uid] for uid in route if uid in positions]
    inversions = sum(a > b for i, a in enumerate(retained) for b in retained[i+1:])
    additions = sum(uid not in positions for uid in route)
    denominator = max(1, len(reference)*(len(reference)-1)//2 + universe_size)
    return (inversions + additions) / denominator


def route_audit(request, units, gate, route, costs, completed=(), reference=(), gamma=0, spent=0):
    """Direct replay independent of search ranking, with completed material coverage."""
    by_id = {u['id']: u for u in units}
    errors = []
    if len(set(completed)) != len(completed) or any(u not in by_id for u in completed):
        return {'valid': False, 'errors': ['INVALID_COMPLETED_PREFIX']}
    known = {c for c, row in gate.items() if row['mastered']}
    known.update(c for uid in completed for c in by_id[uid]['concept_ids'])
    selected = set(completed)
    for uid in route:
        if uid not in by_id or uid in selected:
            errors.append('UNKNOWN_OR_REPEATED_UNIT')
            continue
        for edge in by_id[uid]['prerequisites']:
            pre = edge['unit_id']
            if edge['hard'] and pre not in selected and not set(by_id[pre]['concept_ids']) <= known:
                errors.append('HARD_PREREQUISITE:' + uid + ':' + pre)
        selected.add(uid)
        known.update(by_id[uid]['concept_ids'])
    learning = math.fsum(costs[uid] for uid in route if uid in costs)
    change = gamma * switch_distance(reference, route, len(units))
    missing = sorted(set(request['target_concept_ids']) - known)
    if spent + learning + change > request['budget'] + EPS:
        errors.append('TOTAL_BUDGET')
    return dict(valid=not errors, errors=errors, goal_complete=not missing, missing=missing,
                learning_cost=learning, switch_cost=change, objective=learning+change,
                total_if_executed=spent+learning+change)


def remaining_plan(root, request, units, state, config, *, completed=(), reference=(), spent=0,
                   alpha=0, gamma=0, options=None, clock=time.monotonic):
    """Full ordered prefix states; FEASIBLE is legal, never a global optimum claim."""
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
    gate = mastery_gate(state, request['snapshot_id'], concepts, threshold=config['threshold'],
                        quantile=config['quantile'], allow_simulated=request['is_fixture'])
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
    return dict(version=VERSION, status=status, completed=list(completed), remaining=list(route),
                unit_costs=costs, gate=gate, reference=list(reference), spent_before=spent, alpha=alpha, gamma=gamma,
                **{k: audit[k] for k in ('learning_cost','switch_cost','objective','missing','total_if_executed')},
                replay=audit, options=opt, expansions=expansions, truncated=truncated or limited,
                termination='WALL_CLOCK_TIMEOUT' if timeout else ('EXPANSION_LIMIT' if limited else 'BOUNDED_SEARCH_FINISHED'),
                events=events, elapsed_seconds=clock()-start, optimality_claim=False, certificate=None,
                state_key='full ordered remaining prefix; completed context fixed')


def request_for_state(request, state, config):
    new = copy.deepcopy(request)
    new['learner_state'] = planning_rows(state, request['snapshot_id'], quantile=config['quantile'], allow_simulated=request['is_fixture'])
    return new
