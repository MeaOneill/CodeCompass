# A-D04比较接口交给B-D04

A：新增codecompass.planner.search_service.solve_request(root,request,units,state,config,method='beam',options=None,certify_small=False)。返回(result,details)；方法B2/beam/exact。旧service、__init__、core、learner、契约与B模块不改。详细参数、证书持久化和状态限制见docs/A/algorithm.md与scripts/A/README_D04.md。

A：强B2保持D03来源hash，方法之间只改搜索策略，候选/画像/图/成本一致；不能从A的模拟夹具填B1成绩。B-D04按原卡实现B0/B1/B2与beam同接口批量比较、独立指标单测与手算例，未调用模型时标未运行。不把搜索覆盖分数当代码任务成功率。

A：同集合去重仅限固定可加成本；B后续引入序列相关目标需先通知A扩展状态。TIMEOUT不能折成NO_FEASIBLE或最优；INFEASIBLE_PROVEN仅<=12完整证据，超过12不能生成证明。真实任务本轮成本平局，正式收益待验证。