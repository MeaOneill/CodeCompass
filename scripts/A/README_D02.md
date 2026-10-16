# A-D02运行与复现

环境：Python3.12，PYTHONPATH=src。本机按B的scripts/B/requirements-d01-win-py312.hashes.txt实际hash安装；图形只用同一锁中Pillow，没有新增模型/图数据库依赖。源码图本身只需标准库。Windows图形入口使用系统Arial字体；其他系统需配置同等可用字体后记录配置变更，不能冒称跨平台图像hash一致。

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install --require-hashes -r scripts/B/requirements-d01-win-py312.hashes.txt
$env:PYTHONPATH = 'src'
New-Item -ItemType Directory -Force tmp | Out-Null
./.venv/Scripts/python.exe -m app check-sample
./.venv/Scripts/python.exe -m pytest tests/A tests/B -q --basetemp=tmp/pytest-B-D02-review
./.venv/Scripts/python.exe scripts/A/check_d02.py --run-id A-D02-20261016-graph02
# 新运行使用新ID；不要覆盖A原始结果
./.venv/Scripts/python.exe scripts/A/run_d02.py --run-id B-D02-graph-replay
```

默认git需在PATH；也可CODECOMPASS_GIT指定实际可执行文件。draw_d02.py --run-id 新ID从同一图源生成PNG/SVG，但默认输出report_materials/A/A-D02；B复核先不覆盖A图，若需重绘在独立clone/工作树执行并保存B副本，再由A更新图表版本。

收尾check_d02验证固定源、所有947个span、节点引用、unknown调用、待审核软边、合成共享/替代/掌握/环及3对PNG/SVG。它不验证规划效果或独立答题成绩。输入已验证文件不得按本机浮动上游HEAD替换。
