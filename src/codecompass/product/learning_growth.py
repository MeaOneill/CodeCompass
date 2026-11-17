"""Source-reading exposure and optional, non-independent topic practice checks."""
import ast
import textwrap
from .repositories import features


CHECKS={
 'python.functions':('def add(x, y=4):\n    return x + y\nprint(add(2, y=5))',['6','7','9','报错'],1,'显式传入的 y=5 覆盖默认值。'),
 'python.containers':('a = [3, 5]\na[0] = 8\nprint(a)',['[3, 5]','[8, 5]','[3, 8]','[8]'],1,'下标0对应第一个元素，赋值只替换该位置。'),
 'python.iteration':('print([x + 1 for x in [2, 4, 6] if x > 3])',['[3, 5, 7]','[5, 7]','[4, 6]','[3]'],1,'先保留4和6，再分别加1。'),
 'python.generators':('g = (x for x in [4, 8])\nprint(next(g))\nprint(list(g))',['4，随后[4, 8]','8，随后[]','4，随后[8]','报错'],2,'next消耗第一个元素，之后只能取得剩余元素。'),
 'python.classes':('class Box:\n    def __init__(self, n):\n        self.n = n\na, b = Box(2), Box(5)\na.n += 1\nprint(b.n)',['2','3','5','6'],2,'两个实例分别保存自己的 n 属性。'),
 'python.exceptions':('try:\n    int("x")\nexcept ValueError:\n    print("A")\nprint("B")',['只有A','只有B','先A再B','没有输出'],2,'异常被处理后，继续执行 try/except 后面的语句。'),
 'python.decorators':('def triple(fn):\n    return lambda: fn() * 3\n@triple\ndef number():\n    return 4\nprint(number())',['3','4','7','12'],3,'装饰后的入口调用原函数，再将结果乘3。'),
 'python.async':('import asyncio\nasync def f():\n    return 5\nasync def main():\n    return (await f()) * 2\nprint(asyncio.run(main()))',['5','10','2','报错'],1,'await取得5，随后乘2返回10。')}


def topics(view):
    try:
        tree=ast.parse(textwrap.dedent(view['code']))
        return features(tree.body[0] if tree.body else tree)
    except (SyntaxError,RecursionError):return []


def record_read(prefs,view,repository,*,advance=True,route_id=None,unit_id=None):
    growth=prefs.setdefault('learning_growth',dict(readings={},checks={},explained=[]))
    span=view['span'];key=repository+':'+span['path']+':'+span['content_hash']
    row=growth['readings'].setdefault(key,dict(repository=repository,path=span['path'],topics=topics(view)))
    if route_id and unit_id:row.update(route_id=route_id,unit_id=unit_id)
    growth['explained']=sorted(set(growth['explained'])|set(topics(view)))
    if advance:prefs['revision']=prefs.get('revision',0)+1


def practice(prefs,view):
    checks=prefs.get('learning_growth',{}).get('checks',{})
    return [dict(concept=c,code=CHECKS[c][0],choices=CHECKS[c][1],result=checks.get(c)) for c in topics(view) if c in CHECKS]


def verified(prefs):
    growth=prefs.get('learning_growth',{});read={c for r in growth.get('readings',{}).values() for c in r['topics']}
    return {c for c,r in growth.get('checks',{}).items() if r['correct'] and c in read}
