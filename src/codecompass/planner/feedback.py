"""Pure, costed adaptive session transactions for B's future UI adapter."""
import copy
import math
from codecompass.learner import update_evidence
from .adaptive import VERSION, EPS, nonnegative, remaining_plan, request_for_state, route_audit
from .diagnostics import select_diagnostic, evidence_for, validate_quiz


def start_session(root, request, units, state, config, quizzes, *, strategy='voi', alpha=0, gamma=0,
                  max_quizzes=2, fixed_interval=1, epsilon=0, options=None):
    plan = remaining_plan(root, request, units, state, config, alpha=alpha, gamma=gamma, options=options)
    session = dict(version=VERSION, request=copy.deepcopy(request), units=copy.deepcopy(units),
                   initial_request=copy.deepcopy(request), initial_state=copy.deepcopy(state), initial_plan=copy.deepcopy(plan),
                   state=copy.deepcopy(state), observed_state=copy.deepcopy(state), config=copy.deepcopy(config),
                   quizzes=copy.deepcopy(quizzes), strategy=strategy, alpha=alpha, gamma=gamma,
                   max_quizzes=max_quizzes, fixed_interval=fixed_interval, epsilon=epsilon, options=options,
                   completed=[], spent=0.0, quiz_spent=0.0, learning_spent=0.0, switch_spent=0.0,
                   quiz_count=0, quiz_duration_seconds=0.0, duration_complete=True,
                   last_fixed_completion=None, plan=plan, events=[], status=plan['status'])
    recommend(root, session)
    return session


def recommend(root, session):
    return select_diagnostic(root, session['request'], session['units'], session['state'], session['observed_state'],
        session['config'], session['quizzes'], session['plan'], strategy=session['strategy'],
        quiz_count=session['quiz_count'], max_quizzes=session['max_quizzes'], completed=session['completed'],
        spent=session['spent'], alpha=session['alpha'], gamma=session['gamma'], options=session['options'],
        epsilon=session['epsilon'], fixed_interval=session['fixed_interval'],
        last_fixed_completion=session['last_fixed_completion'])


def apply_feedback(root, session, item_id, outcome, *, timestamp, duration_seconds=None, duration_is_simulated=False, scheduled=False):
    """Outcome enters only after a choice. A caller never supplies future answers to select."""
    if session['status'] != 'FEASIBLE':
        raise ValueError('Stopped session cannot accept a new diagnostic')
    if duration_seconds is not None:
        nonnegative(duration_seconds, 'diagnostic duration')
    if type(duration_is_simulated) is not bool or (duration_is_simulated and not session['request']['is_fixture']):
        raise ValueError('Real sessions cannot accept simulated durations')
    if type(scheduled) is not bool:
        raise ValueError('Explicit scheduled-assessment flag required')
    matches = [q for q in session['quizzes'] if q['item_id']==item_id]
    if len(matches) != 1:
        raise ValueError('Unknown assessment item')
    quiz = matches[0]
    if scheduled:
        validate_quiz(quiz, session['request'])
        if session['quiz_count'] >= session['max_quizzes'] or session['spent']+quiz['cost'] > session['request']['budget']+EPS:
            raise ValueError('Assessment exceeds quiz cap or budget')
        decision = dict(strategy='scheduled_learning_assessment', selected=item_id,
                        reason='CALLER_REQUESTED_INDEPENDENT_ASSESSMENT_SAME_COST_AND_CAP',
                        baseline_objective=session['plan']['objective'])
    else:
        decision = recommend(root, session)
        if decision['selected'] != item_id:
            raise ValueError('Stale, duplicate, unrelated or unselected diagnostic')
    evidence = evidence_for(session['request'], session['observed_state'], quiz, outcome, timestamp)
    observed, accepted = update_evidence(session['observed_state'], evidence, allow_simulated=session['request']['is_fixture'])
    if accepted != 'ACCEPTED':
        raise ValueError('Repeated/ineligible evidence cannot trigger a second diagnostic charge')
    new = copy.deepcopy(session); before = new['spent']; old_plan = copy.deepcopy(new['plan'])
    new.update(observed_state=observed, quiz_count=new['quiz_count']+1,
               quiz_spent=new['quiz_spent']+quiz['cost'], spent=new['spent']+quiz['cost'],
               last_fixed_completion=len(new['completed']))
    if duration_seconds is None:
        new['duration_complete'] = False; new['quiz_duration_seconds'] = None
    elif new['duration_complete']:
        new['quiz_duration_seconds'] += duration_seconds
    paid_switch = 0.0; repair_estimate = None
    if new['strategy'] != 'no_feedback':
        new['state'] = copy.deepcopy(observed)
        new['request'] = request_for_state(new['request'], new['state'], new['config'])
        new['plan'] = remaining_plan(root, new['request'], new['units'], new['state'], new['config'],
            completed=new['completed'], reference=old_plan['remaining'], spent=new['spent'],
            alpha=new['alpha'], gamma=new['gamma'], options=new['options'])
        new['status'] = new['plan']['status']
        repair_estimate = copy.deepcopy(new['plan'])
        if new['status'] == 'FEASIBLE':
            paid_switch = new['plan']['switch_cost']
            new['spent'] += paid_switch
            new['switch_spent'] += paid_switch
    else:
        audit = route_audit(new['request'],new['units'],old_plan['gate'],old_plan['remaining'],old_plan['unit_costs'],
                            new['completed'],(),0,new['spent'])
        new['status'] = 'FEASIBLE' if audit['valid'] else 'NO_FEASIBLE_FOUND'
        new['plan']['status'] = new['status']
    if new['status'] == 'FEASIBLE':
        normalize_adopted_plan(new)
    new['events'].append(dict(type='diagnostic', item_id=item_id, outcome=outcome, evidence=evidence, scheduled=scheduled,
        decision=decision, cost_unit=quiz['cost_unit'], quiz_cost=quiz['cost'], spent_before=before, spent_after=new['spent'],
        duration_seconds=duration_seconds, duration_is_simulated=duration_is_simulated,
        completed_before=list(session['completed']), completed_after=list(new['completed']),
        before_plan=old_plan, after_plan=copy.deepcopy(new['plan']), feedback_applied=new['strategy']!='no_feedback',
        repair_estimate=repair_estimate, paid_switch_cost=paid_switch,
        added_units=sorted(set(new['plan']['remaining'])-set(old_plan['remaining']))))
    return new


def normalize_adopted_plan(session):
    """Paid switching is sunk, so the next decision compares future costs only."""
    plan = session['plan']
    audit = route_audit(session['request'],session['units'],plan['gate'],plan['remaining'],plan['unit_costs'],
                        session['completed'],plan['remaining'],session['gamma'],session['spent'])
    if not audit['valid']:
        raise ValueError('Adopted plan no longer fits total budget')
    plan.update(completed=list(session['completed']), reference=list(plan['remaining']),
                spent_before=session['spent'], replay=audit,
                **{k:audit[k] for k in ('learning_cost','switch_cost','objective','missing','total_if_executed')})


def complete_next(session, unit_id):
    if session['status'] != 'FEASIBLE' or not session['plan']['remaining'] or session['plan']['remaining'][0] != unit_id:
        raise ValueError('Only next legal adopted material may complete')
    new = copy.deepcopy(session); cost = new['plan']['unit_costs'][unit_id]
    if new['spent']+cost > new['request']['budget']+EPS:
        raise ValueError('Material exceeds remaining total budget')
    before = new['spent']; new['completed'].append(unit_id); new['plan']['remaining'].pop(0)
    new['spent'] += cost; new['learning_spent'] += cost
    normalize_adopted_plan(new)
    new['events'].append(dict(type='material', unit_id=unit_id, cost=cost, spent_before=before, spent_after=new['spent'],
                             note='Material completion is coverage only; no mastery evidence is added'))
    return new
