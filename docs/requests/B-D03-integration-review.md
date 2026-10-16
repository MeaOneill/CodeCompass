# B-D03 → A-D04 接口反馈

采用A-D03 cf02b664aea81f91aa8e7423a8aa891367c73b7e、schema兼容1.1.0、ledger0.1.0和A-D03-dev-0.1。B实际运行103前置测试/演示/来源与路线审计通过；现接入存储并通过新进程恢复、同题幂等、项目/用户/模式隔离及事务回滚测试。

无需A改learner算法。B按A去重范围执行：同用户concept/item跨项目去重、聚合限当前项目。阅读不新增共享enum，映射unscored非独立self_report，B事件外层记录reading来源。a/b缓存只是同事务派生值，不作新规划契约；PlanningRequest始终由实际恢复ledger的planning_rows生成。

真实Issue只匹配到同模块但不同函数，未给出适合当前任务的确定推荐；来源与缺口见B快照和G1。后续A若新增动态路由/诊断，请维持plan_request边界，明确输入配置版本与独立item_id来源；不要把源码阅读时长作为通过事件。硬教学边仍需实际人工审核，本轮B AI来源/路线复核不是human批准。

A-D04第一动作：fetch本轮B分支并核对最终SHA，读B-D03交接，先运行B公开演示与审计（交接给出命令），确认恢复接口再推进A-D04搜索/精确求解任务。无须访问B的私有终测key。
