"""Source-grounded F04 and F09, no formal outcomes or fabricated people."""
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tmp/D05-figure-deps'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/D07-matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch
from PIL import Image

font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
FONT=font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name()
RUN=ROOT/'experiments/A/A-D07-development05'
OUT=ROOT/'report_materials/A/A-D07';OUT.mkdir(exist_ok=True,parents=True)
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
records=[]


def box(ax,x,y,label,width=.83,color='#eff5fa'):
    ax.add_patch(FancyBboxPatch((x,y),width,.57,boxstyle='round,pad=.02',facecolor=color,edgecolor='#346382'))
    ax.text(x+.03,y+.47,label,fontsize=11,va='top',linespacing=1.6)


def unit_label(uid,units):
    u=next(u for u in units if u['id']==uid);s=u['source_spans'][0]
    return f"{uid}\n{u['base_cost']:g} proxy_cost\n{Path(s['path']).name}:L{s['start_line']}–{s['end_line']}"


def save(fig,name,caption,sources):
    png=OUT/(name+'.png');svg=OUT/(name+'.svg')
    fig.savefig(png,dpi=300,facecolor='white');fig.savefig(svg,facecolor='white');plt.close(fig)
    with Image.open(png) as im:assert all(abs(d-300)<.1 for d in im.info['dpi'])
    files=[png,svg,*sources,ROOT/'scripts/A/draw_d07.py',RUN/'input_manifest.json']
    records.append(dict(figure_id=name,run_id=RUN.name,caption=caption,human_n=0,
      source_base='c84e8334d681a86151cfa63b22a2307dd0245963',runtime_version='A-D07-runtime-v1',
      cost_unit='proxy_cost, not minutes',formal_study_ready=False,
      files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files],
      command=['python','scripts/A/draw_d07.py'],visual_review='PENDING_AGENT_VIEW'))


def main():
    unknown=load(RUN/'paired/unknown.json');known=load(RUN/'paired/synthetic_evidence.json')
    units=unknown['input']['units']
    fig,ax=plt.subplots(figsize=(15,7));ax.set(xlim=(0,3),ylim=(0,2));ax.axis('off')
    fig.subplots_adjust(left=.04,right=.97,top=.73,bottom=.15)
    fig.suptitle('F04 同一源码任务、两类能力证据的开发路线',fontsize=21,y=.96)
    fig.text(.04,.87,'task_001 / boltons commit 4e5faa3d7e40…；预算100；历史均模拟，不是两名真人。',fontsize=12)
    for data,y,title in [(unknown,1.18,'未知画像：没有独立历史'),(known,.18,'模拟证据画像：每个指定概念6道独立通过历史')]:
        result=data['result'];ax.text(.02,y+.73,f"{title} · 路线成本 {result['learning_cost']:g}",fontsize=12,weight='bold')
        for i,uid in enumerate(result['remaining']):
            x=.04+i*.98;box(ax,x,y,unit_label(uid,units))
            if i:ax.annotate('',xy=(x-.03,y+.28),xytext=(x-.12,y+.28),arrowprops=dict(arrowstyle='->',color='#346382'))
    fig.text(.04,.07,'差异原因：u_chunked_iter的4个概念达到冻结模型门槛后被跳过；模型内门槛不等于真实掌握。',fontsize=12,color='#8b2424')
    fig.text(.04,.025,'模拟历史的获取成本未计本轮；只演示条件路径差异，不作为方法效率提升。',fontsize=10.5)
    save(fig,'F04_evidence_routes','真实固定源码、模拟能力历史；实际执行路线，未测真人学习收益。',
         [RUN/'paired/unknown.json',RUN/'paired/synthetic_evidence.json'])

    repair=load(RUN/'paired/failed_quiz_repair.json');before=repair['before'];after=repair['after'];units=repair['input']['units']
    budget=before['request']['budget']
    fig,(ax,failax)=plt.subplots(2,1,figsize=(15,10),gridspec_kw={'height_ratios':[3,1]})
    fig.subplots_adjust(left=.04,right=.97,top=.80,bottom=.12,hspace=.34)
    fig.suptitle('F09 失败反馈后的剩余修复与预算不足',fontsize=21,y=.97)
    fig.text(.04,.91,'真实源码开发案例；每概念6道独立通过历史及本次失败作答均模拟；保持原阈值、成本和搜索参数。',fontsize=12)
    ax.set(xlim=(0,3),ylim=(0,2));ax.axis('off')
    for session,y,title in [(before,1.13,'反馈前'),(after,.10,'失败反馈后')]:
        total=session['spent']+session['plan']['learning_cost']
        ax.text(.02,y+.75,f"{title}：已支付{session['spent']:g}，预算余额{budget-session['spent']:g}，执行余路线后预计累计{total:g}",fontsize=12,weight='bold')
        for i,uid in enumerate([*session['completed'],*session['plan']['remaining']]):
            box(ax,.04+i*.98,y,('已完成保留\n' if uid in session['completed'] else '')+unit_label(uid,units),
                color='#e7ecef' if uid in session['completed'] else '#eff5fa')
    fail=load(RUN/'faults/budget_insufficient.json');r=fail['result']
    failax.axis('off')
    failax.text(.01,.9,'预算不足注入：同一task_001，临时预算1；冻结正常预算仍为100。',fontsize=13,weight='bold')
    failax.text(.01,.52,f"状态 {r['status']}；未覆盖概念{len(r['missing'])}个；没有签发无解证明或最优证书。",fontsize=12)
    failax.text(.01,.15,'不把局部路线成本0画成完整路线成本；失败与缺失继续保留。',fontsize=12,color='#8b2424')
    fig.text(.04,.045,'测验支付1；新补回u_chunked_iter成本43为未来计划费用，尚未当作已花费用。完成前缀不丢失；切换权重仍为0。',fontsize=11)
    save(fig,'F09_failure_repair','一次模拟独立失败削弱证据并补回源码材料；另保留真实源码预算不足的故障注入。',
         [RUN/'paired/failed_quiz_repair.json',RUN/'faults/budget_insufficient.json'])
    (OUT/'figure_manifest.json').write_bytes((json.dumps(dict(owner='A',figures=records),ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('F04/F09: 2 PNG300dpi + SVG, pending actual view')


if __name__=='__main__':
    with plt.rc_context({'font.family':FONT,'svg.fonttype':'none','axes.unicode_minus':False}):main()
