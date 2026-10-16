# B-D02数据与评分访问边界

应用可读：既有schemas/examples、benchmarks/dev、benchmarks/sources。retrieval.load_object新增白名单，真实路径解析后再核对，拒绝私有目录/评分key路径，阻止正常CLI/规划输入读取评分文件。app与src不import scripts/B/evaluation。此为应用接口边界，不是对能读整个磁盘的用户/Agent的OS访问隔离。

开发题公开：benchmarks/dev/task_001.json沿用A原文；benchmarks/B/task_catalog.json的task_001—004为B独立评分规格，开发题行为key和开发夹具可以共享。A原task_001、units、schema及图源均不改。新增task_002尚非共享CodeTask，原因是origin.kind字段限制，见接口请求；不声称规划端已消费它。

留出候选：task_005—012属strutils，开发模块为iterutils，固定同一boltons commit。公开问题说明、来源和rubric不含独立终测key。当前是候选池，未正式冻结；模块留出仍可能共享Python通用概念，只能主张跨模块留出，不能声称跨仓库泛化。留出集没有局部修改题，类型覆盖仍需人类复核，不能正式定案后再按方法表现挑题。

评估私有：private_evaluation/B-D02/keys.json与含答案的夹具被.gitignore排除。它们只由显式--private-key/--key传给评分脚本，不能交给app、模型上下文或A规划器。公开运行结果只含状态、分数门禁和hash，不能输出原始答案。原始上游源码/测试含自身公开示例，不能假装这些知识对参与者保密；本项目独立题答案key仍单独保存。

私有key目前仅在B本机，未上传任何共享存储，不假称A可取得。A-D03做规划只需公开任务信息，不需要评分key；另机重跑终测评分须由人类选择受限传输渠道，按公开receipt中的SHA256核对，不放进团队公开分支/聊天/应用目录。缺key必须拒绝评分。没有该私有文件的新clone只能复现开发题及通用测试，不能记完整终测重放通过。

元数据中的reviewer_kind=human只是显式审核回执，不自动证明审核者身份；审核人应由团队真实确认。Agent生成的正确开发夹具一律is_fixture=true，不当参与者，也不给它伪造人类解释分。正式人类回执应绑定完整提交hash、评分组、盲评说明、真实用时和审核者，题目/用时未经预演前不签通过。
