"""T02 actual exploratory development table and paired routes; no invented B1."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.B.draw_d02_materials import Canvas


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.source.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    summary=json.loads((source/'summary.json').read_text(encoding='utf-8'))
    live=summary.get('B1_live_calls',0)>0
    b1_label='B1真实API已运行' if live else 'B1未配置，不填0'
    rows=summary['rows'];methods=['B0','B1','B2','beam'];names=['T02_development','task_001_routes','task_002_routes']
    c=Canvas(1800,1250);c.text(48,25,'T02 | 统一条件下的开发比较（探索性）',38)
    c.text(48,89,'真实固定源码 + 两种模拟画像；2任务×2画像；真人0；'+b1_label+'。',27)
    headers=['任务 / 画像','方法','状态','概念覆盖','硬边违反','有效源码','代理成本']
    xs=[48,485,680,1030,1220,1420,1605]
    for x,t in zip(xs,headers):c.text(x,155,t,25)
    for i,row in enumerate([r for r in rows if r['source_kind']=='fixed_real_task']):
        y=215+i*48;m=row['metrics'] or {};na=lambda x:'NA' if x is None else str(x)
        values=[row['case_id'].replace('sim_unknown','未知').replace('sim_evidence','模拟证据'),row['method'],row['execution_status'],
                na(m.get('coverage_ratio')),na(m.get('prerequisite_violation_rate')),na(m.get('source_reference_validity')),na(m.get('replayed_proxy_cost'))]
        for x,t in zip(xs,values):c.text(x,y,t,24)
    c.text(48,1030,'硬教学边分母为0 → NA；源码引用率按实际span检查；覆盖不等于独立任务成功。',27)
    c.text(48,1090,'真实任务中B2与beam成本平局；能力画像为模拟，不支持学习收益或算法优越性。',27)
    c.text(48,1150,'来源：'+summary['run_id']+' / T02.csv + summary.json；固定boltons 4e5faa3d7e40',25)
    if live:
        estimate=sum(r.get('api_cost_cny') or 0 for r in rows)
        c.text(48,1200,f'B1共{summary["B1_live_calls"]}次真实API调用（含2结构夹具输入）；保守估算{estimate:.6f}元，非账单。',23)
    c.save(out,names[0])
    for tid in ['task_001','task_002']:
        c=Canvas(1800,1190);c.text(48,25,tid+' | 同任务路线配对板（开发运行）',38)
        c.text(48,89,'固定源码 boltons 4e5faa3d7e40；共同预算100 proxy_cost；不是分钟或学习效果。',27)
        for col,profile in enumerate(['sim_unknown','sim_evidence']):
            x=48+col*870;c.text(x,155,'未知模拟画像' if col==0 else '有独立模拟证据画像',30)
            for i,method in enumerate(methods):
                row=next(r for r in rows if r['case_id']==tid+'-'+profile and r['method']==method)
                y=225+i*198;c.box(x,y,820,175)
                c.text(x+20,y+12,method+' | '+row['execution_status'],28)
                route=' → '.join(row['plan']['ordered_units']) if row['plan'] else '未配置模型/API预算；未运行；无响应'
                c.text(x+20,y+63,route,25)
                m=row['metrics'];c.text(x+20,y+113,'代理成本：'+str(m['replayed_proxy_cost'])+'；源码合法性已复核' if m else '成本/覆盖/合法性：NA（不是0）',25)
        c.text(48,1055,'B0固定文档前缀；B2保留A闭包贪心；beam使用A-D04；同上下文hash逐方法一致。',27)
        c.text(48,1110,'源码定位/原因与原始JSON：'+summary['run_id']+'/cases/'+tid+'-*；不含私有答案。',25)
        c.save(out,tid+'_routes')
    render={'run_id':summary['run_id'],'source_sha256':hashlib.sha256((source/'summary.json').read_bytes()).hexdigest(),
            'audience':'provisional competition report','dpi':300,'units':'proxy_cost, source lines; coverage fraction; hard relation violations fraction',
            'sample':'2 fixed real tasks x 2 synthetic profiles; no human participants',
            'missing':'zero hard-edge denominator => NA; unattempted B1 => NA',
            'transformations':'Select all fixed_real_task rows; exclude explicitly synthetic mechanism rows from this real-task table; no smoothing/normalization',
            'uncertainty':'not an estimator or population inference; no intervals applicable','formal_study_ready':False}
    (out/'render_config.json').write_text(json.dumps(render,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    manifest=[]
    for name in names:
        paths=[source/'summary.json',source/'T02.csv',out/'render_config.json',Path(__file__),ROOT/'scripts/B/draw_d02_materials.py',out/(name+'.png'),out/(name+'.svg')]
        manifest.append({'figure_id':name,'task_id':'B-D04','run_id':summary['run_id'],'png':(out/(name+'.png')).relative_to(ROOT).as_posix(),'svg':(out/(name+'.svg')).relative_to(ROOT).as_posix(),
                         'caption':'真实源码开发比较/模拟画像；'+b1_label+'；非效果结果','units':'proxy_cost / fractions','human_sample_size':0,'visual_review':'PENDING_AGENT_VIEW',
                         'command':'python scripts/B/draw_d04.py --source '+source.relative_to(ROOT).as_posix()+' --output '+out.relative_to(ROOT).as_posix(),
                         'files':[{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]})
    (out/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(out)


if __name__=='__main__':main()
