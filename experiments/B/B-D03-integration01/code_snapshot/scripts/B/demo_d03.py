"""Real storage + real source planning + saved public Issues; synthetic answers."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT))
from codecompass.app.evidence_store import EvidenceStore
from codecompass.issues.candidates import match_issues
from codecompass.planner import plan_request
from scripts.A.run_d03 import make_request, b0_adapter


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    p = argparse.ArgumentParser(description='B-D03：模拟独立短测→真实持久化/进程恢复→真实源码路线→公开Issue固定快照。无需用户做题。')
    p.add_argument('--run-id', required=True)
    p.add_argument('--snapshot', type=Path, default=ROOT/'experiments/B/B-D03-issues01/snapshot.json')
    a = p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', a.run_id):
        p.error('run-id只允许字母、数字、下划线和短横线')
    out = ROOT/'experiments/B'/a.run_id
    if out.exists():
        p.error('run-id已存在；请换新名称以保留历史证据')
    out.mkdir(parents=True)
    db = ROOT/'tmp'/a.run_id/'personal.sqlite3'
    if db.exists():
        p.error('同名本地数据库已存在，拒绝混入上次记录')
    store = EvidenceStore(db)
    user = 'sim-anon-B03-01'
    task = load(ROOT/'benchmarks/dev/D03/task_001.json')
    config = load(ROOT/'configs/A/D03_common.json')
    units = [u for u in load(ROOT/'benchmarks/dev/D03/units.json') if u['id'] in task['learning_unit_ids']]
    project = task['snapshot_id']; concepts = task['required_concept_ids']
    concept = 'python.iterator_protocol'
    def evidence(n, outcome='pass'):
        return {'schema_version': '1.0.0', 'object_type': 'LearnerEvidence',
                'is_fixture': True, 'evidence_id': f'sim-B03-{n}',
                'pseudonymous_user_id': user, 'concept_id': concept,
                'item_id': f'sim-independent-item-{n}', 'outcome': outcome,
                'timestamp': datetime.now(timezone.utc).isoformat(), 'project': project,
                'evidence_type': 'independent_quiz', 'attempt_id': f'sim-attempt-{n}',
                'independent': True, 'source_status': 'SIMULATED_NOT_HUMAN'}
    stages = []; events = []; routes = []
    def stage(name):
        state = store.read(user, simulated=True)
        summary = store.summary(user, project, concepts, simulated=True)
        request = make_request(task, units, state, config, a.run_id+'-'+name)
        plan, details = plan_request(ROOT, request, units, state, config)
        b0, raw = b0_adapter(request, units, config['routes'][task['task_id']], details['gate'])
        save(out/'stages'/name/'ledger.json', state)
        save(out/'stages'/name/'summary.json', summary)
        save(out/'stages'/name/'request.json', request)
        save(out/'stages'/name/'plan.json', plan)
        save(out/'stages'/name/'detail.json', details)
        save(out/'stages'/name/'B0.json', b0)
        row = next(r for r in summary if r['concept_id'] == concept)
        stages.append({'stage': name, **row})
        routes.append({'stage': name, 'is_simulated': True, 'plan': plan, 'B0': b0,
                       'source_spans': {u['id']: u['source_spans'] for u in units}})
        print(f'{name}: a={row["a"]} b={row["b"]} 模型均值={row["mean"]:.4f} Q10..Q90={row["lower_q10"]:.4f}..{row["upper_q90"]:.4f} 路线={plan["ordered_units"]}')
    stage('initial')
    for n, outcome in [(0, 'pass'), (1, 'fail')]:
        e = evidence(n, outcome); _, d = store.submit(user, e, simulated=True)
        events.append({'evidence': e, 'decision': d})
        stage('correct' if n == 0 else 'incorrect')
    duplicate = {**events[0]['evidence'], 'evidence_id': 'sim-repeat-new-attempt'}
    _, d = store.submit(user, duplicate, simulated=True)
    assert d == 'DUPLICATE_ITEM'; events.append({'evidence': duplicate, 'decision': d})
    reading = {**evidence(2), 'evidence_type': 'reading', 'independent': False}
    _, d = store.submit(user, reading, simulated=True)
    assert d.startswith('IGNORED'); events.append({'evidence': reading, 'decision': d})
    stage('duplicate_and_reading')
    # Additional distinct synthetic items only to exercise the conservative gate.
    batch = [evidence(n) for n in range(3, 23)]
    _, decisions = store.submit_many(user, batch, simulated=True)
    events.extend({'evidence': e, 'decision': d} for e, d in zip(batch, decisions))
    stage('distinct_simulated_items')
    state = store.read(user, simulated=True)
    code = ('import json,sys;from codecompass.app.evidence_store import EvidenceStore;'
            'print(json.dumps(EvidenceStore(sys.argv[1]).read(sys.argv[2],simulated=True)))')
    process = subprocess.run([sys.executable, '-c', code, str(db), user], cwd=ROOT,
                             env={**os.environ, 'PYTHONPATH': str(ROOT/'src')},
                             capture_output=True, text=True, timeout=30)
    save(out/'restart_process.json', {'command': [sys.executable, '-c', code, str(db.relative_to(ROOT)), user],
                                     'exit_code': process.returncode, 'stdout': process.stdout, 'stderr': process.stderr})
    assert process.returncode == 0 and json.loads(process.stdout) == state
    assert store.read('sim-anon-B03-02', simulated=True)['records'] == []
    assert store.read(user, simulated=False)['records'] == []
    save(out/'events.json', {'is_simulated': True, 'human_answers': 0, 'events': events})
    save(out/'capability.json', {'run_id': a.run_id, 'is_simulated': True, 'concept_id': concept,
                               'stages': stages, 'uncertainty': 'Beta model central Q10-Q90; not calibrated real mastery',
                               'restart_equal': True, 'users_isolated': True, 'simulation_isolated': True})
    save(out/'routes.json', routes); save(out/'config.json', config)
    snapshot = load(a.snapshot)
    if snapshot['is_fixture'] is not False:
        raise ValueError('Demo needs a real public Issue snapshot, not fixture input')
    gaps = [r['concept_id'] for r in store.summary(user, project, concepts, simulated=True) if r['lower_q10'] < config['threshold']]
    matches = match_issues(snapshot, units, gaps)
    save(out/'issue_matches.json', matches)
    save(out/'issue_snapshot.json', snapshot)
    print('重启恢复一致；用户/模拟数据隔离通过。回答全部为模拟，真人回答0。')
    print('Issue固定快照：'+snapshot['retrieved_at'])
    print(f'开放模块候选={len(matches["candidates"])} 历史关闭={len(matches["historical"])}；相关性未独立标注，无推荐准确率。')
    for m in matches['candidates']:
        print(f'OPEN #{m["number"]} {m["url"]} modules={m["modules"]} gaps={m["candidate_concept_gaps"]}')
    registration = {'run_id': a.run_id, 'task': 'B-D03', 'actual_time': datetime.now(timezone.utc).isoformat(),
                    'planned_day': '2026-10-17', 'owner': '成员B / 糯糯', 'executor': 'Codex Agent B',
                    'machine': platform.node(), 'python': sys.version, 'command': sys.argv,
                    'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    'dependency_commit': 'cf02b664aea81f91aa8e7423a8aa891367c73b7e',
                    'contracts': '1.1.0 compatible', 'ledger_version': '0.1.0',
                    'response_kind': 'SIMULATED', 'issue_kind': 'REAL_PUBLIC_SNAPSHOT',
                    'formal_experiments': 0, 'independent_human_review': 'NOT_REVIEWED', 'exit_code': 0}
    paths = [*sorted((ROOT/'src/codecompass/app').glob('*.py')),
             *sorted((ROOT/'src/codecompass/issues').glob('*.py')),
             *sorted((ROOT/'src/codecompass/learner').glob('*.py')),
             *sorted((ROOT/'src/codecompass/planner').glob('*.py')),
             ROOT/'scripts/B/demo_d03.py', ROOT/'scripts/B/issues_d03.py',
             ROOT/'tests/B/test_d03_storage_issues.py', ROOT/'schemas/contracts-1.1.schema.json',
             ROOT/'benchmarks/dev/D03/task_001.json', ROOT/'benchmarks/dev/D03/units.json',
             ROOT/'benchmarks/sources/boltons/snapshot.json', ROOT/'configs/A/D03_common.json']
    manifest = []
    for path in paths:
        rel = path.relative_to(ROOT); data = path.read_bytes()
        copy_path = out/'code_snapshot'/rel; copy_path.parent.mkdir(parents=True, exist_ok=True); copy_path.write_bytes(data)
        manifest.append({'path': rel.as_posix(), 'sha256': hashlib.sha256(data).hexdigest(),
                         'frozen_copy': copy_path.relative_to(ROOT).as_posix()})
    save(out/'input_manifest.json', manifest)
    save(out/'registration.json', registration)
    print('B-D03工程演示完成。真实学习效果/准确率：未测。'+str(out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
