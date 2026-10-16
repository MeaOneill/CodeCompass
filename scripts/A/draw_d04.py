"""Data-driven F03 + exact/heuristic table + decision trace, native SVG/PNG."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.A.draw_d03 import Canvas,FONT

def main():
 p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
 if not a.run_id.replace('-','').replace('_','').isalnum():p.error('Invalid run ID')
 source=ROOT/'experiments/A'/a.run_id;summary=json.loads((source/'summary.json').read_text(encoding='utf-8'));out=ROOT/'report_materials/A/A-D04'/a.run_id;out.mkdir(parents=True,exist_ok=True);figures=[]
 c=Canvas(2500,1400);c.text(65,40,'F03：状态、约束与搜索决策框架',46);c.text(65,120,'机制正确性验证｜固定证据与同一候选池｜B2保留原实现｜没有真人学习效果结论',29)
 top=[['输入与证据门控','固定源 / 硬教学边 / 成本','共享画像：未知不跳过','模型下界与阈值沿用D03'],['beam 状态与扩展','已选集合 + 路线 + 覆盖','加入先修闭包，扣增量成本','共享前置计一次，预算 + 1e-9'],['去重与确定性截断','同集合保留字典序代表','宽度16 / 候选上限50','丢弃ID与路线写入原始日志']]
 for i,lines in enumerate(top):
  x=65+i*820;c.box(x,235,740,230,lines)
  if i:c.arrow(x-80,350,x)
 c.box(65,580,740,265,['B2：闭包增益/成本贪心','与beam同池 / 同证据 / 同成本','原core.py文件hash保持不变','不因beam结果调整基线','唯一链与真实任务的平局保留'])
 c.box(885,580,740,265,['精确DP：仅限 n <= 12','枚举全部预算内可达子集','精确成本 / 无解仅限当前输入','反向递推校验器独立重算','不推广一般全局最优'])
 c.box(1705,580,730,265,['独立合法性与证书检查','逐步重放先修 / 预算 / 覆盖','不调用beam / greedy / exact','检查输入hash与全部可达子集','拒绝伪成功 / 篡改证书'])
 c.box(65,965,2370,225,['结果状态：FEASIBLE / NO_FEASIBLE_FOUND / TIMEOUT / INFEASIBLE_PROVEN','启发式未找到：只表示本次有界搜索失败；截断 / 超时都没有最优性结论。','精确证明：仅完成全部子集枚举且独立证书验证后使用，范围是固定候选、证据、图和预算。','诊断、切换惩罚、真人成本标定未实现；仅比较非负代理成本。'])
 c.text(65,1260,'配置、证书、原始搜索日志和源码快照：'+a.run_id,26);figures.append(c.save(out,'F03_search_framework'))
 # All cases are shown; no exclusion of ties or failures. Failure != zero cost.
 c=Canvas(2500,1950);c.text(65,35,'小图精确 / 强B2 / beam 比较表',45);c.text(65,110,'机制验证；14个结构夹具 + 两真实任务×两模拟画像；代理单位，不是分钟',29)
 c.text(65,190,'案例',28);c.text(830,190,'精确可行成本',28);c.text(1280,190,'B2可行成本',28);c.text(1720,190,'beam可行成本',28);c.text(2160,190,'B2差距',28)
 names=list(dict.fromkeys(r['case_id'] for r in summary['comparisons']))
 for i,name in enumerate(names):
  y=260+i*74;rows={r['method']:r for r in summary['comparisons'] if r['case_id']==name};c.text(65,y,name,26)
  for method,x in [('exact',830),('B2',1280),('beam',1720)]:
   r=rows[method];v=r['feasible_proxy_cost'];label=f'{v:g}' if v is not None else ('证明无解' if r['status']=='INFEASIBLE_PROVEN' else '未找到')
   c.text(x,y,label,27,'#245880' if v is not None else '#a63c28')
  gap=rows['B2']['additive_cost_gap'];c.text(2160,y,f'{gap:g}' if gap is not None else '—',27)
 c.text(65,1660,'代价差距 = 可行路线成本 - 同输入精确最小成本；无可行路线不填0，也不参与差距。',27)
 c.text(65,1710,'真实任务现有候选的可替代空间有限，本轮成本均相同；受控反例不代表总体学习收益。',27)
 c.text(65,1760,'beam全部保持 optimality_claim=false；即使本表等于精确解，也不保证一般图最优。',27)
 c.text(65,1840,a.run_id+' | 完整JSON / CSV / 输入与证明见同run目录',26);figures.append(c.save(out,'exact_B2_beam_table'))
 # Actual first expansion of the cost-gap fixture.
 data=json.loads((source/'cases/cost_gap/beam.json').read_text(encoding='utf-8'));event=next(e for e in data['details']['events'] if e['event']=='expand');b2=json.loads((source/'cases/cost_gap/B2.json').read_text(encoding='utf-8'))['result'];exact=json.loads((source/'cases/cost_gap/exact.json').read_text(encoding='utf-8'))['result']
 c=Canvas(2500,1360);c.text(65,40,'决策过程：受控 cost_gap 夹具',46);c.text(65,120,'目标 x、y｜预算10｜a覆盖x成本2；b覆盖x+y成本5；c覆盖y成本4',30)
 c.box(65,230,570,210,['起始状态：空路线','覆盖0 / 2目标，成本0','相同候选输入a、b、c','单位：显式夹具proxy_cost'])
 for i,row in enumerate(event['candidates']):
  c.box(850,220+i*240,1500,185,[f'首轮候选 {row["root"]}：路线 '+','.join(row['route']),f'实际累计成本 {row["cost"]:g}；节点选入原因和来源在beam.json','同集合去重；保留前16状态，未强制第一项成为最终方案'])
 c.arrow(635,335,850)
 c.box(65,1000,1120,210,['B2原实现输出：'+','.join(b2['ordered_units']),f'成本{b2["estimated_cost"]:g}；与精确最小差{b2["estimated_cost"]-exact["estimated_cost"]:g}','此处保留真实基线行为，不改成本或画像'])
 c.box(1250,1000,1180,210,['beam输出：'+','.join(data['result']['ordered_units']),f'成本{data["result"]["estimated_cost"]:g}；精确最小{exact["estimated_cost"]:g}','仅该机制样例一致；无一般最优性结论'])
 c.text(65,1270,a.run_id+' | 此图只取cost_gap演示；全案例（含平局/失败）见完整比较表',26);figures.append(c.save(out,'beam_decision_trace'))
 config={'run_id':a.run_id,'kind':'mechanism_correctness_not_learning_effect','audience':'competition engineering report draft','publisher':None,'source_json':(source/'summary.json').relative_to(ROOT).as_posix(),'source_sha256':hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),'script':'scripts/A/draw_d04.py','font':FONT,'font_sha256':hashlib.sha256(Path(FONT).read_bytes()).hexdigest(),'transformations':'no exclusions, no normalization, exact gaps only for feasible outcomes; missing is never zero','unit':'proxy_cost; not minutes','human_n':0,'seed':None,'command':['python','scripts/A/draw_d04.py','--run-id',a.run_id],'figures':figures,'skill':'scientific-visualization; referenced publication_guidelines.md absent; core guardrails applied'}
 (out/'render_config.json').write_bytes((json.dumps(config,ensure_ascii=False,indent=2)+'\n').encode());print(json.dumps(figures,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
