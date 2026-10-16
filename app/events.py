"""Additional session semantics for A's existing ExperimentEvent, no shared edits."""
from codecompass.retrieval.samples import contract_validator


def validate_event(root, event):
    contract_validator(root).validate(event)
    if event['object_type'] != 'ExperimentEvent':
        raise ValueError('Expected ExperimentEvent')
    kind, payload = event['event_type'], event['payload']
    if kind == 'succeeded' and (payload['exit_code'] != 0 or payload['error'] is not None):
        raise ValueError('Succeeded requires exit 0 and no error')
    if kind == 'failed' and not (payload['exit_code'] not in (None, 0) or payload['error']):
        raise ValueError('Failed requires a nonzero exit or explicit error')
    if kind in ('paused', 'resumed') and not payload['resume_from']:
        raise ValueError('Pause/resume requires a checkpoint reference')
    if payload['evidence_type'] != 'development_validation' and not event['is_fixture']:
        if not all(event[k] for k in ('code_commit', 'data_hash', 'config_hash')):
            raise ValueError('Formal evidence requires version hashes')
    return event
