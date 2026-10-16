"""Explicit fetch or offline contribution-preparation preview; never posts."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from codecompass.issues.candidates import fetch_snapshot, match_issues


def main():
    p = argparse.ArgumentParser(description='只读Issue抓取/固定快照匹配；生成贡献准备信息，不发布内容。')
    sub = p.add_subparsers(dest='action', required=True)
    f = sub.add_parser('fetch'); f.add_argument('--output', type=Path, required=True)
    m = sub.add_parser('prepare'); m.add_argument('--snapshot', type=Path, required=True)
    m.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('输出已存在，请换新路径；不覆盖历史证据')
    try:
        if args.action == 'fetch':
            result = fetch_snapshot()
        else:
            snapshot = json.loads(args.snapshot.read_text(encoding='utf-8'))
            units = json.loads((ROOT/'benchmarks/dev/D03/units.json').read_text(encoding='utf-8'))
            result = match_issues(snapshot, units, {c for u in units for c in u['concept_ids']})
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    except (OSError, ValueError, KeyError) as e:
        print('FAILED: '+str(e)); return 2
    if args.action == 'prepare':
        print('固定快照获取时间：'+result['snapshot_retrieved_at'])
        print('开放候选：'+str(len(result['candidates']))+'；历史关闭：'+str(len(result['historical'])))
        for item in result['candidates']:
            print(str(item['number'])+' '+item['url']+' | '+', '.join(item['modules']))
            print('  仅模块词命中，待核查复现/版本；不代表适合初学者或已提交贡献。')
        print(result['no_suitable_reason'] or '下一步：核查原Issue及固定版本，准备复现/测试；当前不向社区发送内容。')
    print(str(args.output.resolve()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
