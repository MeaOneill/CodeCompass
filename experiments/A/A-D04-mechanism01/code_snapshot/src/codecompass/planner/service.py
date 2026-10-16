"""Versioned contract boundary for B integration; no UI or persistence side effects."""
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from codecompass.retrieval.samples import contract_validator
from codecompass.graph import read_snapshot, validate_span
from .core import greedy_plan
from .validate import check_plan


def plan_request(root,request,units,state,config):
    root=Path(root)
    schema=json.loads((root/'schemas/contracts-1.1.schema.json').read_text(encoding='utf-8'))
    validator=Draft202012Validator(schema,format_checker=contract_validator(root).format_checker)
    validator.validate(request)
    for unit in units:validator.validate(unit)
    real_units=[u for u in units if not u['is_fixture']]
    if real_units:
        matches=[]
        for path in (root/'benchmarks/sources').glob('*/snapshot.json'):
            snapshot=json.loads(path.read_text(encoding='utf-8'))
            if snapshot['snapshot_id']==request['snapshot_id']:matches.append((path.parent,snapshot))
        if len(matches)!=1:raise ValueError('Expected one fixed source snapshot for real materials')
        folder,snapshot=matches[0];contents=read_snapshot(folder,snapshot)
        for unit in real_units:
            for span in unit['source_spans']:validate_span(span,snapshot,contents)
    result,details=greedy_plan(request,units,state,config)
    validator.validate(result)
    audit=check_plan(request,units,result,details['gate'])
    if not audit['structurally_valid']:raise ValueError('Planner output failed replay validation: '+repr(audit))
    return result,{**details,'replay_audit':audit}
