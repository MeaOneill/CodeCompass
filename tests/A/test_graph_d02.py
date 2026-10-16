import copy
import hashlib
import json
from pathlib import Path
import pytest
from codecompass.graph import extract_snapshot, read_snapshot, make_span, validate_span, hard_edges, cyclic_components
from codecompass.graph.provenance import safe_source


def snapshot(tmp_path, files):
    records=[]
    for name,data in files.items():
        if isinstance(data,str):data=data.encode()
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        records.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()})
    records.sort(key=lambda x:x['path'])
    return {'snapshot_id':'fixture_snapshot','commit':'a'*40,'files':records,'hash':hashlib.sha256(json.dumps(records,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'snapshot_scope':'fixture_only'}


def test_static_syntax_does_not_execute_and_tracks_nested_scope(tmp_path):
    text='import os as system\nfrom .helpers import thing as local\nraise RuntimeError("must not execute")\nclass C:\n    async def f(self):\n        import math\n        def nested():\n            return unknown()\n        return getattr(self, "dynamic")()\n'
    s=snapshot(tmp_path,{'module.py':text})
    # Unmanifested files are never enumerated.
    (tmp_path/'rogue.py').write_text('this is invalid syntax')
    g=extract_snapshot(tmp_path,s)
    assert [x['path'] for x in g['source_manifest']]==['module.py']
    assert {'module','class','async_function','function','import_reference'} <= {x['kind'] for x in g['nodes']}
    imports=[e for e in g['edges'] if e['kind']=='imports']
    assert len(imports)==3 and next(e for e in imports if e['symbol']=='thing')['level']==1
    calls=[e for e in g['edges'] if e['kind']=='call_unknown']
    assert len(calls)==4 and all(e['to'] is None and e['resolution']=='unknown' for e in calls)
    assert any('C.f.nested@' in e['from'] for e in calls)
    ids={x['id'] for x in g['nodes']}
    assert all(e['from'] in ids and (e['to'] is None or e['to'] in ids) for e in g['edges'])
    assert g==extract_snapshot(tmp_path,s)


def test_rebound_simple_name_is_not_guessed(tmp_path):
    s=snapshot(tmp_path,{'x.py':'def f():\n    pass\nf = supplied\nf()\n'})
    calls=[e for e in extract_snapshot(tmp_path,s)['edges'] if e['kind']=='call_unknown']
    assert len(calls)==1 and calls[0]['to'] is None


def test_decorators_crlf_and_span_integrity(tmp_path):
    s=snapshot(tmp_path,{'x.py':b'@decorate\r\ndef f():\r\n    return 1\r\n'})
    g=extract_snapshot(tmp_path,s);node=next(n for n in g['nodes'] if n['kind']=='function')
    assert node['source_span']['start_line']==1 and node['source_span']['end_line']==3
    contents=read_snapshot(tmp_path,s);assert validate_span(node['source_span'],s,contents)
    bad=copy.deepcopy(node['source_span']);bad['content_hash']='0'*64
    with pytest.raises(ValueError):validate_span(bad,s,contents)
    with pytest.raises(ValueError):make_span(s['snapshot_id'],'x.py','a\n',2,1)


@pytest.mark.parametrize('bad',['../x.py','/x.py','C:/x.py','a\\x.py',''])
def test_source_paths_cannot_escape(tmp_path,bad):
    with pytest.raises(ValueError):safe_source(tmp_path,bad)


def test_tamper_and_duplicate_rejected(tmp_path):
    s=snapshot(tmp_path,{'x.py':'pass\n'});(tmp_path/'x.py').write_bytes(b'fail\n')
    with pytest.raises(ValueError):read_snapshot(tmp_path,s)
    s=snapshot(tmp_path,{'x.py':'pass\n'});s['files']*=2
    s['hash']=hashlib.sha256(json.dumps(s['files'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    with pytest.raises(ValueError):read_snapshot(tmp_path,s)


def test_parse_errors_and_empty_files_are_visible(tmp_path):
    s=snapshot(tmp_path,{'bad.py':'def broken(\n','encoding.py':b'\xff','empty.py':b''})
    g=extract_snapshot(tmp_path,s)
    assert {x['path']:x['status'] for x in g['source_manifest']}=={'bad.py':'parse_error','encoding.py':'parse_error','empty.py':'empty'}
    assert g['nodes']==[]


def unit(name,prereq=None,hard=False,kind='teaching_judgment',approved=False):
    p={'kind':kind,'review_status':'approved' if approved else 'pending','reviewer':'fixture_human' if approved else None,'evidence':['human-review:fixture_only'] if approved else ['fixture candidate']}
    return {'id':name,'prerequisites':[] if prereq is None else [{'unit_id':prereq,'relation_type':'teaching_prerequisite','hard':hard,'provenance':p}]}


def test_teaching_pending_soft_hard_fail_closed():
    assert hard_edges([unit('a'),unit('b','a')])==[]
    with pytest.raises(ValueError):hard_edges([unit('a'),unit('b','a',True)])
    assert hard_edges([unit('a'),unit('b','a',True,approved=True)])==[('a','b')]
    with pytest.raises(ValueError):hard_edges([unit('a'),unit('b','a',True,kind='model_candidate',approved=True)])


def test_cycles_reported_not_deleted():
    assert cyclic_components({'a','b','s'},[('s','a'),('a','b'),('b','a')])==[['a','b']]
    with pytest.raises(ValueError):hard_edges([unit('a','b',True,approved=True),unit('b','a',True,approved=True)])
    with pytest.raises(ValueError):hard_edges([unit('a','missing')])


def test_real_snapshot_all_spans_and_teaching_pending():
    root=Path(__file__).resolve().parents[2]
    s=json.loads((root/'benchmarks/sources/boltons/snapshot.json').read_text(encoding='utf-8'))
    bundle=root/'benchmarks/sources/boltons';g=extract_snapshot(bundle,s);contents=read_snapshot(bundle,s)
    assert len(g['source_manifest'])==2 and all(x['status']=='parsed' for x in g['source_manifest'])
    for record in g['nodes']+g['edges']:assert validate_span(record['source_span'],s,contents)
    assert hard_edges(json.loads((root/'benchmarks/dev/task_001_units.json').read_text(encoding='utf-8')))==[]
