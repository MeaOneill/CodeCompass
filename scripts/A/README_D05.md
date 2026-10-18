# A-D05 诊断反馈与接入

Python3.12，应用环境继续使用B的hash锁；A-D05不增加运行时依赖。图表工具用独立target目录和`requirements_d05_figures.hashes.txt`，不能覆盖应用环境或共享B锁。

```powershell
Set-Location 'C:\CodeCompass\CodeCompass-A-D05'
$py = '.\.venv\Scripts\python.exe'
$env:PYTHONPATH = 'src'
$env:PYTHONUTF8 = '1'
$env:TEMP = "$PWD\tmp"
$env:TMP = $env:TEMP
& $py -m pytest -q --basetemp=tmp/pytest-A-D05-observe-NEW
& $py scripts/A/demo_d05.py --outcome pass
& $py scripts/A/demo_d05.py --outcome fail
& $py scripts/A/demo_d05.py --strategy fixed
& $py scripts/A/demo_d05.py --strategy no_feedback
& $py scripts/A/demo_d05.py --no-probability
```

`NEW`换成唯一ID。通过示例预计总成本7；失败示例19；无诊断18；禁用反馈保留原路线并支付测验，总成本19；没有可靠概率则保守补学18。均为结构夹具，不是真人效果。

## 全部开发配置

```powershell
& $py scripts/A/run_d05.py --run-id A-D05-development-NEW
& $py scripts/A/audit_d05.py --run-id A-D05-development-NEW --output experiments/A/A-D05-audit-NEW.json
# 可选独立图表工具，不改变应用依赖：
& $py -m pip install --target tmp/D05-figure-deps --require-hashes -r scripts/A/requirements_d05_figures.hashes.txt
& $py scripts/A/draw_d05.py --run-id A-D05-development-NEW --figure-deps tmp/D05-figure-deps
```

扫描32组配置：阈值.65/.7、宽1/4/16/32、个性化权重0/.5、切换权重0/2；6个输入×4策略，768条全部保存。两结构输入是同一场景的通过/失败合成流；另四个是真实固定源码任务×模拟画像。真实源码开发预算160与结构预算25是本轮预设代理预算，所有策略同输入相同预算，不与B-D04旧预算结果混算。没有真人或正式研究。

## B-D05 最小接口

```python
from codecompass.planner.feedback import (
    start_session, recommend, apply_feedback, complete_next,
)
from codecompass.planner.adaptive_validator import verify_session

s = start_session(root, request, units, ledger, config, quizzes,
                  strategy="voi", alpha=0, gamma=2,
                  max_quizzes=2, options={"beam_width": 16})
choice = recommend(root, s)  # 只有题目、成本与概率来源，没有实际答案
if choice["selected"]:
    # 必须在真实独立评分之后才提交 outcome；不能用点击完成充当通过。
    s = apply_feedback(root, s, choice["selected"], scored_outcome,
                       timestamp=timezone_aware_timestamp,
                       duration_seconds=measured_seconds)
elif s["status"] == "FEASIBLE" and s["plan"]["remaining"]:
    s = complete_next(s, s["plan"]["remaining"][0])
audit = verify_session(root, s)
```

start/recommend/apply/complete均返回或使用普通JSON可序列化对象，反馈/完成函数不修改传入会话。B在自己的存储/UI中持久化；A不写B数据库。时间缺失为null，不能换算成代理成本。每次更新带完整事件链和已完成前缀。

`scheduled=True`只供已经按协议安排、独立评分的学习后测验；它不是VOI自选诊断，仍使用同题池、费用、次数上限和去重。不得用它绕过同帮助预算或把终测泄露给规划器。

生产概率需要`kind=development_calibration`及公开`benchmarks/dev`文件路径/SHA，文件含split=dev、非模拟标记、concept_id、n≥20、passes和来源。本轮没有此类校准资料，因此生产VOI禁用；纯结构夹具可用明确标注的synthetic_prior测试代码路径，不能用于真实源码推荐。n≥20只是输入门槛，不保证校准质量，后续仍需开发证据审查。

旧B2、beam、exact、证书和schema均保持兼容。新内部D05响应不是旧PlanResult；B不要把D04证书附到新顺序目标上。新搜索最多报告FEASIBLE、NO_FEASIBLE_FOUND或TIMEOUT，FEASIBLE不保证最优。新目标解释见docs/A/innovation_mechanism.md。
