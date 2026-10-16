# B-D01接力操作与恢复

本轮基线为A已交付但未合main的`54613cf136d788bde7c46454d3d7b9e29f295a9b`，明确登记依赖，不假设main包含A代码。B在`task/B-D01-foundation`单独写入，不覆盖A或setup分支。既有B提交署名糯糯由本仓库配置沿用；未更改全局身份或凭据。Owner来自本轮用户授权为成员B；无法代签队长的原子锁确认。

交出：先运行scripts/B/run_d01_checks.py的新run_id，更新B状态/日志/贡献/交接/图表索引，检查git diff --check和显式暂存清单，commit任务分支，push，git ls-remote origin refs/heads/task/B-D01-foundation核对等于HEAD。不得强推、自动合main或把push当算法通过。

接收A-D02：

```powershell
git status -sb
# 未提交内容先按Owner保存，工作区干净后继续
git fetch origin
git switch --track origin/task/B-D01-foundation
# 若已有本地分支，switch后用pull --ff-only，不创建重复分支
git rev-parse HEAD
# 与B最终通知SHA逐字核对，读docs/B/handoffs/B-D01.md
$env:PYTHONPATH = 'src'
./.venv/Scripts/python.exe -m app check-sample
./.venv/Scripts/python.exe -m pytest tests/B -q
```

A接管后应在自己的A-D02分支继续，基于B已核对提交或经负责人复核集成的main；不能在B分支同时写。首次建环境参考scripts/B/README.md；不要复制B整份目录覆盖现有克隆。

本地演练入口scripts/B/replay_handoff.py：从实际Git检查点本地clone到忽略目录，核对SHA，在独立venv中用本地wheel --no-index安装，运行help、源码校验和pytest。原始证据保存在experiments/B/B-D01-20261016-local-replay。它验证同机接收/断网依赖安装，不能冒称异机验收或A已接管。

复跑必须传新的`--run-id`，例如B-D01-20261016-local-replay02，输出、接收克隆与隔离环境均使用新路径。首轮新克隆pytest缺tmp父目录错误已保留；修复后复验以02登记为准。脚本不删除既有输出，不启动远程或修改main。

正式双机缺项：A对本轮最终SHA fetch与确认、A-D02接管登记、人类独立审核和指定集成人合main；A机CPU/内存/显卡未提供。20261016_member_B_sync_review历史记录已证明旧setup分支反向写入，本轮不重复接受邀请或clone覆盖现有仓库。当前受限shell连接代理失败，已授权的外层网络执行fetch成功；不修改代理/TLS配置。
