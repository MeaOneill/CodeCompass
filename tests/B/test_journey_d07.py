import copy
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import sys
import threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import pytest
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from codecompass.app.journey_d07 import JourneyCollector,PRETEST,RETEST,CROSS_ID,cross_data
from codecompass.learner import mastery_gate,planning_rows
from scripts.B.serve_d07 import make_server
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit


class Clock:
    def __init__(self):self.t=100.;self.epoch='fixture'
    def sample(self):return dict(epoch=self.epoch,mono=self.t,wall=(datetime(2026,10,21,tzinfo=timezone.utc)+timedelta(seconds=self.t)).isoformat())


def enrolled(c):
    p=c.enroll(True)['participant'];c.pretest(p,[q['answer'] for q in PRETEST]);return p


def test_review_is_read_only_and_unavailable_during_independent_quiz(c):
    user=enrolled(c);s=c.create('task_002',participant=user);sid=s['session_id'];unit=s['route'][0]
    c.action(sid,'complete_reading')
    with pytest.raises(ValueError,match='独立小题'):c.review_material(sid,unit)
    c.action(sid,'answer',{'choice':0})
    before=stored(c,sid);profile=c.profile(user)
    r=c.review_material(sid,unit)
    assert r['materials'] and r['mastery_granted'] is False
    assert before==stored(c,sid) and profile['revision']==c.profile(user)['revision']
    with pytest.raises(ValueError):c.review_material(sid,'../../private')


def stored(c,sid):
    with c.connect() as db:return json.loads(db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()[0])


def finish(c,user,tid='task_002',choice=1,method='Ours'):
    s=c.create(tid,method,user);sid=s['session_id'];assert s['status']=='ACTIVE',c.traces(sid)
    c.clock.t+=2;c.action(sid,'complete_reading');c.clock.t+=3;s=c.action(sid,'answer',{'choice':choice})
    assert s['status']=='ACTIVE',c.traces(sid)
    s=c.action(sid,'submit',{'response':json.dumps({'files':{},'outputs':{},'references':[],'explanation':'Explicit engineering fixture, not a human task answer'})})
    return s


@pytest.fixture
def c(tmp_path):return JourneyCollector(ROOT,tmp_path/'db.sqlite3',clock=Clock(),actor='test_fixture')


@pytest.mark.parametrize('method',['Ours','B2'])
def test_full_two_repository_flow_with_one_authority(c,tmp_path,method):
    user=enrolled(c);s=finish(c,user,method=method)
    p=c.profile(user);assert p['evidence_count']==5 and len(p['sessions'])==1
    mapped=c.transfer(user);assert mapped['source_available'] and mapped['source_evidence_ids'] and not mapped['posterior_copied']
    d=cross_data(ROOT,user,True)
    with c.connect() as db:state=c._profile(db,user)['ledger']
    before=mastery_gate(state,d['request']['snapshot_id'],['python.iterator_protocol'],allow_simulated=True)
    assert before['python.iterator_protocol']['lower_bound'] is None and not before['python.iterator_protocol']['mastered']
    target=finish(c,user,CROSS_ID,method=method);p=c.profile(user)
    assert p['evidence_count']==6 and p['transfers'][0]['target_retest_recorded']
    assert p['measured_active_seconds']==10 and p['within_90_minutes'] is True
    assert p['actual_two_people_verified'] is False and p['formal_participant'] is False
    after=stored(c,target['session_id'])['data']['state']
    assert len(planning_rows(after,d['request']['snapshot_id'],allow_simulated=True)[0]['evidence_ids'])==1
    assert len(planning_rows(after,'boltons-4e5faa3d7e40',allow_simulated=True)[0]['evidence_ids'])==1
    export(c.database,tmp_path/'export','test_fixture');assert audit(tmp_path/'export')['passed']


def test_refresh_transfer_repeat_and_read_do_not_add_mastery(c):
    user=enrolled(c);s=finish(c,user);n=c.profile(user)['evidence_count']
    c.transfer(user);rev=c.profile(user)['revision'];c.transfer(user)
    for _ in range(4):c.profile(user);c.get(s['session_id']);c.issues(s['session_id'])
    assert c.profile(user)['evidence_count']==n and c.profile(user)['revision']==rev
    with pytest.raises(ValueError):c.pretest(user,[0,0,0,0])
    with pytest.raises(ValueError):c.create('task_002','Ours',user)


def test_missing_pretest_not_wrong_and_repetition_rejected(c):
    user=c.enroll(True)['participant'];p=c.pretest(user,[None,None,None,None])
    assert p['evidence_count']==0 and len(p['pretest_timing']['missing_items'])==4
    with pytest.raises(ValueError):c.pretest(user,[1,1,0,2])
    s=c.create(participant=user);c.action(s['session_id'],'complete_reading');c.action(s['session_id'],'answer',{'choice':0})
    assert c.profile(user)['evidence_count']==1
    with pytest.raises(ValueError):c.action(s['session_id'],'answer',{'choice':1})


def test_profile_restart_recovery_and_user_isolation(c):
    a=enrolled(c);b=enrolled(c);s=finish(c,a);c.transfer(a)
    next_clock=Clock();next_clock.epoch='newprocess'
    restored=JourneyCollector(ROOT,c.database,clock=next_clock,actor='test_fixture')
    assert restored.profile(a)['history']==c.profile(a)['history']
    assert restored.profile(a)['transfers']==c.profile(a)['transfers']
    assert restored.profile(a)['journey_wall_seconds'] is None
    assert restored.profile(b)['evidence_count']==4 and not restored.profile(b)['transfers']
    assert restored.get(s['session_id'])['status']=='SUBMITTED'
    wrong=JourneyCollector(ROOT,c.database,clock=next_clock,actor='human_manual')
    with pytest.raises(ValueError):wrong.profile(a)


def test_timeouts_restart_and_pause_do_not_fabricate_zero(c):
    user=enrolled(c);s=c.create(participant=user,limit_seconds=4);sid=s['session_id'];c.clock.t+=5
    assert c.get(sid)['status']=='TIMED_OUT'
    assert c.profile(user)['measured_active_seconds']==5
    b=enrolled(c);v=c.create(participant=b);c.clock.t+=3;c.action(v['session_id'],'pause');c.clock.t+=50
    assert c.get(v['session_id'])['elapsed_seconds']==3
    c.action(v['session_id'],'resume');c.clock.epoch='restarted';s=c.get(v['session_id'])
    assert s['elapsed_seconds'] is None and s['status']=='PAUSED'
    assert c.profile(b)['measured_active_seconds'] is None


def test_only_one_active_session_and_two_round_cap(c):
    user=enrolled(c);a=c.create(participant=user)
    with pytest.raises(ValueError):c.create(CROSS_ID,participant=user)
    with pytest.raises(ValueError):c.transfer(user)
    c.action(a['session_id'],'withdraw');s=c.create(CROSS_ID,participant=user);c.action(s['session_id'],'withdraw')
    with pytest.raises(ValueError):c.create('task_003',participant=user)


def test_profile_cache_and_chain_tampering_rejected(c):
    user=enrolled(c);s=c.create(participant=user)
    with c.connect() as db:
        raw=stored(c,s['session_id']);raw['data']['state']['records']=[];c.save(db,raw)
    with pytest.raises(ValueError):c.get(s['session_id'])
    with c.connect() as db:db.execute('DELETE FROM profile_events WHERE user=? AND seq=1',(user,))
    with pytest.raises(ValueError):c.profile(user)


def test_consent_and_pretest_required_no_oracle_in_payload(c):
    with pytest.raises(ValueError):c.enroll(False)
    with pytest.raises(ValueError):c.create()
    r=c.enroll(True);assert all('answer' not in q for q in r['questions'])
    with pytest.raises(ValueError):c.create(participant=r['participant'])
    c.pretest(r['participant'],[None]*4);s=c.create(CROSS_ID,participant=r['participant']);sid=s['session_id']
    s=c.action(sid,'complete_reading');assert 'answer' not in s['quiz'] and s['quiz']['item_id']=='B07-more-counter-v1'


def test_issue_history_and_other_repository_absence_are_explicit(c):
    user=enrolled(c);s=finish(c,user);r=c.issues(s['session_id'])
    assert r['source_mode']=='FIXED_HISTORICAL_SNAPSHOT' and r['current_issue_state_verified'] is False
    assert all(v['state_at_capture']=='closed' for v in r['historical'])
    s=c.create(CROSS_ID,participant=user);r=c.issues(s['session_id'])
    assert r['source_mode']=='UNAVAILABLE' and not r['candidates']


def test_http_origin_private_path_and_server_side_scoring(c):
    server=make_server(c,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        body=urlopen(base).read().decode();token=body.split('name="session-token" content="')[1].split('"')[0]
        rows=json.load(urlopen(base+'/api/tasks'));assert len(rows)==13 and len({r['repo'] for r in rows})==2
        with pytest.raises(HTTPError) as err:urlopen(Request(base+'/api/enroll',data=b'{"consent":true}'))
        assert err.value.code==403
        with pytest.raises(HTTPError) as err:urlopen(base+'/private_evaluation/B-D06/v0.1-candidate/keys.json')
        assert err.value.code==404
        req=Request(base+'/api/enroll',data=b'{"consent":true}',headers={'X-Session-Token':token,'Content-Type':'application/json'})
        p=json.load(urlopen(req));assert all('answer' not in q for q in p['questions'])
    finally:server.shutdown();server.server_close();thread.join()


def test_raw_choices_and_server_scores_bound_to_authoritative_ledger(c):
    user=enrolled(c);s=finish(c,user,choice=0)
    with c.connect() as db:
        rows=[json.loads(r[0]) for r in db.execute('SELECT value FROM answers WHERE user=?',(user,))]
    assert len(rows)==5 and all(r['hash'] and r['source_digest']==c.source_digest for r in rows)
    q=next(r for r in rows if r['item_id']=='B05-iterator-next-v1')
    assert q['choice']==0 and q['outcome']=='fail' and q['session_id']==s['session_id']
    assert c.profile(user)['history'][-1]['concepts'][0]['beta']==2


def test_global_ledger_tampering_is_not_accepted_as_new_authority(c):
    user=enrolled(c)
    with c.connect() as db:
        p=c._profile(db,user);p['ledger']['records'][0]['outcome']='fail'
        db.execute('UPDATE profiles SET value=? WHERE user=?',(json.dumps(p),user))
    with pytest.raises(ValueError):c.profile(user)


def test_cross_case_has_real_take_helper_and_matching_explanation(c):
    user=enrolled(c);s=c.create(CROSS_ID,participant=user)
    assert 'takewhile' not in ' '.join(s['task']['requirements'])
    assert any(m['source_span']['path']=='more_itertools/recipes.py' and 'def take(' in m['text'] for m in s['source_context'])
    assert s['protocol_version']=='B-D07-development-journey-4'


def test_planner_failure_keeps_original_choice_and_accepted_evidence(c,monkeypatch):
    user=enrolled(c);s=c.create(participant=user);sid=s['session_id'];c.action(sid,'complete_reading')
    def broken(_):raise RuntimeError('fixture-only planning failure')
    monkeypatch.setattr(c,'calculate',broken)
    failed=c.action(sid,'answer',{'choice':1})
    assert failed['status']=='FAILED' and failed['quiz_done']
    assert c.profile(user)['evidence_count']==5
    with c.connect() as db:
        original=json.loads(db.execute('SELECT value FROM answers WHERE user=? AND item=?',(user,'B05-iterator-next-v1')).fetchone()[0])
    assert original['choice']==1 and original['outcome']=='pass'
    assert c.traces(sid)[-1]['status']=='PLANNING_ERROR'


def test_concurrent_quiz_update_and_profile_read_use_one_snapshot(c,monkeypatch):
    import time
    user=enrolled(c);s=c.create(participant=user);sid=s['session_id'];c.action(sid,'complete_reading')
    reader_ready=threading.Event();writer_started=threading.Event();result=[];errors=[];reader=threading.get_ident();original=c._profile
    def observed(db,uid):
        value=original(db,uid)
        if threading.get_ident()==reader:
            reader_ready.set();assert writer_started.wait(3);time.sleep(.05)
        return value
    monkeypatch.setattr(c,'_profile',observed)
    def write():
        try:
            assert reader_ready.wait(3);writer_started.set();result.append(c.action(sid,'answer',{'choice':1}))
        except Exception as e:errors.append(type(e).__name__)
    worker=threading.Thread(target=write);worker.start()
    snapshot=c.profile(user);worker.join(8)
    assert not worker.is_alive() and not errors and result[0]['status']=='ACTIVE'
    assert snapshot['evidence_count']==4 and snapshot['revision']==2
    assert c.profile(user)['evidence_count']==5


@pytest.mark.parametrize('question',[*PRETEST,RETEST],ids=lambda q:q['item_id'])
def test_question_oracle_matches_independent_python_execution(question):
    import contextlib,io
    output=io.StringIO()
    with contextlib.redirect_stdout(output):exec(question['code'],{})
    assert output.getvalue().strip()==question['choices'][question['answer']]
