# B-D02接口与编辑范围登记

依赖A-D02=30069ce468a52b68a0d3bfb62bb49b1cce0f2104，共享契约1.0.0、图0.1.0。B先通过31测试/947span图审计后创建独立B分支。

1. CodeTask.origin.kind目前const=upstream_todo_adapted，不能如实表达源码行为定位题、团队设计的调试题。请求A后续升版支持source_behavior_adapted/team_designed_debug并登记设计来源；B不伪称上游TODO或Issue，不改共享schema。B-D02新增题先使用独立的EvaluationTaskSpec（评分规格，不是规划输入/状态），可映射的字段由A集成，暂不宣称共享CodeTask联调通过。
2. B独立评分代码在scripts/B/evaluation及tests/B，候选题/公开任务说明在benchmarks/B；dev评分可复用已公开task_001 rubric，终测评分key不进入app/src/模型接口。私有key与补丁不提交Git，用忽略的tmp/B-D02-private保存；Git只保留不含答案的来源、hash和恢复要求。缺少私有key时评分必须拒绝，不能默认满分。
3. B0为人工规则固定源码顺序，不使用graph/planner或Ours输出。A的三个task_001学习单元成本未知；未获得公共代理成本前，B0只返回INPUT_INCOMPLETE与明确标注的无成本阅读顺序，不能将null当0或虚构预算内可行。测试夹具可验证预算截断逻辑，必须标synthetic，不作算法结果。
4. 新增held-out源包仅放benchmarks/sources/boltons_B_D02，保留A原四文件包/快照/hash不改；同一固定commit，模块按iterutils(dev)/strutils(test候选)隔离。B仅追加.gitattributes的B新增路径与.gitignore精确私有评分目录，理由为原始字节与答案边界，保留旧规则。
5. 用户新增每日规则已接收：提供可见累计成果与逐步人工自验；严格复检，未通过项不得勾过或自动进入下一日。会固化在docs/B/每日验收规则.md，Agent自审与独立人类审核分开。

B0为避免依赖成本未定义而无可展示路线，新增显式选项source_lines_proposal：按固定源码span行数测量静态代理成本，B运行时复制输入后赋值，不改共享单元或A成本配置。此政策尚未获A/人类接受，formal_comparison_eligible=false；保留默认shared模式的INPUT_INCOMPLETE原始运行，正式对照前必须各方法统一成本。静态行数不是学习分钟。

收尾更新：B0改用固定README链接的RST文档出现顺序自动生成，已完成文档固定基线开发验收。12评分规格已逐题AI工程审核并完成负例挑战。新origin适配/共同成本是A-D03至D06集成事项；B-D02当前独立评分/文档路线可运行，不再将这些等同用户必须先做编程题的阻塞。正式比较前仍须统一，不由B擅改共享契约。
