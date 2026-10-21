# A-D07 v3独立实现复核（修复前）

结论：**11项既有新回归通过，但存在P1，暂不能放行真实补充验证。** 仅检查明确授权的新技术文件，模拟数据库与故障输出均在干净克隆tmp；未读真人记录，未改主代码。

## P1：规划失败会回滚已提交答案，并允许改答

位置：`src/codecompass/app/pilot_d07_v3.py` 的 `Pilot.action`，history和diagnosis分支均在同一 `with self.connect() as db` 事务内记录答案、增加花费，再调用 `plans`，直到末尾才save。`plans` 在Ours TIMEOUT/非FEASIBLE时抛ValueError，整个提交回滚。`serve_d07_v3.py` 随后返回通用400，未将会话永久标FAILED。

独立反例：只patch新模块的safe_remaining返回TIMEOUT，不改任何源文件。

- history：提交5个正确答案后规划失败，持久状态仍ACTIVE/history，answers=0；随后可改为5个skip重新提交，系统接受。
- diagnosis：提交第6个正确答案后规划失败，持久状态仍ACTIVE/diagnosis，answers=5；随后可改为skip重交并DONE。

这违反固定六题各答一次、失败记录保留和不可追答约束；不能以正常成功路径11测试通过替代该故障路径。需先将已接收作答/证据/花费持久保存，规划失败时保留并标FAILED，禁止重答；或用等价不可逆提交状态实现。不要把已接收数据的规划异常回滚成“未作答”。

## 已通过及边界

正常全pass时费用10→11、同spent no_feedback=11、Ours/B2实际路线删除u_iterable且保留completed；11既有测试通过。public_item不返回answer/oracle；公开view无gate或掌握下界。第6题仅在before_plan_sealed事件之后进入diagnosis。事件带ui_version和source_digest，provenance持久保留源hash，补足旧UI溯源问题。

JS通过renderedStage避免同阶段重建题目，普通暂停/恢复与轮询保留当前DOM选项；页面刷新未提交选项不会持久恢复。未运行真实浏览器验收，不把静态检查称浏览器证据。单实例顺序重复启动、重复投递及正常时钟/超时的既有测试通过；不据此声称全部跨进程竞态已排除。

另外，“不会/跳过”当前明确保存missing=true，同时作为fail写入Beta证据；新协议应如实说明此保守记法，不可称缺失未计分。此点不影响发现的P1故障结论。

## 实际执行及原始证据

设置PYTHONPATH为主树src/root、PYTHONDONTWRITEBYTECODE=1；授权解释器提升执行，只在克隆tmp写模拟输出。

1. `python.exe -m pytest C:/CodeCompass/CodeCompass-A-D05/tests/A/test_pilot_d07_v3.py --basetemp tmp/independent-audit/v3 -p no:cacheprovider -q`：exit0，**11 passed in 6.94s**。原始输出 `v3-pytest.log`。
2. `python.exe tmp/independent-audit/v3-faults.py`：exit0，两个事务回滚/重答反例断言均复现。原始脚本、JSON、log：`v3-faults.py`、`v3-faults.json`、`v3-faults.log`。

故障输出仅为模拟技术数据，不计真人样本。本报告为独立AI技术审查，不构成人类批准或G2签字。修复后需只复验该P1和受影响回归，无需扩大研究范围。
