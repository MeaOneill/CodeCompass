"""Opt-in A-owned integration guard; original B collector and frozen files untouched."""
from codecompass.app.relay_v2 import RelayCollector,packet
from codecompass.learner import mastery_gate
from codecompass.planner.adaptive import request_for_state
from codecompass.planner.runtime_d07 import VERSION,explain_route,failure,safe_remaining,validate_method_result


class StableRelayCollector(RelayCollector):
    def __init__(self,*args,test_search_options=None,**kwargs):
        if test_search_options is not None and kwargs.get('actor','human_manual')=='human_manual':
            raise ValueError('Fault-injection options are fixture-only, never a human protocol setting')
        self.test_search_options=test_search_options
        super().__init__(*args,**kwargs)

    def calculate(self,s):
        try:
            if s['method']=='Ours':
                d=s['data'];req=request_for_state(d['request'],d['state'],d['config'])
                details=safe_remaining(self.root,req,d['units'],d['state'],d['config'],completed=s['completed'],
                    reference=s['route'],spent=s['spent'],options=self.test_search_options)
                result=dict(status=details['status'],route=details['remaining'],cost=details.get('learning_cost'),
                            context=packet(s),details=details)
            else:
                result=super().calculate(s)
            return validate_method_result(self.root,s,result)
        except Exception as exc:
            details=failure(exc)
            return dict(status=details['status'],route=[],cost=None,
                        context=dict(validation_failed=True,runtime_version=VERSION),details=details)

    def view(self,s):
        v=super().view(s);v['runtime_version']=VERSION
        try:
            d=s['data'];req=request_for_state(d['request'],d['state'],d['config'])
            concepts={c for u in d['units'] for c in u['concept_ids']}|set(req['target_concept_ids'])
            gate=mastery_gate(d['state'],req['snapshot_id'],concepts,threshold=d['config']['threshold'],
                              quantile=d['config']['quantile'],allow_simulated=req['is_fixture'])
            v['route_explanations']=explain_route(self.root,req,d['units'],gate,s['route'],s['completed'])
        except Exception as exc:
            v['route_explanations']=[];v['runtime_error']=failure(exc)
        v['limitation']+=' A-D07运行边界：完整目标校验；模拟演示不等于真人预演，正式G2仍未放行。'
        return v
