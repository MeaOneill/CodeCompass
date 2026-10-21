# A-D07 独立只读技术复核

HEAD：588920db9c9b5c041d9687724203da941aef7296。仅审核指定干净克隆；仅在 `tmp/independent-audit` 写技术输出。未读取真人背景、同意、原答、真人SQLite、private_evaluation、keys、环境秘密或其他worktree，未修改源码、协议或冻结文件。

**结论：软件候选的本次独立回归和冻结完整性检查通过；A-D07原卡整体验收不得通过。** 这是独立AI技术复核，不是人类批准或正式G2签字。

## P1：原卡反馈验收与冻结协议冲突

协议 `docs/protocol/B-D06-v0.2-candidate/protocol.md:23` 规定每轮未知画像、q=.1、阈值.7、alpha=gamma=0、一次共同诊断，背景初测不作先验。

- `src/codecompass/app/relay_v2.py:49` 每轮建立空ledger；`:178`、`:184` 限首次完成后一次短测；`:187`–`:192` 确实更新证据，before_route已是首单元出队后的路线。
- `src/codecompass/learner/model.py:100`–`:110` 只有后验下界跨.7才改变mastered门。一次pass为Beta(2,1)，下界 **.3162277660168379**；fail为Beta(1,2)，下界 **.051316701949486225**，均不能跨门。
- `src/codecompass/planner/adaptive.py:49`–`:53`、`:115` 表明alpha=0时证据均值不影响费用，规划初始覆盖只依赖mastered门与completed；gamma=0也无反馈排序项。
- `tests/A/test_runtime_d07.py:77`–`:80` 的失败后补回材料测试加入每概念六份**模拟**pass历史，只证明另一种输入条件的分支，不能证明未知起点预演满足要求。

独立枚举12任务×pass/fail=24场景，均ACCEPTED、FEASIBLE且completed保留；与“相同completed、相同短测spent、但不更新证据”的反事实路线也全部相同，**反馈路线变化0/24**。12任务unknown均强制选全部单元，且全部费用+短测≤100；task_003仅一个单元，完成后无剩余材料可变化。

因此当前冻结条件下不能靠修实现缺陷真实触发Ours的证据驱动路线变化。不能把完成项出队、任意重排、B1生成波动、预算失败或超时称为反馈效果。保留v0.2时必须登记“证据更新成功、剩余路线不变、原卡该项未通过”。

## 软件、公平性与版本

`runtime_d07.validate_method_result` 对Ours/B1/B2统一重放合法性、预算和完整目标覆盖；合法但不完整的B1空路线判ALGORITHM_INCOMPLETE，不增加语义修复。相关回归通过。新UI仅提供相同格式提示和错误镜像，没有改答案、规划或评分；B1夹具明确模拟，不冒充付费模型验证。未发现另一个阻止软件候选技术复核通过的严重实现缺陷，但不作无限范围无缺陷保证。

**P2，持久溯源限制：** `scripts/A/serve_d07_submission_v1.py:19`–`:21` 仅给HTTP响应加submission_ui_version，没有写入collector会话/事件/trace。因此该字段证明当前展示服务版本，不能单独证明会话开始及全部交互的版本，尤其共用数据库恢复旧会话时。需保留独立启动/会话版本记录；不能按当前响应重标历史。此为代码可定位限制，不表示实际已有误标。

## 最小合规解决路径

“另立开发协议版本，采集同人同项目的真实、非重复独立历史，再用原参数演示反馈修复”方向合理，但**改变未知起点和按轮画像规则，超出原卡只修实现缺陷范围，必须用户事前明确授权后才能实施/采集**，不能称原协议内修复。

新版本须保留v0.2及不变结果，登记受影响运行；预登记多单元、未完成且未被completed覆盖的概念场景。真实历史需审核同人/项目/concept来源、评分和题库内容独立性，item_id不同不等于独立；不允许重复题、阅读、自评或模拟历史充数。六次全pass才首次跨当前门槛，真实结果不能保证；须预登记题量上限、停止条件、失败/未跨门处理，不能诱导答错或挑选结果凑验收。

历史采集的全部时间、题量、费用须计入，明确与预算100、每题1的关系；三方法获得相同合法证据/帮助/计费，不能称额外测验“免费先验”或与旧unknown运行混算。新协议成功也仅支持新条件下机制演示，不能倒推原卡已通过；未过门或路线不变仍应失败。人类任务/协议审核与正式G2继续独立。

## 实际执行

设置 `PYTHONPATH=<clone>/src;<clone>`、`PYTHONDONTWRITEBYTECODE=1`；解释器为授权的 `C:/CodeCompass/CodeCompass-A-D05/.venv/Scripts/python.exe`。未重复原384全套。

1. `python.exe -m pytest tests/A/test_runtime_d07.py tests/A/test_runtime_d07_http.py tests/A/test_submission_ui_d07.py --basetemp tmp/independent-audit/pytest -p no:cacheprovider -q`：默认沙箱首次启动exit101，Unicode launcher尚未执行测试；相同命令授权提升后 **exit0，22 passed in 6.47s**（20core+旧HTTP1+新HTTP1）。原始输出 `pytest.log`。
2. PowerShell按两份manifest用 `Get-FileHash -Algorithm SHA256` 核对源/snapshot/受保护父文件：**exit0，49/49匹配**（runtime43+UI6）。输出 `hashes.json`。
3. `python.exe tmp/independent-audit/feedback_counterexamples.py`：授权提升后 **exit0，24/24反例断言通过，路线变化0**。脚本、原始JSON与log均同名存于本目录。明确全为模拟公开技术输入，无真人记录。
4. `node --check app/A_D07_submission_v1/submission.js`：**exit0**，结果 `javascript_syntax.json`。语法检查不是实际浏览器验收；本轮未运行浏览器验收。

所有证据均在克隆 `tmp/independent-audit/`，可复制到代码审计材料；git受跟踪文件状态干净。
