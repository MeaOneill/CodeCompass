from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import pytest
from scripts.B.comparison.b1 import PersistentSpendMeter, SpendMeter, run_b1, api_transport
from scripts.B.run_d04 import cases
from scripts.B.comparison.adapters import public_packet
ROOT=Path(__file__).resolve().parents[2]


def config():
    return json.loads((ROOT/'configs/B/D04_deepseek_authorized.json').read_text(encoding='utf-8'))['b1']


def test_cny_accounting_no_currency_conversion_or_fake_dollars():
    c=config()
    raw={'model':'deepseek-flash','status':'completed','usage':{'input_tokens':100,'output_tokens':20},
         'output':[{'type':'message','content':[{'type':'output_text','text':'{"ordered_units":[]}'}]}]}
    r=run_b1({},c,'fixture',SpendMeter(5),transport=lambda *args:raw)
    assert r['status']=='PARSED' and r['calls'][0]['estimated_cost_usd'] is None
    assert r['calls'][0]['estimated_cost_cny']==pytest.approx(.00036)
    assert r['calls'][0]['currency']=='CNY' and r['transport_is_fixture']


def test_durable_budget_survives_restarts_and_concurrent_calls(tmp_path):
    path=tmp_path/'budget.sqlite3'
    def reserve(_):return PersistentSpendMeter(path,5,'CNY').reserve(.25)
    with ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(reserve,range(30)))
    assert sum(results)==20
    meter=PersistentSpendMeter(path,5,'CNY')
    assert meter.reserved==5 and not meter.reserve(.25)
    with pytest.raises(ValueError,match='authorization differs'):PersistentSpendMeter(path,10,'CNY')


def test_input_limit_stops_before_call_or_reservation():
    c=config();c['max_input_bytes']=3;meter=SpendMeter(5)
    def forbidden(*args):raise AssertionError('no transport call allowed')
    r=run_b1({},c,'fixture',meter,transport=forbidden)
    assert not r['attempted'] and r['status']=='INPUT_LIMIT_NOT_RUN' and meter.reserved==0


def test_actual_public_inputs_below_declared_limit():
    c=config();prompt=(ROOT/'configs/B/B1_direct_v1.txt').read_text(encoding='utf-8')
    for f in cases():
        context,_,_,_=public_packet(ROOT,f)
        assert len((prompt+'\nCONTEXT_JSON\n'+json.dumps(context,ensure_ascii=False,sort_keys=True)).encode())<c['max_input_bytes']


def test_only_reviewed_endpoints_allowed():
    c=config();c['endpoint']='https://example.invalid/responses'
    with pytest.raises(ValueError,match='reviewed'):api_transport({},c)


def test_deepseek_wire_request_fixture_has_no_key_in_payload(monkeypatch):
    import scripts.B.comparison.b1 as module
    c=config();monkeypatch.setenv('DEEPSEEK_API_KEY','fixture-key-not-real')
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):return b'{"model":"deepseek-flash"}'
    class Opener:
        def open(self,request,timeout):
            assert request.full_url=='https://api.deepseek.com/responses'
            assert request.get_header('Authorization')=='Bearer fixture-key-not-real'
            assert b'fixture-key-not-real' not in request.data
            return Response()
    monkeypatch.setattr(module,'build_opener',lambda *args:Opener())
    assert api_transport({'model':'deepseek-flash','input':'fixture'},c)['model']=='deepseek-flash'
