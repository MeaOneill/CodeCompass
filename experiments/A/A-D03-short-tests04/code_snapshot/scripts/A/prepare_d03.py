"""Integrate two existing dev tasks and one common explicit source-line cost policy."""
from pathlib import Path
import ast,copy,hashlib,json,re
ROOT=Path(__file__).resolve().parents[2]

def save(path,obj):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode())

def main():
 old=json.loads((ROOT/'schemas/contracts.schema.json').read_text(encoding='utf-8'));new=copy.deepcopy(old)
 new['$id']='https://codecompass.invalid/schemas/contracts-1.1.0';new['title']='CodeCompass compatible contracts 1.1.0'
 for name in ['RepoSnapshot','LearningUnit','LearnerEvidence','PlanningRequest','PlanResult','ExperimentEvent','CodeTask']:
  new['$defs'][name]['properties']['schema_version']={'enum':['1.0.0','1.1.0']}
 taskdef=new['$defs']['CodeTask'];taskdef['properties']['origin']['properties']['kind']={'enum':['upstream_todo_adapted','source_behavior_adapted','team_designed_debug']}
 taskdef['allOf']=[{'if':{'properties':{'origin':{'properties':{'kind':{'enum':['source_behavior_adapted','team_designed_debug']}}}}},'then':{'properties':{'schema_version':{'const':'1.1.0'}}}}]
 save('schemas/contracts-1.1.schema.json',new)
 source=(ROOT/'benchmarks/sources/boltons/boltons/iterutils.py').read_text(encoding='utf-8');lines=source.splitlines();tree=ast.parse(source)
 funcs={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
 sid='boltons-4e5faa3d7e40'
 def span(fn):
  n=funcs[fn];return {'snapshot_id':sid,'path':'boltons/iterutils.py','start_line':n.lineno,'end_line':n.end_lineno,'content_hash':hashlib.sha256(('\n'.join(lines[n.lineno-1:n.end_lineno])+'\n').encode()).hexdigest()}
 originals=json.loads((ROOT/'benchmarks/dev/task_001_units.json').read_text(encoding='utf-8'))
 unitmap={u['id']:copy.deepcopy(u) for u in originals}
 def unit(uid,fn,concepts,basis):
  return {'schema_version':'1.1.0','object_type':'LearningUnit','is_fixture':False,'id':uid,'source_spans':[span(fn)],'concept_ids':concepts,'prerequisites':[],
          'provenance':{'kind':'static_source','evidence':[f'boltons commit 4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d: {fn}',basis],'proposed_by':'Codex Agent A','review_status':'pending','reviewer':None,'confidence':None},'base_cost':None,'cost_unit':'proxy_cost','cost_basis':None}
 unitmap['u_windowed_iter']=unit('u_windowed_iter','windowed_iter',['python.tee','python.keyword_presence'],'tee与_UNSET分支直接见L494-510；概念覆盖是AI工程材料映射，不是人类金标准')
 unitmap['u_positive_int']=unit('u_positive_int','_validate_positive_int',['python.type_validation'],'对照int(value)的转换语义与task002要求的严格类型；这不是task002修复答案或完整校验实现')
 for u in unitmap.values():
  u['schema_version']='1.1.0';u['base_cost']=sum(s['end_line']-s['start_line']+1 for s in u['source_spans']);u['cost_basis']='A-D03 common fixed inclusive source-line proxy v1; not learning minutes'
 save('benchmarks/dev/D03/units.json',list(unitmap.values()))
 catalog=json.loads((ROOT/'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
 specs={t['task_id']:t for t in catalog['tasks'] if t['task_id'] in ['task_001','task_002']}
 t1=json.loads((ROOT/'benchmarks/dev/task_001.json').read_text(encoding='utf-8'));t1=copy.deepcopy(t1);t1['schema_version']='1.1.0'
 t2={**copy.deepcopy(t1),'task_id':'task_002','title':specs['task_002']['title'],'task_type':'debug','source_spans':specs['task_002']['source_spans'],
     'origin':{'kind':'team_designed_debug','description':'B-D02 authored windowed_iter boundary task; source benchmarks/B/task_catalog.json; not an upstream TODO/Issue','issue_url':None},
     'goal':specs['task_002']['prompt'],'requirements':[specs['task_002']['prompt'],'解释/时间/材料按B独立rubric审核；本轮只做路径工程验证。'],
     'required_concept_ids':specs['task_002']['required_concept_ids'],'learning_unit_ids':['u_iterable','u_windowed_iter','u_positive_int'],
     'rubric':[{**r,'acceptance':[r['description']]} for r in specs['task_002']['rubric']],
     'success_rule':specs['task_002']['success_rule'],'contribution_preparation':'为真实windowed_iter API输入边界补回归；没有上游提交或真人学习结果。','evaluator_status':'implemented_not_reviewed'}
 t1['evaluator_status']='implemented_not_reviewed'
 for t in [t1,t2]:save('benchmarks/dev/D03/'+t['task_id']+'.json',t)
 rst_path=ROOT/'benchmarks/sources/boltons_B_D02/docs/iterutils.rst';rst=rst_path.read_text(encoding='utf-8')
 names=re.findall(r'^\.\. autofunction:: (\w+)',rst,re.MULTILINE)
 docpos={name:i for i,name in enumerate(names)}
 fn_by_unit={'u_iterable':'is_iterable','u_chunked_iter':'chunked_iter','u_chunked':'chunked','u_windowed_iter':'windowed_iter','u_positive_int':'_validate_positive_int'}
 routes={}
 for task in [t1,t2]:
  routes[task['task_id']]=sorted(task['learning_unit_ids'],key=lambda uid:(docpos.get(fn_by_unit[uid],10**9),unitmap[uid]['source_spans'][0]['start_line'],uid))
 original_b0=json.loads((ROOT/'configs/B/B0_fixed.json').read_text(encoding='utf-8'))
 assert routes['task_001']==original_b0['routes']['task_001']
 config={'version':'A-D03-dev-0.1','cost_unit':'proxy_cost','cost_policy':'fixed-inclusive-source-lines-v1','budget':100,'quantile':0.1,'threshold':0.7,
         'methods':['B0-pinned-document-prefix','B2-initial-closure-gain-greedy'],'routes':routes,
         'documentation':{'path':rst_path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(rst_path.read_bytes()).hexdigest()},
         'undocumented_unit_rule':'Append missing private helper in source-line order; no reordering based on planner result',
         'diagnostics_implemented':False,'formal_study_ready':False,'human_cost_calibration':None,
         'unit_costs':{uid:u['base_cost'] for uid,u in unitmap.items()}}
 save('configs/A/D03_common.json',config)
 save('configs/A/D03_profiles.json',{'is_simulated':True,'profiles':[{'id':'sim_unknown','label':'模拟：无独立能力证据','known_concepts':[]},{'id':'sim_evidence','label':'模拟：基础与接口知识有独立题证据','known_concepts':['python.iterator_protocol','python.keyword_presence','boltons.wrapper_compatibility','python.type_validation']}],'passes_per_known_concept':10,'evidence_generation':'deterministic fixture records, never human observations'})
 print(json.dumps({'routes':routes,'costs':config['unit_costs']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
