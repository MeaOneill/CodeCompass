"""Source-grounded F03/F04 and all-configuration development plots (optional isolated Matplotlib)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--run-id',required=True);parser.add_argument('--figure-deps',type=Path,default=ROOT/'tmp/D05-figure-deps')
args=parser.parse_args()
if not args.run_id.replace('-','').replace('_','').isalnum():parser.error('Unsafe run ID')
sys.path.insert(0,str(args.figure_deps.resolve()))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/D05-matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from PIL import Image

source=ROOT/'experiments/A'/args.run_id
summary=json.loads((source/'summary.json').read_text(encoding='utf-8'))
out=ROOT/'report_materials/A/A-D05'/args.run_id
out.mkdir(parents=True,exist_ok=False)
font=Path('C:/Windows/Fonts/msyh.ttc')
font_manager.fontManager.addfont(str(font))
plt.rcParams.update({'font.family':font_manager.FontProperties(fname=str(font)).get_name(),
                     'font.size':11,'axes.unicode_minus':False,'svg.fonttype':'none','figure.facecolor':'white'})
figures=[]
def save(fig,name,caption,source_paths):
    fig.savefig(out/(name+'.png'),dpi=300,facecolor='white')
    fig.savefig(out/(name+'.svg'),facecolor='white')
    plt.close(fig)
    with Image.open(out/(name+'.png')) as im:
        assert all(abs(v-300)<.1 for v in im.info['dpi'])
    files=[]
    for path in [out/(name+'.png'),out/(name+'.svg'),*source_paths]:
        files.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    figures.append(dict(figure_id=name,run_id=args.run_id,png=(out/(name+'.png')).relative_to(ROOT).as_posix(),
        svg=(out/(name+'.svg')).relative_to(ROOT).as_posix(),caption=caption,files=files,
        cost_unit='proxy_cost; not minutes',human_n=0,formal_study_ready=False,
        command=['python','scripts/A/draw_d05.py','--run-id',args.run_id,'--figure-deps',str(args.figure_deps)],
        visual_review='PENDING_AGENT_VIEW'))

fig,ax=plt.subplots(figsize=(15,9));fig.subplots_adjust(left=.04,right=.96,top=.87,bottom=.12)
ax.set(xlim=(0,3),ylim=(0,3));ax.axis('off')
fig.suptitle('F03 诊断选择与反馈后的剩余路径修复',fontsize=21,y=.97)
fig.text(.04,.91,'真实源码 VOI 缺校准时禁用；结构夹具先验仅验证机制。费用统一代理单位。',fontsize=12)
boxes=[(.02,2.05,'1 输入与保守门控','固定源码 / 独立题目ID\n阅读不增加掌握证据\n个性化成本 α 与总预算'),
       (1.03,2.05,'2 同规划器两分支','直接补学 J；诊断通过/失败 J\n两分支先扣测验代理成本\n未知概率 / 超时 → 保守补学'),
       (2.04,2.05,'3 四种开发策略','无诊断 / 固定频率\nVOI选择 / VOI但禁用反馈\n同题池、成本、次数上限'),
       (.02,.65,'4 接收实际独立反馈','先选择，后读取模拟结果流\n只接受新独立题目\n测验费用已发生不退款'),
       (1.03,.65,'5 修复并保留历史','保留已完成单元\n新增单元和逆序计切换费用\n完整顺序前缀，不按集合合并'),
       (2.04,.65,'6 独立重放与输出','核对费用、先修和证据去重\n截断/超时不签发旧精确证书\n覆盖不是独立任务成功')]
for x,y,title,body in boxes:
    ax.add_patch(FancyBboxPatch((x,y),.91,.85,boxstyle='round,pad=.018',linewidth=1.3,edgecolor='#28577a',facecolor='#f4f7fa'))
    ax.text(x+.04,y+.70,title,fontsize=12,weight='bold',va='top')
    ax.text(x+.04,y+.47,body,fontsize=10.5,va='top',linespacing=1.8)
for y in (2.47,1.07):
    for x in (.95,1.96):ax.annotate('',xy=(x+.075,y),xytext=(x,y),arrowprops=dict(arrowstyle='->',color='#28577a',lw=1.5))
ax.annotate('',xy=(.45,1.55),xytext=(2.5,2),arrowprops=dict(arrowstyle='->',color='#28577a',lw=1.5,connectionstyle='arc3,rad=.1'))
fig.text(.04,.04,'D05-adaptive-v1 · 无一般最优保证 · 正式GUI / 真人效果 / 正式协议冻结尚未完成',fontsize=11)
save(fig,'F03_adaptive_flow','实现分支、预算与回退逻辑的结构说明；不是软件界面或实验收益图',[source/'summary.json'])

candidates=json.loads((source/'candidates.json').read_text(encoding='utf-8'))
chosen=next(c for c in candidates if c['threshold']==.7 and c['beam_width']==16 and c['alpha']==0 and c['gamma']==2)
fig,axes=plt.subplots(1,2,figsize=(15,8));fig.subplots_adjust(left=.05,right=.97,top=.80,bottom=.14,wspace=.17)
fig.suptitle('F04 同一次诊断通过 / 失败后的配对路径',fontsize=20,y=.97)
fig.text(.05,.88,'纯结构夹具 / 合成反馈；固定展示 τ=.7、W=16、α=0、γ=2，未按结果择优。',fontsize=12)
paths=[source/'summary.json']
for ax,outcome,label in zip(axes,('pass','fail'),('通过','失败')):
    row=next(r for r in summary['comparisons'] if r['candidate_id']==chosen['candidate_id'] and r['case_id']=='diagnostic-'+outcome and r['strategy']=='voi')
    path=source/row['raw'];record=json.loads(path.read_text(encoding='utf-8'));paths.append(path)
    s=record['session'];e=next(e for e in s['events'] if e['type']=='diagnostic');decision=next(r for r in e['decision']['candidates'] if r['item_id']==e['item_id'])
    ax.axis('off');ax.set_title('实际合成结果：'+label,fontsize=16,pad=15)
    lines=['诊断前：'+' → '.join(e['before_plan']['remaining']),
           f'总预算 {s["request"]["budget"]:g}；预测直接补学 {e["before_plan"]["objective"]:g}',
           f'先验 p_pass={decision["p_pass"]:g}；预测 VOI={decision["voi"]:g}',
           f'诊断费用 {e["quiz_cost"]:g}；已发生费用 {e["spent_after"]:g}',
           '修复后：'+' → '.join(e['after_plan']['remaining']),
           f'剩余学习 {e["after_plan"]["learning_cost"]:g}；本次切换 {e["paid_switch_cost"]:g}',
           f'实际执行总代理成本 {s["spent"]:g}',
           '通过节省 / 失败多付测验费，均保留。',
           '已完成项不丢失；本例诊断发生在首项前。']
    for i,text in enumerate(lines):ax.text(.02,.96-i*.105,text,transform=ax.transAxes,va='top',fontsize=12)
fig.text(.05,.04,'测验时长未知记 NA；代理成本不是分钟。图来自实际执行的合成分支，不是真人测验。',fontsize=11)
save(fig,'F04_feedback_pair','同输入的通过/失败合成分支，包含负结果和预算变化',paths)

fig,axes=plt.subplots(3,2,figsize=(15,12));fig.subplots_adjust(left=.07,right=.98,top=.88,bottom=.12,hspace=.50,wspace=.22)
fig.suptitle('开发对照：全部配置 × 四种策略',fontsize=21,y=.97)
fig.text(.07,.925,'每个点是一组配置，不是独立参与者；全部 32 组保留。真人 n=0；真实源码也仅用模拟反馈。',fontsize=12)
strategies=['none','fixed','voi','no_feedback']; labels=['无诊断','固定诊断','VOI选择','禁用反馈']
case_ids=list(dict.fromkeys(r['case_id'] for r in summary['comparisons']))
for ax,case_id in zip(axes.flat,case_ids):
    rows=[r for r in summary['comparisons'] if r['case_id']==case_id]
    for i,strategy in enumerate(strategies):
        data=[r for r in rows if r['strategy']==strategy]
        for j,r in enumerate(data):
            if r['total_proxy_cost'] is None:continue
            ax.scatter(i+(j-(len(data)-1)/2)*.012,r['total_proxy_cost'],s=21,
                       marker='o' if r['material_coverage_complete'] else 'x',
                       facecolor=['#28577a','#b66b18','#2c8063','#884779'][i],alpha=.7)
    errors=sum(r['status']=='ERROR' for r in rows);partial=sum(not r['material_coverage_complete'] for r in rows)
    ax.set_title(case_id+f' | ERROR={errors}, 未完整={partial}',fontsize=11)
    family=case_id.split('-sim_')[0] if '-sim_' in case_id else 'diagnostic'
    family_values=[r['total_proxy_cost'] for r in summary['comparisons'] if r['total_proxy_cost'] is not None and
                   ((r['case_id'].split('-sim_')[0] if '-sim_' in r['case_id'] else 'diagnostic')==family)]
    ax.set_xticks(range(4),labels);ax.set_ylabel('实际已支付代理成本')
    ax.set_ylim(0,max(1,max(family_values))*1.12);ax.grid(axis='y',alpha=.25)
fig.text(.07,.035,'点的横向微移只区分配置；圆=材料覆盖完整，叉=未完整；错误/缺失不填0。无参与者效应或显著性推断。',fontsize=10)
save(fig,'D05_all_candidates','保留全部配置与四策略的开发代理成本；不是学习效果',[source/'summary.json',source/'comparison.csv'])

config=dict(run_id=args.run_id,font=str(font),font_sha256=hashlib.sha256(font.read_bytes()).hexdigest(),
    matplotlib_version=matplotlib.__version__,figure_lock='scripts/A/requirements_d05_figures.hashes.txt',
    selected_case_policy='F04 uses predeclared default .7/16/0/2; all candidates shown separately, no best selected',
    missing='NA never zero; unknown durations remain unknown',unit='proxy_cost',human_n=0,
    transformations='no exclusions; deterministic small x-offset by configuration index only; zero origin and common y limits within task family, with 12% headroom',
    uncertainty='none; repeated configuration points are not independent samples',
    destination='internal development / competition draft, no publisher compliance claimed')
(out/'render_config.json').write_bytes((json.dumps(config,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
(out/'figure_manifest.json').write_bytes((json.dumps(figures,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(figures=len(figures),output=str(out)),ensure_ascii=False))
