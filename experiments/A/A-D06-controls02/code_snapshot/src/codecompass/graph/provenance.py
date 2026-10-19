"""Fixed-byte snapshots and source spans. Never import analyzed source."""
import hashlib
import json
from pathlib import Path, PurePosixPath


def digest(data):
    return hashlib.sha256(data).hexdigest()


def safe_source(root, relative):
    root = Path(root).resolve()
    p = PurePosixPath(relative)
    if not relative or p.is_absolute() or '..' in p.parts or ':' in relative or '\\' in relative:
        raise ValueError('Expected a relative POSIX source path')
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Source escapes snapshot root')
    return path


def read_snapshot(root, snapshot):
    """Read only manifest-listed bytes; reject duplicates/tampering before parsing."""
    if len(snapshot['commit']) != 40 or any(c not in '0123456789abcdef' for c in snapshot['commit']):
        raise ValueError('Snapshot requires a fixed commit SHA')
    files = sorted(snapshot['files'], key=lambda f: f['path'])
    if digest(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()) != snapshot['hash']:
        raise ValueError('Snapshot manifest hash mismatch')
    contents = {}
    for f in files:
        name = f['path']
        if name in contents:
            raise ValueError('Duplicate snapshot file')
        data = safe_source(root, name).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if len(data) != f['bytes'] or digest(data) != f['sha256'] or blob != f['git_blob']:
            raise ValueError('Snapshot byte mismatch: ' + name)
        contents[name] = data
    return contents


def make_span(snapshot_id, path, text, start, end):
    lines = text.splitlines()
    if not 1 <= start <= end <= len(lines):
        raise ValueError('Invalid inclusive source range')
    return {'snapshot_id': snapshot_id, 'path': path, 'start_line': start, 'end_line': end,
            'content_hash': digest(('\n'.join(lines[start-1:end]) + '\n').encode('utf-8'))}


def validate_span(span, snapshot, contents):
    if span['snapshot_id'] != snapshot['snapshot_id'] or span['path'] not in contents:
        raise ValueError('Span is outside snapshot')
    text = contents[span['path']].decode('utf-8')
    expected = make_span(span['snapshot_id'], span['path'], text, span['start_line'], span['end_line'])
    if span != expected:
        raise ValueError('Source span content mismatch')
    return True
