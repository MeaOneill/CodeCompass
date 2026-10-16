"""Validate local contract objects and source bytes without importing source code."""
import hashlib
import json
from datetime import datetime
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker


def safe_path(root, relative):
    root = Path(root).resolve()
    p = PurePosixPath(relative)
    if not relative or p.is_absolute() or '..' in p.parts or '\\' in relative or ':' in relative:
        raise ValueError('Expected a repository-relative POSIX path')
    target = (root / relative).resolve()
    if not target.is_relative_to(root):
        raise ValueError('Path escapes root, possibly through a symlink')
    return target


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def contract_validator(root):
    schema = read_json(Path(root) / 'schemas/contracts.schema.json')
    Draft202012Validator.check_schema(schema)
    checker = FormatChecker()

    @checker.checks('date-time', raises=(ValueError, TypeError))
    def zoned_datetime(value):
        if not isinstance(value, str):
            return True
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return 'T' in value and parsed.tzinfo is not None

    return Draft202012Validator(schema, format_checker=checker)


def load_object(root, relative):
    target = safe_path(root, relative)
    public_prefixes = ('schemas/examples/', 'benchmarks/dev/', 'benchmarks/sources/')
    resolved_relative = target.relative_to(Path(root).resolve()).as_posix()
    if not relative.startswith(public_prefixes) or not resolved_relative.startswith(public_prefixes):
        raise ValueError('Object is outside application-readable sample/source paths')
    data = read_json(target)
    contract_validator(root).validate(data)
    return data


def load_dev_bundle(root):
    """Return real dev materials, never fixture plans or hidden test answers."""
    root = Path(root)
    validator = contract_validator(root)
    task = load_object(root, 'benchmarks/dev/task_001.json')
    snap = load_object(root, 'benchmarks/sources/boltons/snapshot.json')
    units = read_json(root / 'benchmarks/dev/task_001_units.json')
    if task['split'] != 'dev' or task['is_fixture'] or snap['is_fixture']:
        raise ValueError('Expected real development materials')
    if task['repo_commit'] != snap['commit'] or task['snapshot_id'] != snap['snapshot_id']:
        raise ValueError('Task snapshot mismatch')
    files = sorted(snap['files'], key=lambda f: f['path'])
    if digest(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()) != snap['hash']:
        raise ValueError('Snapshot manifest hash mismatch')
    bundle = safe_path(root, 'benchmarks/sources/boltons')
    manifest = {}
    for f in files:
        if f['path'] in manifest:
            raise ValueError('Duplicate snapshot path')
        content = safe_path(bundle, f['path']).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        if len(content) != f['bytes'] or digest(content) != f['sha256'] or blob != f['git_blob']:
            raise ValueError('Source file hash mismatch: ' + f['path'])
        manifest[f['path']] = content
    ids = [u['id'] for u in units]
    if len(ids) != len(set(ids)) or not set(task['learning_unit_ids']) <= set(ids):
        raise ValueError('Invalid learning unit references')
    for unit in units:
        validator.validate(unit)
        if unit['is_fixture']:
            raise ValueError('Fixture unit in real bundle')
        for edge in unit['prerequisites']:
            if edge['unit_id'] not in ids:
                raise ValueError('Missing prerequisite')
            if edge['hard'] and not (edge['provenance']['review_status'] == 'approved' and edge['provenance']['reviewer']):
                raise ValueError('Unreviewed hard prerequisite')
    for obj in [task, *units]:
        for span in obj['source_spans']:
            safe_path(bundle, span['path'])
            if span['snapshot_id'] != snap['snapshot_id'] or span['path'] not in manifest:
                raise ValueError('Source outside snapshot manifest')
            lines = manifest[span['path']].decode('utf-8').splitlines()
            start, end = span['start_line'], span['end_line']
            if not 1 <= start <= end <= len(lines):
                raise ValueError('Invalid source line range')
            if digest(('\n'.join(lines[start - 1:end]) + '\n').encode()) != span['content_hash']:
                raise ValueError('Source span hash mismatch')
    return {'task': task, 'snapshot': snap, 'units': units}
