"""Validate D01 artifacts, not planner quality or participant performance."""
import argparse
import ast
import copy
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tmp/d01_validation'))
from jsonschema import Draft202012Validator, FormatChecker


def load(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate():
    schema = load('schemas/contracts.schema.json')
    Draft202012Validator.check_schema(schema)
    checker = FormatChecker()
    @checker.checks('date-time', raises=(ValueError, TypeError))
    def check_datetime(value):
        if not isinstance(value, str):
            return True
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return 'T' in value and parsed.tzinfo is not None
    validator = Draft202012Validator(schema, format_checker=checker)
    examples = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'schemas/examples').glob('*.json')}
    manifest_path = ROOT/'experiments/A/A-D01-20261016-foundation/input_manifest.json'
    if manifest_path.exists():
        for row in json.loads(manifest_path.read_text(encoding='utf-8')):
            assert sha((ROOT/row['path']).read_bytes()) == row['sha256'], row['path']
    assert len(examples) == 7
    for data in examples.values():
        validator.validate(data)
    task = load('benchmarks/dev/task_001.json')
    units = load('benchmarks/dev/task_001_units.json')
    snap = load('benchmarks/sources/boltons/snapshot.json')
    for data in [task,snap,*units]:
        validator.validate(data)
    negative = []
    def reject(label, name, field, value=None, delete=False):
        bad = copy.deepcopy(examples[name])
        if delete:
            del bad[field]
        else:
            bad[field] = value
        assert not validator.is_valid(bad), label
        negative.append(label)
    reject('missing commit','repo_snapshot','commit',delete=True)
    reject('invalid SHA','repo_snapshot','commit','main')
    reject('unknown field','learning_unit','surprise',True)
    reject('unknown cost allowed only as null','learning_unit','base_cost','unknown')
    reject('negative budget','planning_request','budget',-1)
    reject('null budget','planning_request','budget',None)
    reject('minutes are not proxy units','planning_request','cost_unit','minutes')
    reject('invalid planner status','plan_result','status','SUCCESS')
    reject('invalid timestamp','learner_evidence','timestamp','yesterday')
    reject('invalid outcome','learner_evidence','outcome',1)
    reject('missing fixture marker','plan_result','is_fixture',delete=True)
    reject('wrong schema version','code_task','schema_version','0.0')
    files = sorted(snap['files'],key=lambda x:x['path'])
    assert sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode()) == snap['hash']
    bundle = ROOT/'benchmarks/sources/boltons'
    for f in files:
        b = (bundle/f['path']).read_bytes()
        assert len(b)==f['bytes'] and sha(b)==f['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['git_blob']
    count = 0
    def check_span(span):
        nonlocal count
        p = PurePosixPath(span['path'])
        assert not p.is_absolute() and '..' not in p.parts and ':' not in span['path'] and '\\' not in span['path']
        assert span['snapshot_id']==snap['snapshot_id']
        lines = (bundle/span['path']).read_text(encoding='utf-8').splitlines()
        a,b = span['start_line'],span['end_line']
        assert 1<=a<=b<=len(lines)
        assert sha(('\n'.join(lines[a-1:b])+'\n').encode())==span['content_hash']
        count+=1
    ids = {u['id'] for u in units}
    for u in units:
        for sp in u['source_spans']:check_span(sp)
        for edge in u['prerequisites']:
            assert edge['unit_id'] in ids
            if edge['hard']:
                assert edge['provenance']['review_status']=='approved' and edge['provenance']['reviewer']
    for sp in task['source_spans']:check_span(sp)
    graph=load('report_materials/A/F02_sources.json')
    for node in graph['nodes']:check_span(node['source_span'])
    source=(bundle/'boltons/iterutils.py').read_text(encoding='utf-8')
    functions={n.name:n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
    for edge in graph['static_edges']:
        fn=functions[edge['from']]
        assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id==edge['to'] and n.lineno==edge['line'] for n in ast.walk(fn))
    assert snap['commit']==task['repo_commit'] and snap['snapshot_id']==task['snapshot_id']
    assert set(task['learning_unit_ids'])<=ids
    assert set(task['required_concept_ids']) <= {x for u in units for x in u['concept_ids']}
    assert sum(r['points'] for r in task['rubric'])==task['max_score']==10
    assert source.splitlines()[328].strip()=='# TODO: add count kwarg?'
    assert examples['planning_request']['is_fixture'] and examples['plan_result']['is_fixture']
    # Load the original stand-alone module; no build scripts, no submitted patch.
    spec=importlib.util.spec_from_file_location('d01_original_iterutils',bundle/'boltons/iterutils.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    checks=[]
    def check(label, condition):
        assert condition,label
        checks.append(label)
    check('original chunked count',module.chunked(range(10),3,count=2)==[[0,1,2],[3,4,5]])
    check('original short tail',list(module.chunked_iter(range(4),3))==[[0,1,2],[3]])
    check('original explicit None padding',list(module.chunked_iter(range(4),3,fill=None))==[[0,1,2],[3,None,None]])
    check('original strings',list(module.chunked_iter('abcd',3))==['abc','d'])
    check('original bytes',list(module.chunked_iter(b'abcd',3))==[b'abc',b'd'])
    check('original empty input',list(module.chunked_iter([],3))==[])
    consumed=[]
    def source_iter():
        for i in range(10):
            consumed.append(i);yield i
    gen=module.chunked_iter(source_iter(),3)
    check('original construction lazy',consumed==[])
    check('original first next consumes one chunk',next(gen)==[0,1,2] and len(consumed)==3)
    try:
        list(module.chunked_iter(range(10),3,count=2))
    except ValueError:
        checks.append('original count not supported: expected pre-task failure')
    else:
        raise AssertionError('original unexpectedly supports count')
    return dict(schema_examples_passed=len(examples),negative_inputs_rejected=negative,source_spans_checked=count,source_files_verified=len(files),static_edges_verified=len(graph['static_edges']),upstream_behavior_smoke=checks,
                independent_evaluator='NOT_IMPLEMENTED_BY_A',task_human_pilot='NOT_RUN',planner='NOT_RUN',independent_review='NOT_REVIEWED',formal_experiments=0)


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args()
    started=datetime.datetime.now(datetime.timezone.utc).isoformat();t0=time.perf_counter()
    try:
        details=validate();exit_code=0;error=None
    except Exception as exc:
        details={};exit_code=1;error=repr(exc)
    result={'run_id':Path(args.output).parent.name,'task_id':'A-D01','evidence_type':'development_validation','started_at':started,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'machine':platform.node(),'python':sys.version,'command':sys.argv,'exit_code':exit_code,'elapsed_seconds':time.perf_counter()-t0,'error':error,'details':details}
    out=ROOT/args.output
    if out.exists():
        raise FileExistsError('Choose a fresh output path; preserve previous evidence')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2));return exit_code

if __name__=='__main__':
    raise SystemExit(main())
