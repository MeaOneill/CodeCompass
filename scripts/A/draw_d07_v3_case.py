"""Source-backed route-case exports. Human data exports are strictly local-only."""
import argparse,csv,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tmp/D05-figure-deps'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/D07-v3-figure-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

def draw(case_file,output,title):
    s=json.loads(case_file.read_text(encoding='utf-8'));private=ROOT/'experiments/A/A-D07-human-live01'
    if s['actor']=='human_manual' and not output.resolve().is_relative_to(private):raise ValueError('真人案例只导出本机已忽略目录')
    output.mkdir(parents=True,exist_ok=False)
    font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc');font=font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name()
    names={'u_positive_int':'校验工具 · 已完成（5）','u_iterable':'迭代协议材料（16）','u_windowed_iter':'窗口迭代材料（39）'}
    with plt.rc_context({'font.family':font,'font.size':11,'svg.fonttype':'none'}):
        fig,axes=plt.subplots(1,3,figsize=(12,5.4),layout='constrained')
        for ax,(label,key,spent) in zip(axes,[('新诊断前','before',10),('真实新证据后','after',11),('禁用反馈 · 同费用','no_feedback',11)]):
            p=s[key]['Ours'];ax.set(xlim=(0,1),ylim=(0,1));ax.axis('off');ax.set_title(label,fontsize=15,pad=15)
            ax.text(.04,.96,'已支付 '+str(spent)+' / 100；剩余预算 '+str(100-spent),va='top')
            for i,uid in enumerate(s['completed']+p['route']):
                y=.77-i*.16;done=uid in s['completed'];ax.add_patch(FancyBboxPatch((.04,y),.91,.12,boxstyle='round,pad=.012',facecolor='#e9ecef' if done else '#e5f2ee',edgecolor='#526b66'))
                ax.text(.07,y+.06,names[uid],va='center',fontsize=11)
            ax.text(.04,.16,'未来材料 '+str(p['cost'])+' 代理单位\n已付＋未来计划 '+str(spent+p['cost']),va='top',linespacing=1.6)
        fig.suptitle(title+'\n开发预演案例；Ours/B2路线一致，不是正式学习效果',fontsize=16)
        fig.savefig(output/'case.png',dpi=300);fig.savefig(output/'case.svg');plt.close(fig)
    rows=[dict(branch=k,paid=paid,future_cost=s[k]['Ours']['cost'],route=' -> '.join(s[k]['Ours']['route']),completed=';'.join(s['completed'])) for k,paid in [('before',10),('after',11),('no_feedback',11)]]
    with (output/'case.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (output/'manifest.json').write_bytes((json.dumps(dict(raw=str(case_file.resolve()),raw_sha256=hashlib.sha256(case_file.read_bytes()).hexdigest(),source_commit=s['data']['task']['repo_commit'],protocol=s['provenance'],entrypoint='scripts/A/draw_d07_v3_case.py',transformation='No filtering/aggregation; draw all three recorded branches and completed prefix; proxy costs are not minutes',png_dpi=300,exports=['case.png','case.svg','case.csv'],human_data_local_only=s['actor']=='human_manual',formal_study=False),ensure_ascii=False,indent=2)+'\n').encode())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--case',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--title',required=True);a=p.parse_args();draw(a.case,a.output,a.title)
