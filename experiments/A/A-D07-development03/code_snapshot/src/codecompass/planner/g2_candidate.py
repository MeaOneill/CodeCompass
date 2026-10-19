"""D06 development controls around the existing D05 planner, not a new algorithm.

No-gate means disable ALL evidence-based skipping, not posterior-mean gating.
The untouched observation ledger is retained separately from the planning view.
Only alpha=0 is allowed so removing evidence cannot change personalized costs.
"""
import copy

from codecompass.learner import initial_state, update_evidence
from .adaptive import remaining_plan, request_for_state, route_audit
from .diagnostics import evidence_for, validate_quiz

VARIANTS = ('main', 'no_gate', 'no_selection', 'no_feedback', 'no_diagnostic')


def semantic_result(result):
    """Keep recorded timing intact; exclude only wall-clock measurements for equivalence."""
    def stable(value):
        if isinstance(value, dict):
            return {k: stable(v) for k, v in value.items() if k != 'elapsed_seconds'}
        if isinstance(value, list):
            return [stable(v) for v in value]
        return value
    cleaned = stable(result)
    cleaned.pop('variant', None)
    return cleaned


def episode(root, case, candidate, variant):
    if variant not in VARIANTS or candidate['alpha'] != 0 or candidate['production_voi_enabled']:
        raise ValueError('This conservative candidate requires alpha=0 and production VOI disabled')
    if candidate['max_quizzes'] != 1 or candidate['gamma'] != 0 or candidate['cost_unit'] != case['request']['cost_unit']:
        raise ValueError('Unsupported control schedule, switching coefficient or cost unit')
    config = {**case['config'], 'threshold': candidate['threshold'], 'quantile': candidate['quantile']}
    request = copy.deepcopy(case['request'])
    request['budget'] = candidate['budget']
    observed = copy.deepcopy(case['state'])
    frozen_state = copy.deepcopy(observed)
    completed, events = [], []
    spent = learning = quiz_spent = switching = 0.0
    previous = []
    quiz_count = 0

    def planning_view():
        if variant == 'no_gate':
            return initial_state(observed['pseudonymous_user_id'], is_simulated=observed['is_simulated'])
        return frozen_state if variant == 'no_feedback' else observed

    def plan():
        state = planning_view()
        effective = request_for_state(request, state, config)
        return remaining_plan(root, effective, case['units'], state, config, completed=completed,
                              reference=previous, spent=spent, alpha=0, gamma=candidate['gamma'],
                              options=candidate['search'])

    current = plan()
    initial = copy.deepcopy(current)
    for _ in range(len(case['units']) + candidate['max_quizzes'] + 1):
        if current['status'] != 'FEASIBLE':
            break
        # A single common quiz after exactly one completed material, even if that
        # material finishes coverage. No policy is given a free post-task quiz.
        if len(completed) == 1 and quiz_count == 0 and variant != 'no_diagnostic' and case['quizzes']:
            q = case['quizzes'][0]
            validate_quiz(q, request)
            if spent + q['cost'] > request['budget']:
                events.append(dict(type='assessment_unaffordable', spent=spent, cost=q['cost']))
                break
            # Outcomes are accessed AFTER the predetermined selection.
            outcome = case['outcomes'][q['item_id']]
            evidence = evidence_for(request, observed, q, outcome, '2026-10-19T00:00:00+08:00')
            observed, accepted = update_evidence(observed, evidence, allow_simulated=request['is_fixture'])
            if accepted != 'ACCEPTED':
                raise ValueError('Control cannot recharge repeated evidence')
            spent += q['cost']; quiz_spent += q['cost']; quiz_count += 1
            before = copy.deepcopy(current)
            if variant != 'no_feedback':
                previous = list(current['remaining'])
                current = plan()
                if current['status'] == 'FEASIBLE':
                    spent += current['switch_cost']; switching += current['switch_cost']
            else:
                replay = route_audit(request, case['units'], current['gate'], current['remaining'],
                                     current['unit_costs'], completed, (), 0, spent)
                if not replay['valid']:
                    current['status'] = 'NO_FEASIBLE_FOUND'
            events.append(dict(type='quiz', item_id=q['item_id'], outcome=outcome, accepted=accepted,
                               cost=q['cost'], spent=spent, before=before, after=copy.deepcopy(current),
                               feedback_applied=variant != 'no_feedback', observation=evidence))
            continue
        if not current['remaining']:
            break
        uid = current['remaining'][0]
        replay = route_audit(request, case['units'], current['gate'], current['remaining'],
                             current['unit_costs'], completed, (), 0, spent)
        if not replay['valid']:
            current['status'] = 'NO_FEASIBLE_FOUND'
            break
        cost = current['unit_costs'][uid]
        completed.append(uid); spent += cost; learning += cost
        current['remaining'].pop(0)
        events.append(dict(type='material', unit_id=uid, cost=cost, spent=spent,
                           completed=list(completed)))
    coverage_complete = current['status'] == 'FEASIBLE' and not current['remaining']
    return dict(variant=variant, initial_plan=initial, final_plan=current, observed_state=observed,
                planning_state=planning_view(), completed=completed, events=events,
                total_proxy_cost=spent, learning_proxy_cost=learning, quiz_proxy_cost=quiz_spent,
                switch_proxy_cost=switching, quiz_count=quiz_count, budget=request['budget'],
                coverage_complete=coverage_complete, human_task_success=None,
                no_selection_identifiable=False, gate_ablation='disable all evidence-based skipping',
                feedback_is_simulated=True)
