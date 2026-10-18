"""F03 structural flow and F04 actual agent-development mechanism, no learning claim."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts.B.draw_d02_materials import Canvas
from codecompass.learner.model import beta_quantile
from PIL import Image


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    source=a.source.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'figure_manifest.json').exists():p.error('Figure bundle already finalized')
    events=json.loads((source/'events.json').read_text(encoding='utf-8'))
    submissions=[e for e in events if e['kind']=='quiz_submit'];replans=[e for e in events if e['kind']=='replan']
    if len(submissions)!=1 or len(replans)!=1:p.error('This example expects exactly one declared development quiz')
    outcome=submissions[0]['payload']['outcome'];alpha=1+int(outcome=='pass');beta=1+int(outcome=='fail')
    data=dict(run_id='B-D05-browser01',actor='agent_browser',human_sample_size=0,
        prior=dict(alpha=1,beta=1,mean=.5,lower_bound=.1),
        posterior=dict(alpha=alpha,beta=beta,mean=alpha/(alpha+beta),lower_bound=beta_quantile(alpha,beta,.1)),
        quantile=.1,mastery_threshold=.7,source_events=str(source.relative_to(ROOT)/'events.json'),
        route_before=replans[0]['payload']['before'],route_after=replans[0]['payload']['after'],
        outcome=outcome,not_a_learning_effect=True)
    (out/'F04_source.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    c=Canvas(1700,1000);c.text(45,25,'F03 | 统一阅读、诊断与反馈采集流程',36)
    c.text(45,90,'结构说明 · B-D05 开发实现 · 非实测效果 · 共同预算100代理单位 / 任务上限25分钟',25)
    boxes=[('01 固定源码与任务','boltons 固定commit + 两道dev题；不读取终测答案'),
           ('02 方法路线 / 相同界面','B0固定、B1保存静态路线、B2贪心、Ours反馈修复'),
           ('03 阅读 → 一次独立概念短测','阅读不更新掌握；服务器评分；所有方法相同题目与次数'),
           ('04 证据事务 → 剩余路线','A learner去重；Ours调用A反馈；B0/B1保留静态路线'),
           ('05 提交 / 超时 / 退出','服务器单调计时包含诊断和重规划；最终独立评分仍待接入'),
           ('06 去标识导出 / 按参与者汇总','用户令牌、自由文本、绝对时间不导出；缺失保留NA')]
    for i,(title,desc) in enumerate(boxes):
        y=155+i*120;c.box(50,y,1590,98);c.text(75,y+10,title,27);c.text(75,y+50,desc,24)
    c.text(50,910,'异常支路：暂停隐藏内容；活跃会话跨进程重启或时钟跳变 → 标记缺失，暂停等待恢复。',24)
    c.save(out,'F03_collection_flow')
    c=Canvas(1700,1020);c.text(45,25,'F04 | 一次独立开发短测前后：证据改变，路线保持',35)
    c.text(45,90,'真实浏览器操作 / Agent作答 / 固定真实源码；不是人类学习效果或生产VOI收益',25)
    for i,(label,row) in enumerate([('短测前',data['prior']),('短测后',data['posterior'])]):
        x=50+i*830;c.box(x,160,780,310);c.text(x+25,185,label,32)
        c.text(x+25,245,f"Beta({row['alpha']}, {row['beta']})",34)
        c.text(x+25,310,f"模型均值 {row['mean']:.3f}；10%分位下界 {row['lower_bound']:.3f}",26)
        c.text(x+25,375,'下界低于门槛0.700 → 不能据此跳过',25)
    c.box(50,515,1610,240);c.text(75,535,'路线对比（剩余材料）',30)
    c.text(75,595,'前：'+' → '.join(data['route_before']),27)
    c.text(75,655,'后：'+' → '.join(data['route_after']),27)
    c.text(50,800,'Beta均值与分位数是未校准模型状态，不是人群成功率；同一道题不能重复累积证据。',25)
    c.text(50,860,'无真实概率校准，生产VOI仍禁用；没有因展示效果而补造路线变化。',25)
    c.text(50,920,'数据：B-D05-browser01/agent_browser/export01/events.json；独立源码任务结果尚未评分。',23)
    c.save(out,'F04_evidence_route')
    manifest=[]
    for name in ('F03_collection_flow','F04_evidence_route','F11_reading','F11_quiz','F11_feedback','F11_submitted'):
        png=out/(name+'.png');im=Image.open(png)
        files=[png];svg=out/(name+'.svg')
        if svg.exists():files.append(svg)
        manifest.append(dict(figure_id=name,task_id='B-D05',run_id='B-D05-browser01',
            evidence_type='structural_diagram' if name.startswith('F03') else 'agent_development_mechanism' if name.startswith('F04') else 'unaltered_actual_browser_screenshot',
            human_sample_size=0,source_commit='7a2a268cd3122abe9165a78b45b45cddf0a18515',
            source_versions='browser source frozen in experiments/B/B-D05-browser01/source_snapshot; diagram script SHA below',
            source=str((source/'events.json').relative_to(ROOT)),source_hash=hashlib.sha256((source/'events.json').read_bytes()).hexdigest(),
            pixels=list(im.size),dpi=im.info.get('dpi'),
            screenshot_processing='none; full page; same task/session and unchanged viewport/zoom; anonymous label shown',
            command='python scripts/B/draw_d05.py --source '+source.relative_to(ROOT).as_posix()+' --output '+out.relative_to(ROOT).as_posix() if svg.exists() else 'cua browserTab.screenshot({fullPage:true})',
            caption='开发结构/Agent机制验证；不支持真人学习收益。',visual_review='PENDING_AGENT_VIEW',
            files=[dict(path=f.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files]))
    (out/'figure_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'render_config.json').write_text(json.dumps(dict(run_id='B-D05-browser01',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        diagram_dpi=300,renderer='Existing B native SVG/Pillow Canvas',destination='provisional competition report',
        transformations='one explicitly selected agent session; posterior from independent scored evidence; no smoothing',
        uncertainty='Beta 10% quantile; not a confidence interval or calibrated probability',
        missing='human effects and final scores unavailable',figure_sample='one agent operation, zero human sample'),indent=2)+'\n',encoding='utf-8')
    print(out)


if __name__=='__main__':main()
