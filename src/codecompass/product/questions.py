import json
class Questions:
    def __init__(self,root):
        self.data=json.loads((root/'content/product/questions.private.json').read_text(encoding='utf-8'))
    @staticmethod
    def public(q):return {k:q[k] for k in ('item_id','prompt','code','choices')}
    def unit(self,tid,uid):
        try:return self.data[tid][uid]
        except KeyError:raise ValueError('当前单元尚无练习')
    def practice(self,tid):return self.data.get(tid+'_practice',[])
    def baseline(self):return [self.public(q) for q in self.data['baseline']]
    @staticmethod
    def score(q,choice):
        if choice is not None and (type(choice) is not int or not 0<=choice<len(q['choices'])):raise ValueError('请选择有效选项或明确选择不会')
        return None if choice is None else choice==q['answer']
