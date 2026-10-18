# B-D05 对 A-D06 的接口复核请求

基于A-D05 7a2a268cd3122abe9165a78b45b45cddf0a18515，调用start_session/apply_feedback/complete_next与独立verify_session；未修改A模块/共享schema。

开发UI同一短测、单次费用1、最多1次，至少读完一份材料后执行scheduled学习后评估。初始未知画像，alpha/gamma=0、共同预算100。真实p_pass缺失，生产VOI禁用；不能把scheduled当成自选诊断贡献。

B2在已完成覆盖之外规划剩余目标；B0/B1_saved静态保留。B1_saved为D04实际响应回放，没有动态反馈重规划，不做正式同条件效果主张。最终评分保留null且不传递终测答案，UI只保存独立任务提交说明/hash。

请在D06冻结前明确动态B1策略/费用授权、所有方法诊断时机、跨轮能力复用与最终独立评分入口。当前采集支持这些缺失状态，不用默认成功/0秒填补。A接收从B-D05最终验收门禁开始；真人手动操作尚待完成时不要放行正式冻结。
