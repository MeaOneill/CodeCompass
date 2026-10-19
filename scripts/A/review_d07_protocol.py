"""A's technical cross-review of public candidate metadata; never opens final keys."""
import argparse,hashlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from codecompass.app.relay_v2 import registry,prepare
from codecompass.planner.adaptive import route_audit


def review():
    records=registry(ROOT)['records'];rows=[]
    for record in records:
        d=prepare(ROOT,record['task_id'],'p_'+'0'*32,True)
        targets=set(d['target_concept_ids']);units=d['units']
        incidence={c:sum(c in u['concept_ids'] for u in units) for c in targets}
        forced=all(any(c in targets and incidence[c]==1 for c in u['concept_ids']) for u in units)
        assert targets<={c for u in units for c in u['concept_ids']}
        assert d['config']['threshold']==.7 and d['config']['quantile']==.1
        assert sum(u['base_cost'] for u in units)+1<=100
        function_goals=sorted(c for c in targets if c.startswith('source.function.'))
        rows.append(dict(task_id=d['task_id'],split=d['split'],unit_count=len(units),
            total_source_proxy_cost=sum(u['base_cost'] for u in units),target_count=len(targets),
            explicit_function_goals=function_goals,all_units_forced_from_unknown=forced,
            source_commit=d['snapshot']['commit'],snapshot_id=d['snapshot']['snapshot_id'],
            declared_license=d['snapshot']['license'],source_spans_validated=True,
            technical_review='PASS_SOURCE_AND_CONTRACT_ONLY',human_task_approval='NOT_REVIEWED',
            policy_text_exception='Inherited A units: no explicit source.function goals despite generic policy string' if not function_goals else None))
    historic=[]
    live=ROOT/'experiments/B/B-D06-v2-live01/traces.json'
    for method in json.loads(live.read_text(encoding='utf-8')):
        for stage,t in enumerate(method['traces']):
            ctx=t['context'];replay=route_audit(dict(target_concept_ids=ctx['target_concept_ids'],budget=ctx['budget_proxy']),
                ctx['units'],ctx['learner_gate'],t['route'],{u['id']:u['base_cost'] for u in ctx['units']},
                ctx['completed'],(),0,ctx['spent_proxy'])
            historic.append(dict(method=method['method'],stage=stage,valid=replay['valid'],goal_complete=replay['goal_complete']))
    files=['benchmarks/B/executable-v2/registry.json','benchmarks/B/frozen/B-D06-v0.2-candidate/manifest.json',
           'docs/protocol/B-D06-v0.2-candidate/protocol.md','docs/protocol/B-D06-v0.1-candidate/protocol.md',
           'docs/protocol/B-D06-v0.1-candidate/scoring.md','configs/B/D06_v2_deepseek.json',
           'experiments/B/B-D06-v2-live01/traces.json']
    return dict(role='A technical cross-review of B candidate; not human signature',tasks=rows,
      source_tasks=len(rows),dev_tasks=sum(r['split']=='dev' for r in rows),
      single_unit_tasks=sum(r['unit_count']==1 for r in rows),
      forced_all_units_tasks=sum(r['all_units_forced_from_unknown'] for r in rows),
      historical_live_route_replay=historic,
      parameter_retuning=False,final_answers_opened=False,actual_pretesters=None,recruitment=None,
      comparison_branch=None,formal_g2_passed=False,freeze_tag_allowed=False,
      method_fairness='same public source/context, budget100, scheduled quiz1, max1; see final development05 replay audit',
      limitations=['unknown plus one quiz cannot reach lower-bound threshold; no C2 selection/feedback benefit established',
        'unique mandatory function goals limit content optimization freedom; ordering/robustness still testable',
        'task001/002 inherit A concepts and material granularity; do not claim all12 have new function goals',
        'model alias deepseek-flash is not immutable provider weights',
        'private final scoring replay not performed by A; sealed manifest hash only',
        'task/source/protocol human approval and two genuine pretesters remain unconfirmed'],
      files={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();result=review()
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({k:result[k] for k in ('source_tasks','dev_tasks','single_unit_tasks','forced_all_units_tasks','formal_g2_passed')}))
