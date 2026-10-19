"""Public development inputs and explicitly simulated independent histories."""
import copy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path

from codecompass.app.relay_v2 import prepare
from codecompass.learner import update_evidence,planning_rows


class Clock:
    def __init__(self):self.epoch='A-D07-fixture';self.t=100.
    def sample(self):
        return dict(epoch=self.epoch,mono=self.t,wall=(datetime(2026,10,19,tzinfo=timezone(timedelta(hours=8)))+timedelta(seconds=self.t)).isoformat())


def stored(collector,sid):
    with collector.connect() as db:
        return json.loads(db.execute('SELECT value FROM sessions WHERE id=?',(sid,)).fetchone()[0])


def b1_config(root):
    return json.loads((Path(root)/'configs/B/D06_v2_deepseek.json').read_text(encoding='utf-8'))['b1']


def fixture_transport(payload,config):
    ctx=json.loads(payload['input'].split('CONTEXT_JSON\n')[1])
    route=[u['id'] for u in ctx['units'] if u['id'] not in ctx['completed']]
    return dict(model=config['model'],status='completed',usage=dict(input_tokens=100,output_tokens=50),
        output=[dict(type='message',content=[dict(type='output_text',text=json.dumps({'ordered_units':route}))])])


def empty_transport(payload,config):
    response=fixture_transport(payload,config)
    response['output'][0]['content'][0]['text']='{"ordered_units":[]}'
    return response


def development_case(root,task_id='task_001'):
    return prepare(root,task_id,'p_'+'0'*32,True)


def add_history(data,concepts,count=6,project=None):
    d=copy.deepcopy(data)
    for concept in concepts:
        for i in range(count):
            evidence=dict(evidence_id=f'A07-{concept}-{i}',item_id=f'A07-{concept}-{i}',concept_id=concept,
                outcome='pass',timestamp='2026-10-19T00:00:00+08:00',project=project or d['request']['snapshot_id'],
                pseudonymous_user_id=d['state']['pseudonymous_user_id'],is_fixture=True,independent=True,evidence_type='independent_quiz')
            d['state'],decision=update_evidence(d['state'],evidence,allow_simulated=True)
            assert decision=='ACCEPTED'
    d['request']['learner_state']=planning_rows(d['state'],d['request']['snapshot_id'],allow_simulated=True)
    return d
