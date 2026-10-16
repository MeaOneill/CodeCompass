"""Live, human-readable comparison; does not write user data or require answers."""
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from scripts.A.cases_d04 import mechanism_cases
from codecompass.planner.search_service import solve_request
from jsonschema.exceptions import ValidationError

def main():
    cases={x['case_id']:x for x in mechanism_cases()};p=argparse.ArgumentParser();p.add_argument('--case',choices=sorted(cases),default='cost_gap');p.add_argument('--beam-width',type=int,default=16);p.add_argument('--candidate-limit',type=int,default=50);p.add_argument('--time-limit',type=float,default=30);p.add_argument('--certify-small',action='store_true');a=p.parse_args();f=cases[a.case]
    print('A-D04独立CLI：机制夹具与模拟证据；不是正式UI或真人学习实验。')
    print('案例：'+a.case+'；目标：'+','.join(f['request']['target_concept_ids'])+'；预算：'+str(f['request']['budget'])+' proxy_cost（不是分钟）')
    try:
        for method in ('exact','B2','beam'):
            options={'beam_width':a.beam_width,'candidate_limit':a.candidate_limit,'time_limit_seconds':a.time_limit} if method=='beam' else None
            result,detail=solve_request(ROOT,f['request'],f['units'],f['state'],f['config'],method=method,options=options,certify_small=a.certify_small if method=='beam' else False)
            print(f"\n{method}: {result['status']} | 路线="+(' → '.join(result['ordered_units']) or '空')+f" | 选入代理成本={result['estimated_cost']:g}")
            print('独立合法性重放：'+str(detail['replay_audit']['valid']))
            if method=='beam':print('候选/beam截断：'+str(detail['truncated'])+'；最优性声明：False；终止：'+detail['termination'])
            if result['unmet_constraints']:print('未满足：'+'；'.join(result['unmet_constraints']))
            if detail.get('exact_feasible_witness'):print('精确求解另有可行见证：启发式没找到，不是证明无解。')
    except (ValueError,TypeError,ValidationError) as e:
        print('输入未通过检查：'+str(e)[:200]);return 2
    print('\n完整输入/精确证书/逐步搜索事件见保存的A-D04-mechanism01；正式学习效果未测。');return 0
if __name__=='__main__':raise SystemExit(main())
