# B-D04 DeepSeek B1补跑准备

用户确认服务为DeepSeek官方 https://api.deepseek.com，允许5—10元；本轮取较低的**5元人民币累计上限**。模型展示名DeepSeek-V4.1-Flash，对应API标识deepseek-flash。采用官方Responses协议，不更改A算法、原公共prompt/候选池/成本和唯一格式修复次数。关闭thinking，输出上限1200 tokens，最多一次格式修复，逐调用原始输出/usage/时间/hash保留。

依据（2026-10-17核对）：[官方模型与人民币价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)、[Responses接口](https://api-docs.deepseek.com/api/create-response/)。预算估算保守使用高峰缓存未命中输入2元/百万tokens、输出8元/百万tokens，不假定缓存折扣；实际账单字段未知，不能把估算当账单。费率可能变化，正式补跑时再次核查。未启用搜索/工具或额外自动重试。

配置configs/B/D04_deepseek_authorized.json不包含密钥。每次调用预留0.25元（含格式修复），输入上限80000 UTF8字节。SQLite预算账本在忽略的tmp/B-D04-deepseek-budget.sqlite3，BEGIN IMMEDIATE事务累计预留，跨进程/重复运行不自动重置，最多20次预留合计5元。常规6组每组最多2调用，单批最多预留3元。未知费用/失败不会退回预留。该调度上限依赖已核对费率与token限制；服务商账单未验证，不能声称账单硬限制或已花费5元。

用户此前将密钥发进聊天；本工程未将其写入代码/配置/日志或拿它测试。建议撤销并生成替换密钥。用户只需在自己的PowerShell执行一次：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\CodeCompass\CodeCompass\scripts\B\set_deepseek_key.ps1
```

提示后粘贴新密钥并回车（隐藏输入），看到KEY_SAVED_ENCRYPTED即可返回聊天说已保存。此脚本不调用API、不收费。密钥通过Windows DPAPI加密，只存tmp/deepseek-key.dpapi，属于本Windows用户本机数据，受Git忽略；不复制到其它机器或交接目录。不要再发密钥到聊天。

Agent确认文件存在后执行：`powershell -NoProfile -ExecutionPolicy Bypass -File scripts/B/run_deepseek_d04.ps1 -RunId B-D04-deepseek-live-NEW`。启动器在进程内解密到环境变量并清理，不把密钥放命令参数或公开输出。这个步骤调用真实API，会使用已授权额度；当前等待本机替换凭据，尚未执行，不把本地测试当真实B1结果。

离线验证：新增CNY计费/持久预算并发与恢复/输入限额/端点限定/HTTP请求夹具6项，完整套件166项通过。HTTP请求测试为明确fixture，未联网。实际公开上下文均在80000字节之内。PowerShell两个入口语法解析通过；Git忽略检查通过。

当前源版本的公开离线比较为B-D04-deepseek-offline01，图与审计同名，仍是B1未配置/未运行。B04原comparison03的冻结代码对应旧47f9301；新版适配器改变源hash，不能在新版工作树冒称旧版本源码hash仍相同。A接收新版先审计新离线run；需重验原发布材料则在47f9301的独立副本运行，保留历史证据不改写。

已完成更新 2026-10-17T12:19:13.226538+08:00：用户已通过本机DPAPI入口保存替换密钥；启动器.Trim修复换行后run B-D04-deepseek-live01真实6调用全部成功，模型返回deepseek-flash。167测试及4项记录篡改挑战过；估算0.061746元、账单未知，预留1.5元（累计5元授权内）。无需用户继续操作，不重复运行付费脚本作验收；后续只对保存数据离线审计。
