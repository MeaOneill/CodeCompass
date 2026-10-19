"""Versioned runtime boundary; frozen search, evidence math and parameters stay intact."""
import json
from pathlib import Path

from jsonschema import ValidationError
from codecompass.learner import mastery_gate
from .adaptive import remaining_plan, request_for_state, route_audit, validate_input

VERSION = 'A-D07-runtime-v1'


def failure(exc):
    # Never put arbitrary exception messages (possibly transport secrets) in UI/logs.
    code = 'SOURCE_UNAVAILABLE' if isinstance(exc, OSError) else 'INVALID_INPUT'
    if not isinstance(exc, (ValueError, KeyError, TypeError, ValidationError, OSError)):
        code = 'INTERNAL_ERROR'
    return dict(runtime_version=VERSION, status=code, remaining=[], completed=[],
                feasible=False, goal_complete=False, error_type=type(exc).__name__,
                human_task_success=None, optimality_claim=False)


def explain_route(root, request, units, gate, route, completed=()):
    snapshots=[]
    for path in (Path(root)/'benchmarks/sources').glob('*/snapshot.json'):
        row=json.loads(path.read_text(encoding='utf-8'))
        if row['snapshot_id']==request['snapshot_id']:
            snapshots.append(dict(snapshot_id=row['snapshot_id'],commit=row['commit'],
                                  source_manifest_hash=row['hash']))
    goals=set(request['target_concept_ids'])
    known={c for c,g in gate.items() if g['mastered']}
    result=[]
    for uid in [*completed,*route]:
        unit=next(u for u in units if u['id']==uid)
        targets=sorted(set(unit['concept_ids'])&goals)
        needed_by=sorted(u['id'] for u in units if u['id'] in route and any(e['hard'] and e['unit_id']==uid for e in u['prerequisites']))
        result.append(dict(unit_id=uid,completed=uid in completed,base_proxy_cost=unit['base_cost'],
            cost_unit=unit['cost_unit'],target_concepts=targets,
            target_concepts_not_gated=sorted(set(targets)-known),required_by_remaining=needed_by,
            reason='completed coverage retained; no mastery evidence added' if uid in completed else
                   'covers target concepts or a required predecessor; bounded search, no optimality guarantee',
            source_spans=unit['source_spans'],source_versions=snapshots))
    return result


def safe_remaining(root, request, units, state, config, *, completed=(), reference=(), spent=0, options=None):
    try:
        if not all(isinstance(value,dict) for value in (request,state,config)) or not isinstance(units,(list,tuple)):
            raise ValueError('Explicit request, full ledger, config and unit list required')
        result=remaining_plan(root,request,units,state,config,completed=completed,reference=reference,
                              spent=spent,alpha=0,gamma=0,options=options)
        audit=route_audit(request,units,result['gate'],result['remaining'],result['unit_costs'],completed,reference,0,spent)
        if result['status']=='FEASIBLE' and not (audit['valid'] and audit['goal_complete']):
            result['status']='ALGORITHM_INCOMPLETE' if audit['valid'] else 'ALGORITHM_INVALID'
        result.update(runtime_version=VERSION,feasible=result['status']=='FEASIBLE',
                      goal_complete=audit['goal_complete'],human_task_success=None,
                      route_explanations=explain_route(root,request,units,result['gate'],result['remaining'],completed))
        return result
    except Exception as exc:
        result=failure(exc)
        # Keep caller-owned completed identifiers visible, even when input is rejected.
        result['completed']=list(completed) if isinstance(completed,(list,tuple)) else []
        return result


def validate_method_result(root, session, result):
    """Same complete-goal acceptance rule for Ours/B1/B2, without a semantic retry."""
    data=session['data'];request=request_for_state(data['request'],data['state'],data['config'])
    validate_input(root,request,data['units'],data['state'],data['config'])
    if result['status']!='FEASIBLE':
        return dict(result,runtime_version=VERSION)
    concepts={c for u in data['units'] for c in u['concept_ids']}|set(request['target_concept_ids'])
    gate=mastery_gate(data['state'],request['snapshot_id'],concepts,threshold=data['config']['threshold'],
                      quantile=data['config']['quantile'],allow_simulated=request['is_fixture'])
    audit=route_audit(request,data['units'],gate,result['route'],
        {u['id']:u['base_cost'] for u in data['units']},session['completed'],(),0,session['spent'])
    status='FEASIBLE' if audit['valid'] and audit['goal_complete'] else ('ALGORITHM_INCOMPLETE' if audit['valid'] else 'ALGORITHM_INVALID')
    return dict(result,status=status,runtime_version=VERSION,acceptance_replay=audit)
