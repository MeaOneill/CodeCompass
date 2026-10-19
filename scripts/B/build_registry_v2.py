"""App-facing source registry from public specs/AST only, never evaluator keys."""
import ast
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from codecompass.graph import read_snapshot,make_span,validate_span
from codecompass.app.diagnostics_v2 import ITEMS,public_item
from jsonschema import Draft202012Validator,FormatChecker


def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    catalog=json.loads((ROOT/'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    common=json.loads((ROOT/'configs/A/D03_common.json').read_text(encoding='utf-8'))
    validator=Draft202012Validator(json.loads((ROOT/'schemas/contracts-1.1.schema.json').read_text(encoding='utf-8')),format_checker=FormatChecker())
    records=[]
    for t in catalog['tasks']:
        tid=t['task_id'];module=t['module'];source_root=ROOT/('benchmarks/sources/boltons' if module=='iterutils' else 'benchmarks/sources/boltons_B_D02')
        snap=json.loads((source_root/'snapshot.json').read_text(encoding='utf-8'));contents=read_snapshot(source_root,snap)
        path='boltons/'+module+'.py';text=contents[path].decode('utf-8');lines=text.splitlines();tree=ast.parse(text)
        units=[];materials=[];targets=list(t['required_concept_ids']);context=[]
        nodes={n.name:n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        # Preserve A's exact dev01/02 units and costs. New tasks use declared
        # signature + executable-body spans; docstring examples are not gold.
        if tid in ('task_001','task_002'):
            spec=json.loads((ROOT/f'benchmarks/dev/D03/{tid}.json').read_text(encoding='utf-8'))
            units=[u for u in json.loads((ROOT/'benchmarks/dev/D03/units.json').read_text(encoding='utf-8')) if u['id'] in spec['learning_unit_ids']]
            public={k:spec[k] for k in ('task_id','title','goal','requirements','repo_commit')}
        else:
            for index,fn in enumerate(t['functions']):
                n=nodes[fn];body=n.body
                if isinstance(body[0],ast.Expr) and isinstance(body[0].value,ast.Constant) and isinstance(body[0].value.value,str):body=body[1:]
                spans=[make_span(snap['snapshot_id'],path,text,n.lineno,n.body[0].lineno-1),
                       make_span(snap['snapshot_id'],path,text,body[0].lineno,n.end_lineno)]
                source_concept='source.function.'+module+'.'+fn;targets.append(source_concept)
                # Public task concept mapping is a candidate, never a gold key.
                concepts=[source_concept]+t['required_concept_ids'][index::len(t['functions'])]
                unit=dict(schema_version='1.1.0',object_type='LearningUnit',is_fixture=False,id=tid+'__'+fn,
                    source_spans=spans,concept_ids=concepts,prerequisites=[],
                    provenance=dict(kind='static_source',evidence=[f"{t['repo_url']}/blob/{t['repo_commit']}/{path}#L{n.lineno}"],
                        proposed_by='Codex Agent B',review_status='pending',reviewer=None,confidence=None),
                    base_cost=sum(s['end_line']-s['start_line']+1 for s in spans),cost_unit='proxy_cost',
                    cost_basis='D06-v2 explicit function signature and executable-body inclusive line spans; not minutes')
                units.append(unit)
            public=dict(task_id=tid,title=t['title'],goal='独立理解固定源码并按公开要求作答。',requirements=[t['prompt']],repo_commit=t['repo_commit'])
            # Equal public source context for all methods. Include directly
            # referenced module imports/assignments and report unresolved names.
            used={a.id for fn in t['functions'] for a in ast.walk(nodes[fn]) if isinstance(a,ast.Name) and isinstance(a.ctx,ast.Load)}
            for n in tree.body:
                names=set()
                if isinstance(n,(ast.Import,ast.ImportFrom)):names={a.asname or a.name.split('.')[0] for a in n.names}
                elif isinstance(n,ast.Assign):names={x.id for target in n.targets for x in ast.walk(target) if isinstance(x,ast.Name)}
                if names&used:
                    span=make_span(snap['snapshot_id'],path,text,n.lineno,n.end_lineno)
                    context.append(dict(names=sorted(names&used),source_span=span,text='\n'.join(lines[n.lineno-1:n.end_lineno])))
        for u in units:
            validator.validate(u)
            for span in u['source_spans']:
                validate_span(span,snap,contents)
                materials.append(dict(unit_id=u['id'],source_span=span,text='\n'.join(f'{i+1:4}  {lines[i]}' for i in range(span['start_line']-1,span['end_line']))))
        q=ITEMS[tid];assert q['concept_id'] in targets
        records.append(dict(task=public,task_id=tid,split=t['split'],snapshot=snap,source_root=source_root.relative_to(ROOT).as_posix(),
            target_concept_ids=targets,units=units,materials=materials,source_context=context,
            quiz=dict(item_id=q['item_id'],concept_id=q['concept_id'],independent=True,source=q['basis'],cost=1.,cost_unit='proxy_cost',probability=None),
            public_quiz=public_item(tid),config=common,source_hash=hashlib.sha256(contents[path]).hexdigest(),
            human_review='NOT_REVIEWED',source_coverage_policy='Explicit required function targets added from public function list; independent scoring unchanged',
            context_cost_policy='Module context provided identically to every method, not extra scheduled learning units; reading/decision time still counts'))
    result=dict(version='B-D06-executable-candidate-2',formal_study_ready=False,records=records,
        private_answers_loaded=False,original_gold_rubrics_modified=False)
    (out/'registry.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'registry.sha256').write_text(hashlib.sha256((out/'registry.json').read_bytes()).hexdigest()+'\n',encoding='ascii')
    return result


if __name__=='__main__':
    r=build(ROOT/'benchmarks/B/executable-v2');print(json.dumps({'task_records':len(r['records']),'formal_study_ready':False,'private_answers_loaded':False}))
