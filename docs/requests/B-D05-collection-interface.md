# B-D05 对 A-D06 的接口复核请求

基于A-D05 7a2a268cd3122abe9165a78b45b45cddf0a18515，调用start_session/apply_feedback/complete_next与独立verify_session；未修改A模块/共享schema。

开发UI同一短测、单次费用1、最多1次，至少读完一份材料后执行scheduled学习后评估。初始未知画像，alpha/gamma=0、共同预算100。真实p_pass缺失，生产VOI禁用；不能把scheduled当成自选诊断贡献。

B2在已完成覆盖之外规划剩余目标；B0/B1_saved静态保留。B1_saved为D04实际响应回放，没有动态反馈重规划，不做正式同条件效果主张。最终评分保留null且不传递终测答案，UI只保存独立任务提交说明/hash。

请在D06冻结前明确动态B1策略/费用授权、所有方法诊断时机、跨轮能力复用与最终独立评分入口。当前采集支持这些缺失状态，不用默认成功/0秒填补。A接收从B-D05最终验收门禁开始；真人手动操作尚待完成时不要放行正式冻结。

## B-D05 最终验收 2026-10-18T23:17:35.157151+08:00

**本日工程与真人开发操作验收通过，允许进入下一步A-D06。** 状态READY_FOR_REVIEW，未合main；独立人类审核仍NOT_REVIEWED。

用户确认已完成，实际本地human_manual库有同一匿名参与者3轮/35事件：2轮WITHDRAWN、1轮SUBMITTED；1轮完整阅读→短测→反馈→重规划→最终提交，另1轮退出前完成暂停/恢复。时钟有效，无缺失，240项独立日志检查通过；全仓236测试通过。去标识记录在experiments/B/B-D05-manual01/manual/export01；数据库、自由文本和本地令牌不入库。此人是开发预演者，不计正式研究样本，不把3轮当3个人。

纠正了审计脚本额外要求“暂停必须与最终提交处于同一轮”的实现限制：任务卡不规定该顺序。核心完整流程仍必须来自同一会话，暂停恢复另行审计；两轮退出、旧拒绝结果与全部原事件保留，没有拼接会话或补时间。新增正反回归测试通过。

B1静态回放、动态B1/正式终测评分未接入、生产VOI未校准、独立人类审核和异机复现未完成等既有边界不变；本轮没有新API调用。允许A-D06继续协议及接入边界工作，不代表正式研究已经可启动。

A-D06第一动作：fetch并核对B-D05最终通知SHA，然后在自己的工作区运行 `python scripts/B/audit_d05.py --source experiments/B/B-D05-manual01/manual/export01 --output experiments/A/A-D06-accept-B05-manual-NEW.json --require-manual-flow`，预期exit0、complete_manual_flows=1、manual_pause_resume_flows=1；再读measurement_rules和接口请求，复核正式冻结边界。不调用付费模型。
