# A-D03运行与B集成

Python3.12，沿用B的hash锁，不新增依赖。不执行第三方源码安装脚本；静态快照与文档作为数据读取。新机器：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r scripts/B/requirements-d01-win-py312.hashes.txt
$py = '.\.venv\Scripts\python.exe'
$env:PYTHONPATH = 'src'
New-Item -ItemType Directory -Force tmp | Out-Null
& $py -m pytest -q
& $py scripts/A/demo_d03.py
& $py scripts/A/check_d02.py --run-id A-D02-20261016-graph02
& $py scripts/A/audit_d03.py --source-run A-D03-short-tests04 --run-id B-D03-audit01
```

run_id必须新的，不覆盖历史。原始复跑：`python scripts/A/run_d03.py --run-id B-D03-replay01`；git不在PATH时CODECOMPASS_GIT设置本机git绝对路径。绘图`python scripts/A/draw_d03.py --run-id B-D03-replay01`，需Windows微软雅黑字体；渲染配置记录字体字节hash，跨机不可假定像素hash一致。

公开入口 `plan_request(root, request, units, state, config)`（codecompass.planner）返回`(PlanResult, details)`，details含gate/candidate_attempts/replay_audit。root须正确项目根；span和字节会重验；request聚合必须等于从ledger推导的planning_rows。七对象兼容扩展schema见schemas/contracts-1.1.schema.json；旧1.0不改，原D01空成本不能直接规划。

能力API在codecompass.learner：initial_state(user_id)、update_evidence(state,evidence)->(new_state,decision)、planning_rows(state,project)、mastery_gate。序列化状态格式0.1.0 records列表；原状态不会修改，B负责事务/原子落盘、用户隔离、并发、重启恢复。不把阅读、自报、无独立评分事件转为掌握。item去重范围同用户+concept_id+item_id跨项目，聚合只当前项目；模拟须显式state标记和allow_simulated=True，不可用于真人。

示例输入在最终run各cases中的request/units/learner_ledger.json，仅模拟。两任务dev覆盖位于benchmarks/dev/D03，成本/阈值/B0顺序位于configs/A。核心仅整数Beta证据计数，不支持分数权重/跨项目迁移。诊断、持久化、正式UI/原app接线未实现。check_plan验证结构，不是独立学习成功评分器；评分仍由B独立服务负责，A不读取私有答案。

pytest默认现包含tests/A与tests/B，避免只运行一方测试。完整命令与真实退出状态见experiments/A/A-D03-verification02/commands.json，非法负预算退出2是预期拒绝。
