"""Prepare B-only examples/configuration; never edit A's contract or samples."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    folder = ROOT / 'docs/B'
    folder.mkdir(parents=True, exist_ok=True)
    sample = json.loads((ROOT / 'schemas/examples/experiment_event.json').read_text(encoding='utf-8'))
    events = []
    for i, kind in enumerate(('started', 'paused', 'resumed', 'failed', 'succeeded')):
        event = copy.deepcopy(sample)
        event.update(event_id=f'fixture_B_{kind}', run_id='fixture_B_session_failure' if kind != 'succeeded' else 'fixture_B_separate_success', event_type=kind, timestamp=f'2026-10-16T00:0{i}:00+08:00')
        event['actor'].update(role='B', owner='fixture_owner', executor='fixture_executor', machine='fixture_machine')
        event['payload'].update(task_id='fixture_task', command=['fixture_command'], elapsed_seconds=None, resume_from='fixture_checkpoint' if kind in ('paused', 'resumed') else None, exit_code=1 if kind == 'failed' else 0 if kind == 'succeeded' else None, error='fixture_error' if kind == 'failed' else None)
        events.append(event)
    (folder / 'event_examples.json').write_text(json.dumps(events, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'description': 'B draft session profile; A 1.0.0 remains authoritative. Cross-event ordering checked by future recorder.', 'allOf': [{'$ref': '../../schemas/contracts.schema.json'}, {'properties': {'object_type': {'const': 'ExperimentEvent'}}}]}
    for kind, rule in [('succeeded', {'exit_code': {'const': 0}, 'error': {'type': 'null'}}), ('paused', {'resume_from': {'type': 'string', 'minLength': 1}}), ('resumed', {'resume_from': {'type': 'string', 'minLength': 1}})]:
        schema['allOf'].append({'if': {'properties': {'event_type': {'const': kind}}}, 'then': {'properties': {'payload': {'properties': rule}}}})
    schema['allOf'].append({'if': {'properties': {'event_type': {'const': 'failed'}}}, 'then': {'properties': {'payload': {'anyOf': [{'properties': {'exit_code': {'type': 'integer', 'not': {'const': 0}}}}, {'properties': {'error': {'type': 'string', 'minLength': 1}}}]}}}})
    (folder / 'session_event.schema.json').write_text(json.dumps(schema, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
