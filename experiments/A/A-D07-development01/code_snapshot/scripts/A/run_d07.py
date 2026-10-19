"""Read-only source smoke + explicitly synthetic closed loops, no live model/evaluation keys."""
import argparse,copy,csv,datetime as dt,hashlib,json,platform,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from codecompass.app.relay_v2 import RelayCollector,registry
from codecompass.app.diagnostics_v2 import ITEMS
from codecompass.planner.runtime_d07 import safe_remaining
from codecompass.planner.feedback import start_session,complete_next,apply_feedback
from codecompass.planner.adaptive_validator import verify_session
from scripts.A.cases_d07 import Clock,stored,b1_config,fixture_transport,empty_transport,development_case,add_history
from scripts.A.relay_d07 import StableRelayCollector
from scripts.B.comparison.b1 import SpendMeter
from scripts.B.export_d05 import export
from scripts.B.audit_d05 import audit as event_audit


def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8'))


def plan(d,root=ROOT,**options):
    return safe_remaining(root,d['request'],d['units'],d['state'],d['config'],**options)


def run(out,run_id):
    work=ROOT/'tmp'/run_id;work.mkdir(exist_ok=False)
    summary=[];hashes={};quiz_changes=[]
    c=StableRelayCollector(ROOT,work/'fixtures.sqlite3',actor='test_fixture',clock=Clock(),
        b1_config=b1_config(ROOT),meter=SpendMeter(100),transport=fixture_transport)
    for tid in [r['task_id'] for r in registry(ROOT)['records']]:
        for outcome in ('pass','fail'):
            for method in ('Ours','B2','B1'):
                s=c.create(tid,method);sid=s['session_id'];assert s['status']=='ACTIVE'
                initial=c.traces(sid)[0]['context']
                h=hashlib.sha256(json.dumps(initial,sort_keys=True,allow_nan=False).encode()).hexdigest()
                hashes.setdefault(tid,set()).add(h)
                c.clock.t+=2;s=c.action(sid,'complete_reading');completed=list(s['completed'])
                assert s['phase']=='quiz' and not stored(c,sid)['data']['state']['records']
                correct=ITEMS[tid]['answer'];choice=correct if outcome=='pass' else (correct+1)%len(ITEMS[tid]['choices'])
                c.clock.t+=1;s=c.action(sid,'answer',{'choice':choice})
                assert s['status']=='ACTIVE' and s['completed']==completed and s['outcome']==outcome
                assert len(stored(c,sid)['data']['state']['records'])==1
                assert set(completed).isdisjoint(s['route'])
                changed=s['feedback']['before_route']!=s['feedback']['after_route'];quiz_changes.append(changed)
                c.action(sid,'pause');s=c.action(sid,'resume');assert s['completed']==completed
                c.clock.t+=1;s=c.action(sid,'submit',{'response':'A-D07 explicit fixture; not a task answer or human result'})
                assert s['success'] is None
                relative=Path('closed_loops')/tid/(outcome+'-'+method+'.json')
                traces=c.traces(sid)
                save(out/relative,dict(task_id=tid,method=method,actor='test_fixture',feedback_is_simulated=True,
                     outcome=outcome,view=s,traces=traces,quiz_changed_remaining=changed))
                summary.append(dict(task_id=tid,outcome=outcome,method=method,status=s['status'],
                    completed_preserved=True,spent_proxy=s['spent'],quiz_changed_remaining=changed,
                    human_task_success=None,raw=relative.as_posix()))
    assert all(len(v)==1 for v in hashes.values())
    export(c.database,out/'fixtures/export','test_fixture')
    events=event_audit(out/'fixtures/export');assert events['passed'];save(out/'event_audit.json',events)
    # Paired public real-source development task; every prior item is marked fixture.
    d=development_case(ROOT);concepts=next(u['concept_ids'] for u in d['units'] if u['id']=='u_chunked_iter')
    known=add_history(d,concepts,6)
    for name,data in [('unknown',d),('synthetic_evidence',known)]:
        save(out/'paired'/(name+'.json'),dict(input=data,result=plan(data),is_simulated=True))
    session=start_session(ROOT,known['request'],known['units'],known['state'],known['config'],[known['quiz']],
                          strategy='none',max_quizzes=1)
    session=complete_next(session,session['plan']['remaining'][0]);before=copy.deepcopy(session)
    session=apply_feedback(ROOT,session,known['quiz']['item_id'],'fail',timestamp='2026-10-19T01:00:00+08:00',scheduled=True)
    independent=verify_session(ROOT,session);assert independent['valid']
    assert session['completed']==before['completed'] and session['plan']['remaining']!=before['plan']['remaining']
    save(out/'paired/failed_quiz_repair.json',dict(input=known,before=before,after=session,audit=independent,
         provenance='real fixed source; synthetic six-item histories and synthetic independent failure; not a human pretest'))
    faults=[]
    for name in ['budget_insufficient','timeout','wrong_user','duplicate_evidence','aggregate_mismatch','foreign_project','similar_concept']:
        data=copy.deepcopy(d);kw={}
        if name=='budget_insufficient':data['request']['budget']=1
        elif name=='timeout':kw['options']={'time_limit_seconds':0}
        elif name=='foreign_project':data=add_history(data,['python.iterator_protocol'],10,project='different-project')
        elif name=='similar_concept':data=add_history(data,['python.iterator_protocol.v2'],10)
        else:
            data=add_history(data,['python.iterator_protocol'],1)
            if name=='wrong_user':data['state']['records'][0]['pseudonymous_user_id']='foreign-user'
            elif name=='duplicate_evidence':data['state']['records'].append(copy.deepcopy(data['state']['records'][0]))
            else:data['request']['learner_state'][0]['alpha']=1000
        result=plan(data,**kw);save(out/'faults'/(name+'.json'),dict(input=data,options=kw,result=result))
        faults.append(dict(case=name,status=result['status']))
    # Damage only a new public-source copy; never mutate B's or the frozen source.
    fault_root=work/'damaged_source';shutil.copytree(ROOT/'benchmarks/sources',fault_root/'benchmarks/sources')
    shutil.copytree(ROOT/'schemas',fault_root/'schemas')
    target=fault_root/'benchmarks/sources/boltons/boltons/iterutils.py'
    with target.open('ab') as f:f.write(b'\n# A-D07 isolated integrity failure\n')
    damaged=plan(d,root=fault_root);assert not damaged['feasible']
    save(out/'faults/damaged_source.json',dict(result=damaged,only_private_temp_copy_changed=True,
         fault='append a comment to public cached source without updating declared hash'))
    faults.append(dict(case='damaged_source',status=damaged['status']))
    # Exact legacy bug and opt-in correction, simulated transport and isolated memory meter.
    old=RelayCollector(ROOT,work/'legacy.db',actor='test_fixture',clock=Clock(),b1_config=b1_config(ROOT),meter=SpendMeter(5),transport=empty_transport)
    fixed=StableRelayCollector(ROOT,work/'fixed.db',actor='test_fixture',clock=Clock(),b1_config=b1_config(ROOT),meter=SpendMeter(5),transport=empty_transport)
    a=old.create(method='B1');b=fixed.create(method='B1')
    assert a['status']=='ACTIVE' and b['status']=='FAILED'
    save(out/'defects/B1_incomplete_route.json',dict(legacy=a,fixed=b,legacy_trace=old.traces(a['session_id']),
         fixed_trace=fixed.traces(b['session_id']),transport='fixture, no model API',new_live_calls=0,
         fixed_attempts=1,semantic_retries=0))
    with (out/'closed_loops.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(summary[0]));writer.writeheader();writer.writerows(summary)
    result=dict(run_id=run_id,runtime_version='A-D07-runtime-v1',closed_loops=len(summary),same_initial_information_tasks=len(hashes),
         faults=faults,new_model_calls=0,actual_pretesters=None,actual_recruitment=None,formal_task_outcomes=0,
         feedback_is_simulated=True,fixture_remaining_changes=sum(quiz_changes),
         cold_start_single_quiz_pass_lower_bound=1-(.9**.5),threshold=.7,
         protocol_limitation='Unknown prior plus one independent pass cannot open tau=.7 q=.1 gate; no feedback-value claim',
         synthetic_prior_repair='paired/failed_quiz_repair.json',formal_study_ready=False)
    save(out/'summary.json',result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);a=p.parse_args()
    if not a.run_id.replace('-','').isalnum():p.error('Unsafe run ID')
    out=ROOT/'experiments/A'/a.run_id;out.mkdir(exist_ok=False)
    started=dt.datetime.now().astimezone().isoformat();result=run(out,a.run_id)
    files=[*sorted((ROOT/'src/codecompass/planner').glob('*.py')),*sorted((ROOT/'src/codecompass/learner').glob('*.py')),
           *[ROOT/p for p in ['scripts/A/run_d07.py','scripts/A/cases_d07.py','scripts/A/relay_d07.py',
             'scripts/A/serve_d07.py','tests/A/test_runtime_d07.py','configs/A/D07_runtime.json','app/A_D07/a07.js']],
           ROOT/'src/codecompass/app/relay_v2.py',ROOT/'src/codecompass/app/study_d06.py',
           ROOT/'benchmarks/B/executable-v2/registry.json',ROOT/'benchmarks/B/executable-v2/registry.sha256']
    for file in files:
        dest=out/'code_snapshot'/file.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(file.read_bytes())
    save(out/'input_manifest.json',[dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
    save(out/'registration.json',dict(owner='成员A',executor='Codex Agent A',machine=platform.node(),model_id=None,
      planned_date='2026-10-21',started_at=started,finished_at=dt.datetime.now().astimezone().isoformat(),
      base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
      command=[sys.executable,*sys.argv],exit_code=0,source_version='exact hashes in input_manifest.json + byte copies',
      actual_pretesters=None,actual_recruitment=None,new_model_calls=0,formal_g2_passed=False))
    print(json.dumps({k:result[k] for k in ('closed_loops','same_initial_information_tasks','fixture_remaining_changes','new_model_calls')}))


if __name__=='__main__':main()
