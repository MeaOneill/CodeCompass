"""Independent sequential replay and backward subset proof verification.

Does not import/call beam, exact, greedy or closure. Success is recomputed.
"""
import math
from .search_common import input_hash,canonical_hash,EPS

def verify_certificate(request,units,gate,certificate):
    if not isinstance(certificate,dict):return {'valid':False,'reason':'missing certificate'}
    ids=sorted(u['id'] for u in units);by_id={u['id']:u for u in units};n=len(ids)
    if n>12 or len(by_id)!=n:return {'valid':False,'reason':'unsupported proof size or duplicate IDs'}
    if certificate.get('format')!='complete-subset-dp-v1' or certificate.get('complete') is not True or certificate.get('input_hash')!=input_hash(request,units,gate) or certificate.get('unit_ids')!=ids or certificate.get('budget_epsilon')!=EPS:
        return {'valid':False,'reason':'proof identity/model mismatch'}
    mastered={c for c,g in gate.items() if g['mastered']};goals=set(request['target_concept_ids']);reachable={0};best=None
    for mask in range(1<<n):
        selected=[ids[i] for i in range(n) if mask&(1<<i)];cost=math.fsum(by_id[u]['base_cost'] for u in selected)
        if cost>request['budget']+EPS:continue
        if mask:
            # Backward recurrence: a subset is reachable iff some legal final unit
            # can be removed to leave a previously reachable proper subset.
            for i,uid in enumerate(ids):
                if not mask&(1<<i):continue
                prev=mask^(1<<i)
                if prev not in reachable:continue
                before=[ids[j] for j in range(n) if prev&(1<<j)];known=mastered|{c for u in before for c in by_id[u]['concept_ids']}
                if all(not e['hard'] or e['unit_id'] in before or set(by_id[e['unit_id']]['concept_ids'])<=known for e in by_id[uid]['prerequisites']):reachable.add(mask);break
        if mask in reachable and goals<=(mastered|{c for u in selected for c in by_id[u]['concept_ids']}):
            if best is None or cost<best:best=cost
    masks=sorted(reachable)
    optimal_route=certificate.get('optimal_route');route_ok=optimal_route is None if best is None else isinstance(optimal_route,list)
    if best is not None and route_ok:
        known=set(mastered);seen=set();values=[]
        for uid in optimal_route:
            if uid not in by_id or uid in seen:route_ok=False;break
            if any(e['hard'] and e['unit_id'] not in seen and not set(by_id[e['unit_id']]['concept_ids'])<=known for e in by_id[uid]['prerequisites']):route_ok=False;break
            seen.add(uid);known.update(by_id[uid]['concept_ids']);values.append(by_id[uid]['base_cost'])
        route_ok=route_ok and goals<=known and math.fsum(values)==best
    valid=(route_ok and certificate.get('reachable_masks')==masks and certificate.get('reachable_count')==len(masks) and certificate.get('reachable_masks_hash')==canonical_hash(masks) and certificate.get('optimal_cost')==best)
    return {'valid':valid,'feasible':best is not None,'optimal_cost':best,'reachable_count':len(masks),'reason':None if valid else 'complete reachable subset/cost mismatch'}

def verify_result(request,units,result,gate,certificate=None):
    by_id={u['id']:u for u in units};known={c for c,g in gate.items() if g['mastered']};seen=set();costs=[];issues=[];proof=None
    if result.get('request_id')!=request['request_id'] or result.get('is_fixture')!=request['is_fixture'] or result.get('cost_unit')!=request['cost_unit']:issues.append('request identity mismatch')
    for uid in result['ordered_units']:
        if uid not in by_id:issues.append('unknown unit');continue
        if uid in seen:issues.append('duplicate unit')
        u=by_id[uid]
        for e in u['prerequisites']:
            if e['hard'] and e['unit_id'] not in seen and not set(by_id[e['unit_id']]['concept_ids'])<=known:issues.append('prerequisite order violation')
        seen.add(uid);costs.append(u['base_cost']);known.update(u['concept_ids'])
    cost=math.fsum(costs);goals=set(request['target_concept_ids']);complete=goals<=known;status=result['status']
    if cost>request['budget']+EPS:issues.append('budget exceeded')
    if type(result.get('estimated_cost')) not in (int,float) or not math.isfinite(result['estimated_cost']) or not math.isclose(cost,result['estimated_cost'],rel_tol=1e-12,abs_tol=EPS):issues.append('reported cost mismatch')
    if result['coverage']!={'required_concept_ids':sorted(goals),'covered_concept_ids':sorted(goals&known),'ratio':len(goals&known)/len(goals) if goals else None}:issues.append('coverage mismatch')
    if status not in ('FEASIBLE','NO_FEASIBLE_FOUND','TIMEOUT','INFEASIBLE_PROVEN'):issues.append('unknown result status')
    if status=='FEASIBLE' and (not complete or result['unmet_constraints']):issues.append('false feasible')
    if status=='NO_FEASIBLE_FOUND' and complete:issues.append('false incomplete')
    if status=='INFEASIBLE_PROVEN':
        proof=verify_certificate(request,units,gate,certificate)
        if complete or not result.get('proof_path') or not proof.get('valid') or proof.get('feasible') is not False:issues.append('unverified infeasibility')
    return {'valid':not issues,'violations':issues,'goal_complete':complete,'replayed_cost':cost,'certificate_audit':proof,'not_a_learning_success_measure':True}
