"""Task inventory and assignment design; no participant outcome placeholders."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.B.draw_d02_materials import Canvas


if __name__=='__main__':
    source=ROOT/'docs/protocol/B-D06-v0.1-candidate';out=ROOT/'report_materials/B/B-D06-protocol01';out.mkdir(parents=True,exist_ok=False)
    inventory=json.loads((source/'inventory.json').read_text(encoding='utf-8'))
    c=Canvas(1800,1000);c.text(45,25,'T01 | 任务规模与冻结状态（实际清单统计）',36)
    c.text(45,95,'B-D06 · 单仓库boltons固定版本 · iterutils开发 / strutils留出候选 · 非学习效果图',25)
    xs=[60,465,690,920,1180,1440];headers=['划分 / 模块','原计划','规格实有','人工批准','预演校准','正式冻结']
    for x,t in zip(xs,headers):c.text(x,190,t,28)
    for i,row in enumerate(inventory['rows']):
        vals=[row['split']+' / '+row['module'],str(row['planned']),str(row['actual_specs']),str(row['human_reviewed']),str(row['pilot_validated']),str(row['formally_frozen'])]
        for x,t in zip(xs,vals):c.text(x,285+i*120,t,28)
    c.box(45,560,1700,300);c.text(70,585,'规模从目标24缩至最低12份规格；不是12道获批正式题。',29)
    c.text(70,650,'留出候选只有定位解释/调试，没有局部修改题；跨仓库泛化不成立。',27)
    c.text(70,715,'真正的任务成功率、真人用时、学习收益：未测量，不填占位数字。',27)
    c.text(70,780,'来源：inventory.json + task_catalog封存hash；私有key只共享hash，不共享答案。',25)
    c.text(45,925,'计划与实际分列；0表示清单中确无批准/预演回执，不表示实验失败率。',25)
    c.save(out,'T01_actual_inventory')
    c=Canvas(1800,1200);c.text(45,25,'实验分配流程 | 已准备规则，尚未分配真人',36)
    c.text(45,95,'预设种子17 · 三方法6种顺序 / 两方法2种顺序 · SLOT不是参与者',26)
    boxes=[('1 真实自愿确认 / 排除开发与预演者','目前确认人数未知；已有正式同意回执0；D05同一预演者3轮全排除'),
        ('2 事前登记比较分支','≥12人：三方法须动态B1；6–11人：Ours/B2；1–5人：案例；0人：离线'),
        ('3 生成匿名编号后绑定保留SLOT','不同轮不重复题；知识点/函数不重叠；难度平行尚未人类校准'),
        ('4 相同初测 / 阅读 / 固定首材料后短测','同预算、同帮助、相同次数；真实时长包含规划和方法内诊断'),
        ('5 独立终测 + 隐藏方法的双人评分','缺评分/分歧保持PENDING；退出/超时/无效结果分别保留'),
        ('6 按参与者配对汇总','F05/F06只准备字段；按人整组重采样，不把多轮或种子当更多人')]
    for i,(a,b) in enumerate(boxes):
        y=165+i*145;c.box(45,y,1700,120);c.text(70,y+12,a,29);c.text(70,y+62,b,25)
    c.text(45,1090,'当前联合G2未通过：人工审阅、留出规划接入、比较分支确认、main和正式标签仍缺。',25)
    c.save(out,'assignment_flow')
    inputs=[source/'inventory.json',source/'inventory.csv',source/'three_12.csv',source/'three_18.csv',source/'two_6.csv',source/'two_10.csv',Path(__file__)]
    manifest=[]
    for name in ['T01_actual_inventory','assignment_flow']:
        manifest.append(dict(figure_id=name,task_id='B-D06',run_id='B-D06-protocol01',source_version='B-D06-v0.1-candidate',
            source_base='72c0922369d5ef31c4803974dda8965761ca72dd',evidence_type='inventory_count_not_learning_effect' if name.startswith('T01') else 'planned_assignment_flow',
            human_effect_sample_size=0,confirmed_enrollment=None,dpi=300,visual_review='PENDING_AGENT_VIEW',
            caption='实际规格计数与预设分配规则，非正式冻结/真人效果。',command='python scripts/B/draw_d06.py',
            files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in inputs+[out/(name+'.png'),out/(name+'.svg')]]))
    (out/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'render_config.json').write_text(json.dumps(dict(dpi=300,renderer='Existing native SVG/Pillow Canvas',sample='task inventory and planned slots only',missing='enrollment unknown; no outcomes',transformations='direct counts, no inference or normalization'),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(out)
