"""Autonomous task-quality review and negative-answer challenges, no human claims."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.B.evaluation.dev_fixtures import create_fixture
from scripts.B.evaluation.grade import grade
from scripts.B.evaluation.grade_response import grade_response

# Explicit per-question engineering judgment, independent of planner outputs.
NOTES = {
 'task_001': ('较难', '需要同时控制生成器惰性、count边界、输入消费和包装器兼容，难点不只是新增参数。', ['函数与参数', '迭代器', '生成器/yield', 'itertools.islice'], '适合已学过生成器的Python使用者；不能将只学过基本语法视为同等基础。'),
 'task_002': ('中等', '修改局限于入口类型校验，但必须保持tee窗口、默认哨兵和调用包装器兼容。', ['异常类型', 'bool与int关系', '迭代器', '默认参数哨兵'], '理解tee可阅读标准库资料；要求明确只接受内置int，避免校验歧义。'),
 'task_003': ('中等', '需区分保存的key与实际yield对象，不能只背集合去重。', ['集合哈希', 'key回调', '生成器'], '三个输入各测试顺序、大小写键与长度键，解释项检查机制而非只抄输出。'),
 'task_004': ('中等', '需跟踪嵌套访问、异常转译以及缺省值与实际None的区别。', ['字典/列表', '异常处理', '默认值哨兵'], '缺路径、数字字符串索引、空路径分别检查不同分支，不把None都当失败。'),
 'task_005': ('较易', '局部正则和split/join转换，修改规模小但需注意缩写边界。', ['字符串操作', '正则基础'], '两个转换不是严格互逆，解释项必须指出边界。'),
 'task_006': ('中等', '分支优先级、标点与空串、字节/文本返回类型同时出现。', ['条件表达式', 'bytes/str', '正则分割'], '题面用字节列表表示ascii结果，避免JSON无法表达bytes的歧义。'),
 'task_007': ('较易', '单函数字符串末位和teen例外分支，有明确可定位机制。', ['字符串索引', '字典查找', '分支'], '输入列表覆盖teen、常规后缀与非数字文本，不能只测试21。'),
 'task_008': ('中等', '同一功能有文本与字节路径，需识别ANSI支持范围。', ['转义序列', 'bytes/str'], '题面明确是真实ESC字符；评分不要求声称处理任意终端控制协议。'),
 'task_009': ('较易', '两函数往返关系和BytesIO，比完整压缩格式分析简单。', ['字节流', '函数组合', '压缩基础'], '只检验往返与类型，不把受环境影响的压缩字节串作为金标准。'),
 'task_010': ('中等', '生成器末尾空行与缩进谓词存在边界交互。', ['生成器', '正则捕获', '谓词'], '题面明确真实换行；多个输出检验空串、尾空行和缩进连接。'),
 'task_011': ('中等', '需要区分区间闭端点、排序和去重，观察分支组合。', ['range', '排序', '字符串解析'], '明确反向范围与重复保留，不预设文档描述等于去重。'),
 'task_012': ('较易', '精确前缀切片及列表长度分支，源码范围局部。', ['切片', 'startswith', '字符串拼接'], '不将removeprefix等同lstrip；两元素和oxford分支各有独立要求。'),
}


def wrong(value):
    if isinstance(value, list): return value[1:] if value else ['wrong']
    if isinstance(value, dict): return {'wrong': True}
    if isinstance(value, str): return value + '__wrong'
    if value is None: return 'not-null'
    return value + 1


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--run-id', required=True)
    p.add_argument('--private-key', required=True)
    a = p.parse_args()
    if not a.run_id.replace('-', '').replace('_', '').isalnum(): p.error('Invalid run-id')
    out = ROOT / 'experiments/B' / a.run_id
    out.mkdir(parents=True, exist_ok=False)
    private = ROOT / 'private_evaluation/B-D02' / a.run_id
    private.mkdir(parents=True, exist_ok=False)
    catalog_path = ROOT / 'benchmarks/B/task_catalog.json'
    cat = json.loads(catalog_path.read_text(encoding='utf-8'))
    original_task = json.loads((ROOT / 'benchmarks/dev/task_001.json').read_text(encoding='utf-8'))
    # Keep the shared task's complete source/concept requirements, rather than
    # an abbreviated list in the evaluator catalog. No graph-generated gold.
    cat['tasks'][0]['source_spans'] = original_task['source_spans']
    cat['tasks'][0]['required_concept_ids'] = original_task['required_concept_ids']
    keys = json.loads((ROOT / 'benchmarks/B/dev_response_keys.json').read_text(encoding='utf-8'))['tasks']
    keys.update(json.loads(Path(a.private_key).read_text(encoding='utf-8'))['tasks'])
    checks = []
    for task in cat['tasks'][2:]:
        tid = task['task_id']
        baseline = {'outputs': keys[tid]['outputs'], 'source_spans': task['source_spans'], 'explanation': 'Engineering fixture, not participant response.'}
        key_path = ROOT / 'benchmarks/B/dev_response_keys.json' if task['split'] == 'dev' else Path(a.private_key)
        variants = []
        for field in baseline['outputs']:
            bad = copy.deepcopy(baseline);bad['outputs'][field] = wrong(bad['outputs'][field])
            variants.append(('wrong_output_' + field, bad, 'output'))
        bad = copy.deepcopy(baseline);bad['source_spans'][0]['content_hash'] = '0' * 64
        variants.append(('wrong_source_hash', bad, 'source'))
        bad = copy.deepcopy(baseline);bad.pop('outputs')
        variants.append(('missing_outputs', bad, 'output'))
        for label, answer, kind in variants:
            f = private / (tid + '-' + label + '.json')
            f.write_text(json.dumps(answer, ensure_ascii=False), encoding='utf-8')
            result = grade_response(tid, f, key_path)
            passed = result['success'] is False and not result['outputs_passed' if kind == 'output' else 'source_passed']
            checks.append({'task_id': tid, 'mutation': label, 'detected': passed})
    # Specific code mutations challenge genuine API compatibility, not just a
    # correct fixture against its own implementation.
    for label, old, new in [
        ('accept_bool_size', 'if type(size) is not int:', 'if not isinstance(size, int):'),
        ('accept_zero_size', 'if size <= 0:', 'if size < 0:'),
        ('ignore_custom_fill', 'fillvalue=fill)', 'fillvalue=None)'),
    ]:
        folder = create_fixture('task_002', ROOT / 'tmp' / a.run_id / label)
        f = folder / 'candidate.py';text = f.read_text(encoding='utf-8');assert old in text
        f.write_text(text.replace(old, new), encoding='utf-8')
        result = grade('task_002', folder)
        checks.append({'task_id': 'task_002', 'mutation': label, 'detected': result['status'] == 'FAILED_AUTOMATED'})
    passed = all(c['detected'] for c in checks)
    reviews = []
    for task in cat['tasks']:
        level, reason, prerequisites, fairness = NOTES[task['task_id']]
        review = {'task_id': task['task_id'], 'reviewer': 'Codex Agent B', 'reviewer_kind': 'AI_engineering_self_review', 'difficulty_estimate': level, 'difficulty_reason': reason, 'assumed_prerequisites': prerequisites, 'fairness_and_rubric_check': fairness, 'source_lines_to_inspect': sum(s['end_line'] - s['start_line'] + 1 for s in task['source_spans']), 'elapsed_learning_minutes': None, 'human_pilot': 'NOT_RUN', 'human_review': 'NOT_REVIEWED', 'engineering_review_passed': passed}
        reviews.append(review)
        task['engineering_review'] = review
        task['difficulty'] = level + '（AI工程估计，非真人用时测量）'
    cat['scope_decision'] = 'D02 engineering scope: 12 source-grounded task specifications (4 dev / 8 held-out candidates), individually AI-reviewed and evaluator-challenged. Not human-reviewed, piloted or formally frozen.'
    catalog_path.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    fingerprints = {t['task_id']: hashlib.sha256(json.dumps({k: t[k] for k in ('task_id', 'prompt', 'source_spans', 'required_concept_ids', 'rubric', 'time_limit_minutes')}, sort_keys=True, ensure_ascii=False).encode()).hexdigest() for t in cat['tasks']}
    report = {'task_id': 'B-D02', 'review_scope': 'engineering_task_quality_not_human_learning_validation', 'source_of_authority': 'User explicitly authorizes autonomous difficulty judgment; D02 card requires runnable tasks/rubrics, not user solving tasks.', 'reviewed_task_content_hashes': fingerprints, 'checks': checks, 'negative_challenges': len(checks), 'all_detected': passed, 'task_reviews': reviews, 'exit_code': 0 if passed else 1}
    (out / 'quality_review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(len(reviews), 'individual AI engineering reviews;', len(checks), 'negative challenges;', 'passed=', passed)
    return report['exit_code']


if __name__ == '__main__': main()
