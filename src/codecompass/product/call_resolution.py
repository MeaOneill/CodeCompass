"""Conservative source-only call resolution for reading-order suggestions."""
import ast
from collections import defaultdict
from pathlib import PurePosixPath


FUNCTION = (ast.FunctionDef, ast.AsyncFunctionDef)
DEFINITION = (*FUNCTION, ast.ClassDef)


def scoped_nodes(statements):
    """Walk a body without attributing nested definitions to its enclosing symbol."""
    stack = list(reversed(statements))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (*DEFINITION, ast.Lambda)):
            stack.extend(reversed(list(ast.iter_child_nodes(node))))


def call_expressions(node):
    return sorted({ast.unparse(call.func) for call in scoped_nodes(node.body) if isinstance(call, ast.Call)})


def bound_names(nodes):
    names = set()
    for node in nodes:
        if isinstance(node, DEFINITION):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update(a.asname or a.name.split('.')[0] for a in node.names)
        elif isinstance(node, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)) and node.name:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest:
            names.add(node.rest)
    return names


def cross_file_relations(contents, symbols, caller_ids):
    """Resolve explicit imports against snapshot definitions, without importing code."""
    modules = defaultdict(set)
    trees = {}
    definitions = defaultdict(dict)
    by_location = {(s['path'],s['name'],s['span']['end_line']):s for s in symbols if not s['test_source']}
    for path,raw in contents.items():
        if not path.endswith('.py'):
            continue
        parts = list(PurePosixPath(path).with_suffix('').parts)
        if parts[-1]=='__init__':
            parts.pop()
        if parts:
            modules['.'.join(parts)].add(path)
            if parts[0]=='src' and len(parts)>1:
                modules['.'.join(parts[1:])].add(path)
        try:
            trees[path]=ast.parse(raw.decode('utf-8'))
        except (SyntaxError,UnicodeError,RecursionError):
            continue
        body=trees[path].body
        for node in body:
            if isinstance(node,DEFINITION) and (symbol:=by_location.get((path,node.name,node.end_lineno))):
                other=(n for n in scoped_nodes(body) if n is not node)
                if node.name not in bound_names(other) and not any(isinstance(n,ast.ImportFrom) and
                        any(a.name=='*' for a in n.names) for n in scoped_nodes(body)):
                    definitions[path][node.name]=(node,symbol)

    def module_path(module):
        matches=modules[module]
        return next(iter(matches)) if len(matches)==1 else None

    imports={}
    for path,tree in sorted(trees.items()):
        bindings={}
        imports[path]=bindings
        body=tree.body
        if any(isinstance(n,ast.ImportFrom) and any(a.name=='*' for a in n.names) for n in scoped_nodes(body)):
            continue
        package=list(PurePosixPath(path).parts[:-1])
        if package and package[0]=='src':
            package=package[1:]
        for node in body:
            if not isinstance(node,(ast.Import,ast.ImportFrom)):
                continue
            other=bound_names(n for n in scoped_nodes(body) if n is not node)
            names=[a.asname or a.name.split('.')[0] for a in node.names]
            for alias,local in zip(node.names,names):
                if local in other or names.count(local)!=1:
                    continue
                if isinstance(node,ast.Import):
                    if alias.asname or '.' not in alias.name:
                        if imported:=module_path(alias.name):
                            bindings[local]=(imported,None,node.lineno)
                    continue
                if node.level>len(package):
                    continue
                base=package[:len(package)-node.level+1] if node.level else []
                module='.'.join(base+([node.module] if node.module else []))
                imported=module_path(module)
                submodule=module_path('.'.join(filter(None,(module,alias.name))))
                if imported and not submodule:
                    bindings[local]=(imported,alias.name,node.lineno)
                elif submodule and node.module is None:
                    if not modules[module] or (imported in trees and not trees[imported].body):
                        bindings[local]=(submodule,None,node.lineno)

    def exported(path,name,visited=frozenset()):
        found=definitions[path].get(name)
        if found:
            return found
        if not path.endswith('/__init__.py') or (path,name) in visited:
            return None
        binding=imports.get(path,{}).get(name)
        if binding and binding[1]:
            return exported(binding[0],binding[1],visited|{(path,name)})
        return None

    def lookup(path,expr,shadow,before=float('inf')):
        bare=isinstance(expr,ast.Name)
        if not bare and not (isinstance(expr,ast.Attribute) and isinstance(expr.value,ast.Name)):
            return None
        receiver=expr.id if bare else expr.value.id
        if receiver in shadow:
            return None
        binding=imports[path].get(receiver)
        if binding and binding[2]<before:
            target,name,_=binding
            if bare and name:
                return exported(target,name)
            if not bare and not name:
                return exported(target,expr.attr)
        return None

    bases=defaultdict(list)
    subclasses=defaultdict(list)
    class_nodes={}
    for path,rows in definitions.items():
        for name,(node,symbol) in rows.items():
            if not isinstance(node,ast.ClassDef):
                continue
            key=(path,name)
            class_nodes[key]=node
            for base in node.bases:
                bound=lookup(path,base,set(),node.lineno)
                if isinstance(base,ast.Name) and not bound:
                    bound=rows.get(base.id)
                    if bound and bound[0].lineno>=node.lineno:
                        bound=None
                if bound and isinstance(bound[0],ast.ClassDef):
                    target=(bound[1]['path'],bound[1]['name'])
                    bases[key].append((base,bound))
                    subclasses[target].append(key)

    def has_override(owner,name):
        pending=list(subclasses[owner]);seen=set()
        while pending:
            child=pending.pop()
            if child in seen:
                continue
            seen.add(child)
            body=class_nodes[child].body
            if name in bound_names(scoped_nodes(body)) or any(
                isinstance(n,ast.Attribute) and n.attr==name and isinstance(n.ctx,(ast.Store,ast.Del))
                for n in ast.walk(class_nodes[child])):
                return True
            pending.extend(subclasses[child])
        return False

    for path,tree in sorted(trees.items()):
        if not any(p==path and s['id'] in caller_ids for (p,_,_),s in by_location.items()):
            continue
        body=tree.body
        def scan(node,qualified,owner=None,parents=()):
            caller=by_location.get((path,qualified,node.end_lineno))
            if not caller or caller['id'] not in caller_ids:
                return
            statements=list(scoped_nodes(node.body))
            written=bound_names(statements)
            local=written|{n.arg for n in ast.walk(node.args) if isinstance(n,ast.arg)}
            positional=node.args.posonlyargs+node.args.args
            for call in statements:
                if not isinstance(call,ast.Call):
                    continue
                target=lookup(path,call.func,local)
                expression=ast.unparse(call.func)
                site=dict(caller=caller['id'],path=path,line=call.lineno,expression=expression)
                if target and isinstance(target[0],FUNCTION) and target[1]['path']!=path:
                    yield dict(site,callee=target[1]['id'],basis='snapshot_explicit_import')
                if not (owner and parents and positional and isinstance(call.func,ast.Attribute)
                        and isinstance(call.func.value,ast.Name)):
                    continue
                receiver=call.func.value.id
                if receiver!=positional[0].arg or receiver not in ('self','cls') or receiver in written:
                    continue
                attr=call.func.attr
                dynamic={'__getattr__','__getattribute__','__setattr__',attr}
                child_bindings=bound_names(scoped_nodes(owner.body))
                attributes_written={n.attr for n in ast.walk(owner) if isinstance(n,ast.Attribute) and isinstance(n.ctx,(ast.Store,ast.Del))}
                if dynamic & (child_bindings|attributes_written):
                    continue
                for _,(cls,symbol) in parents:
                    if symbol['path']==path:
                        continue
                    methods=[n for n in cls.body if isinstance(n,FUNCTION) and n.name==attr]
                    if len(methods)!=1:
                        continue
                    method=by_location.get((symbol['path'],f"{symbol['name']}.{attr}",methods[0].end_lineno))
                    if not method:
                        continue
                    ambiguous=(len(owner.bases)!=1 or methods[0].decorator_list or cls.bases or
                               cls.decorator_list or cls.keywords or owner.decorator_list or owner.keywords or
                               dynamic & bound_names(n for n in scoped_nodes(cls.body) if n not in methods))
                    overridden=has_override((path,owner.name),attr)
                    if ambiguous or overridden:
                        reason='known_subclass_override' if overridden else 'ambiguous_method_dispatch'
                        yield dict(site,callee=method['id'],basis=reason,kind='call_candidate')
                    else:
                        yield dict(site,callee=method['id'],basis='snapshot_direct_imported_base_method',
                                   confidence_scope='fixed_snapshot_no_known_subclass_override')

        for node in body:
            if isinstance(node,FUNCTION):
                yield from scan(node,node.name)
            elif isinstance(node,ast.ClassDef):
                child=by_location.get((path,node.name,node.end_lineno))
                parents=bases.get((path,node.name),()) if class_nodes.get((path,node.name)) is node else ()
                if child and child['id'] in caller_ids:
                    for base,parent in parents:
                        if parent[1]['path']==path:
                            continue
                        yield dict(caller=child['id'],callee=parent[1]['id'],path=path,line=base.lineno,
                                   basis='snapshot_explicit_imported_base',expression=ast.unparse(base),kind='verified_inheritance')
                for method in node.body:
                    if isinstance(method,FUNCTION):
                        yield from scan(method,f'{node.name}.{method.name}',node,parents)


def resolved_calls(contents, symbols, caller_ids):
    by_path = defaultdict(list)
    for symbol in symbols:
        if not symbol['test_source']:
            by_path[symbol['path']].append(symbol)
    for path, rows in sorted(by_path.items()):
        if not any(s['id'] in caller_ids for s in rows):
            continue
        try:
            tree = ast.parse(contents[path].decode('utf-8'))
        except (SyntaxError, RecursionError):
            continue
        by_location = {(s['name'], s['span']['end_line']):s for s in rows}
        top = defaultdict(list)
        for node in tree.body:
            if isinstance(node, DEFINITION):
                symbol = by_location.get((node.name, node.end_lineno))
                if symbol:
                    top[node.name].append(symbol)
        definitions = {n for n in tree.body if isinstance(n, DEFINITION)}
        rebound = bound_names(n for n in scoped_nodes(tree.body) if n not in definitions)
        classes = defaultdict(list)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                classes[node.name].append(node)

        def class_method(cls, name):

            methods = [n for n in cls.body if isinstance(n, FUNCTION) and n.name == name]
            other_bindings = bound_names(n for n in scoped_nodes(cls.body) if n not in methods)
            if name in other_bindings or len(methods) > 1:
                return None
            if methods:
                return by_location.get((f'{cls.name}.{name}', methods[0].end_lineno)), 'same_file_class_method'
            if len(cls.bases) == 1 and isinstance(cls.bases[0], ast.Name):
                base = cls.bases[0].id
                if len(classes[base]) == 1 and len(top[base]) == 1 and base not in rebound:
                    parent = classes[base][0]
                    inherited = [n for n in parent.body if isinstance(n, FUNCTION) and n.name == name]
                    bindings = bound_names(n for n in scoped_nodes(parent.body) if n not in inherited)
                    if len(inherited) == 1 and name not in bindings:
                        target = by_location.get((f'{parent.name}.{name}', inherited[0].end_lineno))
                        return target, 'same_file_direct_base_method'
            return None

        def scan(node, qualname, owner=None):
            caller = by_location.get((qualname, node.end_lineno))
            if not caller or caller['id'] not in caller_ids:
                return
            body = list(scoped_nodes(node.body))
            local = bound_names(body) | {a.arg for a in ast.walk(node.args) if isinstance(a, ast.arg)}
            written = bound_names(body)
            positional = node.args.posonlyargs + node.args.args
            for call in body:
                if not isinstance(call, ast.Call):
                    continue
                target = None
                func = call.func
                if isinstance(func, ast.Name):
                    matches = top.get(func.id, ())
                    if func.id not in local and func.id not in rebound and len(matches) == 1:
                        target = matches[0], 'same_file_unique_module_definition'
                elif isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                    receiver = func.value.id
                    if (owner is not None and positional and positional[0].arg == receiver
                            and receiver in ('self','cls') and receiver not in written
                            and len(classes[owner.name]) == 1 and len(top[owner.name]) == 1 and owner.name not in rebound):
                        target = class_method(owner, func.attr)
                    elif receiver not in local and receiver not in rebound and len(classes[receiver]) == 1 and len(top[receiver]) == 1:
                        target = class_method(classes[receiver][0], func.attr)
                if target and target[0]:
                    symbol, basis = target
                    yield dict(caller=caller['id'], callee=symbol['id'], path=path,
                               line=call.lineno, basis=basis, expression=ast.unparse(func))

        for node in tree.body:
            if isinstance(node, FUNCTION):
                yield from scan(node, node.name)
            elif isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, FUNCTION):
                        yield from scan(method, f'{node.name}.{method.name}', node)
