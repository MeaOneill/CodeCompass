"""Costed diagnostic candidates; no answer access and no uncalibrated production VOI."""
import copy
import hashlib
import json
from pathlib import Path

from codecompass.learner import update_evidence
from .adaptive import EPS, nonnegative, remaining_plan, request_for_state


def evidence_for(request, state, quiz, outcome, timestamp):
    if outcome not in ('pass', 'fail'):
        raise ValueError('Only independently scored pass/fail is accepted')
    return dict(evidence_id='D05:'+quiz['item_id'], item_id=quiz['item_id'], concept_id=quiz['concept_id'],
                project=request['snapshot_id'], timestamp=timestamp, pseudonymous_user_id=state['pseudonymous_user_id'],
                is_fixture=state['is_simulated'], independent=quiz['independent'], evidence_type='independent_quiz', outcome=outcome)


def validate_quiz(quiz, request):
    for key in ('item_id', 'concept_id', 'source'):
        if not isinstance(quiz.get(key), str) or not quiz[key]:
            raise ValueError('Quiz identity and public source required')
    if quiz.get('independent') is not True:
        raise ValueError('Quiz needs independent scoring; reading/self-report is not evidence')
    nonnegative(quiz.get('cost'), 'quiz cost')
    if quiz.get('cost_unit') != request['cost_unit']:
        raise ValueError('Quiz and learning must use identical cost units')


def probability(root, request, units, quiz):
    prior = quiz.get('probability')
    if not isinstance(prior, dict):
        return None, 'NO_RELIABLE_P_PASS'
    if prior.get('kind') == 'synthetic_prior':
        if request['is_fixture'] and all(u['is_fixture'] for u in units):
            p = prior.get('p_pass')
            if type(p) in (int,float) and 0 <= p <= 1 and prior.get('source'):
                return p, 'SYNTHETIC_PRIOR_FOR_STRUCTURAL_TEST_ONLY'
        return None, 'SYNTHETIC_PRIOR_REJECTED_FOR_REAL_SOURCE'
    if prior.get('kind') != 'development_calibration':
        return None, 'NO_RELIABLE_P_PASS'
    # Restrict to public development artifacts. Never open private/final-answer paths.
    root = Path(root).resolve()
    relative = prior.get('path')
    if not isinstance(relative, str):
        return None, 'MISSING_CALIBRATION_ARTIFACT'
    path = (root/relative).resolve()
    if not path.is_relative_to(root/'benchmarks/dev') or not path.is_file():
        return None, 'CALIBRATION_OUTSIDE_PUBLIC_DEV'
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != prior.get('sha256'):
        return None, 'CALIBRATION_HASH_MISMATCH'
    data = json.loads(raw)
    n = data.get('n'); passes = data.get('passes')
    if (data.get('split') != 'dev' or data.get('is_simulated') is not False
        or data.get('concept_id') != quiz['concept_id'] or not data.get('provenance')
        or type(n) is not int or n < 20 or type(passes) is not int or not 0 <= passes <= n):
        return None, 'INSUFFICIENT_OR_INVALID_DEV_CALIBRATION'
    return passes/n, 'PUBLIC_DEV_CALIBRATION_WITH_PROVENANCE_NOT_A_POPULATION_GUARANTEE'


def nearby_concepts(request, units):
    by_id = {u['id']: u for u in units}
    goals = set(request['target_concept_ids'])
    relevant = {u['id'] for u in units if goals & set(u['concept_ids'])}
    # Bounded two-hop neighborhood; do not quiz unrelated concepts.
    for _ in range(2):
        relevant |= {e['unit_id'] for uid in list(relevant) for e in by_id[uid]['prerequisites'] if e['hard']}
    return goals | {c for uid in relevant for c in by_id[uid]['concept_ids']}


def select_diagnostic(root, request, units, state, observed_state, config, quizzes, plan, *,
                      strategy='voi', quiz_count=0, max_quizzes=2, completed=(), spent=0,
                      alpha=0, gamma=0, options=None, epsilon=0, fixed_interval=1,
                      last_fixed_completion=None):
    if strategy not in ('none','fixed','voi','no_feedback'):
        raise ValueError('Unknown diagnostic strategy')
    if type(max_quizzes) is not int or max_quizzes < 0 or type(fixed_interval) is not int or fixed_interval < 1:
        raise ValueError('Explicit nonnegative quiz cap and positive fixed interval required')
    nonnegative(epsilon, 'epsilon')
    for quiz in quizzes:
        validate_quiz(quiz, request)
    if len({q['item_id'] for q in quizzes}) != len(quizzes):
        raise ValueError('Duplicate diagnostic item IDs')
    result = dict(strategy=strategy, selected=None, candidates=[], baseline_objective=plan['objective'],
                  budget_remaining=request['budget']-spent, quiz_count=quiz_count, max_quizzes=max_quizzes)
    if strategy == 'none' or quiz_count >= max_quizzes:
        result['reason'] = 'DISABLED_OR_QUIZ_LIMIT'; return result
    if strategy == 'fixed' and (len(completed) % fixed_interval or last_fixed_completion == len(completed)):
        result['reason'] = 'NOT_FIXED_FREQUENCY_OPPORTUNITY'; return result
    nearby = nearby_concepts(request, units)
    accepted = {(e['concept_id'],e['item_id']) for e in observed_state['records']}
    for quiz in sorted(quizzes, key=lambda q: q['item_id']):
        concept = quiz['concept_id']; gate = plan['gate'].get(concept)
        row = dict(item_id=quiz['item_id'], concept_id=concept, quiz_cost=quiz['cost'],
                   p_pass=None, voi=None, branches={}, eligible=False)
        result['candidates'].append(row)
        if (concept,quiz['item_id']) in accepted:
            row['reason'] = 'DUPLICATE_ITEM'; continue
        if concept not in nearby or gate is None or gate['mastered']:
            row['reason'] = 'NOT_UNCERTAIN_NEAR_TARGET'; continue
        if spent+quiz['cost'] > request['budget']+EPS:
            row['reason'] = 'QUIZ_BUDGET'; continue
        p, source = probability(root, request, units, quiz)
        row['p_pass'] = p; row['probability_source'] = source
        if strategy != 'fixed' and p is None:
            row['reason'] = source; continue
        for outcome in ('pass','fail'):
            event = evidence_for(request, state, quiz, outcome, '2000-01-01T00:00:00+00:00')
            hypothetical, decision = update_evidence(state, event, allow_simulated=request['is_fixture'])
            branch_request = request_for_state(request, hypothetical, config)
            branch = remaining_plan(root, branch_request, units, hypothetical, config,
                                    completed=completed, reference=plan['remaining'], spent=spent+quiz['cost'],
                                    alpha=alpha, gamma=gamma, options=options)
            row['branches'][outcome] = dict(status=branch['status'], objective=branch['objective'],
                                            remaining=branch['remaining'], gate=branch['gate'].get(concept),
                                            learning_cost=branch['learning_cost'], switch_cost=branch['switch_cost'],
                                            total_if_executed=branch['total_if_executed'], update_decision=decision)
        if strategy == 'fixed':
            row.update(eligible=True, reason='FIXED_FREQUENCY_SAME_ITEM_POOL_AND_BUDGET')
            if result['selected'] is None:
                result['selected'] = quiz['item_id']
            continue
        if p is None:
            row['reason'] = source; continue
        if plan['status'] != 'FEASIBLE' or any(b['status'] != 'FEASIBLE' for b in row['branches'].values()):
            row['reason'] = 'BRANCH_OR_BASELINE_NOT_FEASIBLE_CONSERVATIVE'; continue
        if not row['branches']['pass']['gate']['mastered']:
            row['reason'] = 'ONE_PASS_CANNOT_OPEN_SKIP_GATE'; continue
        row['voi'] = plan['objective'] - (quiz['cost'] + p*row['branches']['pass']['objective'] + (1-p)*row['branches']['fail']['objective'])
        row['eligible'] = row['voi'] > epsilon
        row['reason'] = 'POSITIVE_VOI' if row['eligible'] else 'NONPOSITIVE_VOI'
    if strategy != 'fixed':
        eligible = [r for r in result['candidates'] if r['eligible']]
        if eligible:
            result['selected'] = min(eligible, key=lambda r: (-r['voi'],r['item_id']))['item_id']
    result['reason'] = 'QUIZ_SELECTED' if result['selected'] else 'CONSERVATIVE_DIRECT_LEARNING'
    return result
