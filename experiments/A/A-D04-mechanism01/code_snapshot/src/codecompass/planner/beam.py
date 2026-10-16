"""Deterministic bounded beam; completion never implies global optimality."""
import math,time
from .core import reverse_closure,ClosureCycle,PlanningInputError
from .search_common import model,covered,cost_of,plan_result,EPS
DEFAULT_SEARCH={'beam_width':16,'candidate_limit':50,'max_expansions':100000,'time_limit_seconds':30.0}

def search_options(options=None):
    cfg={**DEFAULT_SEARCH,**(options or {})}
    if set(cfg)!=set(DEFAULT_SEARCH):raise PlanningInputError('Unknown search option')
    for k in ('beam_width','candidate_limit','max_expansions'):
        if type(cfg[k]) is not int or cfg[k]<1:raise PlanningInputError(k+' must be a positive integer')
    limit=cfg['time_limit_seconds']
    if type(limit) not in (int,float) or not math.isfinite(limit) or limit<0:raise PlanningInputError('Finite nonnegative wall-clock limit required')
    return cfg

def beam_plan(request,units,state,config,options=None,*,clock=time.monotonic):
    opt=search_options(options);by_id,gate,mastered=model(request,units,state,config);goals=set(request['target_concept_ids']);start=clock();deadline=start+opt['time_limit_seconds']
    frontier=[()];seen={frozenset():()};incumbent=None;partial=();events=[];expansions=0;timed_out=False;limit_hit=False
    def rank(route):return (len(goals-covered(route,by_id,mastered)),cost_of(route,by_id),len(route),route)
    def timeout():return clock()>=deadline
    for depth in range(len(units)+1):
        if timeout():timed_out=True;break
        pool={}
        for route in sorted(frontier,key=rank):
            if timeout():timed_out=True;break
            if rank(route)<rank(partial):partial=route
            known=covered(route,by_id,mastered)
            if goals<=known:
                if incumbent is None or (cost_of(route,by_id),len(route),route)<(cost_of(incumbent,by_id),len(incumbent),incumbent):incumbent=route
                continue
            candidates=[];blocked=[]
            for uid in sorted(by_id):
                if timeout():timed_out=True;break
                if uid in route or set(by_id[uid]['concept_ids'])<=known:continue
                try:bundle=reverse_closure(uid,by_id,mastered,route)
                except ClosureCycle as exc:blocked.append({'root':uid,'reason':'cycle','detail':str(exc)});continue
                if not bundle:continue
                candidate=route+tuple(bundle);new_cost=cost_of(candidate,by_id)
                if new_cost>request['budget']+EPS:blocked.append({'root':uid,'reason':'budget','required_cost':new_cost});continue
                if incumbent is not None and new_cost>cost_of(incumbent,by_id)+EPS:continue
                gain=len((covered(candidate,by_id,mastered)-known)&goals);delta=new_cost-cost_of(route,by_id)
                ratio=math.inf if delta==0 and gain else (gain/delta if delta else 0)
                candidates.append(((-ratio,delta,uid),uid,candidate,bundle))
            if timed_out:break
            candidates.sort(key=lambda x:x[0]);kept=candidates[:opt['candidate_limit']];dropped=candidates[opt['candidate_limit']:]
            events.append({'event':'expand','depth':depth,'route':list(route),'candidates':[{'root':c[1],'bundle':c[3],'route':list(c[2]),'cost':cost_of(c[2],by_id)} for c in kept],'candidate_truncation':{'dropped_roots':[c[1] for c in dropped],'count':len(dropped)},'blocked':blocked})
            for _,uid,candidate,bundle in kept:
                if timeout():timed_out=True;break
                if expansions>=opt['max_expansions']:limit_hit=True;break
                expansions+=1;key=frozenset(candidate);old=seen.get(key)
                if old is not None and old<=candidate:
                    events.append({'event':'deduplicate','route':list(candidate),'retained_route':list(old)});continue
                seen[key]=candidate;pool[key]=candidate
                if rank(candidate)<rank(partial):partial=candidate
                if goals<=covered(candidate,by_id,mastered):
                    if incumbent is None or (cost_of(candidate,by_id),len(candidate),candidate)<(cost_of(incumbent,by_id),len(incumbent),incumbent):incumbent=candidate
            if timed_out or limit_hit:break
        if timed_out or limit_hit:break
        ordered=sorted(pool.values(),key=rank);frontier=ordered[:opt['beam_width']]
        events.append({'event':'beam_frontier','depth':depth,'retained':[list(x) for x in frontier],'beam_truncation':{'count':max(0,len(ordered)-opt['beam_width']),'dropped_routes':[list(x) for x in ordered[opt['beam_width']:]]}})
        if not frontier:break
    termination='WALL_CLOCK_TIMEOUT' if timed_out else ('EXPANSION_LIMIT' if limit_hit else 'BOUNDED_SEARCH_FINISHED')
    status='TIMEOUT' if timed_out else ('FEASIBLE' if incumbent is not None else 'NO_FEASIBLE_FOUND')
    result=plan_result(request,by_id,gate,incumbent if incumbent is not None else partial,status,'beam',None if status=='FEASIBLE' else termination)
    return result,{'method':'beam','gate':gate,'options':opt,'events':events,'expansions':expansions,'termination':termination,'elapsed_seconds':clock()-start,'incumbent_feasible':incumbent is not None,'optimality_claim':False,'truncated':any((e.get('candidate_truncation',{}).get('count',0) or e.get('beam_truncation',{}).get('count',0)) for e in events) or limit_hit}
