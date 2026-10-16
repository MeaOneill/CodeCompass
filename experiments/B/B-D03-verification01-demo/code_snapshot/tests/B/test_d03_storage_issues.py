import copy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from codecompass.app.evidence_store import EvidenceStore
from codecompass.issues.candidates import match_issues

ROOT = Path(__file__).resolve().parents[2]


def evidence(n=0, *, user='anon-test', concept='python.iterator_protocol', project='p', outcome='pass'):
    return {'evidence_id': f'e{n}', 'item_id': f'item{n}', 'concept_id': concept,
            'project': project, 'timestamp': '2026-10-16T13:00:00+00:00',
            'pseudonymous_user_id': user, 'is_fixture': True, 'independent': True,
            'evidence_type': 'independent_quiz', 'outcome': outcome}


def test_update_deduplicate_failure_and_reading(tmp_path):
    s = EvidenceStore(tmp_path/'personal.sqlite3')
    e = evidence()
    _, d = s.submit('anon-test', e, simulated=True); assert d == 'ACCEPTED'
    _, d = s.submit('anon-test', e, simulated=True); assert d == 'DUPLICATE_EVIDENCE'
    repeat = {**e, 'evidence_id': 'repeat', 'project': 'other'}
    _, d = s.submit('anon-test', repeat, simulated=True); assert d == 'DUPLICATE_ITEM'
    _, d = s.submit('anon-test', evidence(1, outcome='fail'), simulated=True); assert d == 'ACCEPTED'
    for kind in ['reading', 'self_report']:
        _, d = s.submit('anon-test', {**evidence(2), 'evidence_type': kind}, simulated=True)
        assert d == 'IGNORED_NONINDEPENDENT_OR_UNSCORED'
    row = s.summary('anon-test', 'p', [e['concept_id']], simulated=True)[0]
    assert (row['a'], row['b'], row['mean']) == (2, 2, .5)
    assert 0 < row['lower_q10'] < row['mean'] < row['upper_q90'] < 1
    assert s.summary('anon-test', 'other', [e['concept_id']], simulated=True)[0]['unknown']


def test_users_modes_and_all_or_nothing(tmp_path):
    path = tmp_path/'db.sqlite3'; s = EvidenceStore(path)
    s.submit('anon-test', evidence(), simulated=True)
    assert not s.read('anon-other', simulated=True)['records']
    assert not s.read('anon-test', simulated=False)['records']
    before = s.read('anon-test', simulated=True)
    with pytest.raises(ValueError):
        s.submit_many('anon-test', [evidence(1), {**evidence(2), 'is_fixture': False}], simulated=True)
    assert s.read('anon-test', simulated=True) == before
    with sqlite3.connect(path) as c:
        assert c.execute('SELECT COUNT(*) FROM attempts').fetchone()[0] == 1
    with pytest.raises(ValueError):
        s.submit('anon-test', {**evidence(), 'outcome': 'fail'}, simulated=True)
    with pytest.raises(ValueError):
        s.submit('anon-test', evidence(user='wrong'), simulated=True)


def test_restart_fresh_process_and_concurrent_writers(tmp_path):
    path = tmp_path/'db.sqlite3'; s = EvidenceStore(path)
    def put(n):
        return EvidenceStore(path).submit('anon-test', evidence(n), simulated=True)[1]
    with ThreadPoolExecutor(max_workers=5) as pool:
        assert list(pool.map(put, range(12))) == ['ACCEPTED']*12
        decisions = list(pool.map(lambda _: put(20), range(5)))
    assert decisions.count('ACCEPTED') == 1
    assert decisions.count('DUPLICATE_EVIDENCE') == 4
    code = ('import json,sys;from codecompass.app.evidence_store import EvidenceStore;'
            'print(json.dumps(EvidenceStore(sys.argv[1]).read("anon-test",simulated=True)))')
    result = subprocess.run([sys.executable, '-c', code, str(path)], cwd=ROOT,
                            env={**os.environ, 'PYTHONPATH': str(ROOT/'src')},
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == s.read('anon-test', simulated=True)
    assert len(json.loads(result.stdout)['records']) == 13


def test_detect_corrupt_posterior(tmp_path):
    path = tmp_path/'db.sqlite3'; s = EvidenceStore(path)
    s.submit('anon-test', evidence(), simulated=True)
    with sqlite3.connect(path) as c:
        c.execute('UPDATE posterior SET a=100')
    with pytest.raises(ValueError, match='integrity'):
        s.read('anon-test', simulated=True)


def test_issue_closed_unknown_and_url_tamper():
    def row(n, state, title):
        return {'number': n, 'state': state, 'title': title, 'body': '',
                'html_url': f'https://github.com/owner/repo/issues/{n}'}
    snap = {'snapshot_version': 'B-D03-1', 'repo': 'owner/repo', 'is_fixture': True,
            'retrieved_at': '2026-10-16T00:00:00Z',
            'issues': [row(1, 'open', 'iterutils bug'), row(2, 'closed', 'iterutils old'),
                       row(3, 'open', 'other_module') ]}
    units = [{'id': 'u', 'concept_ids': ['c'], 'source_spans': [{'path': 'boltons/iterutils.py'}]}]
    m = match_issues(snap, units, ['c'])
    assert len(m['candidates']) == len(m['historical']) == len(m['unmatched']) == 1
    assert m['candidates'][0]['candidate_concept_gaps'] == ['c']
    assert m['historical'][0]['disposition'] == 'HISTORICAL_CLOSED_NOT_ACTIONABLE'
    assert m['recommendation_accuracy'] is None
    none = match_issues(snap, [], [])
    assert none['no_suitable_reason'] and not none['candidates']
    bad = copy.deepcopy(snap); bad['issues'][0]['html_url'] = 'https://example.com/phish'
    with pytest.raises(ValueError, match='URL'):
        match_issues(bad, units, [])
    bad = copy.deepcopy(snap); bad['issues'][0]['state'] = 'unknown'
    with pytest.raises(ValueError, match='state'):
        match_issues(bad, units, [])
