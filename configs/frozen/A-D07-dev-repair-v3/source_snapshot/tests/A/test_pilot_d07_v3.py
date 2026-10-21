"""Development extension acceptance: real/fixture provenance, sealed budget control."""
import copy
import json
from pathlib import Path
import re
import threading
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import pytest
from codecompass.app.experiment import digest
from codecompass.app.pilot_d07_v3 import Pilot,bank,VERSION
from scripts.A.cases_d07 import Clock
from scripts.A.serve_d07_v3 import make_server
ROOT=Path(__file__).resolve().parents[2]

def stored(pilot,sid):
    with pilot.connect() as db:return json.loads(db.execute('select value from cases where id=?',(sid,)).fetchone()[0])

def begin(tmp_path,*,actor='test_fixture'):
    p=Pilot(ROOT,tmp_path/'db.sqlite3',actor=actor,clock=Clock());v=p.create(True)
    return p,v

def history(p,v,choices=None):
    return p.action(v['id'],'history',dict(read=True,choices=choices or [q['answer'] for q in p.items[:5]]))

def test_open_gate_is_real_replan_with_equal_paid_control(tmp_path):
    p,v=begin(tmp_path);v=history(p,v);before=stored(p,v['id']);assert len(before['data']['state']['records'])==5
    assert v['spent']==10 and v['completed']==['u_positive_int']
    assert len(v['items'])==1 and v['items'][0]['item_id']==p.items[5]['item_id']
    assert 'answer' not in json.dumps(v) and 'lower_bound' not in json.dumps(v)
    gate=before['before']['Ours']['gate']['python.iterator_protocol'];assert not gate['mastered']
    assert gate['lower_bound']==pytest.approx(.1**(1/6))
    v=p.action(v['id'],'diagnosis',{'choice':p.items[5]['answer']});s=stored(p,v['id'])
    assert v['status']=='DONE' and v['spent']==11 and v['route_changed']
    assert s['completed']==['u_positive_int'] and s['before']==before['before'] and len(s['answers'])==6
    for method in ('Ours','B2'):
        assert set(s['before'][method]['route'])=={'u_iterable','u_windowed_iter'}
        assert s['after'][method]['route']==['u_windowed_iter']
        assert s['no_feedback'][method]['route']==s['before'][method]['route']
        assert s['after'][method]['audit']['total_if_executed']==50
        assert s['no_feedback'][method]['audit']['total_if_executed']==66
        assert s['after'][method]['gate']['python.iterator_protocol']['lower_bound']==pytest.approx(.1**(1/7))
    assert all(e['is_fixture'] for e in s['data']['state']['records'])
    previous=None
    for e in s['events']:
        assert e['version']==VERSION and e['ui_version']==VERSION and e['previous_hash']==previous
        assert e['hash']==digest({k:v for k,v in e.items() if k!='hash'});previous=e['hash']
    assert next(e['seq'] for e in s['events'] if e['kind']=='before_plan_sealed')<next(e['seq'] for e in s['events'] if e['kind']=='diagnosis_presented')

@pytest.mark.parametrize('wrong',range(6))
def test_each_wrong_item_is_preserved_without_retry_or_gate(tmp_path,wrong):
    p,v=begin(tmp_path);answers=[q['answer'] for q in p.items];answers[wrong]=(answers[wrong]+1)%4
    v=history(p,v,answers[:5]);v=p.action(v['id'],'diagnosis',{'choice':answers[5]});s=stored(p,v['id'])
    assert v['status']=='DONE' and not v['route_changed'] and len(s['answers'])==6
    assert not s['after']['Ours']['gate']['python.iterator_protocol']['mastered']
    count=len(s['events']);p.action(v['id'],'diagnosis',{'choice':p.items[5]['answer']});assert len(stored(p,v['id'])['events'])==count
    with pytest.raises(ValueError):p.create(True)

def test_protocol_boundaries_and_pause_survive(tmp_path):
    p,v=begin(tmp_path)
    for action,payload in [('diagnosis',{'choice':0}),('history',{'read':False,'choices':[0]*5}),('history',{'read':True,'choices':[True]*5})]:
        with pytest.raises(ValueError):p.action(v['id'],action,payload)
    p.clock.t+=10;p.action(v['id'],'pause',{});before=stored(p,v['id'])['elapsed'];p.clock.t+=100
    with pytest.raises(ValueError):p.action(v['id'],'history',{'read':True,'choices':[0]*5})
    p.action(v['id'],'resume',{});assert stored(p,v['id'])['elapsed']==before
    v=history(p,v)
    assert len(stored(p,v['id'])['answers'])==5
    with pytest.raises(ValueError):p.action(v['id'],'diagnosis',{})
    with pytest.raises(ValueError):p.action(v['id'],'history',{'read':True,'choices':[0]*5})
    v=p.action(v['id'],'diagnosis',{'choice':None});assert v['status']=='DONE' and not v['route_changed']

def test_human_marker_clock_restart_and_time_cap(tmp_path):
    p,v=begin(tmp_path,actor='human_manual');v=history(p,v)
    assert not stored(p,v['id'])['data']['request']['is_fixture']
    assert all(not e['is_fixture'] for e in stored(p,v['id'])['data']['state']['records'])
    p.clock.epoch='new';assert p.get(v['id'])['status']=='FAILED'
    assert p.get(v['id'])['elapsed'] is None

def test_timeout_does_not_accept_late_answers(tmp_path):
    p,v=begin(tmp_path);p.clock.t+=1501;v=history(p,v)
    assert v['status']=='TIMED_OUT' and stored(p,v['id'])['answers']==[]

def test_skip_is_missing_not_scored_failure_or_fake_evidence(tmp_path):
    p,v=begin(tmp_path);v=history(p,v,[None]*5);v=p.action(v['id'],'diagnosis',{'choice':None});s=stored(p,v['id'])
    assert v['status']=='DONE' and not v['route_changed'] and s['spent']==11
    assert s['data']['state']['records']==[] and all(a['missing'] and a['outcome'] is None for a in s['answers'])
    assert s['events'][-2]['kind']=='diagnosis_missing'

def test_diagnosis_clock_excludes_history_search_but_total_includes_all_search(tmp_path,monkeypatch):
    import codecompass.app.pilot_d07_v3 as module
    p,v=begin(tmp_path);original=module.plans
    def slow(*args,**kwargs):
        p.clock.t+=3
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'plans',slow)
    v=history(p,v);assert stored(p,v['id'])['diagnosis_started']==3
    p.clock.t+=7
    p.action(v['id'],'diagnosis',{'choice':p.items[5]['answer']})
    s=stored(p,v['id']);assert s['diagnosis_duration_seconds']==7 and s['elapsed']==16
    assert s['diagnosis_metrics']['switch_cost']==0 and s['diagnosis_metrics']['removed_units']==['u_iterable']

@pytest.mark.parametrize('stage',['history','diagnosis'])
@pytest.mark.parametrize('fault',['TIMEOUT','exception'])
def test_planning_failure_never_erases_or_allows_changed_answers(tmp_path,monkeypatch,stage,fault):
    import codecompass.app.pilot_d07_v3 as module
    p,v=begin(tmp_path)
    if stage=='diagnosis':v=history(p,v)
    def broken(*args,**kwargs):
        if fault=='exception':raise OSError('isolated test failure')
        return {'status':'TIMEOUT'}
    monkeypatch.setattr(module,'safe_remaining',broken)
    v=history(p,v) if stage=='history' else p.action(v['id'],'diagnosis',{'choice':p.items[5]['answer']})
    s=stored(p,v['id']);accepted=5 if stage=='history' else 6
    assert v['status']=='FAILED' and len(s['answers'])==accepted and s['spent']==5+accepted
    assert all(a['outcome']=='pass' for a in s['answers'])
    assert s['events'][-1]['kind']=='planning_failure'
    saved=copy.deepcopy(s)
    p.action(v['id'],stage,{'read':True,'choices':[None]*5,'choice':None})
    assert stored(p,v['id'])==saved

def test_http_omits_scoring_keys_and_protects_post(tmp_path):
    p=Pilot(ROOT,tmp_path/'http.db',actor='test_fixture',clock=Clock());server=make_server(p,0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
    try:
        html=urlopen(base).read().decode();token=re.search(r'name="session-token" content="([^"]+)"',html).group(1)
        with pytest.raises(HTTPError) as err:urlopen(Request(base+'/api/start',data=b'{"consent":true}'))
        assert err.value.code==403
        v=json.load(urlopen(Request(base+'/api/start',data=b'{"consent":true}',headers={'X-Session-Token':token,'Content-Type':'application/json'})))
        assert len(v['items'])==5 and not any('answer' in q or 'oracle_output' in q for q in v['items'])
        with pytest.raises(HTTPError):urlopen(base+'/bank.json')
        assert urlopen(base+'/app.js').status==200
    finally:server.shutdown();server.server_close();thread.join()
