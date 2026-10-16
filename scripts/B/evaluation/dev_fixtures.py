"""Explicit developer fixtures; never participant submissions or learning results."""
import difflib
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def candidate_source(task_id):
    text = (ROOT / 'benchmarks/sources/boltons/boltons/iterutils.py').read_text(encoding='utf-8')
    if task_id == 'task_001':
        text = text.replace('def chunked_iter(src, size, **kw):', 'def chunked_iter(src, size, count=None, **kw):')
        text = text.replace('    # TODO: add count kwarg?', '    # Development fixture, not a participant solution.\n    if count is not None:\n        if type(count) is not int:\n            raise TypeError("count must be a built-in integer")\n        if count < 0:\n            raise ValueError("count must be nonnegative")')
        text = text.replace('    src_iter = iter(src)\n    while True:\n        cur_chunk', '    src_iter = iter(src)\n    emitted = 0\n    while count is None or emitted < count:\n        cur_chunk', 1)
        text = text.replace('        yield postprocess(cur_chunk)', '        emitted += 1\n        yield postprocess(cur_chunk)', 1)
    elif task_id == 'task_002':
        text = text.replace('    tees = itertools.tee(src, size)', '    if type(size) is not int:\n        raise TypeError("size must be a built-in integer")\n    if size <= 0:\n        raise ValueError("size must be positive")\n    tees = itertools.tee(src, size)', 1)
    else:
        raise ValueError('Unknown fixture task')
    return text


def create_fixture(task_id, folder, mutation=None):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    original = (ROOT / 'benchmarks/sources/boltons/boltons/iterutils.py').read_text(encoding='utf-8')
    source = candidate_source(task_id)
    if mutation == 'original':
        source = original
    elif mutation == 'overconsume':
        source = source.replace('while count is None or emitted < count:', 'while True:').replace('        emitted += 1\n        yield postprocess', '        if count is not None and emitted >= count:\n            break\n        emitted += 1\n        yield postprocess')
    elif mutation == 'hang':
        source = source.replace('    # TODO: add count kwarg?', '    # TODO: add count kwarg?')
        source = source.replace('    emitted = 0\n', '    while True:\n        pass\n    emitted = 0\n', 1) if task_id == 'task_001' else source
    elif mutation == 'outside_scope':
        source += '\nILLEGAL_CHANGE = True\n'
    (folder / 'candidate.py').write_text(source, encoding='utf-8', newline='\n')
    (folder / 'patch.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True), source.splitlines(True), fromfile='original/iterutils.py', tofile='candidate/iterutils.py')), encoding='utf-8')
    (folder / 'explanation.md').write_text('Developer fixture only. No human explanation grade or learner timing is claimed.\n', encoding='utf-8')
    (folder / 'regression_tests.py').write_text('# Fixture artifact; not independently human-reviewed regression tests.\n', encoding='utf-8')
    (folder / 'commands_and_elapsed.json').write_text(json.dumps({'is_fixture': True, 'learner_elapsed_seconds': None, 'notes': 'No participant task was performed.'}) + '\n', encoding='utf-8')
    return folder
