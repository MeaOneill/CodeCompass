# A-D04复跑与B集成

Windows Python3.12，沿用B hash依赖锁，不新增包、不运行第三方仓库安装脚本。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r scripts/B/requirements-d01-win-py312.hashes.txt
$py = '.\.venv\Scripts\python.exe'
$env:PYTHONPATH = 'src'
New-Item -ItemType Directory -Force tmp | Out-Null
& $py -m pytest -q
& $py scripts/A/demo_d04.py
& $py scripts/A/audit_d04.py --run-id A-D04-mechanism01 --output experiments/A/B-D04-accept-A04.json
# 新运行ID，不覆盖A原始证据
& $py scripts/A/run_d04.py --run-id B-D04-mechanism-replay01
& $py scripts/A/draw_d04.py --run-id B-D04-mechanism-replay01
```

git不在PATH时CODECOMPASS_GIT指定本机实际git路径；图使用Windows微软雅黑/Pillow/nativeSVG，字体hash进配置。跨机文字渲染不能假定像素hash一致。

新增API `from codecompass.planner.search_service import solve_request`，签名见docs/A/algorithm.md。方法B2/beam/exact共用request/units/state/config；beam options为beam_width16/candidate_limit50/max_expansions100000/time_limit_seconds30。精确<=12，不允许伪装大图无解证明。certify_small默认False。

result仍为现有七对象PlanResult，details为内部搜索/证明诊断，不改旧schema、D03 plan_request、原B2 core或learner门控。保存INFEASIBLE_PROVEN时调用者必须将details.certificate写入相邻certificate.json，随后独立verify_result复核；本轮runner已这样保存。TIMEOUT有incumbent也不转成最优或成功状态。

B原应用/存储路径尚未切换beam。本轮只交比较接口，B-D04后续按自己任务卡接线；严禁把学习后成功分数取自planner coverage。所有画像是模拟，正式UI/真人效果/诊断未完成。原始数据与失败均保留，详见成果导览。
