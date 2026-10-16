# A-D01验证入口

使用Python3.12（本次实测3.12.14）。工具校验依赖独立锁定于requirements-d01-validation.txt，不冒充B将建立的项目依赖锁。无须安装boltons或执行其构建脚本。

```powershell
python -m pip install --target tmp/d01_validation -r scripts/A/requirements-d01-validation.txt
python scripts/A/validate_d01.py --output experiments/A/A-D01-B-review/validation.json
```

首次输出目录用新run_id；已有文件拒绝覆盖。记录实际Python路径、命令退出码。可使用已配好jsonschema的环境；脚本优先寻找项目临时依赖。脚本以标准库显式注册date-time检查，避免jsonschema可选格式依赖未安装而静默跳过日期校验。

来源采集入口prepare_sources.py需三份PINS中的固定checkout，读Git blob而非Windows检出字节，保留LF原样。CODECOMPASS_GIT默认git，可指定路径。它刷新来源采集时间，不自动改任务或样例；重采后由A确认快照与样例一致再提交。文件写入仅限对应来源目录；本轮不需要B重采。

验证脚本不是规划器，也不是独立答题评分器；原版count不支持的预期失败只说明任务目标未实现。
