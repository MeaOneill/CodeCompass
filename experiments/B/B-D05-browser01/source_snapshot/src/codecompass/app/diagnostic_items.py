"""Development-only independent concept questions, not final-task answer keys.

Answers stay server-side. These questions are not generated from planner routes.
Python semantics, checked by tests, are the scoring basis; no difficulty claim.
"""
ITEMS = {
    'task_001': dict(item_id='B05-generator-first-next-v1', concept_id='python.generator_laziness',
        prompt='独立概念短测：下面程序最终打印什么？',
        code='def numbers():\n    yield 7\n    yield 9\ng = numbers()\nprint(next(g))',
        choices=['7', '9', '[7, 9]', '不会输出'], answer=0,
        basis='Python generator first next yields the first value; executable independent snippet'),
    'task_002': dict(item_id='B05-iterator-next-v1', concept_id='python.iterator_protocol',
        prompt='独立概念短测：下面程序最终打印什么？',
        code='it = iter([2, 4, 6])\nnext(it)\nprint(next(it))',
        choices=['2', '4', '6', '[4, 6]'], answer=1,
        basis='Python iterator advances once per next; executable independent snippet'),
}


def public_item(task_id):
    q = ITEMS[task_id]
    return {k: q[k] for k in ('item_id', 'prompt', 'code', 'choices')}


def score(task_id, choice):
    q = ITEMS[task_id]
    if type(choice) is not int or not 0 <= choice < len(q['choices']):
        raise ValueError('请选择一个答案')
    return 'pass' if choice == q['answer'] else 'fail'
