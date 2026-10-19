# A-D06 开源适配与创新审查

本文件是代码来源和适配边界审查，不是研究新颖性认证。Owner成员A；Agent辅助实现；精确会话模型不可核实，unknown。机器糯糯。当前源码基线B-D05 5e6ecb1；新文件由本轮Agent实现，原模块沿用项目A-D03至D05；未导入第三方规划器改名。

| 来源/标准思想 | 实际使用与自主适配 | 定位/检验 | 不主张的原创部分 |
|---|---|---|---|
| Python AST、固定boltons源码快照 | 源码span/hash校验、源码依赖与教学边分层、provenance | src/codecompass/graph，benchmarks/sources/boltons/snapshot.json与LICENSE | Python解析器、boltons源码本身 |
| Beta后验与保守分位门控 | 独立题ID/项目隔离、去重、不以阅读增加掌握 | learner/model.py，test_adaptive_d05.py及test_g2_d06.py | 贝叶斯更新数学与知识追踪思想 |
| 贪心、beam、子集DP | core.py强B2保留；adaptive.py完整有序前缀，在完成前缀/预算/软硬先修下求剩余路径、显式截断与回退 | remaining_plan、route_audit；D04随机枚举及D05顺序反例测试 | 标准搜索框架、DP思想，FEASIBLE不称最优 |
| 信息价值思想 | diagnostics.py同一规划器求pass/fail两分支，同单位成本，超时/未知概率回退；真实候选禁用 | select_diagnostic；D05概率/超时/费用测试 | VOI概念及尚无真实概率校准的收益 |
| 事件驱动重规划 | feedback.py保留完成项、诊断与切换费用去重、观察和规划ledger分开 | apply_feedback、normalize_adopted_plan、verify_session | 普通反馈交互与前端界面 |
| 本轮控制器 | g2_candidate.episode实际调用上述remaining_plan；no_gate显式空规划视图而保留观察ledger；无反馈冻结规划视图；同一题、预算与费用 | run_d06.py、30次开发原始JSON/CSV、test_g2_d06.py | 只是消融封装，不增加第三项算法创新 |
| jsonschema/pytest/Matplotlib | 契约检查、测试、图表导出 | 依赖哈希锁与绘图入口 | 第三方库及字体；字体仅本机渲染，不复制字体文件 |
| B1 DeepSeek | B维护历史调用与提示词；本轮只读回放和hash | experiments/B/B-D04-deepseek-live01/prompt.txt、config.json、registration.json | 第三方模型/上游服务，不称自研，provider revision未知 |

查新使用docs/related_work.md及docs/references/A-D02-source_provenance.json的既有查新矩阵。KnowLP的图/先修/知识追踪、U-GLAD的目标与不确定性、GraphCodeBERT的数据流、code2vec的AST表示都不是本项目原创；本轮没有新检索全文，不声称已穷尽相关工作。无上游规划库代码diff，因为没有引入此类库；相对本项目旧B2的可定位差异是adaptive.py及feedback.py，而非更换库名。完整Git差异以base..任务HEAD为准。

伪代码（当前保守候选）：

```text
validate public source, full independent evidence, units and common proxy budget
planning_view = ledger (no_gate: empty view; no_feedback: frozen initial view)
beam over ORDERED remaining prefixes; preserve completed units; enforce budget/prerequisites
execute first material; charge material cost; do not add mastery evidence
schedule one common independent quiz; charge cost; reject repeats
update observation ledger; if feedback enabled, repair only remaining route using same planner
validate route/accounting; record feasible, timeout or no feasible found explicitly
```

相对B2的适配是状态约束的有序剩余决策与已完成项保留，不只是调权重或改UI。但两个真实源码开发任务没有证明算法优于B2，D06模拟反馈也不证明真实学习收益。至多C1实际任务价值与可选C2反馈价值；生产VOI、权重标定不作为贡献。

审核状态：Agent自审已执行；另一个AI会话按任务卡步骤4开展只读交叉代码检查，原始发现与处理将保存在experiments/A/A-D06-review。成员B确认、独立人类源码/教学边审核、上游许可的正式法律审核仍未完成。不能勾选正式G2或双成员批准。


最终AI交叉审核：独立子会话g2_source_review，22项D06测试独立执行通过、109文件候选审计通过。计时等价误判已修复并用controls03重跑；文档旧run编号及措辞已勘误。报告见experiments/A/A-D06-review/independent_ai_review.md。未获成员B/人类批准。
