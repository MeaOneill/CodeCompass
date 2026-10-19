import copy
from datetime import datetime,timezone,timedelta
import hashlib
import io
import json
from pathlib import Path
import sys
import threading
import time
import uuid
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from codecompass.app.relay_v2 import RelayCollector,registry,packet
from codecompass.app.diagnostics_v2 import ITEMS,public_item
from scripts.B.comparison.b1 import SpendMeter
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit
from scripts.B.serve_relay_v2 import make_server
from scripts.B.grade_session_v2 import assess
from scripts.B.export_relay_v2 import export_assessed


class Clock:
    def __init__(self):self.epoch='fixture';self.t=100.
    def sample(self):return dict(epoch=self.epoch,mono=self.t,wall=(datetime(2026,10,19,tzinfo=timezone.utc)+timedelta(seconds=self.t)).isoformat())


def stored(c,sid):
    with c.connect() as db:return json.loads(db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()[0])


def config():return json.loads((ROOT/'configs/B/D04_deepseek_authorized.json').read_text(encoding='utf-8'))['b1']


def transport(payload,cfg):
    ctx=json.loads(payload['input'].split('CONTEXT_JSON\n')[1])
    text=json.dumps({'ordered_units':[u['id'] for u in ctx['units'] if u['id'] not in ctx['completed']]})
    return dict(model=cfg['model'],status='completed',usage=dict(input_tokens=100,output_tokens=50),
        output=[dict(type='message',content=[dict(type='output_text',text=text)])])


@pytest.mark.parametrize('method',['Ours','B2','B1'])
@pytest.mark.parametrize('tid',[f'task_{i:03}' for i in range(1,13)])
def test_twelve_real_source_closed_loops(tmp_path,method,tid):
    c=RelayCollector(ROOT,tmp_path/'db.sqlite3',actor='test_fixture',clock=Clock(),b1_config=config(),meter=SpendMeter(5),transport=transport)
    s=c.create(tid,method);sid=s['session_id'];assert s['status']=='ACTIVE',c.traces(sid)
    assert s['materials'] and s['task']['repo_commit'].startswith('4e5faa')
    c.clock.t+=3;s=c.action(sid,'complete_reading');assert s['phase']=='quiz'
    assert not stored(c,sid)['data']['state']['records']
    assert 'answer' not in public_item(tid)
    with pytest.raises(ValueError):c.action(sid,'complete_reading')
    with pytest.raises(ValueError):c.action(sid,'submit',{'response':'skip'})
    c.clock.t+=2;s=c.action(sid,'answer',{'choice':ITEMS[tid]['answer']})
    assert s['status']=='ACTIVE' and s['outcome']=='pass' and s['quiz_done'],c.traces(sid)
    assert len(stored(c,sid)['data']['state']['records'])==1
    with pytest.raises(ValueError):c.action(sid,'answer',{'choice':ITEMS[tid]['answer']})
    assert not set(s['route'])&set(s['completed'])
    s=c.action(sid,'submit',{'response':'{"outputs":{},"references":[],"explanation":"fixture"}'})
    assert s['success'] is None and s['elapsed_seconds']==5
    export(c.database,tmp_path/'out','test_fixture');assert audit(tmp_path/'out')['passed']


def test_registry_actual_quantity_and_source_provenance():
    rows=registry(ROOT)['records'];assert len(rows)==12
    assert len([r for r in rows if r['split']=='dev'])==4
    assert len([r for r in rows if r['split']=='test_candidate'])==8
    for r in rows:
        assert r['units'] and all(u['source_spans'] for u in r['units'])
        assert sum(u['base_cost'] for u in r['units'])+1<=100
        assert 'outputs' not in r and 'rubric' not in r and 'answer' not in r['public_quiz']


@pytest.mark.parametrize('tid',[f'task_{i:03}' for i in range(3,13)])
def test_parallel_quizzes_executable_and_independent(tid):
    import contextlib
    out=io.StringIO()
    with contextlib.redirect_stdout(out):exec(ITEMS[tid]['code'],{})
    assert out.getvalue().strip()==ITEMS[tid]['choices'][ITEMS[tid]['answer']]
    assert ITEMS[tid]['item_id'].startswith('B06-parallel-')


def test_equal_initial_information_and_no_gold(tmp_path):
    hashes=[]
    for m in ('Ours','B2','B1'):
        c=RelayCollector(ROOT,tmp_path/(m+'.sqlite3'),actor='test_fixture',b1_config=config(),meter=SpendMeter(5),transport=transport)
        s=c.create(method=m);ctx=c.traces(s['session_id'])[0]['context']
        hashes.append(hashlib.sha256(json.dumps(ctx,sort_keys=True).encode()).hexdigest())
        assert all(k not in json.dumps(ctx) for k in ('private_evaluation','automated_score','expected_outputs'))
    assert len(set(hashes))==1


def test_b1_dynamic_actual_feedback_and_billing(tmp_path):
    c=RelayCollector(ROOT,tmp_path/'db',actor='test_fixture',b1_config=config(),meter=SpendMeter(5),transport=transport)
    s=c.create(method='B1');sid=s['session_id'];c.action(sid,'complete_reading');c.action(sid,'answer',{'choice':0})
    traces=c.traces(sid);assert len(traces)==2 and all(t['status']=='FEASIBLE' for t in traces)
    assert traces[1]['context']['feedback'] in ('pass','fail') and traces[1]['context']['completed']
    assert traces[1]['context']['remaining_proxy']<100
    assert len(traces[1]['context']['learner_evidence'])==1
    assert sum(len(t['details']['calls']) for t in traces)==2
    assert c.meter.reserved==.5 and all(t['details']['transport_is_fixture'] for t in traces)


def test_missing_b1_never_substitutes_saved_routes(tmp_path):
    c=RelayCollector(ROOT,tmp_path/'db',actor='test_fixture');s=c.create(method='B1')
    assert s['status']=='FAILED' and c.traces(s['session_id'])[0]['status']=='NOT_CONFIGURED'
    with pytest.raises(ValueError):c.create(method='B1_saved')


def test_illegal_b1_is_not_semantically_repaired(tmp_path):
    calls=[]
    def bad(p,c):
        calls.append(p);r=transport(p,c);r['output'][0]['content'][0]['text']='{"ordered_units":["invented"]}';return r
    c=RelayCollector(ROOT,tmp_path/'db',actor='test_fixture',b1_config=config(),meter=SpendMeter(5),transport=bad)
    s=c.create(method='B1');assert s['status']=='FAILED' and len(calls)==1
    assert c.traces(s['session_id'])[0]['status']=='ALGORITHM_INVALID'


def test_b1_api_wait_does_not_hold_sqlite_write_transaction(tmp_path):
    entered=threading.Event();release=threading.Event();result=[]
    def slow(p,c):entered.set();assert release.wait(8);return transport(p,c)
    c=RelayCollector(ROOT,tmp_path/'db',actor='test_fixture',b1_config=config(),meter=SpendMeter(5),transport=slow)
    a=c.create(method='Ours');thread=threading.Thread(target=lambda:result.append(c.create(method='B1')));thread.start()
    try:
        assert entered.wait(5);start=time.monotonic();assert c.action(a['session_id'],'pause')['status']=='PAUSED'
        assert time.monotonic()-start<2
    finally:release.set();thread.join(10)
    assert not thread.is_alive() and result[0]['status']=='ACTIVE'


def test_restart_and_user_isolation(tmp_path):
    clk=Clock();c=RelayCollector(ROOT,tmp_path/'db',clock=clk,actor='test_fixture');a=c.create('task_005');b=c.create('task_006')
    c.action(a['session_id'],'complete_reading');c.action(a['session_id'],'answer',{'choice':1})
    assert not stored(c,b['session_id'])['data']['state']['records']
    clk.t+=3;c.action(a['session_id'],'pause');new=Clock();new.epoch='restart'
    d=RelayCollector(ROOT,c.database,clock=new,actor='test_fixture');s=d.action(a['session_id'],'resume')
    assert s['completed']==c.get(a['session_id'])['completed'] and s['outcome']=='pass'
    assert d.get(b['session_id'])['elapsed_seconds'] is None


def test_evaluator_bridge_no_false_human_pass_or_time_override(tmp_path):
    c=RelayCollector(ROOT,tmp_path/'db',clock=Clock(),actor='test_fixture');s=c.create('task_003');sid=s['session_id']
    c.action(sid,'complete_reading');c.action(sid,'answer',{'choice':0});c.clock.t+=12
    c.action(sid,'submit',{'response':json.dumps(dict(outputs={},references=[],explanation='fixture deliberate wrong answer'))})
    job=ROOT/'tmp'/('B06-grade-test-'+uuid.uuid4().hex)
    r=assess(c.database,sid,job,key=ROOT/'benchmarks/B/dev_response_keys.json')
    assert r['status']=='SCORED' and r['success'] is False and r['elapsed_seconds']==12 and r['review_count']==0
    v=c.get(sid);assert v['assessment']['input_response_sha256']==r['input_response_sha256']
    assert 'key_sha256' not in v['assessment'] and not (job/'private_keys.json').exists()
    assert stored(c,sid)['success'] is None  # Raw observation retained; separate assessment receipt.
    counts=export_assessed(c.database,tmp_path/'assessed-export','test_fixture')
    exported=json.loads((tmp_path/'assessed-export/assessments.json').read_text(encoding='utf-8'))
    assert counts['assessment_records']==1 and exported[0]['assessment']['success'] is False
    assert exported[0]['participant']!=stored(c,sid)['participant'] and audit(tmp_path/'assessed-export')['passed']


@pytest.mark.parametrize('tid',['task_001','task_002'])
def test_patch_submission_evaluator_remains_pending_for_real_review(tmp_path,tid):
    from scripts.B.evaluation.dev_fixtures import create_fixture
    fixture=create_fixture(tid,tmp_path/'patch')
    files={p.name:p.read_text(encoding='utf-8') for p in fixture.iterdir() if p.is_file()}
    c=RelayCollector(ROOT,tmp_path/'db',actor='test_fixture');s=c.create(tid);sid=s['session_id']
    c.action(sid,'complete_reading');c.action(sid,'answer',{'choice':0})
    c.action(sid,'submit',{'response':json.dumps({'files':files})})
    r=assess(c.database,sid,ROOT/'tmp'/('B06-patch-test-'+uuid.uuid4().hex))
    assert r['status']=='PENDING' and r['automated_score']==7 and r['success'] is None
    assert c.get(sid)['assessment']['review_count']==0


def test_restart_of_pending_plan_fails_without_duplicate_payment(tmp_path):
    clk=Clock();c=RelayCollector(ROOT,tmp_path/'db',clock=clk,actor='test_fixture');s=c.create();sid=s['session_id']
    with c.connect() as db:
        raw=stored(c,sid);c.schedule(db,raw,'replan')
    new=Clock();new.epoch='new-process'
    d=RelayCollector(ROOT,c.database,clock=new,actor='test_fixture',b1_config=config(),meter=SpendMeter(5),transport=transport)
    recovered=d.get(sid)
    assert recovered['status']=='FAILED' and recovered['elapsed_seconds'] is None
    assert d.meter.reserved==0 and len(d.traces(sid))==1


def test_http_access_boundary_and_twelve_public_tasks(tmp_path):
    c=RelayCollector(ROOT,tmp_path/'db',actor='test_fixture');server=make_server(c,0)
    t=threading.Thread(target=server.serve_forever,daemon=True);t.start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        tasks=json.load(urlopen(base+'/api/tasks'));assert len(tasks)==12
        assert 'answer' not in json.dumps(tasks)
        with pytest.raises(HTTPError) as err:urlopen(Request(base+'/api/start',data=b'{}',headers={'Content-Type':'application/json'}))
        assert err.value.code==403
        for path in ('/private_evaluation/keys.json','/../tmp/deepseek-key.dpapi'):
            with pytest.raises(HTTPError) as err:urlopen(base+path)
            assert err.value.code==404
    finally:server.shutdown();server.server_close();t.join()
