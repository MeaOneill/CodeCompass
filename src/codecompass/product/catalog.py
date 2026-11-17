import json
from pathlib import Path
from codecompass.app.relay_v2 import prepare
from codecompass.app.journey_d07 import cross_data

class Catalog:
    def __init__(self, root):
        self.root = Path(root)
        self.tasks = json.loads((self.root/'content/product/catalog.json').read_text(encoding='utf-8'))
    def task(self, tid):
        for t in self.tasks:
            if t['task_id'] == tid: return t
        raise ValueError('找不到这个任务，请返回任务目录选择')
    def source(self, tid, user='catalog', simulated=True):
        t = self.task(tid)
        d = cross_data(self.root,user,simulated) if t['source_task_id']=='B07_more_chunked' else prepare(self.root,t['source_task_id'],user,simulated)
        if t['source_version'] != d['snapshot']['commit'] or t['unit_ids'] != [u['id'] for u in d['units']]:
            raise ValueError('任务源码版本或单元映射不匹配，请保留记录并修复内容目录')
        return d
    def material(self, tid, uid):
        d=self.source(tid)
        if uid not in self.task(tid)['unit_ids']: raise ValueError('这份源码不属于当前任务')
        p=self.root/'content/product/lessons'/tid/(uid+'.json')
        if not p.exists(): raise ValueError('该单元教学内容尚未开放')
        lesson=json.loads(p.read_text(encoding='utf-8'))
        unit = next(u for u in d['units'] if u['id'] == uid)
        if lesson['source_version'] != d['snapshot']['commit'] or lesson['source_spans'] != unit['source_spans']:
            raise ValueError('教学内容引用与固定源码不匹配')
        materials=[m for m in d['materials'] if m['unit_id']==uid]
        if tid=='P04_chunked_transfer':
            from codecompass.graph import read_snapshot,validate_span
            contents=read_snapshot(self.root/d['source_root'],d['snapshot'])
            for row in d['source_context']:
                validate_span(row['source_span'],d['snapshot'],contents)
                if row['source_span']['path'].endswith('recipes.py'):materials.append(row)
        return dict(**lesson, materials=materials)
