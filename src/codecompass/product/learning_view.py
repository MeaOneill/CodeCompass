"""Source-grounded lesson cards and reproducible product indicators."""
import ast
import math
import textwrap
from .repositories import FEATURES,features
from codecompass.graph.provenance import digest

EXAMPLES={
 'python.functions':('函数与参数','识别输入、默认参数和返回值。','def total(values, extra=0):\n    return sum(values) + extra\nprint(total([2, 3], extra=1))','6','区分调用时传入的实参与函数内部使用的形参。'),
 'python.iteration':('循环与推导式','跟踪筛选条件和每轮迭代的值。','values = [1, 2, 3]\nprint([x * 2 for x in values if x > 1])','[4, 6]','先判断条件，再计算保留元素的结果。'),
 'python.containers':('容器与索引','理解数据的存储、查找和更新。','jobs = ["A", "B", "C"]\nprint(jobs[0])\njobs.remove("B")\nprint(jobs)','A\n[\'A\', \'C\']','索引决定读取位置；更新操作会改变容器中的内容。'),
 'python.generators':('生成器与惰性求值','区分创建数据流与实际读取元素。','items = (x * 2 for x in [1, 2, 3])\nprint(next(items))\nprint(list(items))','2\n[4, 6]','生成器表达式或yield会按需提供数据，读取后位置向前推进。'),
 'python.classes':('类与对象','识别对象状态和实例方法。','class Counter:\n    def __init__(self):\n        self.count = 0\n    def add(self):\n        self.count += 1\nc = Counter()\nc.add()\nprint(c.count)','1','实例属性保存状态，方法读取或更新该状态。'),
 'python.exceptions':('异常处理','区分正常流程、异常触发与处理分支。','try:\n    value = int("abc")\nexcept ValueError:\n    print("输入无效")','输入无效','异常匹配后进入对应处理分支，未匹配的异常向外传播。'),
 'python.decorators':('装饰器','理解原函数与包装函数的关系。','def double(fn):\n    return lambda: fn() * 2\n@double\ndef number():\n    return 3\nprint(number())','6','装饰器在保留调用入口的同时增加行为。'),
 'python.async':('异步调用','识别协程与await的执行关系。','import asyncio\nasync def value():\n    return 3\nasync def main():\n    print(await value())\nasyncio.run(main())','3','await等待协程结果，然后继续后续语句。')}


def source_outline(view):
    """Build a syntax-only outline of a verified, line-addressed source span."""
    span, code = view['span'], view['code']
    if digest((code+'\n').encode()) != span['content_hash']:
        raise ValueError('教学片段与源码引用不一致')
    try:
        root = ast.parse(textwrap.dedent(code)).body[0]
    except (SyntaxError, IndexError, RecursionError):
        return dict(name=None,signature='',doc='',phases=[],returns=[],topics=[])
    start = span['start_line'] - 1
    function = isinstance(root, (ast.FunctionDef, ast.AsyncFunctionDef))
    definition = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    body = root.body if isinstance(root, definition) else [root]
    string_args = {arg.arg for arg in [*root.args.posonlyargs,*root.args.args,*root.args.kwonlyargs]
                   if isinstance(arg.annotation,ast.Name) and arg.annotation.id=='str'} if function else set()
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        body = body[1:]
    signature = ''
    if function:
        signature = ('async ' if isinstance(root,ast.AsyncFunctionDef) else '')+root.name+'('+ast.unparse(root.args)+')'
        if root.returns:
            signature += ' -> '+ast.unparse(root.returns)
    elif isinstance(root, ast.ClassDef):
        signature = 'class '+root.name

    def expr(node):
        return ast.unparse(node) if node is not None else 'None'

    def action(node):
        if isinstance(node,ast.Return):
            return '返回 '+expr(node.value)
        if isinstance(node,ast.Raise):
            return '抛出 '+(expr(node.exc) if node.exc else '当前异常')
        if isinstance(node,(ast.Assign,ast.AnnAssign,ast.AugAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            target='、'.join(expr(t) for t in targets)
            value=node.value
            if isinstance(node,ast.AugAssign):
                return '按 '+expr(node)+' 更新 '+target
            if isinstance(value,ast.Call):
                call=value.func
                if (isinstance(call,ast.Attribute) and isinstance(call.value,ast.Name)
                        and call.value.id in string_args and call.attr in ('strip','lstrip','rstrip')):
                    sides={'strip':'首尾','lstrip':'开头','rstrip':'末尾'}[call.attr]
                    chars='指定的字符' if value.args else '空白'
                    return '清理 '+expr(call.value)+' '+sides+chars+'，结果存入 '+target
                return '调用 '+expr(value)+'，结果存入 '+target
            return '将 '+target+' 设为 '+expr(value) if value else '声明 '+target
        if isinstance(node,ast.Break):
            return '退出循环'
        if isinstance(node,ast.Continue):
            return '进入下一轮循环'
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call):
            return '调用 '+expr(node.value)
        return ''

    def actions(statements, limit=2):
        return '，再'.join(filter(None,(action(node) for node in statements[:limit])))

    def walk(statements, conditions=()):
        for node in statements:
            if isinstance(node, (*definition, ast.Lambda)):
                continue
            if isinstance(node, ast.If):
                yield from walk(node.body,(*conditions,expr(node.test)))
                yield from walk(node.orelse,(*conditions,'不满足 '+expr(node.test)))
                continue
            if isinstance(node, ast.Return):
                yield dict(line=start+node.lineno,end_line=start+node.end_lineno,expression=expr(node.value),
                           conditions=list(conditions),early=bool(conditions) or node is not body[-1])
                continue
            for child in ast.iter_child_nodes(node):
                yield from walk([child],conditions)

    def detail(node):
        if isinstance(node,ast.If):
            effect=actions(node.body)
            if not effect and isinstance(node.body[0],ast.If):
                effect='继续检查 '+expr(node.body[0].test)
            alternative=actions(node.orelse,1)
            return '当 '+expr(node.test)+' 时，'+(effect or '执行分支体')+('；否则'+alternative if alternative else '')
        if isinstance(node,(ast.For,ast.AsyncFor)):
            checks=[expr(n.test) for n in node.body if isinstance(n,ast.If)]
            focus='，重点检查 '+ '、'.join(checks[:2]) if checks else ''
            return '遍历 '+expr(node.iter)+'，逐项处理 '+expr(node.target)+focus
        if isinstance(node,ast.While):
            return '满足 '+expr(node.test)+' 时继续循环'
        if isinstance(node,(ast.Try,ast.TryStar)):
            normal=actions(node.body,1)
            handlers=[]
            for handler in node.handlers:
                kind=expr(handler.type) if handler.type else '任意异常'
                recovery=actions(handler.body,1)
                handlers.append('遇到 '+kind+(' 时，'+recovery if recovery else ' 时进入异常处理'))
            return '；'.join([('先尝试'+normal) if normal else '执行受保护的代码块',*handlers]+
                            (['最后执行清理'] if node.finalbody else []))
        simple=action(node)
        if simple:
            return simple
        if isinstance(node,ast.Assert):
            return '检查 '+expr(node.test)
        if isinstance(node,ast.Match):
            return '根据 '+expr(node.subject)+' 匹配分支'
        if isinstance(node,definition):
            return '定义 '+node.name
        if isinstance(node,ast.Expr):
            return '执行 '+expr(node.value)
        return '查看 '+ast.unparse(node).splitlines()[0]

    def phase(node, started):
        if isinstance(node,(ast.Return,ast.Raise)):
            return '返回结果' if isinstance(node,ast.Return) else '异常出口'
        if isinstance(node,(ast.For,ast.AsyncFor,ast.While,ast.Try,ast.TryStar,ast.Match)):
            return '核心处理'
        if isinstance(node,ast.If):
            return '入口检查' if not started and not node.orelse and isinstance(node.body[0],(ast.Return,ast.Raise)) else '条件分支'
        return '入口准备' if not started else '整理中间结果'

    phases = []
    started = False
    for node in body:
        title = phase(node,started)
        if title in ('核心处理','条件分支'):
            started = True
        if not phases or phases[-1]['title'] != title:
            phases.append(dict(title=title,line=start+node.lineno,end_line=start+node.end_lineno,details=[]))
        phases[-1]['end_line'] = start+node.end_lineno
        phases[-1]['details'].append(detail(node))
    for block in phases:
        notes=block.pop('details')
        block['text']='；'.join(notes[:3])+'。'
    doc=ast.get_docstring(root) if isinstance(root,definition) else None
    return dict(name=getattr(root,'name',None),signature=signature,doc=doc or '',phases=phases,
                returns=list(walk(body)) if function else [],topics=features(root),is_function=function)


def lesson(view,state,prefs):
    outline=source_outline(view)
    topics=outline["topics"]
    topic_order=state['data'].get('intent',{}).get('topics',[])+state['data'].get('support',[])+topics
    taught=list(dict.fromkeys(c for c in topic_order if c in topics and c in EXAMPLES))[:2]
    if not taught:taught=list(dict.fromkeys(c for c in view['concepts'] if c in EXAMPLES))[:2]
    from .learning_growth import practice
    explained=set(prefs.get('learning_growth',{}).get('explained',[]))
    focused=state.get('adjustment',{}).get('topics',[]) if state.get('adjustment',{}).get('action')=='hard' else []
    hidden={c for c,v in prefs.get('source_feedback',{}).items() if v=='familiar'}
    examples=[dict(concept=c,title=EXAMPLES[c][0],goal=EXAMPLES[c][1],code=EXAMPLES[c][2],output=EXAMPLES[c][3],explanation=EXAMPLES[c][4],review=c in explained and c not in focused) for c in taught if c not in hidden]
    label=state['data'].get('intent',{}).get('label','学习目标')
    assessment=prefs.get('assessment',{}).get('topics',{})
    review=[FEATURES[c] for c in taught if c not in hidden and c in assessment and assessment[c]['answered']>assessment[c]['correct']]
    why=('测评建议先巩固'+ '、'.join(review)+'，本步通过项目中的实际用法衔接后续阅读。' if review else
         '本步补充'+'、'.join(FEATURES[c] for c in taught)+'，为后续目标实现建立基础。' if view['kind']=='foundation' and taught else
         '本步位于“'+label+'”的学习范围内，帮助理解目标功能的具体实现。' if view['kind']=='target' else '本步介绍目标实现依赖的数据结构或调用关系。')
    title=view['title'].replace('基础例子 · ','基础研读 · ')
    return dict(title=title,objective='理解 '+title+' 的输入、处理流程与结果。',
                goal_link=state['goal'],reason=why,signature=outline['signature'],source_summary=outline['doc'].split('\n\n')[0][:450],
                concepts=[FEATURES[c] for c in taught],examples=examples,source_steps=outline['phases'],practice=practice(prefs,view),
                completion='能够说明该实现的输入、主要分支与返回结果，并定位相关源码。',
                method='ast-source-v1',is_model_generated=False)


def profile_metrics(prefs):
    assessment=prefs.get('assessment',{});survey=prefs.get('onboarding',{});rows=[]
    growth=prefs.get('learning_growth',{});readings=list(growth.get('readings',{}).values())
    from .learning_growth import CHECKS
    for c,title in FEATURES.items():
        r=assessment.get('topics',{}).get(c,{})
        n=r.get('answered',0);correct=r.get('correct',0)
        studied=[r for r in readings if c in r['topics']];check=growth.get('checks',{}).get(c)
        reference=next((r for r in studied if r.get('route_id') and r.get('unit_id')),None)
        review=dict(concept=c,code=CHECKS[c][0],choices=CHECKS[c][1],route_id=reference['route_id'],unit_id=reference['unit_id']) if reference and not check else None
        rows.append(dict(concept=c,title=title,answered=n,correct=correct,score=round(100*correct/n) if n else None,review_question=review,
                         reading_count=len(studied),repositories=len({r['repository'] for r in studied}),
                         growth_status='基础复核通过' if check and check['correct'] and studied else '建议复习' if check and not check['correct'] else '已研读' if studied else '尚未研读',
                         check_correct=check['correct'] if check else None,
                         self_report=c in survey.get('familiar',[]),status='待测评' if not n else '建议巩固' if correct<n else '基础题通过'))
    answered=sum(r['answered'] for r in rows);correct=sum(r['correct'] for r in rows)
    return dict(topics=rows,answered=answered,correct=correct,score=round(100*correct/answered) if answered else None,
                experience={'new':'基础入门','some':'实践巩固','comfortable':'进阶阅读'}.get(assessment.get('recommended_experience',survey.get('experience')),'待建立'),
                months=survey.get('months'),basis='scored_questions' if answered else 'survey',
                learning=dict(readings=len(readings),repositories=len({r['repository'] for r in readings}),
                              verified_topics=sum(r['growth_status']=='基础复核通过' for r in rows),
                              stage='跨仓库实践' if len({r['repository'] for r in readings})>=2 else '源码研读' if readings else '开始学习'))


def insights(state,prefs):
    result=state['result'];data=state['data'];ids=state['completed']+result['remaining'];units={u['id']:u for u in data['units']}
    coverage={c for x in ids for c in units[x]['concept_ids']}
    coverage.update(c for c,g in result.get('gate',{}).items() if g['mastered'])
    goals=set(data['request']['target_concept_ids']);support=set(data['support'])
    return dict(profile=profile_metrics(prefs),route=dict(goal_coverage=round(100*len(goals&coverage)/max(1,len(goals))),
        covered_goals=len(goals&coverage),total_goals=len(goals),foundation_coverage=round(100*len(support&coverage)/len(support)) if support else 100,
        candidates=len(units),selected=len(ids),files=len({data['views'][x]['path'] for x in ids}),
        workload=round(result['learning_cost'],1),objective=round(result['objective'],2),completed=len(state['completed']),total=len(ids),
        progress=round(100*len(state['completed'])/max(1,len(ids)))),
        learning_phase='issues' if result['status']=='FEASIBLE' and not result['remaining'] else 'reading',
        lessons={x:lesson(data['views'][x],state,prefs) for x in ids})
