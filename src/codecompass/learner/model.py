"""Pure independent-evidence ledger with conservative integer-Beta gating.

The Beta/binomial identity is DLMF 8.17.5. Only integer counts with unit
Beta(1,1) prior are supported; this is not a calibrated knowledge tracker.
"""
import copy
from datetime import datetime
import json
import math


def beta_quantile(alpha, beta, q=0.1):
    if type(alpha) is not int or type(beta) is not int or min(alpha,beta)<1 or alpha+beta>2001:
        raise ValueError('Integer posterior counts in [1,2000] are required')
    if type(q) not in (int,float) or not math.isfinite(q) or not 0<q<1:
        raise ValueError('Quantile must lie strictly inside (0,1)')
    n=alpha+beta-1
    logs=[math.lgamma(n+1)-math.lgamma(j+1)-math.lgamma(n-j+1) for j in range(alpha,n+1)]
    lo,hi=0.0,1.0
    for _ in range(64):
        x=(lo+hi)/2
        if x==lo or x==hi:break
        terms=[math.exp(c+j*math.log(x)+(n-j)*math.log1p(-x)) for c,j in zip(logs,range(alpha,n+1))]
        cdf=min(1.0,math.fsum(terms))
        if cdf<q:lo=x
        else:hi=x
    return lo


def initial_state(user_id, *, is_simulated=False):
    if not isinstance(user_id,str) or not user_id or type(is_simulated) is not bool:
        raise ValueError('Explicit user identity and simulation flag required')
    return {'state_version':'0.1.0','pseudonymous_user_id':user_id,'is_simulated':is_simulated,'records':[]}


def _eligible(state, evidence, allow_simulated):
    if state['is_simulated'] and not allow_simulated:
        raise ValueError('Simulated state cannot be used in a real-evidence call')
    for key in ('evidence_id','item_id','concept_id','project','timestamp'):
        if not isinstance(evidence.get(key),str) or not evidence[key]:
            raise ValueError('Missing evidence identity: '+key)
    t=datetime.fromisoformat(evidence['timestamp'].replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('Evidence timestamp needs a timezone')
    if evidence.get('pseudonymous_user_id')!=state['pseudonymous_user_id']:
        raise ValueError('Evidence user mismatch')
    if type(evidence.get('is_fixture')) is not bool:
        raise ValueError('Explicit fixture marker required')
    if evidence['is_fixture'] != state['is_simulated']:
        raise ValueError('Real and fixture evidence cannot be mixed')
    return (evidence.get('independent') is True
            and evidence.get('evidence_type') in ('independent_quiz','independent_code_task')
            and evidence.get('outcome') in ('pass','fail'))


def validate_state(state, *, allow_simulated=False):
    if (state.get('state_version')!='0.1.0' or type(state.get('is_simulated')) is not bool
        or not isinstance(state.get('pseudonymous_user_id'),str) or not state['pseudonymous_user_id']
        or not isinstance(state.get('records'),list)):
        raise ValueError('Unsupported learner ledger')
    ids=set();items=set()
    for e in state['records']:
        if not _eligible(state,e,allow_simulated):raise ValueError('Ineligible record in accepted ledger')
        key=(e['concept_id'],e['item_id'])
        if e['evidence_id'] in ids or key in items:raise ValueError('Duplicate accepted evidence/item')
        ids.add(e['evidence_id']);items.add(key)
    if state['is_simulated'] and not allow_simulated:raise ValueError('Simulation flag must be explicit')
    return True


def update_evidence(state, evidence, *, allow_simulated=False):
    """Return (new_state, decision); never modify inputs or count repeat items."""
    validate_state(state,allow_simulated=allow_simulated)
    new=copy.deepcopy(state)
    if not _eligible(state,evidence,allow_simulated):return new,'IGNORED_NONINDEPENDENT_OR_UNSCORED'
    for old in state['records']:
        if old['evidence_id']==evidence['evidence_id']:
            if old!=evidence:raise ValueError('Evidence ID reused with altered content')
            return new,'DUPLICATE_EVIDENCE'
        if (old['concept_id'],old['item_id'])==(evidence['concept_id'],evidence['item_id']):
            return new,'DUPLICATE_ITEM'
    new['records'].append(copy.deepcopy(evidence))
    return new,'ACCEPTED'


def planning_rows(state, project, *, quantile=0.1, allow_simulated=False):
    validate_state(state,allow_simulated=allow_simulated)
    grouped={}
    for e in state['records']:
        if e['project']==project:grouped.setdefault(e['concept_id'],[]).append(e)
    result=[]
    for concept,records in sorted(grouped.items()):
        a=1+sum(e['outcome']=='pass' for e in records)
        b=1+sum(e['outcome']=='fail' for e in records)
        result.append({'concept_id':concept,'alpha':a,'beta':b,
                       'evidence_ids':sorted(e['evidence_id'] for e in records),
                       'lower_bound':beta_quantile(a,b,quantile),'quantile':quantile})
    return result


def mastery_gate(state, project, concepts, *, threshold=0.7, quantile=0.1, allow_simulated=False):
    if type(threshold) not in (int,float) or not math.isfinite(threshold) or not 0<threshold<1:
        raise ValueError('Mastery threshold must lie strictly inside (0,1)')
    rows=planning_rows(state,project,quantile=quantile,allow_simulated=allow_simulated)
    by_id={r['concept_id']:r for r in rows};result={}
    for concept in sorted(set(concepts)):
        row=by_id.get(concept)
        result[concept]=({'concept_id':concept,'lower_bound':None,'evidence_ids':[],
                         'mastered':False,'reason':'unknown: no independent current-project item'} if row is None else
                        {**row,'mastered':row['lower_bound']>=threshold,
                         'reason':'posterior lower quantile meets threshold' if row['lower_bound']>=threshold else 'insufficient lower-bound evidence'})
    return result
