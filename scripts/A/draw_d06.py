"""F01/F03 candidate diagrams and complete 30-result development matrix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument('--figure-deps', type=Path, default=ROOT/'tmp/D05-figure-deps')
parser.add_argument('--output', type=Path, default=ROOT/'report_materials/A/A-D06')
args = parser.parse_args()
sys.path.insert(0,str(args.figure_deps.resolve()))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/D06-matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from PIL import Image

font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name(),
                     'font.size':12,'svg.fonttype':'none','axes.unicode_minus':False})
out = args.output; out.mkdir(parents=True,exist_ok=True)
run = ROOT/'experiments/A/A-D06-controls03'
rows = json.loads((run/'summary.json').read_text(encoding='utf-8'))['rows']
records = []


def save(fig, name, caption):
    fig.savefig(out/(name+'.png'),dpi=300,facecolor='white')
    fig.savefig(out/(name+'.svg'),facecolor='white')
    plt.close(fig)
    with Image.open(out/(name+'.png')) as im:
        assert all(abs(v-300)<.1 for v in im.info['dpi'])
    paths = [out/(name+'.png'),out/(name+'.svg'),run/'comparison.csv',ROOT/'scripts/A/draw_d06.py',
             ROOT/'configs/frozen/v0.1-candidate/candidate.json']
    records.append(dict(figure_id=name,caption=caption,run_id=run.name,human_n=0,formal_study_ready=False,
        source_base_sha='5e6ecb186e9b06d72599ae41d851e9b35ea59399',
        files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in paths],
        command=['python','scripts/A/draw_d06.py'],visual_review='PENDING_AGENT_VIEW'))


def diagram(name,title,subtitle,boxes,footer):
    fig, ax = plt.subplots(figsize=(15,8))
    ax.set(xlim=(0,3),ylim=(0,2));ax.axis('off')
    fig.subplots_adjust(left=.03,right=.97,top=.82,bottom=.14)
    fig.suptitle(title,fontsize=22,y=.96)
    fig.text(.04,.88,subtitle,fontsize=12)
    for i,(head,body) in enumerate(boxes):
        x=(i%3)+.03; y=1.12 if i<3 else .10
        ax.add_patch(FancyBboxPatch((x,y),.90,.77,boxstyle='round,pad=.02',facecolor='#f0f5f9',edgecolor='#346382'))
        ax.text(x+.035,y+.68,head,weight='bold',fontsize=12,va='top')
        ax.text(x+.035,y+.48,body,fontsize=11,va='top',linespacing=1.7)
    fig.text(.04,.06,footer,fontsize=12,color='#8b2424')
    save(fig,name,subtitle+' '+footer)


diagram('F01_source_boundary','F01 自主实现与第三方边界（G2候选）',
    '实际调用按模块定位；标准算法思想、第三方模型与源代码均不称原创。',[
    ('上游固定源码','boltons snapshot + LICENSE\nPython AST / 依赖与 span\n源码关系不等于教学先修'),
    ('A：证据与联合规划','独立证据 / 项目隔离 / 去重\n有序前缀 beam + 总预算\n完成项覆盖与剩余修复'),
    ('第三方与标准思想','Beta / beam / greedy / VOI\njsonschema / pytest / 绘图库\n不复制上游规划器改名'),
    ('B：应用和比较','采集界面 / 事件 / 代理评分\nB2动态；B1仅历史回放\n动态B1与终测评分待接入'),
    ('AI辅助与核查','Codex辅助编写与自动验证\nAI交叉代码检查另行记录\n不替代成员/人类确认'),
    ('候选交付边界','v0.1-candidate 逐文件hash\nmain未集成 / 不打正式标签\n正式研究不放行')],
    'G2未通过；这是边界图，不是效果图或新颖性认证。')

diagram('F03_candidate_flow','F03 收敛后的候选算法流程',
    '同单位代理预算100；q=.1 / τ=.7 / W16；α=γ=0；生产VOI禁用。',[
    ('1 校验与保守状态','源码 / 单元 / 独立证据\n阅读只算完成覆盖\n缺证据保守补学'),
    ('2 联合规划','有序剩余前缀 / 先修\n预算与搜索上限 / 明确超时\nFEASIBLE不等于全局最优'),
    ('3 完成首份材料','扣材料代理成本\n保留完成前缀\n不把阅读写成掌握'),
    ('4 共同短测','D06控制：首材料后一次\n先付同一题费用1\n无新可靠p_pass不做VOI'),
    ('5 证据与剩余修复','题目去重 / 接收真实或标明模拟\n同规划器修复 / 完成项保留\n无反馈变体只观察和扣费'),
    ('6 审计与G2门禁','原始JSON/CSV + 配置hash\nmain=去选择：效果不可识别\n终测评分缺失不写学习收益')],
    '此图定稿到候选版本；UI仍为用户点选时机，正式协议时机需B-D06接入复验。')

variants=['main','no_gate','no_selection','no_feedback','no_diagnostic']
cases=list(dict.fromkeys(r['case_id'] for r in rows))
labels=['结构：通过','结构：失败','源码task1：未知画像','源码task1：证据画像','源码task2：未知画像','源码task2：证据画像']
data=[[str(next(r['total_proxy_cost'] for r in rows if r['case_id']==cid and r['variant']==v)) for v in variants] for cid in cases]
fig,ax=plt.subplots(figsize=(15,8));ax.axis('off')
fig.suptitle('候选机制消融矩阵：全部30次开发结果',fontsize=22,y=.95)
fig.text(.04,.86,'所有能力历史与反馈均模拟；成本为proxy_cost，不是分钟。无真人正式任务成功率。',fontsize=12)
table=ax.table(cellText=[[label,*values] for label,values in zip(labels,data)],
               colLabels=['开发输入','主候选','去证据跳过','去诊断选择','禁用反馈','无诊断'],
               colWidths=[.30,.14,.14,.14,.14,.14],cellLoc='center',bbox=[.02,.28,.96,.52])
table.auto_set_font_size(False);table.set_fontsize(12)
for (r,c),cell in table.get_celld().items():
    cell.set_edgecolor('#bbc9d3')
    cell.set_facecolor('#dceaf3' if r==0 else ('#f1f5f8' if r%2 else '#ffffff'))
fig.text(.04,.22,'隔离含义：去门控=关闭所有证据跳过（未比较均值门控）；去反馈=同题同费、冻结规划证据。',fontsize=12)
fig.text(.04,.15,'生产VOI禁用 → 主候选与去选择六组相同，不能估计选择收益；真实源码四组反馈均无成本改善。',fontsize=12,color='#8b2424')
fig.text(.04,.08,'无诊断少付1单位；结构失败显示测验开销。预算统一100；6种输入不是6名参与者。',fontsize=12)
save(fig,'D06_ablation_matrix','全部30次开发结果与负结果；模拟反馈，非正式效果。去选择不可识别；不是B2直接比较。')
(out/'figure_manifest.json').write_bytes((json.dumps(dict(owner='A',figures=records),ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(figures=len(records),png_dpi=300)))
