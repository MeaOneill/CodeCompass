# B-D01运行与依赖锁定

工作目录为Git仓库根。当前使用本机Python 3.12.10，依赖隔离在被忽略的`.venv`；精确版本草案在本目录。公共锁/打包元数据由A集成，本轮未另建规划对象、未修改共享schema。

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r scripts/B/requirements-d01.lock-draft.txt
$env:PYTHONPATH = 'src'
./.venv/Scripts/python.exe -m app --help
./.venv/Scripts/python.exe -m app check-sample
./.venv/Scripts/python.exe -m pytest tests/B -q
./.venv/Scripts/python.exe -m pip check
./.venv/Scripts/python.exe scripts/B/draw_d01.py
# Choose a new run-id every time; evidence directories are never overwritten.
./.venv/Scripts/python.exe scripts/B/run_d01_checks.py --run-id B-D01-your-new-run-id
```

锁定流程：只在隔离环境安装→pip check→真实smoke/pytest→pip freeze保存B草案→pip download到忽略的tmp wheel目录→保存wheel SHA256→在第二个隔离环境用`--no-index --find-links`重装并检查。普通freeze不等于跨平台/供应链hash锁；本轮wheel清单只对应Windows CPython 3.12，不承诺Linux可直接用。A确认后整合公共锁；新增依赖先提交请求，不改全局包。不把本机全局已有networkx当项目依赖。

运行入口CLI不导入或执行上游代码；A只读校验入口额外执行已固定的上游行为smoke，其范围另列。testpaths目前仅tests/B，A添加测试入口时由A集成，现有A脚本不受此配置替代。
