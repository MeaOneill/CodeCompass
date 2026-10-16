"""Inventory and fixed-route materials; no learning-effect chart or fake outcomes."""
import csv
import hashlib
import html
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]


class Canvas:
    def __init__(self, width, height):
        self.image = Image.new('RGB', (width, height), '#f5f7fb')
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="#f5f7fb"/>']

    def text(self, x, y, text, size=25, fill='#243c59'):
        font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', size)
        self.draw.text((x, y), text, font=font, fill=fill)
        self.svg.append(f'<text x="{x}" y="{y + size}" font-family="Microsoft YaHei,sans-serif" font-size="{size}" fill="{fill}">{html.escape(text)}</text>')

    def box(self, x, y, w, h, fill='white'):
        self.draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=fill, outline='#b5c4d8', width=2)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="#b5c4d8" stroke-width="2"/>')

    def save(self, out, name):
        self.image.save(out / (name + '.png'), dpi=(300, 300))
        (out / (name + '.svg')).write_text('\n'.join(self.svg + ['</svg>']) + '\n', encoding='utf-8', newline='\n')


def main():
    out = ROOT / 'report_materials/B/B-D02'
    out.mkdir(parents=True, exist_ok=True)
    cat = json.loads((ROOT / 'benchmarks/B/task_catalog.json').read_text(encoding='utf-8'))
    rows = []
    for split, plan, module in [('dev', 8, 'iterutils'), ('test_candidate', 16, 'strutils')]:
        selected = [t for t in cat['tasks'] if t['split'] == split]
        rows.append({'split': split, 'planned_target': plan, 'candidate_specs': len(selected), 'evaluator_implemented': len(selected), 'human_approved': sum(bool(t['human_reviewer']) for t in selected), 'piloted': 0, 'formally_frozen': sum(t['frozen'] for t in selected), 'module': module})
    (out / 'T01_inventory.json').write_text(json.dumps({'record_type': 'inventory_not_effect_results', 'rows': rows, 'repo_commit': cat['tasks'][0]['repo_commit'], 'source': 'benchmarks/B/task_catalog.json', 'limitation': 'Candidate specifications do not count as human-approved tasks; no participant outcomes.'}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    with (out / 'T01_inventory.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n');writer.writeheader();writer.writerows(rows)
    c = Canvas(1800, 1040)
    c.text(48, 25, 'T01 | B-D02 任务构成与审核门禁', 38)
    c.text(48, 89, '清单统计 · 非效果结果 · 固定 boltons 4e5faa3d7e40 · 单仓库跨模块留出', 26)
    c.box(48, 155, 1700, 310)
    headers = ['划分 / 模块', '原目标', '评分候选规格', '评分器可运行', '人工批准', '真实预演', '正式冻结']
    xs = [72, 430, 622, 870, 1130, 1350, 1555]
    for x, text in zip(xs, headers): c.text(x, 180, text, 25)
    for i, row in enumerate(rows):
        vals = ['开发 / iterutils' if i == 0 else '留出候选 / strutils', str(row['planned_target']), str(row['candidate_specs']), str(row['evaluator_implemented']), str(row['human_approved']), str(row['piloted']), str(row['formally_frozen'])]
        for x, text in zip(xs, vals): c.text(x, 270 + 85 * i, text, 28)
    c.text(65, 510, '已实现：2 道补丁评分 + 10 道输出/源码依据评分；正确夹具仍等待人类解释评分。', 27)
    c.text(65, 567, '独立性：预先指定行为 key / 人类机制 rubric；不以图谱或 Ours 路径作为金标准。', 27)
    c.text(65, 624, '划分：开发 iterutils；留出 strutils。通用 Python 概念仍可能重叠，不能称跨仓库泛化。', 27)
    c.box(48, 710, 1700, 235, '#fff2df')
    c.text(72, 731, '整体验收尚未通过：候选规格 ≠ 已人工审核任务', 32, '#7a4d12')
    c.text(72, 796, '尚缺：人类题目/难度/必要概念审核、时长预演、B0 人工路线确认、公共契约与成本集成。', 25)
    c.text(72, 846, '目标从 24 缩至 12 候选；实际已人工批准 0，不能用候选数填满验收规模。', 25)
    c.text(72, 896, '没有参与者、学习成功率或提升比例；不生成效果图。', 25)
    c.save(out, 'T01_inventory')
    b = Canvas(1800, 1050)
    b.text(48, 25, 'B0 | task_001 固定源码阅读路线示例', 38)
    b.text(48, 91, '已运行的开发路线 · 非真人路线记录 · 非最优路径或学习效果', 27)
    cards = [('is_iterable', 'iterutils.py:61–76', '迭代协议检查', '静态代理 16'), ('chunked_iter', 'iterutils.py:316–358', '惰性消费 / 填充语义', '静态代理 43'), ('chunked', 'iterutils.py:286–306', '包装器 / count 截断', '静态代理 21')]
    for i, texts in enumerate(cards):
        x = 50 + i * 585
        b.box(x, 180, 520, 300)
        for j, text in enumerate(texts): b.text(x + 22, 205 + j * 62, text, 28 if j == 0 else 25)
        if i < 2: b.text(x + 530, 295, '→', 35)
    b.text(65, 535, '默认 shared：A 的 base_cost 均为 null → INPUT_INCOMPLETE，退出码 2，不能补零。', 27)
    b.text(65, 595, '显式 source_lines_proposal：预算 100 代理单位，固定路线成本 80，三单元前缀返回。', 27)
    b.text(65, 655, '16 + 43 + 21 来自固定源码闭区间行数，不是学习分钟、校准成本或算法收益。', 27)
    b.box(48, 745, 1700, 225, '#e6eef8')
    b.text(72, 766, '边界与下一步', 32)
    b.text(72, 828, 'Agent 按阅读逻辑编排，未看 Ours 输出；正式 B0 仍需人类独立确认及各方法统一成本。', 26)
    b.text(72, 885, '源码 commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d', 25)
    b.save(out, 'B0_task001_route')
    inputs = ['benchmarks/B/task_catalog.json', 'configs/B/B0_fixed.json', 'scripts/B/draw_d02_materials.py', 'report_materials/B/B-D02/T01_inventory.json', 'report_materials/B/B-D02/T01_inventory.csv']
    manifest = {'task_id': 'B-D02', 'evidence_type': 'inventory_and_reading_route_not_learning_effect', 'run_id': 'B-D02-20261016-evaluation04', 'source_commit': '30069ce468a52b68a0d3bfb62bb49b1cce0f2104', 'command': 'python scripts/B/draw_d02_materials.py', 'config': {'dpi': 300, 'font': 'Microsoft YaHei'}, 'human_sample_size': 0, 'units': 'task inventory counts / static source-line proxy', 'inputs': [{'path': p, 'sha256': hashlib.sha256((ROOT / p).read_bytes()).hexdigest()} for p in inputs], 'outputs': [{'path': f.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(out.glob('*')) if f.suffix in ('.png', '.svg')], 'limits': 'No human approval, pilot or effect study. Explicit source-line B0 cost proposal awaits common-cost integration.'}
    (out / 'figure_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
