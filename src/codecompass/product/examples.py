"""Execute only the verified public fixed-source functions used by P04 examples.

This is teaching context for a partial upstream bundle, never uploaded code.
"""
import ast
from functools import partial
from itertools import islice
from pathlib import Path
from codecompass.app.journey_d07 import cross_data
from codecompass.graph import read_snapshot, validate_span

def pinned_chunked(root):
    root=Path(root);data=cross_data(root,'public-example',True)
    contents=read_snapshot(root/data['source_root'],data['snapshot'])
    for row in data['source_context']:validate_span(row['source_span'],data['snapshot'],contents)
    definitions=[]
    for path,name in [('more_itertools/recipes.py','take'),('more_itertools/more.py','chunked')]:
        source=(root/data['source_root']/path).read_text(encoding='utf-8')
        definitions.append(next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name==name))
    namespace={'partial':partial,'islice':islice}
    exec(compile(ast.Module(body=definitions,type_ignores=[]),'<verified P04 excerpts>','exec'),namespace)
    return namespace

def execution_code(code,context=None):
    if context is None:return code
    if context!='pinned_chunked':raise ValueError('未知教学执行上下文')
    return 'from pathlib import Path\nfrom codecompass.product.examples import pinned_chunked\nexec('+repr(code)+', pinned_chunked(Path.cwd()))'
