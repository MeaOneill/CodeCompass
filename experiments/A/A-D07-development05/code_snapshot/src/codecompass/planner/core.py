"""D03 B2-initial: target-related gain / incremental prerequisite-closure cost.

This deterministic greedy is the planned strong baseline scaffold, not the
future beam-search method and not a global optimizer.
"""
import math
from codecompass.learner import planning_rows, mastery_gate


class PlanningInputError(ValueError):pass
class ClosureCycle(ValueError):pass


def validate_units(units, *, allow_fixture_edges=False):
    by_id={}
    for u in units:
        if not isinstance(u.get('id'),str) or not u['id'] or u['id'] in by_id:
            raise PlanningInputError('Invalid/duplicate learning unit ID')
        if not u.get('concept_ids') or not all(isinstance(c,str) and c for c in u['concept_ids']) or len(set(u['concept_ids']))!=len(u['concept_ids']):
            raise PlanningInputError('Nonempty unique unit concepts required')
        cost=u.get('base_cost')
        if type(cost) not in (int,float) or not math.isfinite(cost) or cost<0:
            raise PlanningInputError('base_cost missing/invalid; never fill with zero')
        if u.get('cost_unit')!='proxy_cost':raise PlanningInputError('Mixed cost units')
        by_id[u['id']]=u
    for u in units:
        for edge in u.get('prerequisites',[]):
            if edge['unit_id'] not in by_id:raise PlanningInputError('Dangling prerequisite')
            if edge['relation_type']!='teaching_prerequisite' or type(edge['hard']) is not bool:
                raise PlanningInputError('Only explicit teaching relations are permitted')
            if edge['hard']:
                p=edge['provenance']
                fixture=(allow_fixture_edges and u.get('is_fixture') is True and p['kind']=='fixture'
                         and p['review_status']=='approved' and p['reviewer']=='SYNTHETIC_REVIEW_NOT_A_PERSON'
                         and 'fixture-only:structural-constraint' in p['evidence'])
                human=(p['kind']=='teaching_judgment' and p['review_status']=='approved'
                       and bool(p['reviewer']) and any(x.startswith('human-review:') for x in p['evidence']))
                if not (human or fixture):raise PlanningInputError('Unreviewed hard prerequisite rejected')
    return by_id


def reverse_closure(root, by_id, known_concepts, selected=()):
    """Postorder required bundle; alternatives sharing concepts can satisfy prior learning."""
    if root not in by_id:raise PlanningInputError('Unknown root unit')
    available=set(known_concepts);done=set(selected);active=[];result=[]
    for uid in done:available.update(by_id[uid]['concept_ids'])
    def visit(uid):
        unit=by_id[uid]
        if uid in done or set(unit['concept_ids'])<=available:return
        if uid in active:raise ClosureCycle(' -> '.join(active[active.index(uid):]+[uid]))
        active.append(uid)
        for edge in sorted(unit.get('prerequisites',[]),key=lambda e:e['unit_id']):
            if edge['hard']:visit(edge['unit_id'])
        active.pop();result.append(uid);done.add(uid);available.update(unit['concept_ids'])
    visit(root)
    return result


def validate_request(request,units,state,config):
    budget=request.get('budget')
    if type(budget) not in (int,float) or not math.isfinite(budget) or budget<0:
        raise PlanningInputError('Finite nonnegative budget required')
    if request.get('cost_unit')!='proxy_cost':raise PlanningInputError('Unsupported cost unit')
    if request.get('config_version')!=config['version']:raise PlanningInputError('Config version mismatch')
    fixture=request.get('is_fixture') is True
    if state['is_simulated']!=fixture:raise PlanningInputError('Profile/request simulation mismatch')
    rows=planning_rows(state,request['snapshot_id'],quantile=config['quantile'],allow_simulated=fixture)
    if request.get('learner_state')!=rows:
        raise PlanningInputError('Request aggregates do not match the independent evidence ledger')
    if len(request['unit_ids'])!=len(set(request['unit_ids'])) or set(request['unit_ids'])!={u['id'] for u in units}:
        raise PlanningInputError('Candidate set mismatch')
    by_id=validate_units(units,allow_fixture_edges=fixture)
    for u in units:
        if u.get('is_fixture') and not fixture:raise PlanningInputError('Fixture materials cannot enter a real request')
        if not u.get('is_fixture') and not u.get('source_spans'):
            raise PlanningInputError('Real learning unit lacks source provenance')
        if any(s['snapshot_id']!=request['snapshot_id'] for s in u.get('source_spans',[])):
            raise PlanningInputError('Unit snapshot mismatch')
    if not all(isinstance(c,str) and c for c in request['target_concept_ids']):raise PlanningInputError('Invalid goal concept')
    if len(set(request['target_concept_ids']))!=len(request['target_concept_ids']):
        raise PlanningInputError('Duplicate goals')
    return by_id


def greedy_plan(request,units,state,config):
    by_id=validate_request(request,units,state,config)
    goals=set(request['target_concept_ids'])
    all_concepts={c for u in units for c in u['concept_ids']}|goals
    gate=mastery_gate(state,request['snapshot_id'],all_concepts,threshold=config['threshold'],
                      quantile=config['quantile'],allow_simulated=request['is_fixture'])
    mastered={c for c,g in gate.items() if g['mastered']}
    known=set(mastered);chosen=[];cost=0;trace=[];attempts=[]
    for c in sorted(mastered):
        trace.append({'step':len(trace)+1,'unit_id':None,'reason':f'EVIDENCE_GATE skip {c}; lower={gate[c]["lower_bound"]:.6f} >= {config["threshold"]}; no reading is counted as mastery',
                      'evidence_ids':gate[c]['evidence_ids']})
    while goals-known:
        candidates=[];blocked=[]
        for uid,u in sorted(by_id.items()):
            if uid in chosen or not (set(u['concept_ids'])&(goals-known)):continue
            try:bundle=reverse_closure(uid,by_id,mastered,chosen)
            except ClosureCycle as exc:
                blocked.append(f'{uid}: prerequisite cycle ({exc})');continue
            incremental=sum(by_id[x]['base_cost'] for x in bundle)
            gain=len(({c for x in bundle for c in by_id[x]['concept_ids']}-known)&goals)
            if not gain:continue
            if cost+incremental>request['budget']+1e-9:
                blocked.append(f'{uid}: requires incremental proxy_cost={incremental}, remaining={request["budget"]-cost}');continue
            ratio=math.inf if incremental==0 else gain/incremental
            candidates.append(((-ratio,incremental,uid),uid,bundle,incremental,gain))
        attempts.append({'iteration':len(chosen)+1,'pending_goals':sorted(goals-known),'blocked_candidates':blocked,
                         'candidates':[{'root':x[1],'bundle':x[2],'incremental_cost':x[3],'new_goal_gain':x[4]} for x in candidates]})
        if not candidates:break
        _,root,bundle,incremental,gain=min(candidates,key=lambda x:x[0])
        for uid in bundle:
            u=by_id[uid];chosen.append(uid);cost+=u['base_cost'];known.update(u['concept_ids'])
            spans='; '.join(f'{s["path"]}:L{s["start_line"]}-{s["end_line"]}' for s in u.get('source_spans',[])) or 'explicit structural fixture'
            trace.append({'step':len(trace)+1,'unit_id':uid,
                          'reason':f'{"TARGET_MATERIAL" if uid==root else "REQUIRED_PREREQUISITE"} for {root}; bundle new-goal gain={gain}, incremental proxy_cost={incremental}; own proxy_cost={u["base_cost"]}; source={spans}; soft edges do not create hard constraints',
                          'evidence_ids':[]})
    covered=sorted(goals&known);missing=sorted(goals-known)
    unmet=['uncovered target: '+c for c in missing]
    if missing:
        unmet+=['no candidate material for '+c for c in missing if not any(c in u['concept_ids'] for u in units)]
        unmet+=sorted(set(x for a in attempts[-1:] for x in a['blocked_candidates']))
        unmet.append('Greedy search did not find a complete feasible route; this is not an infeasibility proof')
    result={'schema_version':'1.0.0','object_type':'PlanResult','is_fixture':request['is_fixture'],
            'plan_id':request['request_id']+'-greedy','request_id':request['request_id'],
            'status':'FEASIBLE' if not missing else 'NO_FEASIBLE_FOUND','ordered_units':chosen,
            'coverage':{'required_concept_ids':sorted(goals),'covered_concept_ids':covered,'ratio':len(covered)/len(goals) if goals else None},
            'unmet_constraints':unmet,'estimated_cost':cost,'cost_unit':'proxy_cost','reason_trace':trace,'proof_path':None}
    return result,{'gate':gate,'candidate_attempts':attempts,'method':'B2-initial-closure-gain-greedy','diagnostics_implemented':False,'optimality_claim':False}
