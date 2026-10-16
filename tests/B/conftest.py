"""Prepare only the repository-owned temporary parent in fresh checkouts."""
from pathlib import Path


def pytest_configure(config):
    base = config.option.basetemp
    if base:
        path = Path(base).resolve()
        owned = (Path(config.rootpath) / 'tmp').resolve()
        if path.is_relative_to(owned):
            path.parent.mkdir(parents=True, exist_ok=True)
