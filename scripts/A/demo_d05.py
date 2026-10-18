"""Readable D05 synthetic diagnostic demo. No API, no UI, no learner data writes."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
from jsonschema.exceptions import ValidationError
from scripts.A.cases_d05 import near_gate_case
from codecompass.planner.feedback import start_session,recommend,apply_feedback,complete_next
from codecompass.planner.adaptive_validator import verify_session


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--outcome',choices=['pass','fail'],default='pass')
    p.add_argument('--strategy',choices=['none','fixed','voi','no_feedback'],default='voi')
    p.add_argument('--no-probability',action='store_true')
    p.add_argument('--alpha',type=float,default=0);p.add_argument('--gamma',type=float,default=2)
    p.add_argument('--time-limit',type=float,default=30)
    a=p.parse_args();case=near_gate_case(a.outcome)
    if a.no_probability:case['quizzes'][0]['probability']=None
    print('A-D05 结构机制演示：模拟画像/合成反馈；不是正式UI或真人学习实验。')
    print('统一单位 proxy_cost，不是分钟。真实源码无概率校准时默认禁用VOI。')
    try:
        s=start_session(ROOT,case['request'],case['units'],case['state'],case['config'],case['quizzes'],
                        strategy=a.strategy,alpha=a.alpha,gamma=a.gamma,options={'time_limit_seconds':a.time_limit})
        print('初始路线：'+' → '.join(s['plan']['remaining'])+f'；剩余目标估计 {s["plan"]["objective"]:g}')
        d=recommend(ROOT,s);print('诊断决定：'+d['reason'])
        for row in d['candidates']:
            print(f"  {row['item_id']}：{row['reason']}；p_pass={row['p_pass']}；VOI={row['voi']}")
            for outcome,b in row['branches'].items():
                print(f"    {outcome}: {b['status']} | {' → '.join(b['remaining'])} | J={b['objective']:g}")
        if d['selected'] and s['status']=='FEASIBLE':
            s=apply_feedback(ROOT,s,d['selected'],a.outcome,timestamp='2026-10-18T00:00:00+08:00')
            print(f'实际合成反馈={a.outcome}；已扣测验={s["quiz_spent"]:g}；切换={s["switch_spent"]:g}')
            print('反馈后路线：'+' → '.join(s['plan']['remaining']))
        while s['status']=='FEASIBLE' and s['plan']['remaining']:
            s=complete_next(s,s['plan']['remaining'][0])
        audit=verify_session(ROOT,s)
        print(f'结果状态：{s["status"]}；完成材料：'+', '.join(s['completed']))
        print(f'已支付：学习={s["learning_spent"]:g}，测验={s["quiz_spent"]:g}，切换={s["switch_spent"]:g}，合计={s["spent"]:g} / 预算25')
        print(f'测验次数={s["quiz_count"]}；测验时长={s["quiz_duration_seconds"]}（None=未知，不填0）；独立重放={audit["valid"]}')
        print('生产VOI校准、真人效果、正式GUI未完成；材料覆盖不等于掌握或独立任务成功。')
        return 0 if audit['valid'] else 1
    except (ValueError,TypeError,ValidationError) as error:
        print('输入被拒绝：'+str(error)[:250]);return 2


if __name__=='__main__':raise SystemExit(main())
