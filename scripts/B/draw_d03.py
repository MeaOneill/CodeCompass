"""Native SVG/Pillow figures from recorded engineering data, no effect claims."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.B.draw_d02_materials import Canvas


def main():
    p = argparse.ArgumentParser(); p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); a = p.parse_args()
    a.source = a.source.resolve(); a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=False)
    cap = json.loads((a.source/'capability.json').read_text(encoding='utf-8'))
    matches = json.loads((a.source/'issue_matches.json').read_text(encoding='utf-8'))
    config = {'run_id': cap['run_id'], 'source': a.source.as_posix(), 'font': 'Microsoft YaHei',
              'width': 1800, 'height': 1100, 'dpi': 300, 'audience': 'competition report provisional development material',
              'uncertainty': 'model Beta posterior Q10-Q90, central 80%, not calibrated mastery',
              'transformations': 'No filtering/normalization/smoothing; show all five named stages of one simulated ledger',
              'sample': '1 simulated ledger, 22 distinct accepted simulated items (21 pass / 1 fail); humans 0',
              'publisher_requirements': 'not applicable / not claimed', 'seed': None}
    labels = {'initial': '初测前（未知）', 'correct': '一道模拟题答对', 'incorrect': '另一道模拟题答错',
              'duplicate_and_reading': '重答同题 + 阅读', 'distinct_simulated_items': '再加20道不同模拟题'}
    c = Canvas(1800, 1100)
    c.text(48, 25, 'F04 | 能力证据存储与不确定性：开发示例', 38)
    c.text(48, 87, '模拟回答 · 非真人结果 · 固定概念 python.iterator_protocol · A learner 0.1.0', 27)
    c.text(48, 138, '点 = a/(a+b)；横线 = Beta 模型 Q10—Q90；范围统一 0—1；不是实测掌握率。', 27)
    x0, x1 = 500, 1450
    def line(x, y, xx, yy, color='#385779', width=3):
        c.draw.line((x, y, xx, yy), fill=color, width=width)
        c.svg.append(f'<line x1="{x}" y1="{y}" x2="{xx}" y2="{yy}" stroke="{color}" stroke-width="{width}"/>')
    for i, r in enumerate(cap['stages']):
        y = 250 + i*118
        c.text(48, y-22, labels[r['stage']], 26)
        c.text(48, y+17, f'a={r["a"]}, b={r["b"]}', 23)
        lo, mid, hi = [x0 + v*(x1-x0) for v in (r['lower_q10'], r['mean'], r['upper_q90'])]
        line(lo, y, hi, y, '#17496b', 5); line(lo, y-11, lo, y+11); line(hi, y-11, hi, y+11)
        c.draw.ellipse((mid-9, y-9, mid+9, y+9), fill='#17496b')
        c.svg.append(f'<circle cx="{mid}" cy="{y}" r="9" fill="#17496b"/>')
        c.text(1490, y-20, f'{r["mean"]:.3f}', 27)
        c.text(1490, y+18, f'[{r["lower_q10"]:.3f}, {r["upper_q90"]:.3f}]', 22)
    line(x0, 820, x1, 820)
    for n in range(6):
        x = x0 + n*(x1-x0)/5
        line(x, 814, x, 829); c.text(x-18, 838, f'{n/5:.1f}', 23)
    c.text(48, 920, '同题重答和阅读不改变 a/b；新进程读取结果与原状态逐字一致；不同用户及模拟/真实模式隔离。', 26)
    c.text(48, 974, '1 个模拟账户、22 个独立模拟题目；无真实答题者。区间是模型内不确定性，不是学习效果区间。', 26)
    c.text(48, 1030, '来源：'+cap['run_id']+' / capability.json + events.json；未校准、未作推荐准确率评估。', 24)
    c.save(a.output, 'F04_capability')
    b = Canvas(1800, 1100)
    b.text(48, 25, 'F11 | 真实 Issue 固定快照与贡献准备 CLI', 38)
    b.text(48, 90, '实际输出信息的案例排版 · 非GUI截图 · 无社区提交 · 无推荐准确率', 27)
    b.text(48, 144, '抓取时间（UTC）：'+matches['snapshot_retrieved_at'], 26)
    b.text(48, 196, '本页源：7条公开Issue；开放模块词候选 '+str(len(matches['candidates']))+'；历史关闭 '+str(len(matches['historical']))+'。', 27)
    for i, m in enumerate(matches['candidates'][:2]):
        y = 285 + i*240
        b.box(48, y, 1700, 215)
        b.text(72, y+16, f'OPEN #{m["number"]} | '+m['title'], 28)
        b.text(72, y+72, m['url'], 26)
        b.text(72, y+125, '模块命中：'+', '.join(m['modules'])+'；仅词匹配，相关性未独立审核。', 25)
        b.text(72, y+169, '候选函数不在当前 chunked 路线；需补函数阅读/复现/测试，再决定是否贡献。', 25)
    b.text(48, 820, '缺口：当前路线覆盖 chunked/is_iterable，不等于已掌握 redundant 或 untyped_sorted。', 27)
    b.text(48, 880, '下一步：重查原链接状态 → 核对固定commit → 隔离复现/回归 → 检查贡献规范与重叠PR。', 27)
    b.text(48, 940, '在线抓取只发生在记录时间；后续运行读取固定快照。公开Issue可变化，页面匹配不是适配确认。', 26)
    b.text(48, 1000, '来源：'+cap['run_id']+' / issue_snapshot.json + issue_matches.json；不包含用户身份和私有答案。', 24)
    b.save(a.output, 'F11_issue_case')
    with (a.output/'capability.csv').open('w', encoding='utf-8', newline='') as f:
        keys = ['stage', 'a', 'b', 'mean', 'lower_q10', 'upper_q90', 'is_simulated']
        w = csv.DictWriter(f, fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(cap['stages'])
    (a.output/'render_config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    manifest = []
    for name, sources in [('F04_capability', ['capability.json', 'events.json']),
                          ('F11_issue_case', ['issue_snapshot.json', 'issue_matches.json'])]:
        paths = [a.source/f for f in sources] + [a.output/(name+'.png'), a.output/(name+'.svg'),
                                                   a.output/'render_config.json', Path(__file__), ROOT/'scripts/B/draw_d02_materials.py']
        manifest.append({'figure_id': name, 'run_id': cap['run_id'], 'task': 'B-D03',
                         'png': (a.output/(name+'.png')).relative_to(ROOT).as_posix(),
                         'svg': (a.output/(name+'.svg')).relative_to(ROOT).as_posix(),
                         'dependency_commit': 'cf02b664aea81f91aa8e7423a8aa891367c73b7e',
                         'caption': '模拟能力模型记录' if name.startswith('F04') else '真实公开Issue快照与未确认模块候选；CLI信息排版，非GUI截图',
                         'unit': 'model probability' if name.startswith('F04') else None,
                         'human_sample_size': 0, 'effect_result': False, 'visual_review': 'PENDING_AGENT_VIEW',
                         'command': 'python scripts/B/draw_d03.py --source '+str(a.source)+' --output '+str(a.output),
                         'files': [{'path': path.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths]})
    (a.output/'figure_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(str(a.output))


if __name__ == '__main__':
    main()
