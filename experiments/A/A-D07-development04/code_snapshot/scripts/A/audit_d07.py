"""Independent replay of D07 outcomes, original inputs and provenance; no search calls."""
import argparse,csv,hashlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from codecompass.app.relay_v2 import prepare
from codecompass.planner.adaptive import route_audit
from codecompass.planner.adaptive_validator import verify_session
from scripts.B.audit_d05 import audit as event_audit


def audit(run_id):
    out=ROOT/'experiments/A'/run_id
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    summary=load(out/'summary.json');checks=0
    for entry in load(out/'input_manifest.json'):
        for p in (ROOT/entry['path'],out/'code_snapshot'/entry['path']):
            assert hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256'],entry['path']
            checks+=1
    rows=list(csv.DictReader((out/'closed_loops.csv').open(encoding='utf-8',newline='')))
    assert len(rows)==72 and len({(r['task_id'],r['method'],r['outcome']) for r in rows})==72
    initial_hashes={}
    for row in rows:
        raw=load(out/row['raw']);v=raw['view'];d=prepare(ROOT,row['task_id'],'p_'+'0'*32,True)
        assert v['actor']=='test_fixture' and v['success'] is None and v['score_status']=='PENDING_INDEPENDENT_FINAL_SCORING'
        assert len(v['completed'])==1 and v['outcome']==row['outcome']
        assert len(raw['traces'])==2
        for index,t in enumerate(raw['traces']):
            ctx=t['context'];gate=ctx['learner_gate']
            assert not any(g['mastered'] for g in gate.values())
            assert len(ctx['learner_evidence'])==index
            if index:
                expected=.1**.5 if row['outcome']=='pass' else 1-.9**.5
                evidence=ctx['learner_evidence'][0]
                assert evidence['outcome']==row['outcome'] and evidence['independent'] and evidence['is_fixture']
                assert abs(gate[evidence['concept_id']]['lower_bound']-expected)<1e-10
            else:
                initial_hashes.setdefault(row['task_id'],set()).add(hashlib.sha256(json.dumps(ctx,sort_keys=True).encode()).hexdigest())
            replay=route_audit(d['request'],d['units'],gate,t['route'],
                {u['id']:u['base_cost'] for u in d['units']},ctx['completed'],(),0,ctx['spent_proxy'])
            assert t['status']=='FEASIBLE' and replay['valid'] and replay['goal_complete']
            assert abs(t['cost']-replay['learning_cost'])<1e-9
            if row['method']=='B1':assert t['details']['transport_is_fixture']
            checks+=8
        costs={u['id']:u['base_cost'] for u in d['units']}
        assert abs(v['spent']-(sum(costs[u] for u in v['completed'])+1))<1e-9
        assert raw['quiz_changed_remaining']==(v['feedback']['before_route']!=v['feedback']['after_route'])
        checks+=3
    assert len(initial_hashes)==12 and all(len(h)==1 for h in initial_hashes.values())
    assert event_audit(out/'fixtures/export')['passed']
    before=load(out/'paired/failed_quiz_repair.json')['before']
    after=load(out/'paired/failed_quiz_repair.json')['after']
    assert verify_session(ROOT,after)['valid'] and after['completed']==before['completed']
    assert after['plan']['remaining']!=before['plan']['remaining']
    assert abs(after['spent']-before['spent']-1)<1e-9
    assert 'u_chunked_iter' not in before['plan']['remaining'] and 'u_chunked_iter' in after['plan']['remaining']
    expected={'budget_insufficient':'NO_FEASIBLE_FOUND','timeout':'TIMEOUT','wrong_user':'INVALID_INPUT',
      'duplicate_evidence':'INVALID_INPUT','aggregate_mismatch':'INVALID_INPUT','foreign_project':'FEASIBLE',
      'similar_concept':'FEASIBLE','damaged_source':'INVALID_INPUT'}
    for name,status in expected.items():
        r=load(out/'faults'/(name+'.json'))['result'];assert r['status']==status
        if name in ('foreign_project','similar_concept'):assert r['learning_cost']==80
        elif name=='timeout':assert r['certificate'] is None
        checks+=1
    defect=load(out/'defects/B1_incomplete_route.json')
    assert defect['legacy']['status']=='ACTIVE' and defect['fixed']['status']=='FAILED'
    assert defect['fixed_trace'][0]['status']=='ALGORITHM_INCOMPLETE' and defect['fixed_attempts']==1
    assert summary['new_model_calls']==0 and summary['actual_pretesters'] is None and summary['formal_task_outcomes']==0
    assert abs(summary['cold_start_single_quiz_pass_lower_bound']-(.1**.5))<1e-10
    return dict(passed=True,checks=checks,closed_loops=72,paired_development_repair_passed=True,
                real_human_pretests='NOT_RUN',recruitment=None,new_model_calls=0,formal_g2_passed=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-id',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=audit(a.run_id)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result))
