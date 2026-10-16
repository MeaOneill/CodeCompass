"""Trusted local dev-submission checks in a timeout-controlled child process.

This process boundary is not a security sandbox for hostile submissions.
No graph, planner score, or path coverage is used as a correctness oracle.
"""
import argparse
import importlib.util
import itertools
import json
from pathlib import Path
import traceback


def load_candidate(path):
    spec = importlib.util.spec_from_file_location('candidate', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def raises(kind, fn):
    try:
        fn()
    except kind:
        return
    raise AssertionError('Expected ' + kind.__name__)


def equal(a, b):
    if a != b:
        raise AssertionError(f'{a!r} != {b!r}')


def checks_001(m):
    def bounds():
        equal(list(m.chunked_iter(range(4), 3, count=None)), [[0, 1, 2], [3]])
        equal(list(m.chunked_iter(range(10), 3, count=1)), [[0, 1, 2]])
        equal(list(m.chunked_iter(range(10), 3, count=2)), [[0, 1, 2], [3, 4, 5]])
        equal(list(m.chunked_iter(range(4), 3, count=100)), [[0, 1, 2], [3]])
        seen = []
        src = (seen.append(i) or i for i in range(10))
        equal(list(m.chunked_iter(src, 3, count=0)), [])
        equal(seen, [])

    def laziness():
        seen = []
        src = (seen.append(i) or i for i in range(10))
        gen = m.chunked_iter(src, 3, count=2)
        equal(seen, [])
        equal(list(gen), [[0, 1, 2], [3, 4, 5]])
        equal(seen, list(range(6)))
        equal(list(m.chunked_iter(itertools.count(), 3, count=2)), [[0, 1, 2], [3, 4, 5]])

    def compatibility():
        equal(list(m.chunked_iter(range(4), 3, count=2)), [[0, 1, 2], [3]])
        equal(list(m.chunked_iter(range(4), 3, fill=None, count=2)), [[0, 1, 2], [3, None, None]])
        equal(list(m.chunked_iter([], 3, count=2)), [])
        equal(list(m.chunked_iter('abcd', 3, count=2)), ['abc', 'd'])
        equal(list(m.chunked_iter(b'abcd', 3, count=2)), [b'abc', b'd'])
        equal(m.chunked(range(10), 3, count=2), [[0, 1, 2], [3, 4, 5]])

    def validation():
        raises(ValueError, lambda: list(m.chunked_iter([], 3, count=-1)))
        for value in [True, False, 1.0, '2']:
            raises(TypeError, lambda: list(m.chunked_iter([], 3, count=value)))
        raises(ValueError, lambda: list(m.chunked_iter([], 0)))
        raises(ValueError, lambda: list(m.chunked_iter([], 3, surprise=True)))
    return {'R1': bounds, 'R2': laziness, 'R3': compatibility, 'R4': validation}


def checks_002(m):
    def validation():
        for size in [0, -1]:
            raises(ValueError, lambda: list(m.windowed_iter([1, 2], size)))
        for size in [True, False, 2.0, '2', None]:
            raises(TypeError, lambda: list(m.windowed_iter([1, 2], size)))

    def normal():
        equal(list(m.windowed_iter(range(4), 2)), [(0, 1), (1, 2), (2, 3)])
        equal(list(m.windowed_iter(range(2), 3)), [])
        equal(list(m.windowed_iter([], 2)), [])
        equal(list(m.windowed_iter(range(2), 1)), [(0,), (1,)])

    def sentinel():
        equal(list(m.windowed_iter(range(3), 2, fill=None)), [(0, 1), (1, 2), (2, None)])
        equal(m.pairwise([1, 2], end=None), [(1, 2), (2, None)])
        equal(m.windowed([1, 2, 3], 2), [(1, 2), (2, 3)])
        equal(list(itertools.islice(m.windowed_iter(itertools.count(), 2), 2)), [(0, 1), (1, 2)])
    return {'R1': validation, 'R2': normal, 'R3': sentinel}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--task', required=True, choices=['task_001', 'task_002'])
    p.add_argument('--candidate', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    result = {'task_id': a.task, 'criteria': {}, 'import_error': None}
    try:
        mod = load_candidate(a.candidate)
        checks = checks_001(mod) if a.task == 'task_001' else checks_002(mod)
        for name, fn in checks.items():
            try:
                fn()
                result['criteria'][name] = {'passed': True, 'error': None}
            except Exception:
                result['criteria'][name] = {'passed': False, 'error': traceback.format_exc(limit=3)}
    except Exception:
        result['import_error'] = traceback.format_exc(limit=3)
    Path(a.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
