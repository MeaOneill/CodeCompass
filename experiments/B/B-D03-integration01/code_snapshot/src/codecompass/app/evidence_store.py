"""B-owned transactional storage around A's unchanged learner 0.1.0 API."""
import json
import sqlite3
from pathlib import Path

from codecompass.learner import (
    initial_state, update_evidence, validate_state, planning_rows, beta_quantile,
)


class EvidenceStore:
    """One local database; caller supplies an anonymous user and explicit mode.

    BEGIN IMMEDIATE serializes read/update/write across processes. Accepted
    evidence remains the source of truth; a/b are transactionally materialized
    per project/concept and checked on read. Ignored attempts are audit only.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript('''
                CREATE TABLE IF NOT EXISTS ledgers (
                    user TEXT NOT NULL, simulated INTEGER NOT NULL,
                    ledger TEXT NOT NULL, revision INTEGER NOT NULL,
                    PRIMARY KEY(user, simulated));
                CREATE TABLE IF NOT EXISTS posterior (
                    user TEXT NOT NULL, simulated INTEGER NOT NULL,
                    project TEXT NOT NULL, concept TEXT NOT NULL,
                    a INTEGER NOT NULL, b INTEGER NOT NULL,
                    PRIMARY KEY(user, simulated, project, concept));
                CREATE TABLE IF NOT EXISTS attempts (
                    seq INTEGER PRIMARY KEY, user TEXT NOT NULL,
                    simulated INTEGER NOT NULL, evidence TEXT NOT NULL,
                    decision TEXT NOT NULL);
            ''')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=15)

    @staticmethod
    def _identity(user, simulated):
        if not isinstance(user, str) or not user.strip() or type(simulated) is not bool:
            raise ValueError('Anonymous user and explicit boolean simulation mode required')

    @staticmethod
    def _load(con, user, simulated):
        row = con.execute('SELECT ledger,revision FROM ledgers WHERE user=? AND simulated=?',
                          (user, simulated)).fetchone()
        state, revision = (json.loads(row[0]), row[1]) if row else (
            initial_state(user, is_simulated=simulated), 0)
        validate_state(state, allow_simulated=simulated)
        if state['pseudonymous_user_id'] != user or state['is_simulated'] != simulated:
            raise ValueError('Stored identity mismatch')
        expected = {}
        for project in {e['project'] for e in state['records']}:
            for r in planning_rows(state, project, allow_simulated=simulated):
                expected[(project, r['concept_id'])] = (r['alpha'], r['beta'])
        actual = {(p, c): (a, b) for p, c, a, b in con.execute(
            'SELECT project,concept,a,b FROM posterior WHERE user=? AND simulated=?',
            (user, simulated))}
        if expected != actual:
            raise ValueError('Stored posterior/ledger integrity mismatch')
        return state, revision

    def read(self, user, *, simulated=False):
        self._identity(user, simulated)
        with self._connect() as con:
            con.execute('BEGIN')
            state, _ = self._load(con, user, simulated)
            return state

    def submit_many(self, user, evidences, *, simulated=False):
        """All-or-nothing import; invalid evidence rolls back ledger and audit."""
        self._identity(user, simulated)
        with self._connect() as con:
            con.execute('BEGIN IMMEDIATE')
            state, revision = self._load(con, user, simulated)
            decisions = []
            for evidence in evidences:
                state, decision = update_evidence(state, evidence, allow_simulated=simulated)
                con.execute('INSERT INTO attempts(user,simulated,evidence,decision) VALUES(?,?,?,?)',
                            (user, simulated, json.dumps(evidence, ensure_ascii=False, allow_nan=False), decision))
                decisions.append(decision)
            con.execute('INSERT OR REPLACE INTO ledgers VALUES(?,?,?,?)',
                        (user, simulated, json.dumps(state, ensure_ascii=False), revision + 1))
            con.execute('DELETE FROM posterior WHERE user=? AND simulated=?', (user, simulated))
            for project in {e['project'] for e in state['records']}:
                for r in planning_rows(state, project, allow_simulated=simulated):
                    con.execute('INSERT INTO posterior VALUES(?,?,?,?,?,?)',
                                (user, simulated, project, r['concept_id'], r['alpha'], r['beta']))
            return state, decisions

    def submit(self, user, evidence, *, simulated=False):
        state, decisions = self.submit_many(user, [evidence], simulated=simulated)
        return state, decisions[0]

    def summary(self, user, project, concepts, *, simulated=False):
        state = self.read(user, simulated=simulated)
        rows = {r['concept_id']: r for r in planning_rows(state, project, allow_simulated=simulated)}
        result = []
        for concept in sorted(set(concepts)):
            r = rows.get(concept)
            a, b = (r['alpha'], r['beta']) if r else (1, 1)
            result.append({'concept_id': concept, 'a': a, 'b': b, 'mean': a/(a+b),
                           'lower_q10': beta_quantile(a, b, .1),
                           'upper_q90': beta_quantile(a, b, .9),
                           'evidence_ids': r['evidence_ids'] if r else [],
                           'source_status': 'SIMULATED' if simulated else 'REAL_INPUT_UNVERIFIED',
                           'unknown': r is None, 'is_simulated': simulated})
        return result
