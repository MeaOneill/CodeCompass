"""Check manually authored output keys against fixed original source behavior.

No graph/path output is read. No key contents are printed for held-out tasks.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def actual_outputs():
    it = module(ROOT / 'benchmarks/sources/boltons/boltons/iterutils.py', 'original_iterutils')
    st = module(ROOT / 'benchmarks/sources/boltons_B_D02/boltons/strutils.py', 'original_strutils')
    return {
        'task_003': {'plain': list(it.unique_iter(['a', 'A', 'a', 'b'])), 'casefold': list(it.unique_iter(['a', 'A', 'a', 'b'], key=str.lower)), 'length': list(it.unique_iter(['hi', 'ok', 'hey', 'bye'], key=len))},
        'task_004': {'null': it.get_path({'a': [{'x': None}]}, ('a', 0, 'x'), default='MISSING'), 'missing': it.get_path({'a': [{'x': None}]}, 'a.0.z', default='MISSING'), 'string_index': it.get_path({'a': [10, 20]}, 'a.1'), 'empty_path': it.get_path({'x': 1}, ())},
        'task_005': {'acronym': st.camel2under('HTTPServer2Thing'), 'simple': st.under2camel('parse_http_body'), 'underscores': st.under2camel('__edge__')},
        'task_006': {'normal': st.slugify('Hello, World!'), 'empty': st.slugify(''), 'punct': st.slugify('!!!'), 'ascii_bytes': list(st.slugify('Café', ascii=True))},
        'task_007': {'teens': [st.ordinalize(n) for n in (11, 12, 13, 21, 112)], 'suffix': st.ordinalize(23, ext_only=True), 'text': st.ordinalize('abc')},
        'task_008': {'text': st.strip_ansi('A\x1b[31mB\x1b[0mC'), 'bytes': list(st.strip_ansi(b'X\x1b[1mY\x1b[0m')), 'plain': st.strip_ansi('plain')},
        'task_009': {'roundtrip': list(st.gunzip_bytes(st.gzip_bytes(b'open-source navigation'))), 'empty': list(st.gunzip_bytes(st.gzip_bytes(b''))), 'type_name': type(st.gzip_bytes(b'open-source navigation')).__name__},
        'task_010': {'lines': list(st.iter_splitlines('a\r\nb\n')), 'empty': list(st.iter_splitlines('')), 'indented': st.indent('a\n\nb\n', '> ')},
        'task_011': {'reverse': st.parse_int_list('5-3,1'), 'duplicates': st.parse_int_list('2,1,2'), 'formatted': st.format_int_list([1, 2, 3, 5]), 'empty': st.parse_int_list('')},
        'task_012': {'prefix': st.removeprefix('foobar', 'foo'), 'not_chars': st.removeprefix('barfoo', 'foo'), 'two': st.human_readable_list(['a', 'b']), 'three': st.human_readable_list(['a', 'b', 'c'], oxford=False)},
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--private-key', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    expected = json.loads((ROOT / 'benchmarks/B/dev_response_keys.json').read_text(encoding='utf-8'))['tasks']
    private = Path(a.private_key)
    expected.update(json.loads(private.read_text(encoding='utf-8'))['tasks'])
    actual = actual_outputs()
    rows = [{'task_id': k, 'behavior_key_matches_fixed_source': actual[k] == v['outputs']} for k, v in expected.items()]
    out = Path(a.output)
    if out.exists():
        raise FileExistsError('Fresh output required')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'evidence_type': 'development_validation', 'basis': 'B manually authored keys checked against fixed original functions, not graph', 'private_key_sha256': hashlib.sha256(private.read_bytes()).hexdigest(), 'checks': rows, 'exit_code': int(not all(r['behavior_key_matches_fixed_source'] for r in rows)), 'human_semantic_review': 'NOT_REVIEWED'}, indent=2) + '\n', encoding='utf-8')
    print('Behavior key matches:', sum(r['behavior_key_matches_fixed_source'] for r in rows), '/', len(rows))
    return int(not all(r['behavior_key_matches_fixed_source'] for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
