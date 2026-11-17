"""Versioned first-use survey + scored, tiered Python questions (answers server-only)."""
import hashlib
import json
import secrets
from collections import defaultdict
from .workspaces import stamp,dump

VERSION='python-start-v1'

ITEMS=[
 ('print([10, 20, 30][1])',['10','20','30','报错'],1,'20','containers','列表下标从0开始。'),
 ('xs = [1, 2]\nys = xs\nys.append(3)\nprint(xs)',['[1, 2]','[1, 2, 3]','[3]','报错'],1,'[1, 2, 3]','containers','两个变量可以指向同一个可变列表。'),
 ('print(sum(i for i in range(4)))',['3','4','6','10'],2,'6','iteration','range(4)依次给出0、1、2、3。'),
 ('print([x * 2 for x in [1, 2, 3] if x > 1])',['[2, 4, 6]','[4, 6]','[2, 3]','[1, 2]'],1,'[4, 6]','iteration','先按条件筛选，再计算每个保留元素。'),
 ('def f(x, y=2):\n    return x + y\nprint(f(3))',['2','3','5','报错'],2,'5','functions','未提供y时使用默认值2。'),
 ('def f(xs):\n    xs.append(2)\na = [1]\nf(a)\nprint(a)',['[1]','[1, 2]','None','报错'],1,'[1, 2]','functions','函数可以修改传入的可变对象。'),
 ('class Box:\n    def __init__(self, value):\n        self.value = value\nprint(Box(7).value)',['value','None','7','报错'],2,'7','classes','实例属性保存每个对象的数据。'),
 ('class Box:\n    def __init__(self):\n        self.x = []\na, b = Box(), Box()\na.x.append(1)\nprint(b.x)',['[1]','[]','None','报错'],1,'[]','classes','在初始化方法内创建的列表由各实例分别持有。'),
 ('try:\n    int("abc")\nexcept ValueError:\n    print("bad")',['abc','0','bad','没有输出'],2,'bad','exceptions','转换失败进入匹配的异常处理分支。'),
 ('try:\n    print(1)\nfinally:\n    print(2)',['1','2','先1再2','报错'],2,'1\n2','exceptions','finally会在离开该语句前执行。'),
 ('def numbers():\n    yield 1\n    yield 2\ng = numbers()\nprint(next(g))',['1','2','[1, 2]','报错'],0,'1','generators','next推进生成器至下一个yield。'),
 ('g = (x * 2 for x in range(3))\nprint(list(g))\nprint(list(g))',['两次都是[0, 2, 4]','先[0, 2, 4]再[]','两次都是[]','报错'],1,'[0, 2, 4]\n[]','generators','同一个生成器被消费后不会自动重新开始。'),
 ('def mark(fn):\n    def wrapped():\n        return fn() + 1\n    return wrapped\n@mark\ndef f():\n    return 2\nprint(f())',['1','2','3','报错'],2,'3','decorators','装饰器用包装后的函数替换原入口。'),
 ('def wrap(fn):\n    return lambda: fn() * 2\ndef f():\n    return 3\nprint(wrap(f)())',['2','3','6','报错'],2,'6','decorators','函数可以作为参数传递并被另一个函数包装。'),
 ('import asyncio\nasync def f():\n    return 3\nprint(asyncio.run(f()))',['None','3','f','报错'],1,'3','async','协程需要由事件循环驱动执行。'),
 ('import asyncio\nasync def f():\n    return 2\nasync def main():\n    return await f() + 1\nprint(asyncio.run(main()))',['1','2','3','报错'],2,'3','async','await取得协程结果后继续后续计算。'),
]


class Onboarding:
    def __init__(self,service):
        self.service=service
        with service.store.connect() as db:db.execute('CREATE TABLE IF NOT EXISTS product_assessments(id TEXT PRIMARY KEY,user_id TEXT NOT NULL,version TEXT NOT NULL,state_json TEXT NOT NULL,result_json TEXT)')

    def question(self,index):
        code,choices,_,_,topic,_=ITEMS[index]
        return dict(id=f'{VERSION}:{index}',prompt='这段代码会输出什么？',code=code,choices=choices,topic='python.'+topic)

    def start(self,user):
        with self.service.store.connect() as db:
            prefs=self.service.workspaces.preferences(db,user)
            if not prefs.get('onboarding'):raise ValueError('请先保存学习经历')

            row=db.execute('SELECT * FROM product_assessments WHERE user_id=? AND result_json IS NULL ORDER BY rowid DESC LIMIT 1',(user,)).fetchone()
            if row and json.loads(row['state_json'])['profile_revision']==prefs.get('revision',0):state=json.loads(row['state_json']);attempt=row['id']
            else:
                basic=list(range(0,len(ITEMS),2));familiar=prefs['onboarding']['familiar']
                topics=sorted(range(8),key=lambda i:('python.'+ITEMS[i*2][4] not in familiar,i))

                indices=basic+[i*2+1 for i in topics[:4]]
                attempt='a_'+secrets.token_hex(16);state=dict(indices=indices,profile_revision=prefs.get('revision',0))
                db.execute('INSERT INTO product_assessments VALUES(?,?,?,?,NULL)',(attempt,user,VERSION,dump(state)))
        return dict(id=attempt,questions=[self.question(i) for i in state['indices']],answered_before=bool(prefs.get('assessment')))

    def submit(self,user,attempt,answers):
        if not isinstance(answers,list):raise ValueError('请保存题目选项')
        with self.service.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');prefs=self.service.workspaces.preferences(db,user)
            row=db.execute('SELECT * FROM product_assessments WHERE id=? AND user_id=?',(attempt,user)).fetchone()
            if not row:raise ValueError('找不到这次能力了解')
            state=json.loads(row['state_json'])
            if len(answers)!=len(state['indices']) or any(x is not None and (type(x) is not int or not 0<=x<=3) for x in answers):raise ValueError('题目选项不完整')
            if row['result_json']:
                saved=json.loads(row['result_json'])
                if saved['answers']!=answers:raise ValueError('本次结果已保存，可以重新开始一次能力了解')
                return saved
            if prefs.get('revision',0)!=state['profile_revision']:raise ValueError('画像已调整，请重新打开能力了解')
            topics=defaultdict(lambda:dict(correct=0,answered=0,total=0));feedback=[];evidence=[]
            for index,choice in zip(state['indices'],answers):
                code,options,correct,_,topic,note=ITEMS[index];concept='python.'+topic;t=topics[concept];t['total']+=1
                if choice is not None:t['answered']+=1;t['correct']+=int(choice==correct)
                feedback.append(dict(question_id=f'{VERSION}:{index}',correct=None if choice is None else choice==correct,explanation=note))
                if choice is not None:evidence.append(dict(evidence_id=f'{attempt}:{index}',item_id=f'{VERSION}:{index}',concept_id=concept,project=VERSION,
                    timestamp=stamp(),pseudonymous_user_id=user,is_fixture=self.service.actor!='local_user',independent=True,evidence_type='independent_quiz',outcome='pass' if choice==correct else 'fail'))
            if evidence:self.service.store.evidence.submit_many_in_connection(db,user,evidence,simulated=self.service.actor!='local_user')

            previous=prefs.get('assessment')
            prefs['assessment']=dict(version=VERSION,attempt_id=attempt,topics=dict(topics),completed_at=stamp(),correct=sum(t['correct'] for t in topics.values()),answered=sum(t['answered'] for t in topics.values()),total=len(answers))
            prefs['assessment']['baseline_attempt_id']=previous.get('baseline_attempt_id',previous['attempt_id']) if previous else attempt
            a=prefs['assessment'];ratio=a['correct']/max(1,a['answered'])
            a['recommended_experience']=('new' if ratio<.45 else 'comfortable' if ratio>=.85 and a['answered']>=10 else 'some') if a['answered']>=6 else prefs['onboarding']['experience']
            prefs['revision']=prefs.get('revision',0)+1
            db.execute('UPDATE product_users SET preferences_json=? WHERE user_id=?',(dump(prefs),user))
            result=dict(answers=answers,feedback=feedback,summary=prefs['assessment'])
            db.execute('UPDATE product_assessments SET result_json=? WHERE id=?',(dump(result),attempt))
        return result
