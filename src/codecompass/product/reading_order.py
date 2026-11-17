"""Reorder the first plan's fixed material selection using soft source evidence."""
import math
from time import perf_counter
from functools import lru_cache

from codecompass.graph import cyclic_components
from codecompass.planner.adaptive import route_audit


STAGE = {'foundation': 0, 'related': 1, 'target': 2}
EXACT_LIMIT = 10


def route_metrics(route, views, familiar):
    seen = set(familiar)
    increments = []
    for uid in route:
        features = set(views[uid]['pedagogical_features'])
        increments.append(len(features - seen))
        seen.update(features)
    violations = sum(STAGE[views[a]['kind']] > STAGE[views[b]['kind']]
                     for i,a in enumerate(route) for b in route[i+1:])
    return dict(increments=increments,mcs=max(increments,default=0),
                squares=sum(n*n for n in increments),category_violations=violations,
                target_before_foundation_pairs=sum(views[a]['kind']=='target' and views[b]['kind']=='foundation'
                    for i,a in enumerate(route) for b in route[i+1:]),
                related_before_foundation_pairs=sum(views[a]['kind']=='related' and views[b]['kind']=='foundation'
                    for i,a in enumerate(route) for b in route[i+1:]))


def concept_conditions(ids, views, units, support, familiar, gate, parents):
    """Keep only jointly feasible OR conditions, in stable target/topic order."""
    available = set(ids)
    topics = set(support) - set(familiar) - {t for t,g in gate.items() if g['mastered']}
    accepted = {u:[] for u in ids}
    dropped = []
    for uid in ids:
        if views[uid]['kind'] != 'target':
            continue
        for topic in sorted(topics & set(views[uid]['pedagogical_features'])):
            suppliers = [u for u in ids if views[u]['kind']=='foundation' and topic in units[u]['concept_ids']]
            condition = dict(target=uid,topic=topic,suppliers=suppliers)
            if not suppliers:
                dropped.append(dict(condition,dropped_reason='no_selected_foundation'))
                continue
            accepted[uid].append(condition)
            seen = set()
            while ready := {u for u in available-seen if parents[u]<=seen and
                            all(seen.intersection(c['suppliers']) for c in accepted[u])}:
                seen.update(ready)
            if seen != available:
                accepted[uid].pop()
                dropped.append(dict(condition,dropped_reason='conflicts_with_precedence'))
    return accepted,dropped


def exact_order(ids, parents, features, familiar, conditions=None):
    """Minimize peak first, then sum of squares at that peak."""
    conditions = conditions or {u:[] for u in ids}
    bits = {uid:1 << i for i,uid in enumerate(ids)}
    full = (1 << len(ids)) - 1
    required = {u:sum(bits[p] for p in parents[u]) for u in ids}
    supply = {u:[sum(bits[p] for p in c['suppliers']) for c in conditions[u]] for u in ids}

    @lru_cache(maxsize=None)
    def encountered(mask):
        if not mask:
            return frozenset(familiar)
        bit = mask & -mask
        return encountered(mask ^ bit) | features[ids[bit.bit_length()-1]]

    def transitions(mask):
        known = encountered(mask)
        for i,uid in enumerate(ids):
            bit = bits[uid]
            if not mask & bit and not required[uid] & ~mask and all(mask & group for group in supply[uid]):
                yield i,mask | bit,len(features[uid]-known)

    @lru_cache(maxsize=None)
    def peak(mask):
        if mask == full:
            return 0,1
        choices = [(max(delta,p),count) for _,nxt,delta in transitions(mask)
                   for p,count in [peak(nxt)] if count]
        return min((p for p,_ in choices),default=math.inf),sum(c for _,c in choices)

    limit,count = peak(0)

    @lru_cache(maxsize=None)
    def squares(mask):
        if mask == full:
            return 0,()
        choices = []
        for i,nxt,delta in transitions(mask):
            if delta <= limit and peak(nxt)[0] <= limit:
                suffix,route = squares(nxt)
                choices.append((delta*delta+suffix,(i,*route)))
        return min(choices)

    route = [ids[i] for i in squares(0)[1]] if count else []
    return route,count,peak.cache_info().currsize+squares.cache_info().currsize


def greedy_order(ids, parents, features, familiar, conditions):
    seen = set(familiar)
    route = []
    visited = set()
    while len(route)<len(ids):
        ready = [u for u in ids if u not in visited and parents[u]<=visited and
                 all(visited.intersection(c['suppliers']) for c in conditions[u])]
        if not ready:
            break
        uid = min(ready,key=lambda u:len(features[u]-seen))
        route.append(uid)
        visited.add(uid)
        seen.update(features[uid])
    return route


def supply_demands(ids, views, units, support, familiar, gate, parents):
    topics = set(support) - set(familiar) - {t for t,g in gate.items() if g['mastered']}
    features = {u:set(views[u]['pedagogical_features']) & topics for u in ids}

    @lru_cache(maxsize=None)
    def ancestors(uid):
        return {p for p in parents[uid]} | set().union(*(ancestors(p) for p in parents[uid]))

    demands = []
    for target in ids:
        if views[target]['kind'] != 'target':
            continue
        for topic in sorted(features[target]):
            candidates = []
            raw = []
            for uid in ids:
                if uid == target:
                    continue
                kind = views[uid]['kind']
                required = uid in ancestors(target)
                if (kind == 'foundation' and topic in units[uid]['concept_ids']) or (required and topic in features[uid]):
                    raw.append(uid)
                if topic not in features[uid]:
                    continue
                collateral = sorted(features[uid] - features[target])
                load, target_load = len(features[uid]), len(features[target])
                role = kind in ('foundation','related')
                if target in ancestors(uid):
                    basis = 'reverse_verified_precedence'
                elif not (role or required):
                    basis = 'role_not_eligible'
                elif load < target_load:
                    basis = 'lower_support_load'
                elif role and load == target_load and not collateral:
                    basis = 'equal_load_no_collateral'
                else:
                    basis = 'load_not_eligible'
                candidates.append(dict(unit_id=uid,kind=kind,load=load,target_load=target_load,collateral=collateral,
                                       required_by_call=required,basis=basis,
                                       qualified=basis in ('lower_support_load','equal_load_no_collateral')))
            demands.append(dict(target=target,topic=topic,qualifications=candidates,raw_suppliers=raw,
                                suppliers=[c['unit_id'] for c in candidates if c['qualified']]))
    return topics,demands


def supply_metrics(route, demands, features, topics, familiar, parents):
    positions = {u:i for i,u in enumerate(route)}
    rows = []
    totals = dict(root_exposure_topic_count=0,satisfied_supply_topic_count=0,avoidable_supply_gap_count=0)
    for item in demands:
        before = [u for u in item['suppliers'] if positions[u]<positions[item['target']]]
        raw_before = [u for u in item['raw_suppliers'] if positions[u]<positions[item['target']]]
        status,key = ('satisfied','satisfied_supply_topic_count') if before else (
            ('avoidable_gap','avoidable_supply_gap_count') if item['suppliers'] else ('root_exposure','root_exposure_topic_count'))
        totals[key] += 1
        rows.append(dict(item,classification=status,suppliers_before=before,raw_suppliers_before=raw_before))
    seen = set(familiar); raw = []; support = []
    for uid in route:
        new = set(features[uid]) - seen
        raw.append(len(new)); support.append(len(new & topics)); seen.update(new)
    return dict(totals,total_target_demands=len(rows),raw_unsupplied_count=sum(not r['raw_suppliers_before'] for r in rows),
                dependency_violations=sum(positions[p]>=positions[u] for u in route for p in parents[u]),
                delta_raw=raw,delta_support=support,MCS_raw=max(raw,default=0),SS_raw=sum(n*n for n in raw),
                MCS_support=max(support,default=0),SS_support=sum(n*n for n in support),demands=rows)


def exact_supply_order(ids, parents, features, familiar, topics, demands, *, reference=()):
    bits = {u:1<<i for i,u in enumerate(ids)}
    full = (1<<len(ids))-1
    required = {u:sum(bits[p] for p in parents[u]) for u in ids}
    later_reference = {}
    later = 0
    for uid in reversed(reference):
        if uid in bits:
            later_reference[uid] = later
            later |= bits[uid]
    supply = {u:[] for u in ids}
    for item in demands:
        if item['suppliers']:
            supply[item['target']].append(sum(bits[a] for a in item['suppliers']))
    layers = {0:{(0,0):((0,0,0,0,()),1)}}

    @lru_cache(maxsize=None)
    def seen(mask):
        if not mask:
            return frozenset(familiar)
        bit=mask & -mask
        return seen(mask ^ bit) | features[ids[bit.bit_length()-1]]

    states = 0
    for mask in range(full+1):
        if mask not in layers:
            continue
        labels = layers[mask]
        states += len(labels)
        for idx,uid in enumerate(ids):
            bit = bits[uid]
            if mask & bit or required[uid] & ~mask:
                continue
            new = features[uid] - seen(mask)
            raw, support = len(new),len(new & topics)
            gap = sum(not mask & group for group in supply[uid])
            inversions = (mask & later_reference.get(uid,0)).bit_count()
            dest = layers.setdefault(mask | bit,{})
            for (ps,pr),((g,ss,sr,changes,seq),count) in labels.items():
                key = max(ps,support),max(pr,raw)
                candidate = (g+gap,ss+support*support,sr+raw*raw,changes+inversions,seq+(idx,))
                prior,total = dest.get(key,(candidate,0))
                dest[key] = min(candidate,prior),total+count
    final = layers.get(full,{})
    if not final:
        return [],0,states
    winner = min((g,ps,ss,pr,sr,changes,seq) for (ps,pr),((g,ss,sr,changes,seq),_) in final.items())
    return [ids[i] for i in winner[-1]],sum(count for _,count in final.values()),states


def greedy_supply_order(ids, parents, features, familiar, topics, demands):
    seen=set(familiar); visited=set(); route=[]
    while len(route)<len(ids):
        ready=[u for u in ids if u not in visited and parents[u]<=visited]
        if not ready:
            break
        def rank(uid):
            new=features[uid]-seen
            return (sum(bool(d['suppliers']) and not visited.intersection(d['suppliers'])
                        for d in demands if d['target']==uid),len(new & topics),len(new))
        uid=min(ready,key=rank)
        route.append(uid);visited.add(uid);seen.update(features[uid])
    return route


def optimize_first_order(data, result, *, completed=(), reference=()):
    if completed or reference or result['status'] != 'FEASIBLE':
        return result

    before = result['remaining']
    selected = set(before)
    views = data['views']
    edges = {(e['before'], e['after']) for e in data['verified_order_edges']
             if e['before'] in selected and e['after'] in selected}
    cycles = cyclic_components(selected, edges)
    if cycles:
        return {**result,'reading_order':dict(status='fallback',reason='verified_call_cycle',cycles=cycles,
                                             dropped_cycle_edges=[])}
    parents = {uid:{a for a,b in edges if b == uid} for uid in before}
    familiar = set(data['order_familiar_features'])
    seen = familiar.copy()
    def stable_key(uid):
        view = views[uid]
        return (view['path'],view['span']['start_line'],view['title'],uid)

    ids = sorted(selected,key=stable_key)
    features = {uid:frozenset(views[uid]['pedagogical_features']) for uid in ids}
    by_id = {u['id']:u for u in data['units']}
    topics,demands = supply_demands(ids,views,by_id,data.get('support',()),familiar,result['gate'],parents)
    feature_space = set().union(*features.values()) - familiar
    bound = (1<<len(ids)) * (len(feature_space & topics)+1) * (len(feature_space)+1)
    count = states = None
    started = perf_counter()
    if len(ids) <= EXACT_LIMIT:
        route,count,states = exact_supply_order(ids,parents,features,familiar,topics,demands)
        method = 'exact_supply_dp'
    else:
        route = greedy_supply_order(ids,parents,features,familiar,topics,demands)
        method = 'greedy_supply'
    seconds = perf_counter() - started
    if len(route) != len(before):
        return {**result,'reading_order':dict(status='fallback',reason='incomplete_topological_order',cycles=cycles)}

    supply_result = supply_metrics(route,demands,features,topics,familiar,parents)
    if supply_result['dependency_violations']:
        return {**result,'reading_order':dict(status='fallback',reason='verified_precedence_failed')}
    explanations = {}
    for uid in route:
        new = sorted(features[uid] - seen)
        reasons = [f'引入{len(new)}项此前未接触的语法特征。']
        followers = sorted({views[b]['title'] for a,b in edges if a == uid})
        if followers:
            reasons.append('被后续实现直接调用，建议先读。')
        needs = [c for c in supply_result['demands'] if c['target']==uid]
        supply = [dict(topic=c['topic'],suppliers=[dict(unit_id=u,title=views[u]['title'])
                 for u in c['suppliers_before']]) for c in needs if c['suppliers_before']]
        root_count = sum(c['classification']=='root_exposure' for c in needs)
        explanations[uid] = dict(reason=''.join(reasons),new_features=new,before=followers,concept_supply=supply,
                                 root_exposure_topic_count=root_count)
        seen.update(new)

    req = {**data['request'], 'budget':result['budget']}
    audit = route_audit(req,data['units'],result['gate'],route,result['costs'],(),(),1,result['spent'])
    concepts = [c for uid in route for c in by_id[uid]['concept_ids']]
    duplicate = .4 * (len(concepts) - len(set(concepts)))
    objective = audit['objective'] + duplicate
    unchanged = (len(route) == len(before) and set(route) == selected
                 and audit['valid'] and audit['goal_complete'] and result['audit']['valid'] and result['audit']['goal_complete']
                 and audit['missing'] == result['audit']['missing'] and result['spent'] + objective <= result['budget'] + 1e-9
                 and all(math.isclose(a,b,rel_tol=0,abs_tol=1e-9) for a,b in (
                     (objective,result['objective']), (duplicate,result['duplicate_cost']),
                     (audit['learning_cost'],result['learning_cost']), (audit['switch_cost'],result['switch_cost']))))
    if not unchanged:
        return {**result, 'reading_order':dict(status='fallback', reason='invariant_failed', cycles=cycles)}

    metrics = route_metrics(route,views,familiar)
    metrics['target_before_later_foundation_pairs'] = metrics['target_before_foundation_pairs']
    metrics.update(supply_result)
    objective_keys = ('dependency_violations','avoidable_supply_gap_count','MCS_support','SS_support','MCS_raw','SS_raw')
    return {**result, 'remaining':route, 'audit':audit, 'soft_order_violations':metrics['category_violations'],
            'order_policy':'Verified call precedence, minimum avoidable supply gaps, then concept load',
            'reading_order':dict(status='applied',original=before,cycles=[],dropped_cycle_edges=[],
                                 explanations=explanations,method=method,solver_mode=method,exact_optimal=method=='exact_supply_dp',
                                 legal_sequence_count=count,visited_dp_states=states,dp_state_limit=bound,solver_seconds=seconds,
                                 zero_gap_feasible=(metrics['avoidable_supply_gap_count']==0) if method=='exact_supply_dp'
                                                   or metrics['avoidable_supply_gap_count']==0 else None,
                                 objective=[metrics[k] for k in objective_keys],metrics=metrics,
                                 concept_supply_unmet=[c for c in metrics['demands'] if not c['raw_suppliers_before']])}


def optimize_remaining_order(data, result, completed, reference):
    """Project an immutable completed prefix onto a separately ordered suffix."""
    original = result['remaining']
    views = data['views']
    selected, prefix = set(original), set(completed)
    active = selected | prefix
    prefix_index = {uid:i for i,uid in enumerate(completed)}
    verified = {(e['before'],e['after']) for e in data['verified_order_edges']
                if {e['before'],e['after']} <= active}
    historical = sorted((a,b) for a,b in verified if b in prefix and
                        (a in selected or prefix_index[a]>=prefix_index[b]))
    edges = {(a,b) for a,b in verified if a in selected and b in selected}
    familiar = set(data['order_familiar_features'])
    for uid in completed:
        familiar.update(views[uid]['pedagogical_features'])
    features = {uid:frozenset(views[uid]['pedagogical_features']) for uid in original}

    def diagnostic(route, supply=None):
        seen = familiar.copy()
        steps = {}
        positions = {uid:i for i,uid in enumerate(route)}
        for uid in route:
            new = sorted(features[uid]-seen)
            following = sorted({views[b]['title'] for a,b in edges
                                if uid==a and positions[a]<positions[b]})
            needs = [row for row in supply['demands'] if row['target']==uid] if supply else []
            supplied = [dict(topic=row['topic'],suppliers=[dict(unit_id=s,title=views[s]['title'])
                        for s in row['suppliers_before']]) for row in needs if row['suppliers_before']]
            reason = f'引入{len(new)}项此前未接触的语法特征。'
            if following:
                reason += '被后续实现直接调用，建议先读。'
            steps[uid] = dict(reason=reason,new_features=new,before=following,concept_supply=supplied,
                              root_exposure_topic_count=sum(r['classification']=='root_exposure' for r in needs))
            seen.update(new)
        return steps

    cycles = cyclic_components(selected,edges)
    common = dict(scope='remaining',original=original,cycles=cycles,dropped_cycle_edges=[],
                  historical_order_conflicts=[dict(before=a,after=b) for a,b in historical])

    def fallback(reason, metrics=None):
        return {**result,'reading_order':dict(common,status='fallback',reason=reason,metrics=metrics,
                                             explanations=diagnostic(original,metrics))}

    if len(selected)!=len(original) or selected & prefix or list(completed)!=result['completed']:
        return fallback('invalid_suffix_identity')
    if cycles:
        return fallback('verified_call_cycle')
    parents = {uid:{a for a,b in edges if b==uid} for uid in original}
    by_id = {u['id']:u for u in data['units']}
    reference_rank = {uid:i for i,uid in enumerate(reference)}

    def stable_key(uid):
        view = views[uid]
        return (reference_rank.get(uid,len(reference)),view['path'],view['span']['start_line'],view['title'],uid)

    ids = sorted(selected,key=stable_key)
    topics,demands = supply_demands(ids,views,by_id,data.get('support',()),familiar,result['gate'],parents)

    def measure(route):
        metrics = route_metrics(route,views,familiar)
        metrics['target_before_later_foundation_pairs'] = metrics['target_before_foundation_pairs']
        metrics.update(supply_metrics(route,demands,features,topics,familiar,parents))
        return metrics

    unchanged = measure(original)
    if result['status']!='FEASIBLE':
        return fallback('stage1_not_feasible',unchanged)
    count = states = None
    if selected <= reference_rank.keys() and not unchanged['dependency_violations'] and not unchanged['avoidable_supply_gap_count']:
        route,method = original,'preserved_reference'
    elif len(ids)<=EXACT_LIMIT:
        route,count,states = exact_supply_order(ids,parents,features,familiar,topics,demands,reference=reference)
        method = 'exact_supply_dp'
    else:
        route = greedy_supply_order(ids,parents,features,familiar,topics,demands)
        method = 'greedy_supply'
    if len(route)!=len(original) or set(route)!=selected:
        return fallback('incomplete_topological_order',unchanged)
    metrics = measure(route)
    if metrics['dependency_violations']:
        return fallback('verified_precedence_failed',unchanged)

    req = {**data['request'],'budget':result['budget']}
    spent = result['spent']
    audit = route_audit(req,data['units'],result['gate'],route,result['costs'],completed,reference,1,spent)
    concepts = [c for uid in (*completed,*route) for c in by_id[uid]['concept_ids']]
    duplicate = .4*(len(concepts)-len(set(concepts)))
    objective = audit.get('objective',math.inf)+duplicate
    if spent+objective>result['budget']+1e-9 and audit.get('errors') in ([],['TOTAL_BUDGET']):
        return fallback('reordered_budget_exceeded',unchanged)
    if not audit['valid'] or not audit['goal_complete'] or audit['missing']!=result['audit']['missing']:
        return fallback('reordered_audit_failed',unchanged)

    exact = method=='exact_supply_dp'
    keys = ('dependency_violations','avoidable_supply_gap_count','MCS_support','SS_support','MCS_raw','SS_raw')
    order = dict(common,status='applied',method=method,solver_mode=method,exact_optimal=exact,
                 legal_sequence_count=count,visited_dp_states=states,
                 zero_gap_feasible=True if not metrics['avoidable_supply_gap_count'] else False if exact else None,
                 objective=[metrics[key] for key in keys],metrics=metrics,explanations=diagnostic(route,metrics),
                 concept_supply_unmet=[row for row in metrics['demands'] if not row['raw_suppliers_before']])
    return {**result,'remaining':route,'audit':audit,'objective':objective,'duplicate_cost':duplicate,
            'switch_cost':audit['switch_cost'],'learning_cost':audit['learning_cost'],
            'soft_order_violations':metrics['category_violations'],
            'order_policy':'Verified call precedence, minimum avoidable supply gaps, then concept load',
            'reading_order':order}
