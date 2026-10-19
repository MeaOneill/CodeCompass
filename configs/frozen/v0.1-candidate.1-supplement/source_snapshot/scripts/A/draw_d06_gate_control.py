"""All 60 supplemental development results, including failures and ties."""
import hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tmp/D05-figure-deps'))
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'tmp/D06-matplotlib-cache'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image
font_manager.fontManager.addfont('C:/Windows/Fonts/msyh.ttc')
plt.rcParams.update({'font.family':font_manager.FontProperties(fname='C:/Windows/Fonts/msyh.ttc').get_name(),'svg.fonttype':'none'})
run=ROOT/'experiments/A/A-D06-gate-control02'
summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
rows=summary['rows'];cases=list(dict.fromkeys(r['case_id'] for r in rows));data=[]
for cid in cases:
    group=[r for r in rows if r['case_id']==cid]
    vals=[]
    for method in ['candidate_lower','candidate_mean','B2_original']:
        r=next(r for r in group if r['method']==method)
        vals.append(format(r['proxy_cost'],'.4g') if r['status']=='FEASIBLE' else 'NFF / '+format(r['proxy_cost'],'.4g'))
    data.append([cid,format(group[0]['budget'],'.4g'),*vals])
out=ROOT/'report_materials/A/A-D06-supplement';out.mkdir(exist_ok=True)
fig,ax=plt.subplots(figsize=(15,13));ax.axis('off')
fig.suptitle('补充开发对照：可信下界、均值门控与原B2（全部60结果）',fontsize=19,y=.97)
fig.text(.04,.91,'只比较初始路线；能力历史均模拟。前6行D06预算100，后14行为历史结构压力输入，各方法同预算。',fontsize=11)
t=ax.table(cellText=data,colLabels=['输入条件','预算','候选：下界','消融：均值','强基线：原B2'],
           colWidths=[.44,.10,.15,.15,.16],cellLoc='center',bbox=[.01,.12,.98,.78])
t.auto_set_font_size(False);t.set_fontsize(11)
for (r,c),cell in t.get_celld().items():
    cell.set_facecolor('#dceaf3' if r==0 else ('#f2f5f8' if r%2 else 'white'))
    cell.set_edgecolor('#b7c8d5')
fig.text(.04,.10,'单位proxy_cost，非分钟。NFF=未找到可行完整路线；斜杠后为局部路线成本，不能当成功成本。',fontsize=11)
fig.text(.04,.06,'源码task1/task2三方法仍平局；均值少选材料不证明正确掌握，下界多选也不证明学习收益。',fontsize=11,color='#8b2424')
png=out/'D06_mean_B2_controls.png';svg=out/'D06_mean_B2_controls.svg'
fig.savefig(png,dpi=300,facecolor='white');fig.savefig(svg,facecolor='white');plt.close(fig)
with Image.open(png) as im:assert all(abs(d-300)<.1 for d in im.info['dpi'])
files=[png,svg,run/'comparison.csv',ROOT/'scripts/A/draw_d06_gate_control.py']
(out/'figure_manifest.json').write_bytes((json.dumps(dict(owner='A',run_id=run.name,
    version='v0.1-candidate.1-supplement',human_n=0,formal_study_ready=False,
    files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files],
    command=['python','scripts/A/draw_d06_gate_control.py'],visual_review='PENDING_AGENT_VIEW'),ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print('Supplement figure: PNG300dpi and SVG')
