"""Run with python -m app from the checkout root."""
import argparse
import json
import sys
from pathlib import Path

from codecompass.retrieval.samples import load_dev_bundle, load_object


def main():
    p = argparse.ArgumentParser(description='CodeCompass B-D01: read-only contract and fixed-source validation. Planner/UI not implemented.')
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1], help='Checkout containing schemas and benchmarks')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('check-sample', help='Verify real task_001, pinned source hashes and line spans without executing source')
    obj = sub.add_parser('validate-object', help='Validate one local object against A contract 1.0.0; fixtures remain fixtures')
    obj.add_argument('path', help='Repository-relative POSIX JSON path')
    args = p.parse_args()
    try:
        if args.command == 'check-sample':
            b = load_dev_bundle(args.root)
            result = {'task_id': b['task']['task_id'], 'repo_commit': b['snapshot']['commit'], 'units': len(b['units']), 'schema_version': b['task']['schema_version'], 'source_spans': b['task']['source_spans'], 'planner': 'NOT_IMPLEMENTED', 'base_costs': [u['base_cost'] for u in b['units']]}
        else:
            d = load_object(args.root, args.path)
            result = {'object_type': d['object_type'], 'schema_version': d['schema_version'], 'is_fixture': d['is_fixture']}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception as exc:
        from jsonschema.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            print(exc.message, file=sys.stderr)
            return 1
        raise


if __name__ == '__main__':
    raise SystemExit(main())
