"""Deterministic design wireframe, no measurements or performance claims."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]


def main():
    out = ROOT / 'report_materials/B'
    out.mkdir(parents=True, exist_ok=True)
    font_path = Path('C:/Windows/Fonts/msyh.ttc')
    font = ImageFont.truetype(str(font_path), 22)
    small = ImageFont.truetype(str(font_path), 18)
    title = ImageFont.truetype(str(font_path), 32)
    im = Image.new('RGB', (1800, 1210), '#f5f7fb')
    d = ImageDraw.Draw(im)
    d.text((44, 25), 'CodeCompass | B-D01 页面线框与 F01 依赖补充', font=title, fill='#132c49')
    d.text((44, 78), '设计图 · 非运行截图 · 无效果数据 | 契约 1.0.0 | A 依赖 54613cf', font=font, fill='#49566b')
    cards = [
        ('仓库导入', ['boltons · BSD-3-Clause', '固定 commit + 采集时间 + 文件 hash', '局部源码包；校验失败停止']),
        ('任务选择', ['task_001 · count 惰性扩展', '25 分钟为设计目标，未预演', '独立评分与应用输入隔离']),
        ('短测与证据', ['题目 ID / 匿名用户 / 独立性', '未实现；不显示掌握率', '重复作答不能重复累计证据']),
        ('路径与约束', ['调用 A planner；当前未实现', '成本 null 不得补零', '理由 / 未覆盖 / 失败状态']),
        ('源码依据', ['iterutils.py:286–306 / 316–358', '固定版本字节与闭区间 hash', '只读校验已实现；不执行源码']),
        ('反馈与恢复', ['独立测验 → learner → 重规划', '旧路径 / 新路径 / 触发原因', '暂停检查点；当前为格式设计']),
        ('长期记忆', ['计划 SQLite；用户库不入 Git', '重启核对 run_id / 输入 hash', '未实现持久化与恢复服务']),
        ('Issue 准备', ['计划 GitHub API + 抓取时间', 'TODO 并非已确认开放 Issue', '当前无候选，不生成假链接']),
    ]
    for i, (heading, lines) in enumerate(cards):
        row, col = divmod(i, 4)
        x, y = 44 + col * 438, 144 + row * 265
        d.rounded_rectangle((x, y, x + 406, y + 224), 14, fill='white', outline='#b9c7d8', width=2)
        d.rectangle((x + 1, y + 1, x + 405, y + 53), fill='#e3ebf5')
        d.text((x + 16, y + 12), heading, font=font, fill='#173d65')
        for j, text in enumerate(lines):
            d.text((x + 16, y + 77 + j * 42), text, font=small, fill='#283b50')
        if col < 3:
            d.text((x + 412, y + 99), '→', font=font, fill='#537398')
    d.text((44, 666), '真实固定版本：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d', font=font, fill='#173d65')
    d.text((44, 705), '源码 TODO: iterutils.py:329；未知成本和未核验教学边保持 null / soft。', font=font, fill='#49566b')
    d.rounded_rectangle((44, 770, 1750, 1148), 14, fill='#eaf0f7', outline='#b9c7d8', width=2)
    d.text((68, 789), 'F01 存储与 API 依赖 / 实现边界', font=title, fill='#173d65')
    deps = [
        '已实现：CLI → B retrieval → A schema 1.0.0 + 固定任务 / 四文件源码包（只读）',
        'A 待实现：graph / learner / planner；模型解释可选，不能替代路径算法',
        'B 计划：SQLite 匿名证据 / 事件 / 路径；GitHub API 在线 Issue；模型接口可禁用',
        '固定快照：用于断网复现；在线抓取：用于发现与时效核验，缓存必须标日期',
        '保存边界：小型任务 / 源码许可 / 配置进 Git；用户数据库 / 密钥 / 终测答案隔离',
        '错误入口：hash 不符 → 停止；API 失败 → 记录；暂停 → 检查点；未知值不冒充测量',
    ]
    for j, text in enumerate(deps):
        d.text((68, 856 + j * 44), text, font=font, fill='#283b50')
    image_path = out / 'B-D01_wireframe.png'
    im.save(image_path, dpi=(300, 300))
    config = {'figure_id': 'F01-B-D01-wireframe', 'task_id': 'B-D01', 'evidence_type': 'design_not_measurement', 'run_id': None, 'dependency_commit': '54613cf136d788bde7c46454d3d7b9e29f295a9b', 'schema_version': '1.0.0', 'width': 1800, 'height': 1210, 'dpi': 300, 'font': str(font_path), 'cards': cards, 'dependencies': deps, 'source_records': ['docs/B/user_flow.md', 'docs/contracts.md', 'benchmarks/dev/task_001.json', 'benchmarks/sources/boltons/snapshot.json'], 'image_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(), 'command': 'python scripts/B/draw_d01.py', 'limits': 'Design only; no implemented GUI, no human/effect results.'}
    (out / 'wireframe_config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
