# A-D03 → B-D03接口与待办

前置：B-D02 fc6485329691efda2662e21116d8f23e329b4d96；本轮codex/A-D03-planner。A回应B成本/来源请求：新增兼容schema1.1和dev覆盖文件，旧schema/旧D01空成本不变。成本为固定源行数proxy_cost，明确非分钟；B0函数不改，task2按同一文档策略扩展。

B第一动作：核对最终通知SHA与origin/codex/A-D03-planner，干净工作区创建B-D03分支并运行pytest和最终run审计。参见docs/A/handoffs/A-D03.md，不从旧main猜测依赖。

随后按B-D03卡实现：

1. 将codecompass.learner纯函数ledger接入B持久化；按用户隔离、原子存储、重启恢复、重复item/evidence幂等，不将阅读/自报转为掌握，不把模拟记录导入真人。先按README_D03/API做roundtrip，保存实际命令和结果。
2. 规划接线调用plan_request(root,request,units,state,config)，在加载1.1之前验证版本，拒绝空成本；聚合必须来自ledger，不可手填强掌握数值。演示使用D03覆盖及同一cost_unit/config。
3. 真实少量Issue保存URL/状态/获取日期/源相关性，贡献准备CLI；需与模拟事件分开。A不代做B模块，也不发社区消息。
4. 联合G1 T1图/T2路线/T3能力+Issue，T3本轮未完成；逐步复核至少一个真实任务路线再记录B实际审核。诊断/beam/正式UI/真人学习效果不可标完成。

硬教学先修仅人工approved且有human-review证据方可生效；当前真实边全部soft。合成夹具的SYNTHETIC_REVIEW_NOT_A_PERSON不是人工审核。公开分支不含B私有答案，A没有读取私有评分key。
