"""Public, unmodified task source and submission scaffolding; no final oracle."""
import io
import json
import zipfile
from codecompass.app.relay_v2 import prepare

README='''# 从这里开始：给窗口函数加输入检查

你只需要完成一个局部修改。先读网页中的任务说明和路线，再使用这个包。
滑动窗口示例：[1,2,3,4]，大小2，得到(1,2)、(2,3)、(3,4)。

1. 将本zip解压到一个新文件夹，在编辑器中打开该文件夹。
2. candidate.py 是完整、未修改的固定版本源码。original.py 是对照副本，请勿修改。
3. 打开终端，在该文件夹运行：python -c "from candidate import windowed_iter; print(list(windowed_iter([1,2,3,4], 2)))"
   这一步只观察正常行为，不表示最终任务通过。
4. 在candidate.py中搜索 def windowed_iter，只修改此函数。要求：size只接受内置正int，排除bool；类型不对抛TypeError，整数<=0抛ValueError；保留原正常窗口、空/短源、fill省略与None、pairwise end及无限输入前缀行为。
5. 在regression_tests.py补写你自己的测试。先保留正常输入，再自己检查错误输入和兼容情况。不会时回网页阅读或用源码提问卡学习；包内没有完成补丁或最终评分答案。
6. 运行：python prepare_submission.py。它会执行你的测试，保存真实输出、退出码和耗时，并生成patch.diff。运行失败也如实保存；修复后可重跑，新输出在runs目录保留。
7. 在explanation.md中写你改了哪里、为什么、读到的源码行号、仍有什么没完成。
8. 回到网页选择5个文件：candidate.py、explanation.md、regression_tests.py、patch.diff、commands_and_elapsed.json。

准备脚本不是最终评分器；模板中的测试仅检查一个正常示例。不要把测试退出0当作题目通过。无需上传original.py、START_HERE.md或runs目录。
如果做不完，页面可保存为退出，不必编造答案、测试或耗时。
'''
PREPARE='''from pathlib import Path
import subprocess,sys,time,json,difflib,datetime
root=Path(__file__).resolve().parent
start=time.perf_counter()
try:
 r=subprocess.run([sys.executable,'regression_tests.py'],cwd=root,capture_output=True,text=True,timeout=30)
 result=dict(command=[sys.executable,'regression_tests.py'],exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr,status='EXECUTED')
except subprocess.TimeoutExpired:
 result=dict(command=[sys.executable,'regression_tests.py'],exit_code=None,status='TIMED_OUT',stdout=None,stderr='30 second timeout; partial output not reconstructed')
result.update(elapsed_seconds=time.perf_counter()-start,recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),final_grade=None,notice='Learner tests only; not independent grading')
runs=root/'runs';runs.mkdir(exist_ok=True)
name=datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
raw=json.dumps(result,ensure_ascii=False,indent=2)+'\\n'
(runs/(name+'.json')).write_text(raw,encoding='utf-8')
(root/'commands_and_elapsed.json').write_text(raw,encoding='utf-8')
old=(root/'original.py').read_text(encoding='utf-8').splitlines(keepends=True)
new=(root/'candidate.py').read_text(encoding='utf-8').splitlines(keepends=True)
(root/'patch.diff').write_text(''.join(difflib.unified_diff(old,new,fromfile='original.py',tofile='candidate.py')),encoding='utf-8')
print('Recorded actual test run; final grade is still pending. Exit:',result['exit_code'])
print('Upload the five files listed in START_HERE.md when ready.')
'''

def starter(root,task_id):
    if task_id!='task_002':raise ValueError('此版本仅提供默认任务的起始包')
    d=prepare(root,task_id,'public-starter',True)  # Validates public snapshot hashes.
    source=(root/d['source_root']/'boltons/iterutils.py').read_bytes()
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in {'candidate.py':source,'original.py':source,'LICENSE':(root/d['source_root']/'LICENSE').read_bytes(),
            'START_HERE.md':README,'prepare_submission.py':PREPARE,
            'explanation.md':'# 我的修改说明\n\n## 修改位置和理由\n（请自己填写）\n\n## 源码依据及行号\n（请自己填写）\n\n## 自己运行的测试与未完成项\n（请自己填写）\n',
            'regression_tests.py':"# 这只有一个正常行为示例，请自己补充边界/兼容测试。\nfrom candidate import windowed_iter\nassert list(windowed_iter([1,2,3,4], 2)) == [(1,2),(2,3),(3,4)]\nprint('Normal example passed; final task is NOT graded.')\n",
            'source.json':json.dumps(dict(task_id=task_id,commit=d['task']['repo_commit'],source_path='boltons/iterutils.py',original_unmodified=True,final_answers_included=False),indent=2)}.items():z.writestr(name,data)
    return out.getvalue()
