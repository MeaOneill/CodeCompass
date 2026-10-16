"""Export fixed-snapshot AST facts and separate teaching candidates."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from codecompass.graph import extract_snapshot, hard_edges, cyclic_components


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);args=p.parse_args()
    if not args.run_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in args.run_id):
        raise ValueError('run_id must be a single safe identifier')
    out=ROOT/'experiments/A'/args.run_id;out.mkdir(parents=True,exist_ok=False)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();t0=time.perf_counter()
    snap=json.loads((ROOT/'benchmarks/sources/boltons/snapshot.json').read_text(encoding='utf-8'))
    units=json.loads((ROOT/'benchmarks/dev/task_001_units.json').read_text(encoding='utf-8'))
    graph=extract_snapshot(ROOT/'benchmarks/sources/boltons',snap)
    for key in ['nodes','edges','source_manifest']:write_json(out/(key+'.json'),graph[key])
    teaching=[]
    for u in units:
        for pre in u['prerequisites']:
            teaching.append({'from':pre['unit_id'],'to':u['id'],'kind':'teaching_prerequisite','hard':pre['hard'],'provenance':pre['provenance'],'source_spans':u['source_spans'],'note':'AI提议与B工程反馈；无独立人类审核，保持soft'})
    write_json(out/'teaching_edges.json',teaching)
    # Synthetic stress fixture for the same task, not a human profile or gold standard.
    fixture={'is_fixture':True,'task_id':'task_001','snapshot_id':snap['snapshot_id'],
             'label':'controlled synthetic structure only; not empirical learning results',
             'units':[{'id':'shared','concept_ids':['iterator'],'base_cost':1},
                      {'id':'material_A','concept_ids':['chunk_behavior'],'base_cost':2},
                      {'id':'material_B','concept_ids':['chunk_behavior'],'base_cost':3},
                      {'id':'goal','concept_ids':['compatible_count'],'base_cost':2},
                      {'id':'cycle_X','concept_ids':['fixture_X'],'base_cost':1},
                      {'id':'cycle_Y','concept_ids':['fixture_Y'],'base_cost':1}],
             'fixture_mastered_concepts':['iterator'],
             'teaching_edges':[{'from':a,'to':b,'hard':False,'review_status':'fixture_pending'} for a,b in [('shared','material_A'),('shared','material_B'),('material_A','goal'),('material_B','goal'),('cycle_X','cycle_Y'),('cycle_Y','cycle_X')]],
             'alternative_materials':[['material_A','material_B']],
             'cost_unit':'proxy_cost','cost_status':'invented_for_fixture_only_not_calibrated'}
    fixture['cycle_components']=cyclic_components({u['id'] for u in fixture['units']},[(e['from'],e['to']) for e in fixture['teaching_edges']])
    assert fixture['cycle_components']==[['cycle_X','cycle_Y']]
    write_json(out/'controlled_fixture.json',fixture)
    task=json.loads((ROOT/'benchmarks/dev/task_001.json').read_text(encoding='utf-8'))
    selected=[]
    for span in task['source_spans']:
        matches=[n for n in graph['nodes'] if n['source_span']==span and n['kind']=='function']
        if len(matches)!=1:raise ValueError('Task source does not identify exactly one function')
        selected.extend(matches)
    keep={n['id'] for n in selected};keep.add('boltons/iterutils.py::module')
    import_edges=[e for e in graph['edges'] if e['kind']=='imports' and e['from']=='boltons/iterutils.py::module' and e['symbol']=='itertools']
    keep.update(e['to'] for e in import_edges)
    local_nodes=[n for n in graph['nodes'] if n['id'] in keep]
    local_edges=[e for e in graph['edges'] if (e['kind'] in ('contains','imports') and e['to'] in keep) or (e['from'] in keep and e['kind']=='call_unknown' and e['from']!='boltons/iterutils.py::module')]
    write_json(out/'task_001_local_graph.json',{'task_id':'task_001','commit':snap['commit'],'repo_url':snap['url'],'snapshot_id':snap['snapshot_id'],'selection_rule':'task.source_spans对应四函数、模块、import itertools声明与函数内调用语法；非完整跨模块图','nodes':local_nodes,'edges':local_edges,'teaching_edges':teaching,'model_candidate_edges':[]})
    git=os.environ.get('CODECOMPASS_GIT','git')
    base=subprocess.check_output([git,'rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    inputs=[]
    paths=[ROOT/'benchmarks/dev/task_001.json',ROOT/'benchmarks/dev/task_001_units.json',ROOT/'benchmarks/sources/boltons/snapshot.json',*sorted((ROOT/'src/codecompass/graph').glob('*.py')),Path(__file__).resolve()]
    for path in paths:inputs.append({'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    write_json(out/'input_manifest.json',inputs)
    summary={'run_id':args.run_id,'task_id':'A-D02','evidence_type':'development_validation','started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':time.perf_counter()-t0,'exit_code':0,'snapshot_commit':snap['commit'],'base_commit':base,'code_commit':None,'uncommitted_code_manifest':out.relative_to(ROOT).as_posix()+'/input_manifest.json','machine':platform.node(),'python':sys.version,'actor':'Codex Agent A','model_id':None,'contract_version':'1.0.0','graph_format_version':'0.1.0','command':sys.argv,'node_count':len(graph['nodes']),'edge_count':len(graph['edges']),'source_files':len(graph['source_manifest']),'parse_errors':[x for x in graph['source_manifest'] if x['status']=='parse_error'],'hard_teaching_edges':hard_edges(units),'formal_experiments':0,'independent_review':'NOT_REVIEWED','cost':None,'metrics':None,'seed':None}
    write_json(out/'registration.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
