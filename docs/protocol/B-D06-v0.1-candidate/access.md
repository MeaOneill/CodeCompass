# 数据与访问边界

- 公开：候选任务说明、rubric结构、source版本、代码、哈希、匿名空模板、保留SLOT。无任何正式答案值或真实联系信息。
- B私有评估：private_evaluation/B-D06/v0.1-candidate/keys.json及评分目录。实际存在并与D02封存hash一致；文件只按字节复制，没有向规划/模型读取答案。目录被Git忽略。指定B评估负责人通过显式--private-key运行，不作应用自动发现。
- 同机个人数据：tmp SQLite、DPAPI凭据、原始提交、真实审核身份、同意/撤回码。默认不上传。仅创建ignored目录不是OS级权限隔离，本轮未宣称设置了独立系统账号或ACL。
- A/另机：仅获key的SHA256和任务id清单，尚无受限同步渠道；不能用普通Git/聊天发送key。B可留本机评分，或人类选受限传输后逐hash复核。当前另机终测不能重放，是G2实际缺项。
- app/frontend/prompt不import scripts/B/evaluation；serve_d06仅开发两题。终测评分器独立命令score_d06.py只导出答案hash/结果状态，不输出评分人身份。开发私有测试的历史验证不当正式终测运行。
- 初测/诊断项目使用独立item_id；D05诊断属于dev01/dev02的Python概念，正式候选005—012列出概念与它们不重叠。概念不重叠并不能自动证明等难或无迁移；正式映射仍需人类批准。
