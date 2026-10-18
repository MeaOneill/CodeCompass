import copy
from datetime import datetime,timezone,timedelta
import io
import json
from pathlib import Path
import sys
import threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from codecompass.app.experiment import Collector, digest, METHODS
from codecompass.app.diagnostic_items import ITEMS
from codecompass.planner.adaptive_validator import verify_session
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit
from scripts.B.serve_d05 import make_server


class FakeClock:
    epoch='test-process'
    def __init__(self):self.t=100.;self.offset=0
    def sample(self):return dict(epoch=self.epoch,mono=self.t,wall=(datetime(2026,10,18,tzinfo=timezone.utc)+timedelta(seconds=self.t+self.offset)).isoformat())


@pytest.fixture
def collector(tmp_path):
    return Collector(ROOT,tmp_path/'sessions.sqlite3',clock=FakeClock(),actor='test_fixture')


def stored(c,sid):
    with c.connect() as db:return json.loads(db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()[0])


@pytest.mark.parametrize('method',METHODS)
@pytest.mark.parametrize('tid',['task_001','task_002'])
def test_real_source_method_roundtrip(collector,tmp_path,method,tid):
    c=collector;s=c.create(tid,method);sid=s['session_id']
    assert s['materials'] and s['task']['repo_commit'].startswith('4e5faa')
    c.clock.t+=3;c.action(sid,'complete_reading')
    assert stored(c,sid)['data']['state']['records']==[]
    c.action(sid,'quiz');c.clock.t+=2
    s=c.action(sid,'answer',{'choice':ITEMS[tid]['answer']})
    assert s['outcome']=='pass' and s['quiz_done']
    assert len(stored(c,sid)['data']['state']['records'])==1
    with pytest.raises(ValueError):c.action(sid,'answer',{'choice':ITEMS[tid]['answer']})
    if method=='Ours':assert verify_session(ROOT,stored(c,sid)['adaptive'])['valid']
    s=c.action(sid,'submit',{'response':'Development pipeline check'})
    assert s['status']=='SUBMITTED' and s['success'] is None
    out=tmp_path/'export';export(c.database,out,'test_fixture');assert audit(out)['passed']
    assert audit(out)['manual_flow_passed'] is False  # Agent/fixture flow cannot satisfy human gate.


def test_pause_excludes_time_and_restart_preserves_state(collector):
    c=collector;s=c.create();sid=s['session_id'];c.clock.t+=5;c.action(sid,'pause')
    c.clock.t+=80;s=c.get(sid);assert s['elapsed_seconds']==5
    new=FakeClock();new.epoch='new';c2=Collector(ROOT,c.database,clock=new,actor='test_fixture')
    s=c2.action(sid,'resume');assert s['elapsed_seconds']==5 and not s['missing']
    new.t+=2;assert c2.get(sid)['elapsed_seconds']==7


def test_active_restart_marks_missing_not_negative(collector,tmp_path):
    c=collector;sid=c.create()['session_id'];c.clock.t+=4;c.get(sid)
    new=FakeClock();new.epoch='restarted';new.t=1
    c2=Collector(ROOT,c.database,clock=new,actor='test_fixture');s=c2.get(sid)
    assert s['elapsed_seconds'] is None and s['status']=='PAUSED' and s['observed_seconds']==4
    c2.action(sid,'resume');c2.action(sid,'submit',{'response':'incomplete time retained'})
    export(c.database,tmp_path/'out','test_fixture');assert audit(tmp_path/'out')['passed']


@pytest.mark.parametrize('delta,offset',[(-10,0),(1,-100),(1,100)])
def test_clock_discontinuities(collector,delta,offset):
    c=collector;sid=c.create()['session_id'];c.clock.t+=delta;c.clock.offset=offset;s=c.get(sid)
    assert s['elapsed_seconds'] is None and s['status']=='PAUSED'


def test_timeout_rejects_late_final_and_keeps_nonzero_time(collector,tmp_path):
    c=collector;sid=c.create(limit_seconds=5)['session_id'];c.clock.t+=6
    s=c.action(sid,'submit',{'response':'too late'});assert s['status']=='TIMED_OUT' and s['elapsed_seconds']==6
    export(c.database,tmp_path/'out','test_fixture');rows=json.loads((tmp_path/'out/sessions.json').read_text());assert rows[0]['t_cap_seconds']==5
    assert audit(tmp_path/'out')['passed']


def test_user_isolation_no_answers_in_payload(collector):
    c=collector;a=c.create();b=c.create();assert a['participant']!=b['participant']
    c.action(a['session_id'],'complete_reading');s=c.action(a['session_id'],'quiz')
    assert 'answer' not in json.dumps(s) and 'rubric' not in json.dumps(s)
    c.action(a['session_id'],'answer',{'choice':0})
    assert not stored(c,b['session_id'])['data']['state']['records']
    with pytest.raises(ValueError):c.create('../../private_evaluation')


def test_participant_grouping_export_drops_free_text(collector,tmp_path):
    c=collector;a=c.create();b=c.create(method='B2',participant=a['participant'])
    c.action(a['session_id'],'submit',{'response':'SECRET PERSON TEST'})
    export(c.database,tmp_path/'out','test_fixture')
    text=''.join(p.read_text() for p in (tmp_path/'out').glob('*.json'))
    assert 'SECRET PERSON TEST' not in text and a['participant'] not in text and a['session_id'] not in text
    groups=json.loads((tmp_path/'out/participants.json').read_text());assert len(groups)==1 and groups[0]['sessions']==2
    rows=json.loads((tmp_path/'out/sessions.json').read_text());assert any(r['duration_seconds'] is None for r in rows)
    assert audit(tmp_path/'out')['passed']


def test_export_refuses_tampered_event(collector,tmp_path):
    c=collector;sid=c.create()['session_id']
    with c.connect() as db:
        raw=json.loads(db.execute('SELECT value FROM events WHERE id=? AND seq=1',(sid,)).fetchone()[0]);raw['method']='other'
        db.execute('UPDATE events SET value=? WHERE id=? AND seq=1',(json.dumps(raw),sid))
    with pytest.raises(ValueError):export(c.database,tmp_path/'out','test_fixture')


def test_independent_questions_execute_expected_output():
    from contextlib import redirect_stdout
    for q in ITEMS.values():
        output=io.StringIO()
        with redirect_stdout(output):exec(q['code'],{})
        assert output.getvalue().strip()==q['choices'][q['answer']]


@pytest.mark.parametrize('mutation',['negative_time','identity','fake_success','missing_event','mixed_actor','group'])
def test_export_audit_rejects_tampering(collector,tmp_path,mutation):
    c=collector;s=c.create();c.clock.t+=2;c.action(s['session_id'],'submit',{'response':'fixture'})
    out=tmp_path/'out';export(c.database,out,'test_fixture')
    rows=json.loads((out/'sessions.json').read_text());es=json.loads((out/'events.json').read_text());gs=json.loads((out/'participants.json').read_text())
    if mutation=='negative_time':es[-1]['elapsed_observed']=-1
    elif mutation=='identity':es[-1]['participant']='wrong'
    elif mutation=='fake_success':rows[0]['success']=True
    elif mutation=='missing_event':es.pop()
    elif mutation=='mixed_actor':rows[0]['actor']='human_manual'
    elif mutation=='group':gs[0]['sessions']=9
    # Even when transport hashes are renewed, semantic checks must reject altered records.
    previous=None
    for e in es:
        e['previous_hash']=previous;e['hash']=digest({k:v for k,v in e.items() if k!='hash'});previous=e['hash']
    for name,obj in [('sessions.json',rows),('events.json',es),('participants.json',gs)]:
        (out/name).write_text(json.dumps(obj),encoding='utf-8')
    import hashlib
    m=json.loads((out/'manifest.json').read_text());m['files']={k:hashlib.sha256((out/k).read_bytes()).hexdigest() for k in m['files']}
    (out/'manifest.json').write_text(json.dumps(m),encoding='utf-8')
    assert not audit(out)['passed']


def test_http_boundaries(collector):
    server=make_server(collector,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        page=urlopen(base).read().decode();token=page.split('name="session-token" content="')[1].split('"')[0]
        with pytest.raises(HTTPError) as e:urlopen(Request(base+'/api/start',data=b'{}',headers={'Content-Type':'application/json'}))
        assert e.value.code==403
        req=Request(base+'/api/start',data=b'{}',headers={'X-Session-Token':token,'Content-Type':'application/json','Origin':base})
        data=json.loads(urlopen(req).read());assert data['actor']=='test_fixture'
        with pytest.raises(HTTPError):urlopen(base+'/../../private_evaluation')
        with pytest.raises(HTTPError):urlopen(Request(base+'/api/start',data=b'{}',headers={'X-Session-Token':token,'Origin':'https://evil.example'}))
    finally:server.shutdown();server.server_close();thread.join()
