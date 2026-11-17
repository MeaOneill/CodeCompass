"""A source-grounded overview; structural edges and study order stay separate."""
import json
from pathlib import PurePosixPath
from itertools import chain
from .goal_resolution import enrich
from .call_resolution import cross_file_relations, resolved_calls
from codecompass.graph import read_snapshot


def overview(workspaces,uid,route_id):
    route=workspaces.route(uid,route_id);state=route['state'];folder=workspaces.root/route['repository_id']
    repo=enrich(folder,workspaces._repo(route['repository_id']))
    graph=json.loads((folder/'graph.json').read_text(encoding='utf-8'))
    symbols={s['id']:s for s in repo['symbols']}
    contents=read_snapshot(folder/'benchmarks/sources/imported',repo['snapshot'])
    projected=state['result'].get('reading_order',{})
    incremental=projected.get('scope')=='remaining'
    explanations=projected.get('explanations',{})
    selected=set(state['result']['remaining'])
    dropped={tuple(edge) for edge in projected.get('dropped_cycle_edges',[])}
    active={(e['caller'],e['callee'],e['path'],e['line']) for e in state['data'].get('verified_order_edges',[])
            if projected.get('status')=='applied' and {e['before'],e['after']}<=selected
            and (e['before'],e['after']) not in dropped}
    verified={}
    inheritance=[]; uncertain={}
    for site in chain(resolved_calls(contents,symbols.values(),symbols.keys()),
                      cross_file_relations(contents,symbols.values(),symbols.keys())):
        pair=(site['caller'],site['callee'])
        if site.get('kind')=='verified_inheritance':
            inheritance.append(dict(site,source=pair[0],target=pair[1]))
            continue
        if site.get('kind')=='call_candidate':
            uncertain.setdefault(pair,dict(site,source=pair[0],target=pair[1],resolution='ambiguous_dynamic_binding'))
            continue
        site['used_for_order']=(pair[0],pair[1],site['path'],site['line']) in active
        if pair not in verified:
            verified[pair]=dict(site,source=pair[0],target=pair[1],kind='verified_call',sites=[])
        verified[pair]['sites'].append(site)
    by_name={}
    for symbol in symbols.values():by_name.setdefault(symbol['name'].rsplit('.',1)[-1],[]).append(symbol)
    nodes=[];edges=[];by_span={};path_ids={}
    edges.extend(verified.values())
    edges.extend(inheritance)
    for entry in repo['snapshot']['files']:
        path=entry['path'];identity='file:'+path;path_ids[path]=identity
        nodes.append(dict(id=identity,kind='file',label=path,path=path,selected=False,steps=[],
                          test=any(p in ('tests','test') for p in path.split('/')) or PurePosixPath(path).name.startswith('test_')))
        edges.append(dict(source='repository',target=identity,kind='contains'))
    for symbol in sorted(symbols.values(),key=lambda s:(s['path'],s['span']['start_line'],s['id'])):
        span=symbol['span'];identity=symbol['id'];key=(span['path'],span['start_line'],span['end_line'])
        by_span[key]=identity
        nodes.append(dict(id=identity,kind='symbol',label=symbol['name'],path=symbol['path'],span=span,selected=False,steps=[],
                          target=identity in state['data']['targets'],test=symbol['test_source']))
        edges.append(dict(source=path_ids[symbol['path']],target=identity,kind='contains'))
    by_id={n['id']:n for n in nodes};steps=[]
    for i,unit in enumerate(state['completed']+state['result']['remaining'],1):
        view=state['data']['views'][unit];span=view['span'];identity=by_span.get((span['path'],span['start_line'],span['end_line']))
        if identity is None:continue
        node=by_id[identity];node['selected']=True;node['steps'].append(i)
        file_node=by_id[path_ids[view['path']]];file_node['selected']=True;file_node['steps'].append(i)
        steps.append(dict(number=i,unit_id=unit,node_id=identity,title=view['title'].replace('基础例子 · ','基础研读 · '),
                          path=view['path'],kind=view['kind'],completed=unit in state['completed'],url=view['url'],
                          reason=route['insights']['lessons'][unit]['reason'],
                          order_reason=None if incremental else explanations.get(unit)))

    modules={}
    for path,identity in path_ids.items():
        name=path[:-3].replace('/','.')
        modules[name]=identity
        if name.endswith('.__init__'):modules[name[:-9]]=identity
    edges.extend(e for pair,e in uncertain.items() if pair not in verified)
    seen={(*pair,'call_candidate') for pair in uncertain};unresolved=0
    for edge in graph['edges']:
        if edge['kind']=='imports':
            path=edge['source_span']['path'];name=edge.get('module') or edge.get('symbol','')
            if edge.get('level'):
                package=path.split('/')[:-1];level=edge['level'];base=package[:len(package)-level+1]
                name='.'.join(base+([name] if name else []))
            target=modules.get(name)
            if target and target!=path_ids[path]:
                key=(path_ids[path],target,'imports')
                if key not in seen:edges.append(dict(source=key[0],target=key[1],kind=key[2],line=edge['source_span']['start_line']));seen.add(key)
        elif edge['kind']=='call_unknown':
            expression=edge.get('expression','');name=expression.rsplit('.',1)[-1]
            candidates=by_name.get(name,[])
            if edge['from'] in symbols and len(candidates)==1:
                if (edge['from'],candidates[0]['id']) in verified:continue
                key=(edge['from'],candidates[0]['id'],'call_candidate')
                if key not in seen:edges.append(dict(source=key[0],target=key[1],kind=key[2],line=edge['source_span']['start_line'],resolution='unique_name_candidate'));seen.add(key)
            else:unresolved+=1
    return dict(repository=state['repository'],goal=state['goal'],commit=repo['snapshot']['commit'],
                nodes=nodes,edges=edges,steps=steps,
                **({'remaining_order_explanations':explanations} if incremental else {}),
                study_edges=[dict(source=a['node_id'],target=b['node_id'],kind='study_order') for a,b in zip(steps,steps[1:]) if a['node_id']!=b['node_id']],
                counts=dict(files=len(path_ids),symbols=len(symbols),imports=sum(e['kind']=='imports' for e in edges),
                            verified_calls=len(verified),call_candidates=sum(e['kind']=='call_candidate' for e in edges),unresolved_calls=unresolved,selected=len(steps)))
