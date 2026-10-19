# A-D07稳定规划接口与B-D07接收约定

Owner成员A。新增文件均在A命名空间，原B collector、页面、评分器、协议及封存字节不覆盖。版本A-D07-runtime-v1；候选manifest在configs/frozen/A-D07-runtime-v1/manifest.json。生产阈值/搜索/成本未调；正式G2未通过。

纯规划：`codecompass.planner.runtime_d07.safe_remaining(root, request, units, full_ledger, config, completed=..., reference=..., spent=...)`。必须传完整独立证据ledger和与其一致的request聚合，不接受“阅读次数当掌握”。返回status/feasible/goal_complete及可核对route_explanations；源码span与快照仍由原校验器检查。NO_FEASIBLE_FOUND/TIMEOUT非无解证明，human_task_success始终未测。

接入已有三方法：`scripts.A.relay_d07.StableRelayCollector`继承B的RelayCollector，保留B1初始/反馈/一次格式修复/计时/账本语义。统一完整目标校验，不对B1失败多给一次语义修复。客户端入口 `scripts/A/serve_d07.py`复用原B HTTP访问边界，新增中文路线依据，提交阶段不显示学习依据。

**必须选新入口或把等价guard接到B的新版本，不能以旧serve_relay_v2入口代表修复已启用。** 不自动迁移B旧数据库；新预演单独A-D07/B-D07数据库，保留历史数据和来源。A演示入口默认B1未配置、不会调用服务；B1需由B在既有5元累计授权和真实剩余额度内通过原受控配置接入，不能把本轮fixture transport当真实模型。

新代码与旧B06方案的差异包括完整目标判定、错误状态、事件runtime_version和均等路线依据展示。正式选择此版本须在收结果前登记，旧B06输出不换名重写。旧的合法完整路线不因本次修复被宣布无效；旧的合法未覆盖结果应标受影响并停止继续采集。

B-D07第一动作：核对A最终分支/SHA后执行 `python scripts/A/audit_d07_version.py --output experiments/B/B-D07-accept-A07-version-NEW.json` 和 `python scripts/A/audit_d07.py --run-id A-D07-development05 --output experiments/B/B-D07-accept-A07-smoke-NEW.json`，再复核tests/A/test_runtime_d07.py中的空B1反例、同规则、版本、前缀及无跨项目自动转移。最后按新入口接入、审阅新A代码并组织两名非正式样本的真实预演，保留通过/失败/路线不变的全部记录。

只能允许B-D07整合/审核/组织预演，不能由技术检查越过招募同意、任务/协议批准、真实比较分支确认与main/标签门禁。缺私有key时A只验hash，不宣布私有终测评分复现。
