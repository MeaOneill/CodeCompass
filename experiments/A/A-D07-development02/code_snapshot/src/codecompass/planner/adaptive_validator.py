"""Independent accounting/evidence/order replay. Never calls search or selection."""
import copy
import math
from codecompass.learner import mastery_gate, update_evidence, planning_rows
from .diagnostics import probability


def verify_session(root, session):
    checks=[]
    def check(name, condition):
        checks.append(dict(check=name,passed=bool(condition)))
        if not condition:
            raise ValueError(name)
    def equal(a,b):
        return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-8
    try:
        units=session['units']; by_id={u['id']:u for u in units}; request=session['initial_request']; config=session['config']
        concepts={c for u in units for c in u['concept_ids']}|set(request['target_concept_ids'])
        state=copy.deepcopy(session['initial_state']);observed=copy.deepcopy(state)
        completed=[]; spent=learning=quizzing=switching=0.; count=0; durations=[]
        plan=copy.deepcopy(session['initial_plan'])
        def costs_for(ledger):
            counts={}
            for e in ledger['records']:
                if e['project']==request['snapshot_id']:
                    row=counts.setdefault(e['concept_id'],[1,1]);row[0 if e['outcome']=='pass' else 1]+=1
            result={}
            for u in units:
                gaps=[1-counts.get(c,[1,1])[0]/sum(counts.get(c,[1,1])) for c in u['concept_ids']]
                result[u['id']]=u['base_cost']*(1+session['alpha']*sum(gaps)/len(gaps))
            return result
        def measured(route, ledger, done, reference, already_spent):
            gate=mastery_gate(ledger,request['snapshot_id'],concepts,threshold=config['threshold'],quantile=config['quantile'],allow_simulated=request['is_fixture'])
            known={c for c,row in gate.items() if row['mastered']}|{c for uid in done for c in by_id[uid]['concept_ids']}
            selected=set(done)
            for uid in route:
                check('unit unique and known',uid in by_id and uid not in selected)
                for edge in by_id[uid]['prerequisites']:
                    check('hard predecessor legal',not edge['hard'] or edge['unit_id'] in selected or set(by_id[edge['unit_id']]['concept_ids'])<=known)
                selected.add(uid);known.update(by_id[uid]['concept_ids'])
            costs=costs_for(ledger); base=sum(costs[u] for u in route)
            pos={u:i for i,u in enumerate(reference)};order=[pos[u] for u in route if u in pos]
            inv=sum(a>b for i,a in enumerate(order) for b in order[i+1:]); additions=sum(u not in pos for u in route)
            penalty=(session['gamma']*(inv+additions)/max(1,len(reference)*(len(reference)-1)//2+len(units))) if reference else 0
            check('remaining total budget',already_spent+base+penalty<=request['budget']+1e-8)
            return dict(costs=costs,gate=gate,learning=base,switch=penalty,objective=base+penalty,
                        complete=set(request['target_concept_ids'])<=known)
        def verify_plan(p,ledger,done,reference,already_spent):
            m=measured(p['remaining'],ledger,done,reference,already_spent)
            check('cost table',all(equal(p['unit_costs'][u],c) for u,c in m['costs'].items()))
            check('posterior gate',p['gate']==m['gate'])
            for name,key in [('learning_cost','learning'),('switch_cost','switch'),('objective','objective')]:
                check(name,equal(p[name],m[key]))
            check('feasible coverage',p['status']!='FEASIBLE' or m['complete'])
            check('no reused order-insensitive certificate',p.get('certificate') is None and p.get('optimality_claim') is False)
            return m
        verify_plan(plan,state,completed,[],0)
        for event in session['events']:
            check('event spent before',equal(event['spent_before'],spent))
            if event['type']=='material':
                uid=event['unit_id']
                check('next material follows adopted route',bool(plan['remaining']) and plan['remaining'][0]==uid)
                cost=plan['unit_costs'][uid]
                check('material charge',equal(event['cost'],cost))
                check('no repeat completed material',uid not in completed)
                completed.append(uid);plan['remaining'].pop(0);spent+=cost;learning+=cost
                plan['objective']=sum(plan['unit_costs'][u] for u in plan['remaining'])
            elif event['type']=='diagnostic':
                quiz=next(q for q in session['quizzes'] if q['item_id']==event['item_id'])
                check('quiz unit and cost',event['cost_unit']==request['cost_unit'] and equal(event['quiz_cost'],quiz['cost']))
                check('quiz cap',count<session['max_quizzes'])
                check('completed prefix retained',event['completed_before']==event['completed_after']==completed)
                check('decision baseline route',event['before_plan']['remaining']==plan['remaining'])
                check('decision baseline objective',equal(event['decision']['baseline_objective'],plan['objective']))
                decision=event['decision']
                check('selected item',decision['selected']==quiz['item_id'])
                if not event.get('scheduled'):
                    check('strategy unchanged',decision['strategy']==session['strategy'])
                    row=next(r for r in decision['candidates'] if r['item_id']==quiz['item_id'])
                    check('both branch estimates saved',set(row['branches'])=={'pass','fail'})
                    check('diagnostic cost in decision',equal(row['quiz_cost'],quiz['cost']))
                    for outcome,b in row['branches'].items():
                        evidence=dict(event['evidence'],outcome=outcome,timestamp='2000-01-01T00:00:00+00:00')
                        branch_state,_=update_evidence(state,evidence,allow_simulated=request['is_fixture'])
                        m=measured(b['remaining'],branch_state,completed,plan['remaining'],spent+quiz['cost'])
                        check('branch objective',equal(b['objective'],m['objective']))
                        check('branch gate',b['gate']==m['gate'].get(quiz['concept_id']))
                        check('branch feasibility',b['status']!='FEASIBLE' or m['complete'])
                    if session['strategy']!='fixed':
                        p,_=probability(root,request,units,quiz)
                        check('VOI needs reliable permitted probability',p is not None and row['p_pass']==p)
                        expected=plan['objective']-(quiz['cost']+p*row['branches']['pass']['objective']+(1-p)*row['branches']['fail']['objective'])
                        check('VOI computation',equal(row['voi'],expected) and expected>session['epsilon'])
                        check('VOI no failed branch',all(b['status']=='FEASIBLE' for b in row['branches'].values()))
                evidence=event['evidence']
                check('actual outcome matches evidence',evidence['outcome']==event['outcome'] and evidence['item_id']==quiz['item_id'] and evidence['concept_id']==quiz['concept_id'])
                check('independent assessment',evidence['independent'] is True)
                observed,accepted=update_evidence(observed,evidence,allow_simulated=request['is_fixture'])
                check('new independent item only',accepted=='ACCEPTED')
                spent+=quiz['cost'];quizzing+=quiz['cost'];count+=1;durations.append(event['duration_seconds'])
                feedback=session['strategy']!='no_feedback'
                check('feedback ablation respected',event['feedback_applied']==feedback)
                if feedback:
                    state=copy.deepcopy(observed);estimate=event['repair_estimate']
                    verify_plan(estimate,state,completed,plan['remaining'],spent)
                    fee=estimate['switch_cost'] if estimate['status']=='FEASIBLE' else 0
                    spent+=fee;switching+=fee
                    check('switch paid once',equal(event['paid_switch_cost'],fee))
                    check('new plan equals repair estimate',event['after_plan']['remaining']==estimate['remaining'])
                else:
                    check('no feedback plan unchanged',event['after_plan']['remaining']==plan['remaining'] and event['paid_switch_cost']==0)
                check('added units explicitly logged',event['added_units']==sorted(set(event['after_plan']['remaining'])-set(plan['remaining'])))
                plan=copy.deepcopy(event['after_plan'])
                if plan['status']=='FEASIBLE':
                    verify_plan(plan,state,completed,plan['remaining'],spent)
            else:
                raise ValueError('Unknown event')
            check('event spent after',equal(event['spent_after'],spent))
            check('spent within budget',spent<=request['budget']+1e-8)
        for name,value in [('spent',spent),('learning_spent',learning),('quiz_spent',quizzing),('switch_spent',switching)]:
            check('final '+name,equal(session[name],value))
        check('final evidence/state',session['state']==state and session['observed_state']==observed)
        check('request aggregates current',session['request']['learner_state']==planning_rows(state,request['snapshot_id'],quantile=config['quantile'],allow_simulated=request['is_fixture']))
        check('final completed/remaining',session['completed']==completed and session['plan']['remaining']==plan['remaining'])
        check('final count',session['quiz_count']==count)
        duration=None if any(d is None for d in durations) else sum(durations)
        check('duration missing not zero',session['quiz_duration_seconds']==duration)
        if session['status']=='FEASIBLE':
            verify_plan(session['plan'],state,completed,session['plan']['remaining'],spent)
        return dict(valid=True,checks=checks,errors=[],coverage_is_not_task_success=True)
    except (ValueError,KeyError,TypeError,StopIteration) as error:
        return dict(valid=False,checks=checks,errors=[str(error)])
