import pytest
from scripts.B.b0 import fixed_order


def units(costs):
    return [{'id': str(i), 'base_cost': c, 'cost_unit': 'proxy_cost'} for i, c in enumerate(costs)]


def test_null_never_becomes_zero():
    r = fixed_order(units([None, 2]), ['0', '1'], 100, 'proxy_cost')
    assert r['status'] == 'INPUT_INCOMPLETE' and r['estimated_cost'] is None
    assert r['ordered_units'] == [] and r['reading_order_only'] == ['0', '1']


def test_budget_truncates_prefix_without_skipping():
    # Explicit synthetic costs, not real task costs or learning minutes.
    r = fixed_order(units([2, 8, 1]), ['0', '1', '2'], 5, 'proxy_cost')
    assert r['ordered_units'] == ['0'] and r['estimated_cost'] == 2


def test_zero_budget_keeps_only_known_zero_cost_prefix():
    assert fixed_order(units([0, 1]), ['0', '1'], 0, 'proxy_cost')['ordered_units'] == ['0']


def test_bad_budget_and_duplicate_rejected():
    with pytest.raises(ValueError): fixed_order(units([1]), ['0'], -1, 'proxy_cost')
    with pytest.raises(ValueError): fixed_order(units([1]), ['0', '0'], 2, 'proxy_cost')
    with pytest.raises(ValueError): fixed_order(units([1]), ['0'], float('nan'), 'proxy_cost')


def test_real_fixed_route_matches_pinned_document_order():
    import json, re
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    config = json.loads((root / 'configs/B/B0_fixed.json').read_text(encoding='utf-8'))
    doc = (root / 'benchmarks/sources/boltons_B_D02/docs/iterutils.rst').read_text(encoding='utf-8')
    mapping = {'chunked': 'u_chunked', 'chunked_iter': 'u_chunked_iter', 'is_iterable': 'u_iterable'}
    expected = [mapping[n] for n in re.findall(r'^\.\. autofunction:: (\w+)', doc, re.MULTILINE) if n in mapping]
    assert config['routes']['task_001'] == expected
    assert config['baseline_type'] == 'README_documentation_fixed_route'
