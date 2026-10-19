"""Regression: unrelated current-project history must not enter a task's gate universe."""
from scripts.A.audit_d06_gate_control import audit


def test_saved_controls_with_unrelated_history_replay():
    result=audit()
    assert result['passed'] and result['checked_results']==60
    assert not result['formal_test_allowed'] and not result['freeze_tag_allowed']
