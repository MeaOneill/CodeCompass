"""Goal-grounded dynamic units and a bounded coverage search with explicit J.

Reuse the contract/source validator, conservative evidence gate and replay from D05.
Self report changes requested scaffolding and proxy cost, never the evidence ledger.
"""
import math
import re
import time
from collections import Counter
from urllib.parse import quote
from codecompass.graph import read_snapshot
from codecompass.graph.provenance import digest
from codecompass.learner import mastery_gate
from codecompass.planner.adaptive import validate_input, personalized_costs, request_for_state, route_audit, switch_distance
from .repositories import FEATURES, normalize_symbols
from .goal_resolution import resolve
from .call_resolution import cross_file_relations, resolved_calls

ALIASES = {'分组':'chunk group batch', '去重':'unique duplicate dedup', '窗口':'window',
           '请求':'request get session', '网络':'http request url', '解析':'parse decode load',
           '编码':'encode dump', '装饰器':'decorator wrap', '缓存':'cache memo',
           '迭代':'iter yield generator', '排序':'sort order', '过滤':'filter select',
           '时间':'time date', '路径':'path file', '命令':'cli command', '验证':'valid check',
           '配置':'config setting', '重试':'retry', '连接':'connect pool', '文本':'text string', '签名':'sign signature verify'}
CONFIG = dict(version='source-route-v1', threshold=.7, quantile=.1)


def ranked_symbols(repo, goal):
    query = goal.lower()
    for zh, en in ALIASES.items():
        if zh in query: query += ' ' + en
    words = set(re.findall(r'[a-z][a-z0-9_]{1,}', query)) - {'python','learn','learning','understand','code','the','and','how'}
    def score(s):
        name = s['name'].lower(); path = s['path'].lower(); doc = s['doc'].lower()
        return sum(8 if w == name else 4 if w in name else 2 if w in path else 1 if w in doc else 0 for w in words) - (20 if s['test_source'] else 0)
    return [(score(s),s) for s in sorted(repo['symbols'], key=lambda s:(-score(s), s['path'],s['name']))]


def build(folder, repo, goal, selected, preferences, user, simulated, intent=None):
    repo={**repo,'symbols':normalize_symbols(repo['symbols'])}
    ranked = ranked_symbols(repo, goal)
    by_id = {s['id']:s for s in repo['symbols']}
    intent=intent or resolve(repo,goal,selected)
    if not intent:return None
    targets=[by_id[x] for x in intent['targets']]
    contents = read_snapshot(folder/'benchmarks/sources/imported', repo['snapshot'])
    target_ids = {s['id'] for s in targets}
    target_calls = list(resolved_calls(contents,repo['symbols'],target_ids))
    name_counts = Counter(s['name'] for s in repo['symbols'] if not s['test_source'])

    related_ids = {e['callee'] for e in target_calls
                   if e['basis'] != 'same_file_unique_module_definition' or name_counts[by_id[e['callee']]['name']] == 1} - target_ids
    related = sorted((by_id[x] for x in related_ids),key=lambda s:(s['path'],s['name'],s['id']))[:4]
    related_ids = {s['id'] for s in related}
    focus = targets + related
    profile = preferences.get('onboarding', {})
    familiar = set(profile.get('familiar', []))
    for c,row in preferences.get('assessment',{}).get('topics',{}).items():
        if row['correct']<row['answered']:familiar.discard(c)
        elif row['correct']>=2:familiar.add(c)
    from .learning_growth import verified
    familiar.update(verified(preferences))
    difficulty = preferences.get('source_feedback', {})
    familiar.update(c for c,v in difficulty.items() if v=='familiar')
    concepts = set(c for s in focus for c in s['features'])

    support = sorted(c for c in concepts if c not in familiar or difficulty.get(c) == 'hard')
    units = []; views = {}
    def add(key, span, covers, title, kind, reason):
        uid = 'dyn_' + digest(key.encode())[:20]
        text = contents[span['path']].decode('utf-8'); lines = text.splitlines()
        url = repo['snapshot']['url']+'/blob/'+repo['snapshot']['commit']+'/'+quote(span['path'])+f"#L{span['start_line']}-L{span['end_line']}"
        loc = span['end_line'] - span['start_line'] + 1
        level = preferences.get('assessment',{}).get('recommended_experience',profile.get('experience','new'))
        factor = {'new':1.5,'some':1.2,'comfortable':1.0}[level]
        if any(difficulty.get(c) == 'hard' for c in covers): factor *= 1.5
        cost = round((1 + math.log2(1+loc)) * factor, 4)
        units.append(dict(schema_version='1.0.0',object_type='LearningUnit',is_fixture=False,id=uid,
                          source_spans=[span],concept_ids=covers,prerequisites=[],
                          provenance=dict(kind='static_source',evidence=[url],proposed_by='CodeCompass AST importer',review_status='pending',reviewer=None,confidence=None),
                          base_cost=cost,cost_unit='proxy_cost',cost_basis='(1+log2(1+source_lines))*self_report_difficulty; not minutes'))
        views[uid] = dict(id=uid,title=title,kind=kind,path=span['path'],span=span,url=url,
                          code='\n'.join(lines[span['start_line']-1:span['end_line']]),concepts=covers,reason=reason)
        return uid
    target_concepts = []
    source_units = {}
    for s in focus:
        concept = 'source.'+digest(s['id'].encode())[:20]; target_concepts.append(concept)
        nested=['source.'+digest(v['id'].encode())[:20] for v in focus if v['id']!=s['id'] and v['path']==s['path'] and v['span']['start_line']>=s['span']['start_line'] and v['span']['end_line']<=s['span']['end_line']]
        source_units[s['id']] = add(s['id'], s['span'], [concept]+nested, s['name'], 'target' if s in targets else 'related',
                                    '围绕你的学习目标，阅读这一部分的实现。' if s in targets else '先了解目标代码使用到的关联实现。')
        views[source_units[s['id']]]['pedagogical_features'] = sorted(set(s['features']) & FEATURES.keys())

    chosen = []; counts = {c:0 for c in support}
    focus_ids={s['id'] for s in focus}
    for _,s in ranked:
        if s['test_source'] or s['id'] in focus_ids: continue
        cover = set(s['features']) & set(support)
        if not cover or not any(counts[c] < 3 for c in cover): continue
        if s['span']['end_line'] - s['span']['start_line'] > 100: continue
        chosen.append(s)
        for c in cover: counts[c] += 1
        if len(chosen) >= 30 or all(n >= 3 for n in counts.values()): break
    for s in chosen:

        cover = sorted(set(s['features']) & set(support))
        uid = add('support:'+s['id'],s['span'],cover,'基础例子 · '+s['name'],'foundation',
                  '通过这个例子理解'+'、'.join(FEATURES[c] for c in cover)+'。')
        views[uid]['pedagogical_features'] = sorted(set(s['features']) & FEATURES.keys())
    available = {c for u in units for c in u['concept_ids']}
    missing_support = sorted(set(support)-available)
    if missing_support:

        for s in focus:
            cover = sorted(set(s['features']) & set(missing_support))
            if cover:
                existing=next(u for u in units if u['source_spans']==[s['span']])
                existing['concept_ids']=sorted(set(existing['concept_ids'])|set(cover))
                views[existing['id']]['concepts']=list(existing['concept_ids'])
                missing_support = sorted(set(missing_support)-set(cover))
    if len(units)!=len(views):
        raise ValueError('Ambiguous source identity: duplicate learning unit')
    request = dict(schema_version='1.0.0',object_type='PlanningRequest',is_fixture=simulated,
                   request_id='dynamic-'+digest((user+goal).encode())[:20],snapshot_id=repo['snapshot']['snapshot_id'],task_id='dynamic-source',
                   learner_state=[],budget=10000,cost_unit='proxy_cost',config_version=CONFIG['version'],
                   target_concept_ids=sorted(set(target_concepts+support)),unit_ids=[u['id'] for u in units],prior_plan_id=None)
    related_calls = resolved_calls(contents,repo['symbols'],{s['id'] for s in related})
    imported_calls = (edge for edge in cross_file_relations(contents,repo['symbols'],source_units.keys())
                      if edge.get('kind') not in ('verified_inheritance','call_candidate'))
    order_edges = [dict(edge, before=source_units[edge['callee']], after=source_units[edge['caller']])
                   for edge in [*target_calls,*related_calls,*imported_calls]
                   if edge['callee'] in source_units and edge['callee'] != edge['caller']]
    order_familiar = (familiar - {c for c,v in difficulty.items() if v == 'hard'}) & FEATURES.keys()
    return dict(request=request,units=units,views=views,targets=[s['id'] for s in targets],intent=intent,
                verified_order_edges=order_edges,order_familiar_features=sorted(order_familiar),
                support=support,self_report_familiar=sorted(familiar & concepts),
                dependencies=[dict(source=caller,target=callee,hard=False,resolution='verified_static_call')
                              for caller,callee in sorted({(e['caller'],e['callee']) for e in target_calls
                                                           if e['callee'] in related_ids})])


def solve(folder, data, ledger, *, completed=(), reference=(), spent=0, budget=10000, seconds=1.5):
    """Bounded full ordered-prefix beam, shared support counted once.

    J = personalized proxy cost + .4 duplicate concepts + 1 switch distance.
    Foundation/dependency order is a visible suggestion, not a hard prerequisite.
    """
    req = request_for_state(data['request'], ledger, CONFIG); req['budget'] = budget
    units = data['units']; by_id = {u['id']:u for u in units}
    validate_input(folder,req,units,ledger,CONFIG)
    costs = personalized_costs(req,units,ledger,CONFIG,.5)
    gate = mastery_gate(ledger,req['snapshot_id'],set(c for u in units for c in u['concept_ids']),allow_simulated=req['is_fixture'])
    initial = {c for c,g in gate.items() if g['mastered']} | {c for u in completed for c in by_id[u]['concept_ids']}
    goals = set(req['target_concept_ids'])
    def known(route): return initial | {c for uid in route for c in by_id[uid]['concept_ids']}
    def duplicate(route):
        seq = [c for uid in list(completed)+list(route) for c in by_id[uid]['concept_ids']]
        return len(seq)-len(set(seq))
    def objective(route): return math.fsum(costs[x] for x in route)+.4*duplicate(route)+switch_distance(reference,route,len(units))
    def order(route):

        priority = {'foundation':0,'related':1,'target':2}
        return tuple(sorted(route,key=lambda x:(priority[data['views'][x]['kind']],x)))
    def soft_order_violations(route):
        priority = {'foundation':0,'related':1,'target':2}
        return sum(priority[data['views'][a]['kind']]>priority[data['views'][b]['kind']]
                   for i,a in enumerate(route) for b in route[i+1:])
    def quality(route): return (objective(route),soft_order_violations(route),len(route),route)
    def legal(route): return spent+objective(route) <= budget+1e-9
    def rank(route): return (len(goals-known(route)), *quality(route))
    candidates = [u['id'] for u in units if u['id'] not in completed]

    greedy = (); expansions = 0
    while goals-known(greedy):
        choices = [x for x in candidates if x not in greedy and (set(by_id[x]['concept_ids']) & (goals-known(greedy))) and legal(order(greedy+(x,)))]
        if not choices: break
        x = min(choices,key=lambda x:((objective(order(greedy+(x,)))-objective(greedy))/len(set(by_id[x]['concept_ids']) & (goals-known(greedy))),x))
        greedy = order(greedy+(x,))
    incumbent = greedy if goals <= known(greedy) else None
    reference_seed=tuple(reference)
    if reference_seed and goals<=known(reference_seed) and legal(reference_seed):
        if incumbent is None or quality(reference_seed)<quality(incumbent): incumbent=reference_seed
    partial = greedy; frontier = [()]; started = time.monotonic(); timed = False
    for _ in range(len(candidates)):
        pool = set()
        for route in frontier:
            for uid in candidates:
                if time.monotonic()-started > seconds or expansions >= 15000: timed = True; break
                if uid in route or not (set(by_id[uid]['concept_ids']) & (goals-known(route))): continue
                new = route+(uid,); expansions += 1
                if not legal(new): continue
                if rank(new) < rank(partial): partial = new
                if goals <= known(new):
                    if incumbent is None or quality(new) < quality(incumbent): incumbent = new
                else: pool.add(new)
            if timed: break
        if timed or not pool: break
        frontier = sorted(pool,key=rank)[:24]
    route = list(incumbent if incumbent is not None else partial)
    audit = route_audit(req,units,gate,route,costs,completed,reference,1,spent)
    dup = .4*duplicate(route)
    if not audit['valid'] or spent+audit['objective']+dup > budget+1e-9: raise ValueError('路线回放验证失败')
    return dict(version='source-route-v1',remaining=route,completed=list(completed),costs=costs,gate=gate,
                status='FEASIBLE' if incumbent is not None else 'LIMIT_REACHED' if timed else 'NO_FEASIBLE_FOUND',
                objective=objective(route),duplicate_cost=dup,switch_cost=audit['switch_cost'],learning_cost=audit['learning_cost'],
                budget=budget,spent=spent,audit=audit,expansions=expansions,search_limited=timed,optimality_claim=False,
                objective_formula='J=sum(personalized_proxy_cost)+0.4*duplicated_concepts+1.0*switch_distance',
                elapsed_seconds=time.monotonic()-started,state_key='full ordered prefix',
                soft_order_violations=soft_order_violations(route),
                order_policy='at equal J, prefer foundations and related implementations before targets; soft, never a hard prerequisite')
