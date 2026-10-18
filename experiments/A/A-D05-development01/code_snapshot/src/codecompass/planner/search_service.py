"""Versioned comparison entry; schema and source validation before all methods."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from codecompass.retrieval.samples import contract_validator
from codecompass.graph import read_snapshot,validate_span
from .core import greedy_plan
from .beam import beam_plan
from .exact import exact_plan
from .comparison_validator import verify_result

def solve_request(root,request,units,state,config,*,method='beam',options=None,certify_small=False):
    if type(certify_small) is not bool:raise ValueError('certify_small must be an explicit boolean')
    root=Path(root);validator=Draft202012Validator(json.loads((root/'schemas/contracts-1.1.schema.json').read_text(encoding='utf-8')),format_checker=contract_validator(root).format_checker)
    validator.validate(request)
    for u in units:validator.validate(u)
    real=[u for u in units if not u['is_fixture']]
    if real:
        snapshots=[]
        for path in (root/'benchmarks/sources').glob('*/snapshot.json'):
            snap=json.loads(path.read_text(encoding='utf-8'))
            if snap['snapshot_id']==request['snapshot_id']:snapshots.append((path.parent,snap))
        if len(snapshots)!=1:raise ValueError('Expected unique fixed snapshot')
        folder,snapshot=snapshots[0];contents=read_snapshot(folder,snapshot)
        for u in real:
            for span in u['source_spans']:validate_span(span,snapshot,contents)
    if method=='beam':result,detail=beam_plan(request,units,state,config,options)
    elif method=='B2':
        if options:raise ValueError('Beam options cannot alter B2')
        result,detail=greedy_plan(request,units,state,config)
    elif method=='exact':
        if options:raise ValueError('Beam options cannot alter exact DP')
        result,detail=exact_plan(request,units,state,config)
    else:raise ValueError('Unknown comparison method')
    if certify_small and method=='beam' and result['status']=='NO_FEASIBLE_FOUND' and len(units)<=12:
        exact,ed=exact_plan(request,units,state,config);detail['certificate']=ed['certificate']
        if exact['status']=='INFEASIBLE_PROVEN':
            result.update(status='INFEASIBLE_PROVEN',proof_path='certificate.json');result['unmet_constraints'].append('COMPLETE_EXACT_ENUMERATION verified absence within this input/budget')
        else:detail['exact_feasible_witness']=exact
    if certify_small and method=='beam' and len(units)>12:detail['certificate_skipped']='EXACT_CAP_12_EXCEEDED; no infeasibility proof'
    validator.validate(result)
    audit=verify_result(request,units,result,detail['gate'],detail.get('certificate'))
    if not audit['valid']:raise ValueError('Independent replay failed: '+repr(audit))
    return result,{**detail,'replay_audit':audit}
