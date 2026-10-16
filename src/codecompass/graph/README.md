# 源码图与来源校验

A-D02实现provenance.py、extract.py、pedagogy.py，可直接从codecompass.graph导入。格式/边界见docs/graph_format.md；所有输入来自固定快照，不运行被分析代码。调用目标统一unknown；教学关系单独存储并经人工门禁才可hard。

运行：python scripts/A/run_d02.py --run-id A-D02-your-new-id；重建图形：python scripts/A/draw_d02.py --run-id 该实际ID。先设置PYTHONPATH=src，测试入口tests/A/test_graph_d02.py。完整导入/安装基于B已有hash锁，根项目尚无pyproject。
