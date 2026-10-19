"""Teaching claims are separate from AST facts and fail closed for hard use."""

def hard_edges(units):
    ids = [u['id'] for u in units]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate learning unit')
    result = []
    for unit in units:
        for edge in unit['prerequisites']:
            if edge['unit_id'] not in ids:
                raise ValueError('Dangling teaching prerequisite')
            p = edge['provenance']
            if edge['relation_type'] != 'teaching_prerequisite':
                raise ValueError('Code edges cannot be used as teaching edges')
            if edge['hard']:
                # Approval label alone is insufficient: an explicit human record is mandatory.
                if (p['kind'] != 'teaching_judgment' or p['review_status'] != 'approved'
                    or not p['reviewer'] or not p['evidence']
                    or not any(x.startswith('human-review:') for x in p['evidence'])):
                    raise ValueError('Hard prerequisite lacks explicit human review record')
                result.append((edge['unit_id'], unit['id']))
    if cyclic_components(set(ids), result):
        raise ValueError('Hard prerequisites contain a cycle; review/cluster before planning')
    return sorted(result)


def cyclic_components(nodes, edges):
    """Tarjan SCCs; report cycles rather than deleting an edge."""
    adjacency = {n: [] for n in nodes}
    for a, b in edges:
        if a not in adjacency or b not in adjacency:
            raise ValueError('Unknown cycle endpoint')
        adjacency[a].append(b)
    index, stack, active, indices, low, components = 0, [], set(), {}, {}, []
    def visit(v):
        nonlocal index
        indices[v] = low[v] = index
        index += 1
        stack.append(v);active.add(v)
        for w in sorted(adjacency[v]):
            if w not in indices:
                visit(w);low[v] = min(low[v], low[w])
            elif w in active:
                low[v] = min(low[v], indices[w])
        if low[v] == indices[v]:
            part = []
            while True:
                w = stack.pop();active.remove(w);part.append(w)
                if w == v:break
            if len(part) > 1 or v in adjacency[v]:components.append(sorted(part))
    for n in sorted(nodes):
        if n not in indices:visit(n)
    return sorted(components)
