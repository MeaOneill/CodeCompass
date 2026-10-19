"""D04 shared input model only; B2 implementation remains untouched."""
import hashlib,json,math
from codecompass.learner import mastery_gate
from .core import validate_request
EPS=1e-9

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def input_hash(request,units,gate):
    req={**request,'unit_ids':sorted(request['unit_ids'])}
    return canonical_hash({'request':req,'units':sorted(units,key=lambda u:u['id']),'gate':gate})

def model(request,units,state,config):
    by_id=validate_request(request,units,state,config)
    concepts={c for u in units for c in u['concept_ids']}|set(request['target_concept_ids'])
    gate=mastery_gate(state,request['snapshot_id'],concepts,threshold=config['threshold'],quantile=config['quantile'],allow_simulated=request['is_fixture'])
    return by_id,gate,{c for c,g in gate.items() if g['mastered']}

def cost_of(route,by_id):return math.fsum(by_id[u]['base_cost'] for u in sorted(route))

def covered(route,by_id,mastered):
    return set(mastered)|{c for u in route for c in by_id[u]['concept_ids']}

def plan_result(request,by_id,gate,route,status,method,termination=None,proof_path=None):
    known={c for c,g in gate.items() if g['mastered']};goals=set(request['target_concept_ids']);trace=[]
    for c in sorted(known):
        trace.append({'step':len(trace)+1,'unit_id':None,'reason':'EVIDENCE_GATE: '+c,'evidence_ids':gate[c]['evidence_ids']})
    for uid in route:
        u=by_id[uid];prereqs=[e['unit_id'] for e in u['prerequisites'] if e['hard']]
        spans='; '.join(f"{s['path']}:L{s['start_line']}-{s['end_line']}" for s in u.get('source_spans',[])) or 'explicit structural fixture'
        trace.append({'step':len(trace)+1,'unit_id':uid,'reason':f'{method}: selected material; hard prerequisites={prereqs}; source={spans}; proxy_cost={u["base_cost"]}; soft edges are not constraints','evidence_ids':[]})
        known.update(u['concept_ids'])
    missing=sorted(goals-known);unmet=['uncovered target: '+c for c in missing]
    if status!='FEASIBLE' and termination:unmet.append(termination)
    return {'schema_version':'1.0.0','object_type':'PlanResult','is_fixture':request['is_fixture'],'plan_id':request['request_id']+'-'+method,'request_id':request['request_id'],'status':status,'ordered_units':list(route),'coverage':{'required_concept_ids':sorted(goals),'covered_concept_ids':sorted(goals&known),'ratio':len(goals&known)/len(goals) if goals else None},'unmet_constraints':unmet,'estimated_cost':cost_of(route,by_id),'cost_unit':'proxy_cost','reason_trace':trace,'proof_path':proof_path}
