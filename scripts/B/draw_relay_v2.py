"""Actual task inventory and paired route trace; no human outcome chart."""
import csv
import hashlib
import json
from pathlib import Path
import sys
import textwrap
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.B.draw_d02_materials import Canvas


def draw():
    out=ROOT/'report_materials/B/B-D06-v2';out.mkdir(exist_ok=False)
    registry=ROOT/'benchmarks/B/executable-v2/registry.json';records=json.loads(registry.read_text(encoding='utf-8'))['records']
    traces=ROOT/'experiments/B/B-D06-v2-live01/traces.json';data=json.loads(traces.read_text(encoding='utf-8'))
    inventory=[dict(split=s,module=m,planned=p,actual_specs=len([r for r in records if r['split']==s]),
        executable=len([r for r in records if r['split']==s]),human_approved=0,formal_frozen=0)
        for s,m,p in [('dev','iterutils',8),('test_candidate','strutils',16)]]
    (out/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    with (out/'inventory.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(inventory[0]));w.writeheader();w.writerows(inventory)
    c=Canvas(1900,800);c.text(45,30,'T01 | v0.2 任务规模与可执行状态',36)
    c.text(45,100,'真实清单统计 · 固定boltons版本 · 非真人结果 / 非学习效果',27)
    for x,t in zip([55,490,750,1020,1280,1570],['划分 / 模块','原计划','实际规格','已联调','人类批准','正式冻结']):c.text(x,200,t,28)
    for i,r in enumerate(inventory):
        for x,t in zip([55,490,750,1020,1280,1570],[r['split']+' / '+r['module'],r['planned'],r['actual_specs'],r['executable'],0,0]):c.text(x,290+100*i,str(t),28)
    for y,t in [(520,'12题可运行 ≠ 12题正式获批；未知招募人数不填零。'),(590,'开发与留出按模块分开，仍属单仓库；24题目标缩减为12题。'),(660,'源码 / 初测 / 诊断 / 评分和同意方案待实际组织者批准后才能正式收集。')]:c.text(50,y,t,27)
    c.save(out,'T01_v2_inventory')
    c=Canvas(1900,1350);c.text(45,25,'同任务路线配对板 | task_001 开发验证',36)
    c.text(45,95,'真实B1服务 + 合成作答 · 三方法统一公开输入与100代理预算 · 非真人成绩',27)
    for i,row in enumerate(data):
        y=175+i*335;ts=row['traces'];c.box(45,y,1800,300);c.text(70,y+15,row['method'],32)
        c.text(250,y+18,'初始：'+' → '.join(ts[0]['route']),26)
        c.text(250,y+80,'反馈后剩余：'+' → '.join(ts[1]['route']),26)
        ctx=ts[1]['context'];c.text(250,y+145,'已完成：'+', '.join(ctx['completed'])+'；模拟短测：'+ctx['feedback'],25)
        calls=[call for t in ts for call in t['details'].get('calls',[])];cost=sum(call['estimated_cost_cny'] or 0 for call in calls)
        c.text(250,y+210,f'真实API调用 {len(calls)}；估算费用 CNY {cost:.6f}；状态 '+ts[1]['status'],25)
    c.text(45,1240,'保持路线不变也保留；不据此推断学习收益或某方法更好。计时含调用，原始响应已留存。',25)
    c.save(out,'paired_routes_v2')
    entries=[]
    for name in ('T01_v2_inventory','paired_routes_v2'):
        inputs=[registry,traces,Path(__file__),out/'inventory.json',out/'inventory.csv',out/(name+'.png'),out/(name+'.svg')]
        entries.append(dict(figure_id=name,task_id='B-D06',run_id='B-D06-v2-live01' if name.startswith('paired') else 'B-D06-v2',
            source_base='72c0922369d5ef31c4803974dda8965761ca72dd',source_version='B-D06-executable-candidate-2',
            evidence_type='inventory_and_engineering_fixture_not_human_effect',human_effect_sample_size=0,confirmed_enrollment=None,dpi=300,
            visual_review='PENDING_AGENT_VIEW',command='python scripts/B/draw_relay_v2.py',
            files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in inputs]))
    (out/'figure_manifest.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    (out/'render_config.json').write_text(json.dumps(dict(dpi=300,renderer='native SVG/Pillow',data='exact registry counts and saved route traces',run_id='B-D06-v2-live01',effect_numbers=False),indent=2)+'\n',encoding='utf-8')
    print(out)


if __name__=='__main__':draw()
