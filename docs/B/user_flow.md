# B-D01用户流程设计

本轮是页面与存储设计，只有CLI、契约和只读源码加载可运行；页面、规划器、持久化、模型与Issue API尚未实现。结构图不代表学习效果。

1. 仓库导入：选固定快照，展示URL、完整commit、许可、采集时间、局部包范围与hash。当前真实输入为boltons，commit `4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d`，BSD-3-Clause，四文件局部包。hash不匹配则阻止进入任务。
2. 任务：选task_001，显示局部count扩展、25分钟设计上限、要求与独立评分原则。时长未预演。开发题rubric允许共享；未来冻结终测答案不交应用/模型。
3. 短测：拟采集题目ID、匿名证据、时间与独立性。阅读次数/自述不能直接计掌握；当前无测验实现，不显示分数或推断掌握率。
4. 路径：调用A规划接口，展示ordered_units、理由、proxy_cost、未满足约束。未知base_cost必须阻止成本计算，不能用零；只有FEASIBLE且独立约束检查通过才展示可行。TIMEOUT、NO_FEASIBLE_FOUND和INFEASIBLE_PROVEN分别提示。模型问答只能辅助解释，不能生成替代算法的“成功路径”。
5. 源码依据：每个单元展示固定commit、相对路径、1起闭区间和片段hash。真实案例：`boltons/iterutils.py:286–306`为chunked包装器，`:316–358`为chunked_iter生成器，`:329`为TODO。点击定位必须打开本快照字节，不跳到浮动main。CLI已经验证这些定位。
6. 反馈：独立题通过/失败才向A learner接口提交证据，重复item_id去重；保存旧路径、新路径及原因，不覆盖失败历史。接口未实现则暂停并保留检查点。
7. 记忆：拟使用本地SQLite保存匿名证据、事件和路径版本，排除Git。重启后按run_id、最新checkpoint和输入hash恢复，暂停时长不计主动学习时间但单独保留。当前只定义字段，未宣称持久化通过。
8. Issue：未来在线拉取真实链接、状态、抓取日期及模块关系，输出技能缺口和贡献准备步骤；无适合Issue就明确为空。task_001来源为固定源码TODO，上游未确认、issue_url=null，不能将它显示为开放Issue。发帖/PR需人类另行授权。

在线抓取服务于候选发现和状态更新，受网络、认证和速率限制影响；固定快照服务于复现，URL+commit+许可+原始字节hash不可用浮动分支替代。断网时加载当前局部包，不伪称拥有完整checkout；Issue缓存必须显示“历史抓取，当前状态未核验”。

F01依赖：B app→B retrieval→只读源包/共享schema；app→A graph/learner/planner（未实现）；app→本地SQLite（计划）；B issues→GitHub API（计划）；可选模型接口仅解释（计划，可禁用）。源码/任务JSON入Git；用户数据库、密钥不入Git；独立终测答案由B隔离。API失败有事件、重试预算和暂停入口，不回填成功。
