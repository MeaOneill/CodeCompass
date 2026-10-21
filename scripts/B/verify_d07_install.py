"""Portable, offline HTTP journey replay. A local clone is not a second machine."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import socket
import sqlite3
import sys
import threading
from urllib.request import build_opener,ProxyHandler,Request
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from codecompass.app.journey_d07 import JourneyCollector,PRETEST,CROSS_ID,source_manifest
from codecompass.app.experiment import digest
from scripts.B.serve_d07 import make_server
from scripts.B.audit_journey_d07 import audit
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit as audit_export


def machine_fingerprint():return hashlib.sha256((socket.gethostname()+'|'+platform.system()+'|'+platform.machine()).encode()).hexdigest()


def run(run_id,owner='B',executor=None,compare_machine=None):
    if not run_id.replace('-','').replace('_','').isalnum() or owner not in ('A','B'):raise ValueError('Safe run ID and role required')
    out=ROOT/'experiments'/owner/run_id;out.mkdir(parents=True,exist_ok=False);db=ROOT/'tmp'/(run_id+'.sqlite3')
    if db.exists():raise FileExistsError('Fresh database required')
    c=JourneyCollector(ROOT,db,actor='test_fixture');server=make_server(c,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}';opener=build_opener(ProxyHandler({}));operations=[]
    try:
        html=opener.open(base).read().decode();token=html.split('name="session-token" content="')[1].split('"')[0]
        def call(path,data=None):
            request=Request(base+path,data=None if data is None else json.dumps(data).encode(),
                headers={'Content-Type':'application/json','X-Session-Token':token})
            return json.load(opener.open(request,timeout=40))
        user=call('/api/enroll',dict(consent=True))['participant']
        call('/api/pretest',dict(participant=user,choices=[q['answer'] for q in PRETEST]))
        for tid in ('task_002',CROSS_ID):
            if tid==CROSS_ID:call('/api/transfer',dict(participant=user))
            s=call('/api/start',dict(task=tid,method='Ours',participant=user));sid=s['session_id']
            def action(name,payload=None):return call('/api/action',dict(session_id=sid,action=name,payload=payload))
            action('complete_reading');s=action('answer',dict(choice=1))
            while s['route']:s=action('complete_reading')
            action('pause');action('resume')
            s=action('submit',dict(response=json.dumps(dict(files={},outputs={},references=[],explanation='Explicit offline HTTP fixture, not a human answer'))))
            issues=call('/api/issues?id='+sid)
            if s['status']!='SUBMITTED':raise ValueError('HTTP journey did not finish')
            operations.append(dict(task_id=tid,status=s['status'],source_commit=s['task']['repo_commit'],issue_mode=issues['source_mode']))
        p=call('/api/profile?user='+user)
        if p['evidence_count']!=6 or not p['transfers'][0]['target_retest_recorded']:raise ValueError('Profile/retest not persisted')
        # A new collector reads the same database; no hardcoded server state.
        restored=JourneyCollector(ROOT,db,actor='test_fixture')
        if restored.profile(user)['history']!=p['history']:raise ValueError('Restart profile mismatch')
    finally:server.shutdown();server.server_close();thread.join()
    export(db,out/'fixtures/export','test_fixture');receipt=audit(db,'test_fixture');logs=audit_export(out/'fixtures/export')
    fingerprint=machine_fingerprint()
    result=dict(run_id=run_id,owner=owner,executor=executor,machine_fingerprint_sha256=fingerprint,python=platform.python_version(),
        runtime_source_digest=digest(source_manifest(ROOT)),source_files=source_manifest(ROOT),http_operations=operations,
        profile_restart_verified=True,receipt_audit=receipt,event_audit=logs,actor='test_fixture',
        passed=receipt['passed'] and logs['passed'],compared_machine_fingerprint=compare_machine,
        different_machine_observed=None if compare_machine is None else fingerprint!=compare_machine,
        human_people_verified=False,formal_participants=0,model_calls=0,network_scope='loopback HTTP + fixed local source/Issue cache; no upstream fetch')
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:result[k] for k in ('passed','machine_fingerprint_sha256','different_machine_observed','human_people_verified','model_calls')}))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-id',required=True);p.add_argument('--owner',choices=['A','B'],default='B');p.add_argument('--executor');p.add_argument('--compare-machine');a=p.parse_args()
    raise SystemExit(0 if run(a.run_id,a.owner,a.executor,a.compare_machine)['passed'] else 1)
