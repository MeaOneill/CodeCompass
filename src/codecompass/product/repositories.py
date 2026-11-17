"""Bounded public GitHub snapshots. Imported code is data, never executed."""
import ast
import hashlib
import io
import json
import re
import shutil
import stat
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from codecompass.graph import extract_snapshot
from codecompass.graph.provenance import digest
from .call_resolution import DEFINITION, call_expressions, scoped_nodes

MAX_ARCHIVE = 8 * 1024 * 1024
MAX_SOURCE = 12 * 1024 * 1024
MAX_FILES = 150
FEATURES = {
    'python.functions': '函数与参数', 'python.iteration': '循环与推导式',
    'python.generators': '生成器与惰性求值', 'python.classes': '类与对象',
    'python.exceptions': '异常处理', 'python.containers': '容器与索引',
    'python.decorators': '装饰器', 'python.async': '异步调用',
}


def repository_url(value):
    if not isinstance(value, str) or len(value) > 200:
        raise ValueError('请输入公开 GitHub 仓库主页链接')
    u = urlsplit(value.strip())
    if u.scheme != 'https' or u.netloc.lower() != 'github.com' or u.query or u.fragment:
        raise ValueError('目前支持 https://github.com/作者/仓库 格式的公开 Python 仓库')
    parts = u.path.strip('/').removesuffix('.git').split('/')
    if len(parts) != 2 or any(not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,99}', p) or p in ('.', '..') for p in parts):
        raise ValueError('请使用仓库主页，暂不支持分支、文件或子目录链接')
    return '/'.join(parts)


def fetch(url, limit):
    started = time.monotonic()
    req = Request(url, headers={'User-Agent': 'CodeCompass-local/1', 'Accept': 'application/vnd.github+json'})
    with urlopen(req, timeout=15) as response:
        final = urlsplit(response.url)
        if final.scheme != 'https' or final.hostname not in ('api.github.com', 'codeload.github.com'):
            raise ValueError('仓库下载跳转地址不受支持')
        chunks = []; size = 0
        while True:
            if time.monotonic() - started > 50:
                raise ValueError('下载超时，请稍后重试')
            data = response.read(min(65536, limit + 1 - size))
            if not data:
                break
            size += len(data)
            if size > limit:
                raise ValueError('仓库压缩包超过 8 MB，请选择更小的 Python 仓库')
            chunks.append(data)
        return b''.join(chunks)


def unpack_python(raw):
    """Inspect every archive member; write nothing until all bounds pass."""
    files = {}; total = 0; seen = set(); folded = set()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.infolist()) > 15000:
            raise ValueError('仓库文件过多，请选择更小的仓库')
        for member in z.infolist():
            p = PurePosixPath(member.filename)
            if p.is_absolute() or '..' in p.parts or ':' in member.filename or '\\' in member.filename:
                raise ValueError('仓库压缩包含有不安全路径')
            if stat.S_ISLNK(member.external_attr >> 16):
                raise ValueError('暂不支持包含符号链接的仓库压缩包')
            if member.is_dir() or len(p.parts) < 2:
                continue
            name = '/'.join(p.parts[1:])
            if name in seen or name.casefold() in folded:
                raise ValueError('仓库含有重复或大小写冲突路径')
            seen.add(name); folded.add(name.casefold())
            if not name.endswith('.py'):
                continue
            if len(files) >= MAX_FILES or member.file_size > 512 * 1024:
                raise ValueError('目前支持最多 150 个 Python 文件，单文件不超过 512 KB')
            total += member.file_size
            if total > MAX_SOURCE:
                raise ValueError('Python 源码超过 12 MB')

            for part in PurePosixPath(name).parts:
                if part.rstrip(' .') != part or part.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(10)),*(f'LPT{i}' for i in range(10))}:
                    raise ValueError('仓库路径无法安全保存到本机')
            data = z.read(member)
            try:
                data.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError('目前只支持 UTF-8 编码的 Python 源码') from None
            files[name] = data
    if not files:
        raise ValueError('仓库中没有 Python 源码')
    return files


def features(node):
    result = {'python.functions'} if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) else set()
    for child in ast.walk(node):
        if isinstance(child, (ast.For, ast.While, ast.comprehension)): result.add('python.iteration')
        if isinstance(child, (ast.Yield, ast.YieldFrom, ast.GeneratorExp)): result.add('python.generators')
        if isinstance(child, ast.ClassDef): result.add('python.classes')
        if isinstance(child, (ast.Try, ast.Raise)): result.add('python.exceptions')
        if isinstance(child, (ast.Subscript, ast.Dict, ast.List, ast.Set)): result.add('python.containers')
        if getattr(child, 'decorator_list', []): result.add('python.decorators')
        if isinstance(child, (ast.AsyncFunctionDef, ast.Await, ast.AsyncFor)): result.add('python.async')
    return sorted(result)


def definition_key(path,name,node):
    kind = 'class' if isinstance(node,ast.ClassDef) else 'async_function' if isinstance(node,ast.AsyncFunctionDef) else 'function'
    return path,name,kind,min([node.lineno]+[d.lineno for d in node.decorator_list]),node.end_lineno


class DefinitionIndex:
    def __init__(self, entries):
        self.by_name = {}
        self.by_span = {}
        for key,row in entries:
            self.by_name.setdefault(key[:3],[]).append(row)
            self.by_span.setdefault(key,[]).append(row)

    def match(self,key,diagnostics):
        exact=self.by_span.get(key,[])
        matches=exact or self.by_name.get(key[:3],[])
        if len(matches)==1:
            if not exact:
                diagnostics.append(dict(identity=key,status='unique_legacy_fallback'))
            return matches[0]
        if matches:
            diagnostics.append(dict(identity=key,status='ambiguity',count=len(matches)))
        return None


def normalize_symbols(symbols):
    by_id={}
    for row in symbols:
        previous=by_id.get(row['id'])
        if previous is None:
            by_id[row['id']]=row
            continue
        if any(row[k]!=previous[k] for k in ('name','path','span')):
            raise ValueError('Ambiguous source identity: symbol ID points to distinct spans: '+row['id'])
        merged={**row,**previous}
        for field in ('features','calls','semantic_tags'):
            if field in row or field in previous:
                merged[field]=sorted(set(row.get(field,()))|set(previous.get(field,())))
        merged['doc']=previous.get('doc') or row.get('doc','')
        by_id[row['id']]=merged
    return list(by_id.values())


def acquire(root, folder, repo, *, loader=fetch):
    meta = json.loads(loader(f'https://api.github.com/repos/{repo}/commits/HEAD', 2 * 1024 * 1024))
    commit = meta.get('sha', '')
    if not re.fullmatch('[0-9a-f]{40}', commit):
        raise ValueError('无法确认仓库提交版本')
    files = unpack_python(loader(f'https://api.github.com/repos/{repo}/zipball/{commit}', MAX_ARCHIVE))
    source = folder / 'benchmarks/sources/imported'; source.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, data in sorted(files.items()):
        path = source / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)
        manifest.append(dict(path=name, bytes=len(data), sha256=digest(data), git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()))
    snapshot = dict(schema_version='1.0.0', object_type='RepoSnapshot', is_fixture=False,
                    snapshot_id='github-'+digest(repo.encode())[:10]+'-'+commit[:12], url='https://github.com/'+repo,
                    commit=commit, license='not_checked', retrieved_at=datetime.now(timezone.utc).isoformat(),
                    hash=digest(json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()),
                    hash_scope='selected_files_manifest_sha256', snapshot_scope='bounded public GitHub Python source', files=manifest)
    (source/'snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    (folder/'schemas').mkdir(exist_ok=True)
    for name in ('contracts.schema.json', 'contracts-1.1.schema.json'):
        shutil.copyfile(root/'schemas'/name, folder/'schemas'/name)
    graph = extract_snapshot(source, snapshot)
    symbols = []
    diagnostics=[]
    graph_by_span=DefinitionIndex(
        ((s['path'],n['name'],n['kind'],s['start_line'],s['end_line']),n)
        for n in graph['nodes'] for s in [n['source_span']])
    conditional=[]
    for name, data in sorted(files.items()):
        try:
            tree = ast.parse(data.decode('utf-8'))
        except (SyntaxError, RecursionError):
            continue

        definitions=[(node,node.name) for node in tree.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))]
        conditional.extend((name,n) for n in scoped_nodes(tree.body) if isinstance(n,DEFINITION)
                           and n not in tree.body and not n.name.startswith('_'))
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef) and not cls.name.startswith('_'):
                definitions.extend((node,cls.name+'.'+node.name) for node in cls.body if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)))
        for node,qualname in definitions:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) or node.name.startswith('_'):
                continue
            gn = graph_by_span.match(definition_key(name,qualname,node),diagnostics)
            if not gn: continue
            calls = call_expressions(node)
            symbols.append(dict(id=gn['id'], name=qualname, path=name, span=gn['source_span'],
                                features=features(node), doc=(ast.get_docstring(node) or '')[:800], calls=calls,
                                test_source=any(p in ('tests','test') for p in PurePosixPath(name).parts) or PurePosixPath(name).name.startswith('test_')))
    if not symbols:
        for path,node in conditional:
            gn=graph_by_span.match(definition_key(path,node.name,node),diagnostics)
            if gn:
                symbols.append(dict(id=gn['id'],name=node.name,path=path,span=gn['source_span'],features=features(node),
                                    calls=call_expressions(node),doc=(ast.get_docstring(node) or '')[:800],
                                    test_source=bool({'tests','test'} & set(PurePosixPath(path).parts)) or PurePosixPath(path).name.startswith('test_')))
    if not symbols:
        raise ValueError('未找到可规划的顶层公开函数或类；请选择包含公开 Python API 的仓库')
    result = dict(repository=repo, snapshot=snapshot, symbols=normalize_symbols(symbols),identity_diagnostics=diagnostics,
                  graph_summary=dict(nodes=len(graph['nodes']), edges=len(graph['edges']), calls_policy='unresolved; suggestions only'),
                  parse_manifest=graph['source_manifest'])
    (folder/'repository.json').write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    (folder/'graph.json').write_text(json.dumps(graph, ensure_ascii=False), encoding='utf-8')
    return result
