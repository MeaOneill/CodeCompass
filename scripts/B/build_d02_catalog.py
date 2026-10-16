"""Author source-grounded evaluation candidates, never mark human review complete.

This is an evaluator catalog, not a second planning contract. Every prompt below
is an explicitly authored question; function spans are AST-located only for
provenance, not inferred gold concepts or correctness labels.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d'


def source_span(module, names):
    base = 'benchmarks/sources/boltons' if module == 'iterutils' else 'benchmarks/sources/boltons_B_D02'
    path = ROOT / base / 'boltons' / (module + '.py')
    text = path.read_text(encoding='utf-8')
    snap = json.loads((ROOT / base / 'snapshot.json').read_text(encoding='utf-8'))
    tree = ast.parse(text)
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    rows = []
    for name in names:
        node = funcs[name]
        excerpt = '\n'.join(text.splitlines()[node.lineno - 1:node.end_lineno]) + '\n'
        rows.append({'snapshot_id': snap['snapshot_id'], 'path': f'boltons/{module}.py', 'start_line': node.lineno, 'end_line': node.end_lineno, 'content_hash': hashlib.sha256(excerpt.encode()).hexdigest()})
    return rows


def main():
    # id, module, function(s), task type, title, prompt, manually authored concepts
    questions = [
        ('task_001', 'iterutils', ['chunked', 'chunked_iter'], 'local_modification', '惰性count限制', '完整要求沿用benchmarks/dev/task_001.json；仅修改chunked_iter，提交candidate.py及解释/补丁/回归测试/命令时间记录。', ['python.generator_laziness', 'python.islice_consumption', 'python.keyword_presence']),
        ('task_002', 'iterutils', ['windowed_iter', 'windowed', 'pairwise'], 'debug', '滑动窗口size边界防护', '仅修改windowed_iter：size只接受内置正int，排除bool；非int TypeError，<=0 ValueError。保持正常窗口、短源/空源、fill省略与显式None、pairwise end及无限输入前缀兼容。说明tee和填充哨兵的作用。', ['python.iterator_protocol', 'python.tee', 'python.keyword_presence', 'python.type_validation']),
        ('task_003', 'iterutils', ['unique_iter'], 'locate_explain', '稳定去重与key定位', "给answer.json的outputs填写plain=list(unique_iter(['a','A','a','b']))、casefold=list(unique_iter(['a','A','a','b'], key=str.lower))、length=list(unique_iter(['hi','ok','hey','bye'], key=len))。在source_spans引用本题函数，explanation解释seen的键和输出对象区别、保持首次顺序和哈希限制。", ['python.hash_set', 'python.key_function', 'python.generator_laziness']),
        ('task_004', 'iterutils', ['get_path'], 'debug', '默认值与路径索引调试', "root={'a':[{'x':None}]}。填写outputs：null=get_path(root,('a',0,'x'),default='MISSING')，missing=get_path(root,'a.0.z',default='MISSING')，string_index=get_path({'a':[10,20]},'a.1')，empty_path=get_path({'x':1},())。解释为何None不代表查找失败、字符串数字何时转换以及何时抛PathAccessError。", ['python.eafp', 'python.exception_translation', 'python.sentinel_default']),
        ('task_005', 'strutils', ['camel2under', 'under2camel'], 'locate_explain', '缩写与分隔符转换定位', "填写outputs：acronym=camel2under('HTTPServer2Thing')，simple=under2camel('parse_http_body')，underscores=under2camel('__edge__')。引用正则使用位置；解释缩写边界和空片段的处理，不假定两个函数总互逆。", ['python.regex_boundary', 'python.string_transform']),
        ('task_006', 'strutils', ['slugify', 'split_punct_ws', 'asciify'], 'debug', 'slug返回类型与标点边界', "填写outputs：normal=slugify('Hello, World!')，empty=slugify('')，punct=slugify('!!!')，ascii_bytes=list(slugify('Café',ascii=True))。解释ascii=True的返回类型为何影响JSON/文本调用方以及空串与全标点输入差异。", ['python.regex_split', 'python.bytes_text', 'python.conditional_precedence']),
        ('task_007', 'strutils', ['ordinalize'], 'locate_explain', '序数词teen例外与后缀', "填写outputs：teens=[ordinalize(n) for n in (11,12,13,21,112)]，suffix=ordinalize(23,ext_only=True)，text=ordinalize('abc')。定位teen分支；解释数值先转字符串及不以数字结尾的行为。", ['python.string_index', 'python.branch_exception']),
        ('task_008', 'strutils', ['strip_ansi'], 'locate_explain', 'ANSI清理与bytes边界', "填写outputs：text=strip_ansi('A\\x1b[31mB\\x1b[0mC')（转义序列为真实ESC），bytes=list(strip_ansi(b'X\\x1b[1mY\\x1b[0m'))，plain=strip_ansi('plain')。解释文本与字节实现路径及函数支持边界，不声称清理任意终端协议。", ['python.escape_sequence', 'python.bytes_text']),
        ('task_009', 'strutils', ['gzip_bytes', 'gunzip_bytes'], 'locate_explain', 'gzip往返与字节约定', "对data=b'open-source navigation'，填写outputs：roundtrip=list(gunzip_bytes(gzip_bytes(data)))，empty=list(gunzip_bytes(gzip_bytes(b'')))，type_name=type(gzip_bytes(data)).__name__。解释BytesIO与压缩级别；不要把压缩后完整字节串当稳定跨版本金标准。", ['python.bytes_io', 'python.compression_roundtrip']),
        ('task_010', 'strutils', ['iter_splitlines', 'indent'], 'debug', '换行尾空行与缩进调试', "填写outputs：lines=list(iter_splitlines('a\\r\\nb\\n'))，empty=list(iter_splitlines(''))，indented=indent('a\\n\\nb\\n','> ')。输入中的转义为真实换行。解释末尾空行和key=bool如何影响空行缩进及连接符。", ['python.regex_group', 'python.generator_boundary', 'python.predicate']),
        ('task_011', 'strutils', ['parse_int_list', 'format_int_list'], 'debug', '整数区间解析与重复保留', "填写outputs：reverse=parse_int_list('5-3,1')，duplicates=parse_int_list('2,1,2')，formatted=format_int_list([1,2,3,5])，empty=parse_int_list('')。解释排序不等于去重、反向范围取min/max及区间闭端点。", ['python.range_closed', 'python.sorting_duplicates', 'python.branch_parse']),
        ('task_012', 'strutils', ['removeprefix', 'human_readable_list'], 'locate_explain', '前缀切片与自然语言列表', "填写outputs：prefix=removeprefix('foobar','foo')，not_chars=removeprefix('barfoo','foo')，two=human_readable_list(['a','b'])，three=human_readable_list(['a','b','c'],oxford=False)。解释精确前缀与lstrip字符集合的区别，并定位两元素及oxford分支。", ['python.prefix_slice', 'python.branch_formatting']),
    ]
    tasks = []
    for i, (tid, module, functions, kind, title, prompt, concepts) in enumerate(questions):
        patch = i < 2
        rubric = json.loads((ROOT / 'benchmarks/dev/task_001.json').read_text(encoding='utf-8'))['rubric'] if i == 0 else (
            [{'criterion_id': 'R1', 'points': 3, 'description': '严格类型/正值拒绝', 'critical': True}, {'criterion_id': 'R2', 'points': 2, 'description': '原窗口/空源/短源/size1兼容', 'critical': True}, {'criterion_id': 'R3', 'points': 2, 'description': 'fill/end哨兵和无限源前缀兼容', 'critical': True}, {'criterion_id': 'R4', 'points': 2, 'description': '人类盲评源码解释与行号', 'critical': True}, {'criterion_id': 'R6', 'points': 1, 'description': '人类复核补丁、回归用例和实际命令', 'critical': False}] if i == 1 else
            [{'criterion_id': 'outputs', 'points': 6, 'description': '全部预先指定输出与独立key逐项一致；整组全有或全无', 'critical': True}, {'criterion_id': 'source', 'points': 2, 'description': '固定commit的相关函数闭区间、path与hash准确', 'critical': True}, {'criterion_id': 'explanation', 'points': 2, 'description': '人类盲于方法按问题中机制要求审核，每项覆盖才满分', 'critical': True}])
        tasks.append({'record_type': 'EvaluationTaskSpec', 'evaluation_version': 'B-D02-0.1', 'task_id': tid, 'split': 'dev' if i < 4 else 'test_candidate', 'repo_url': 'https://github.com/mahmoud/boltons', 'repo_commit': COMMIT, 'license': 'BSD-3-Clause', 'module': module, 'functions': functions, 'task_type': kind, 'title': title, 'prompt': prompt, 'source_spans': source_span(module, functions), 'required_concept_ids': concepts, 'concept_basis': 'B authored from source behavior; not generated from A graph or Ours path', 'time_limit_minutes': 25, 'timing_status': 'NOT_PILOTED', 'difficulty': 'Python基础，局部API阅读/调试；难度未预演', 'allowed_context': ['固定版本源码', '统一Python标准库资料', '同方法同预算学习材料'], 'prohibited_help': ['终测阶段禁止解答型AI和他人帮助', '评分key不得提供给规划或模型'], 'rubric': rubric, 'max_score': 10, 'success_rule': '全部关键组通过，总分>=9且人类记录用时<=1500秒；缺人类审核为null而非成功', 'submission_format': 'candidate.py + patch.diff + regression_tests.py + explanation.md + commands_and_elapsed.json' if patch else 'answer.json: {outputs: object, source_spans: 本题相关固定源片段, explanation: string}', 'evaluator': 'scripts/B/evaluation/grade.py' if patch else 'scripts/B/evaluation/grade_response.py', 'review_status': 'AGENT_CHECKED_NOT_HUMAN_REVIEWED', 'human_reviewer': None, 'frozen': False})
    folder = ROOT / 'benchmarks/B'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'task_catalog.json').write_text(json.dumps({'record_type': 'evaluation_catalog_not_planning_contract', 'version': 'B-D02-0.1', 'plan': {'target_dev': 8, 'target_test': 16, 'fallback_dev': 4, 'fallback_test': 8}, 'scope_decision': 'One fixed repository with iterutils dev / strutils held-out module. 12 evaluation specifications; human approval and pilot pending, not 12 finalized tasks.', 'formal_freeze': False, 'tasks': tasks}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    for task in tasks:
        (folder / (task['task_id'] + '.md')).write_text('# ' + task['task_id'] + ' ' + task['title'] + '\n\n' + task['prompt'] + '\n\n固定版本：' + COMMIT + '\n\n状态：未人工审核、未预演、未正式冻结。来源与评分组见task_catalog.json。\n', encoding='utf-8', newline='\n')
    print('12 authored evaluation specifications; 0 human approved, 0 formally frozen')


if __name__ == '__main__':
    main()
