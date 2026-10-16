"""Human-readable live D03 engineering demo; no UI server or participant study."""
import argparse,json,sys,math
from jsonschema.exceptions import ValidationError
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from scripts.A.run_d03 import load,make_profile,make_request,b0_adapter
from codecompass.planner import plan_request


def main():
 p=argparse.ArgumentParser(description='两道真实任务的模拟画像路径演示；不是正式图形界面或学习效果。')
 p.add_argument('--task',choices=['task_001','task_002'],default='task_001');p.add_argument('--profile',choices=['sim_unknown','sim_evidence'],default='sim_evidence');p.add_argument('--budget',type=float,default=100)
 a=p.parse_args()
 if not math.isfinite(a.budget) or a.budget<0:
  print('输入未通过检查：预算必须是有限非负数');return 2
 try:
  task=load('benchmarks/dev/D03/'+a.task+'.json');config=load('configs/A/D03_common.json')
  profile=next(p for p in load('configs/A/D03_profiles.json')['profiles'] if p['id']==a.profile)
  units=[u for u in load('benchmarks/dev/D03/units.json') if u['id'] in task['learning_unit_ids']]
  state=make_profile(profile,task['snapshot_id']);req=make_request(task,units,state,config,'live-demo-'+a.task+'-'+a.profile,a.budget)
  route,details=plan_request(ROOT,req,units,state,config);b0,_=b0_adapter(req,units,config['routes'][a.task],details['gate'])
 except ValidationError:
  print('输入未通过检查：请求或学习单元不符合版本契约');return 2
 except (ValueError,TypeError) as e:
  print('输入未通过检查：'+str(e));return 2
 print('当前：A-D03核心算法独立CLI演示；正式UI尚未接入。')
 print('任务：'+task['title']);print('画像：'+profile['label']+'（明确模拟，不是真人）');print('预算：'+str(a.budget)+' 代理单位，不是分钟')
 for method,result in [('B0 固定文档路线',b0),('初版闭包增量贪心',route)]:
  print('\n'+method+'：'+result['status']);print('路线：'+(' → '.join(result['ordered_units']) or '空路线'));print('代理成本：'+str(result['estimated_cost']))
  for step in result['reason_trace']:
   if step['unit_id'] is not None:print('  '+step['unit_id']+' | '+step['reason'])
  if result['unmet_constraints']:print('未满足：'+'；'.join(result['unmet_constraints']))
 print('\n独立任务成功/真人用时：未测量；诊断：尚未实现。')
 return 0

if __name__=='__main__':raise SystemExit(main())
