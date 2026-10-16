"""Compile fixed B0 order from pinned upstream README-linked documentation."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def main():
    folder = ROOT / 'benchmarks/sources/boltons_B_D02/docs'
    readme = (folder / 'README.md').read_text(encoding='utf-8')
    rst = (folder / 'iterutils.rst').read_text(encoding='utf-8')
    assert '[chunked]' in readme and '[iterutils]' in readme
    names = re.findall(r'^\.\. autofunction:: (\w+)', rst, re.MULTILINE)
    mapping = {'chunked': 'u_chunked', 'chunked_iter': 'u_chunked_iter', 'is_iterable': 'u_iterable'}
    route = [mapping[name] for name in names if name in mapping]
    assert len(route) == len(mapping)
    config = {'version': 'B0-upstream-document-order-0.2', 'compiler': 'deterministic pinned upstream documentation order', 'baseline_type': 'README_documentation_fixed_route', 'compiled_before_ours_implementation': True, 'routes': {'task_001': route}, 'rationale': ['固定README列出chunked/windowed并链接iterutils文档；固定版本RST以autofunction列出文档顺序。', '在同一三个候选单元中按上游文档出现顺序读取：chunked、chunked_iter、is_iterable；不是为Ours表现挑选路线。', '只按固定顺序取预算内前缀，不做能力门控；静态行数成本仅作D02开发代理，正式对照需所有方法同成本。', '默认shared仍保留null成本输入拒绝；显式source_lines_proposal不修改A共享单元。'], 'documentation': [{'path': (folder / name).relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256((folder / name).read_bytes()).hexdigest()} for name in ['README.md', 'iterutils.rst']], 'human_review': 'NOT_REVIEWED', 'limitations': 'D02 documentation baseline is executable; no human learning effect, optimality or formal common-cost approval is claimed.'}
    (ROOT / 'configs/B/B0_fixed.json').write_text(json.dumps(config, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('B0 pinned-document order:', route)


if __name__ == '__main__': main()
