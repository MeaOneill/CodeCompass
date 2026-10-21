"""Build one source-grounded second-repository functional case, not a test task."""
import ast
import copy
import json
import secrets
import datetime
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from codecompass.graph import make_span,read_snapshot
from codecompass.app.relay_v2 import prepare


def build():
    folder=ROOT/'benchmarks/sources/more_itertools_B_D07_v2';snap=json.loads((folder/'snapshot.json').read_text())
    contents=read_snapshot(folder,snap);path='more_itertools/more.py';text=contents[path].decode();lines=text.splitlines()
    fn=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='chunked')
    spans=[make_span(snap['snapshot_id'],path,text,fn.lineno,fn.body[0].lineno-1),make_span(snap['snapshot_id'],path,text,fn.body[1].lineno,fn.end_lineno)]
    u=dict(schema_version='1.1.0',object_type='LearningUnit',is_fixture=False,id='B07_more_chunked',source_spans=spans,
        concept_ids=['python.iterator_protocol','source.function.more_itertools.chunked'],prerequisites=[],
        provenance=dict(kind='static_source',evidence=[f"{snap['url']}/blob/{snap['commit']}/{path}#L{fn.lineno}"],proposed_by='Codex Agent B',review_status='pending',reviewer=None,confidence=None),
        base_cost=sum(s['end_line']-s['start_line']+1 for s in spans),cost_unit='proxy_cost',cost_basis='signature + executable body inclusive lines; functional demo only')
    old=prepare(ROOT,'task_002','p_'+'0'*32,True)
    d=dict(snapshot=snap,source_root=folder.relative_to(ROOT).as_posix(),task_id='B07_more_chunked',units=[u],config=old['config'],
        materials=[dict(unit_id=u['id'],source_span=s,text='\n'.join(f'{i+1:4}  {lines[i]}' for i in range(s['start_line']-1,s['end_line']))) for s in spans],
        source_context=[],target_concept_ids=u['concept_ids'],
        task=dict(task_id='B07_more_chunked',repo_commit=snap['commit'],title='more-itertools跨仓库功能案例：chunked的迭代器消费',
            goal='根据固定源码解释chunked如何消费迭代器，并在新仓库独立再测。仅验证功能，不进正式任务池。',
            requirements=['定位真实chunked函数及源码行号。','结合提供的take辅助函数，解释iter(callable, sentinel)与partial如何消费迭代器。','完成一次独立新题；源项目证据不直接复制为目标项目掌握。']),
        quiz=dict(item_id='B07-more-counter-v1',concept_id='python.iterator_protocol',independent=True,source='Independent custom iterator snippet; distinct from boltons quiz',cost=1.,cost_unit='proxy_cost',probability=None),
        source_dependencies='Read-only source excerpt; more.py dependencies are not installed/imported; not a runnable upstream checkout',formal_task=False)
    # Module dependency statements that directly support the real function.
    for n in ast.parse(text).body:
        if isinstance(n,ast.ImportFrom) and n.module in ('functools','itertools'):
            span=make_span(snap['snapshot_id'],path,text,n.lineno,n.end_lineno)
            d['source_context'].append(dict(source_span=span,text='\n'.join(f'{i+1:4}  {lines[i]}' for i in range(n.lineno-1,n.end_lineno))))
    recipe_path='more_itertools/recipes.py';recipe=contents[recipe_path].decode();recipe_lines=recipe.splitlines()
    take=next(n for n in ast.parse(recipe).body if isinstance(n,ast.FunctionDef) and n.name=='take')
    span=make_span(snap['snapshot_id'],recipe_path,recipe,take.lineno,take.end_lineno)
    d['source_context'].append(dict(source_span=span,text='\n'.join(f'{i+1:4}  {recipe_lines[i]}' for i in range(take.lineno-1,take.end_lineno))))
    d['context_policy']='Supporting take source is common context for every method; not an extra scheduled unit. Actual reading time counts.'
    out=ROOT/'benchmarks/B/D07';out.mkdir(parents=True,exist_ok=True)
    version=out/('cross_project_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d_%H%M%S')+'.json')
    with version.open('x',encoding='utf-8',newline='\n') as f:json.dump(d,f,ensure_ascii=False,indent=2)
    (out/'cross_project.json').write_bytes(version.read_bytes())
    print(json.dumps(dict(case=d['task_id'],snapshot=snap['snapshot_id'],proxy_cost=u['base_cost'],formal_task=False)))


if __name__=='__main__':build()
