"""Read-only independent replay; never calls search or changes human records."""
import argparse,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from codecompass.app.experiment import digest
from codecompass.app.pilot_d07_v3 import VERSION,bank
from codecompass.learner import mastery_gate,validate_state
from codecompass.planner.adaptive import route_audit,request_for_state

def audit_case(s,root=ROOT):
    checks=0
    def check(value):
        nonlocal checks
        checks+=1
        if not value:raise ValueError('独立审计发现原始记录不一致')
    items=bank(root)['items'];previous=None;elapsed=0;spent=0
    check(s['provenance']['protocol_version']==VERSION and s['provenance']['ui_version']==VERSION)
    for rel,sha in s['provenance']['source_hashes'].items():check(hashlib.sha256((Path(root)/rel).read_bytes()).hexdigest()==sha)
    for i,e in enumerate(s['events'],1):
        check(e['seq']==i and e['previous_hash']==previous and e['hash']==digest({k:v for k,v in e.items() if k!='hash'}))
        check(e['version']==VERSION and e['ui_version']==VERSION and e['source_digest']==digest(s['provenance']))
        check(e['elapsed']>=elapsed and e['spent']>=spent);previous=e['hash'];elapsed=e['elapsed'];spent=e['spent']
    check(s['spent']==spent and s['elapsed']>=elapsed)
    check(len(s['answers'])<=6 and s['actor'] in ('human_manual','agent_browser','test_fixture'))
    check(s['data']['request']['is_fixture']==(s['actor']!='human_manual'))
    validate_state(s['data']['state'],allow_simulated=s['actor']!='human_manual')
    records=s['data']['state']['records'];valid_answers=[a for a in s['answers'] if a['choice'] is not None]
    check(len(records)==len(valid_answers))
    cursor=0
    for i,answer in enumerate(s['answers']):
        if answer['choice'] is None:
            check(answer['missing'] and answer['outcome'] is None);continue
        e=records[cursor];cursor+=1
        q=items[i];expected='pass' if answer['choice']==q['answer'] else 'fail'
        check(answer['item_id']==e['item_id']==q['item_id'] and answer['outcome']==e['outcome']==expected)
        check(e['project']==s['data']['request']['snapshot_id'] and e['pseudonymous_user_id']==s['data']['state']['pseudonymous_user_id'])
        check(e['is_fixture']==(s['actor']!='human_manual') and e['independent'] and e['concept_id']=='python.iterator_protocol')
    check(s['spent']==(5+len(s['answers']) if s['completed'] else 0))
    if s['status']!='DONE':return dict(passed=True,checks=checks,status=s['status'],mechanism_case_completed=False,real_route_change=False)
    check(len(s['answers'])==6 and s['completed']==['u_positive_int'])
    history_valid=sum(a['choice'] is not None for a in s['answers'][:5])
    check(len(s['state_before']['records'])==history_valid and s['state_before']['records']==records[:history_valid])
    kinds=[e['kind'] for e in s['events']]
    diagnosis_kind='diagnosis_missing' if s['answers'][-1]['missing'] else 'diagnosis_evidence'
    check(kinds.index('before_plan_sealed')<kinds.index('diagnosis_presented')<kinds.index(diagnosis_kind)<kinds.index('finished'))
    sealed=next(e for e in s['events'] if e['kind']=='before_plan_sealed')
    check(sealed['payload']['plans_digest']==digest(s['before']) and sealed['payload']['state_digest']==digest(s['state_before']))
    check(s['history_cost']==5 and s['diagnosis_cost']==1 and s['spent']==11)
    check(s['diagnosis_metrics']['count']==1 and s['diagnosis_metrics']['switch_cost']==0)
    received=next(e for e in s['events'] if e['kind']==diagnosis_kind)
    shown=next(e for e in s['events'] if e['kind']=='diagnosis_presented')
    check(abs(s['diagnosis_duration_seconds']-(received['elapsed']-shown['elapsed']))<1e-7)
    d=s['data'];concepts={c for u in d['units'] for c in u['concept_ids']}|set(d['request']['target_concept_ids'])
    for label,state,paid in [('before',s['state_before'],10),('after',d['state'],11),('no_feedback',s['state_before'],11)]:
        gate=mastery_gate(state,d['request']['snapshot_id'],concepts,threshold=.7,quantile=.1,allow_simulated=d['request']['is_fixture'])
        req=request_for_state(d['request'],state,d['config'])
        for method in ('Ours','B2'):
            plan=s[label][method];check(plan['gate']==gate)
            a=route_audit(req,d['units'],gate,plan['route'],{u['id']:u['base_cost'] for u in d['units']},s['completed'],(),0,paid)
            check(a['valid'] and a['goal_complete'] and a['total_if_executed']==paid+plan['cost'])
            check(a['total_if_executed']==plan['audit']['total_if_executed'])
    changed=s['before']['Ours']['route']!=s['after']['Ours']['route']
    check(changed==all(a['outcome']=='pass' for a in s['answers']))
    check(s['no_feedback']['Ours']['route']==s['before']['Ours']['route'])
    return dict(passed=True,checks=checks,status=s['status'],actor=s['actor'],mechanism_case_completed=True,
                observed_route_change=changed,real_route_change=changed and s['actor']=='human_manual',
                completed_preserved=True,spent=11,diagnosis_seconds=s['diagnosis_duration_seconds'],
                formal_sample=False,formal_success=None,statistical_independence_validated=False)

def main():
    p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    con=sqlite3.connect(f'file:{a.database.resolve().as_posix()}?mode=ro',uri=True)
    try:cases=[json.loads(r[0]) for r in con.execute('select value from cases')]
    finally:con.close()
    if any(s['actor']=='human_manual' for s in cases) and not a.output.resolve().is_relative_to(ROOT/'experiments/A/A-D07-human-live01'):
        p.error('真人审计只能保存本机已排除Git的私有目录')
    if a.output.exists():p.error('保留已有审计，使用新输出名')
    result=dict(passed=True,cases=[audit_case(s) for s in cases],formal_G2_passed=False)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=True,cases=len(cases))))

if __name__=='__main__':main()
