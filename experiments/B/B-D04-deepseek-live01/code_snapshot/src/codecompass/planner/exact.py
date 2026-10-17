"""Complete subset DP for <=12 units. Never uses beam/greedy/closure search."""
from .core import PlanningInputError
from .search_common import model,covered,cost_of,plan_result,input_hash,canonical_hash,EPS

def exact_plan(request,units,state,config):
    by_id,gate,mastered=model(request,units,state,config);ids=sorted(by_id);n=len(ids)
    if n>12:raise PlanningInputError('Exact certificate is restricted to at most 12 units')
    goals=set(request['target_concept_ids']);routes={0:()};best=None;transitions=0
    for mask in range(1<<n):
        if mask not in routes:continue
        route=routes[mask];known=covered(route,by_id,mastered)
        if goals<=known:
            key=(cost_of(route,by_id),len(route),route)
            if best is None or key<best[0]:best=(key,route)
        for i,uid in enumerate(ids):
            if mask&(1<<i):continue
            u=by_id[uid]
            if any(e['hard'] and e['unit_id'] not in route and not set(by_id[e['unit_id']]['concept_ids'])<=known for e in u['prerequisites']):continue
            candidate=route+(uid,)
            if cost_of(candidate,by_id)>request['budget']+EPS:continue
            transitions+=1;next_mask=mask|(1<<i)
            if next_mask not in routes or candidate<routes[next_mask]:routes[next_mask]=candidate
    masks=sorted(routes)
    certificate={'format':'complete-subset-dp-v1','complete':True,'input_hash':input_hash(request,units,gate),'unit_ids':ids,'budget_epsilon':EPS,'reachable_masks':masks,'reachable_masks_hash':canonical_hash(masks),'reachable_count':len(masks),'transition_count':transitions,'optimal_route':list(best[1]) if best else None,'optimal_cost':best[0][0] if best else None,'claim_scope':'only this fixed candidate set, evidence gate, hard graph, nonnegative proxy costs and budget+1e-9'}
    route=best[1] if best else ();status='FEASIBLE' if best else 'INFEASIBLE_PROVEN'
    result=plan_result(request,by_id,gate,route,status,'exact-dp',None if best else 'COMPLETE_EXACT_ENUMERATION: no reachable budget-admissible target-covering subset',None if best else 'certificate.json')
    return result,{'method':'exact-subset-dp','gate':gate,'certificate':certificate,'optimality_claim':bool(best),'scope_units':n}
