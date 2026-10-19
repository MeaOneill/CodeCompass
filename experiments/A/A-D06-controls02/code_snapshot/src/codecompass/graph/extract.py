"""Deterministic Python AST declarations and syntax, without executing input."""
import ast
from .provenance import digest, make_span, read_snapshot, validate_span


class Extractor(ast.NodeVisitor):
    def __init__(self, snapshot, path, text):
        self.snapshot, self.path, self.text = snapshot, path, text
        self.nodes, self.edges = [], []
        self.scope = [(path + '::module', '')]
        self.add_node(self.scope[0][0], 'module', path, 1, max(1, len(text.splitlines())))

    def span(self, start, end):
        return make_span(self.snapshot['snapshot_id'], self.path, self.text, start, end)

    def add_node(self, identity, kind, name, start, end, **extra):
        self.nodes.append({'id': identity, 'kind': kind, 'name': name,
                           'source_span': self.span(start, end), **extra})

    def edge(self, kind, target, node, **extra):
        self.edges.append({'kind': kind, 'from': self.scope[-1][0], 'to': target,
                           'source_span': self.span(node.lineno, node.end_lineno),
                           'provenance': 'static_ast', **extra})

    def definition(self, node, kind):
        qual = '.'.join(x for x in (self.scope[-1][1], node.name) if x)
        identity = f'{self.path}::{qual}@{node.lineno}'
        start = min([node.lineno] + [d.lineno for d in node.decorator_list])
        self.add_node(identity, kind, qual, start, node.end_lineno)
        self.edge('contains', identity, node, resolution='syntactic_fact')
        self.scope.append((identity, qual))
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node):
        self.definition(node, 'function')

    def visit_AsyncFunctionDef(self, node):
        self.definition(node, 'async_function')

    def visit_ClassDef(self, node):
        self.definition(node, 'class')

    def imports(self, node, module, level):
        for index, alias in enumerate(node.names):
            target = f'{self.path}::import@{node.lineno}:{node.col_offset}:{index}'
            self.add_node(target, 'import_reference', alias.name, node.lineno, node.end_lineno,
                          module=module, level=level, alias=alias.asname)
            self.edge('imports', target, node, resolution='declaration_only',
                      module=module, symbol=alias.name, level=level, alias=alias.asname)

    def visit_Import(self, node):
        self.imports(node, None, 0)

    def visit_ImportFrom(self, node):
        self.imports(node, node.module, node.level)

    def visit_Call(self, node):
        # No name/type/runtime inference: even a simple name may be rebound.
        self.edge('call_unknown', None, node, resolution='unknown',
                  expression=ast.unparse(node.func), column=node.col_offset,
                  reason='Syntax identifies a call expression; target binding is not resolved')
        self.generic_visit(node)


def extract_snapshot(root, snapshot):
    contents = read_snapshot(root, snapshot)
    nodes, edges, manifest = [], [], []
    for path, data in sorted(contents.items()):
        if not path.endswith('.py'):
            continue
        entry = {'path': path, 'sha256': digest(data), 'bytes': len(data),
                 'commit': snapshot['commit'], 'snapshot_id': snapshot['snapshot_id'],
                 'status': 'parsed', 'diagnostic': None}
        try:
            text = data.decode('utf-8')
            # Empty files have no 1-based span; keep the manifest record only.
            if not text.splitlines():
                entry['status'] = 'empty'
            else:
                tree = ast.parse(text, filename=path)
                visitor = Extractor(snapshot, path, text)
                visitor.visit(tree)
                for record in visitor.nodes + visitor.edges:
                    validate_span(record['source_span'], snapshot, contents)
                nodes.extend(visitor.nodes)
                edges.extend(visitor.edges)
        except (SyntaxError, UnicodeDecodeError) as exc:
            entry.update(status='parse_error', diagnostic=str(exc))
        manifest.append(entry)
    nodes.sort(key=lambda n: n['id'])
    edges.sort(key=lambda e: (e['source_span']['path'], e['source_span']['start_line'],
                              e['kind'], e['from'], str(e['to']), e.get('column', -1)))
    for index, edge in enumerate(edges):
        edge['id'] = f'edge_{index:06d}'
    return {'graph_format_version': '0.1.0', 'snapshot_id': snapshot['snapshot_id'],
            'commit': snapshot['commit'], 'nodes': nodes, 'edges': edges,
            'source_manifest': manifest, 'calls_policy': 'all_unresolved_unknown',
            'scope': snapshot['snapshot_scope']}
