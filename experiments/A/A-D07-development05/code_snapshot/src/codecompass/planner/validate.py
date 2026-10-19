"""Independent replay checker: does not call the greedy or closure algorithm."""
import math


def check_plan(request,units,result,gate):
    by_id={u['id']:u for u in units};known={c for c,g in gate.items() if g['mastered']}
    seen=set();cost=0;issues=[]
    if result['status'] not in ('FEASIBLE','NO_FEASIBLE_FOUND','TIMEOUT'):issues.append('Unsupported status or unverified infeasibility proof')
    if type(result.get('estimated_cost')) not in (int,float):issues.append('Invalid reported cost type')
    for uid in result['ordered_units']:
        if uid not in by_id:issues.append('unknown unit '+str(uid));continue
        if uid in seen:issues.append('duplicate unit '+uid)
        u=by_id[uid]
        for edge in u['prerequisites']:
            if edge['hard']:
                p=edge['unit_id']
                if p not in seen and not set(by_id[p]['concept_ids'])<=known:
                    issues.append(f'unmet prerequisite {p} before {uid}')
        cost+=u['base_cost'];seen.add(uid);known.update(u['concept_ids'])
    if cost>request['budget']+1e-9:issues.append('budget exceeded')
    if not math.isclose(cost,result['estimated_cost'],rel_tol=1e-12,abs_tol=1e-9):issues.append('reported cost mismatch')
    goals=set(request['target_concept_ids']);covered=sorted(goals&known)
    if result['coverage']['required_concept_ids']!=sorted(goals):issues.append('target set mismatch')
    if result['coverage']['covered_concept_ids']!=covered:issues.append('coverage mismatch')
    ratio=len(covered)/len(goals) if goals else None
    if result['coverage']['ratio']!=ratio:issues.append('coverage ratio mismatch')
    complete=goals<=known
    if result['status']=='FEASIBLE' and (not complete or result['unmet_constraints']):issues.append('false feasible status')
    if result['status']=='NO_FEASIBLE_FOUND' and complete:issues.append('false incomplete status')
    if result['status']=='INFEASIBLE_PROVEN' and not result.get('proof_path'):issues.append('missing proof')
    return {'structurally_valid':not issues,'goal_complete':complete,'violations':issues,
            'replayed_proxy_cost':cost,'covered_concepts':covered,'not_a_learning_success_measure':True}
