# A-D02源码图格式与使用边界

共享七对象契约保持1.0.0；本轮新增内部图导出graph_format_version=0.1.0，不替换LearningUnit，不改B对象或D01冻结原件。

## 调用入口

```python
from codecompass.graph import extract_snapshot, read_snapshot, validate_span, hard_edges
# snapshot是固定commit、原始blob和SHA清单；root是其局部源码目录。
graph = extract_snapshot(root, snapshot)
```

解析只枚举snapshot.files中.py；先核验全部清单原始文件的bytes/SHA256/Git blob与清单hash。路径必须安全相对路径且resolve后仍在root；不执行import、eval、构建/安装脚本或被分析仓库代码。当前只支持UTF8，无法解码/语法失败记入source_manifest.status=parse_error，不伪造空的成功图。空文件标empty，无虚构1起行号。

nodes包含module/function/async_function/class/import_reference；定义ID包含相对路径、语法限定名与起始行，保留装饰器起行与闭区间source_span。imports的module/symbol/alias/level保留原声明，内部/外部符号不推断实际运行装载结果。contains表示语法包含，不是运行先后。节点scope表示语法归属；装饰器/默认参数等的真实执行作用域不在本轮模型内。

edges.kind为contains、imports、call_unknown。前两种分别是语法包含/导入声明事实；call_unknown保留表达式、行号、列、reason，to=null、resolution=unknown。即便名字与本文件函数相同，也可能被重绑定，不据此解析目标。全保守策略牺牲调用解析覆盖率；不能称完整调用图或把unknown当失败删除。语法声明可能位于条件/未执行分支，不代表已经运行。

source_manifest逐文件记录commit/hash/parse状态。每节点/边的source_span都按D01规则核验，相关代码在provenance.py；extract.py负责AST。source_span不含列级内容hash，多个同一行语句可共享span，调用column辅助区分。

## 教学关系与审核门禁

真实学习单元继续使用benchmarks/dev/task_001_units.json；导出teaching_edges.json单独保存，当前两条均soft/pending。代码导入/调用绝不自动变成教学先修。hard_edges只接受teaching_prerequisite + teaching_judgment + approved + reviewer非空 + human-review:证据引用；缺失、模型候选、悬空引用、硬环均拒绝。该引用是审核记录声明，不是身份认证；只有真实人类确认才可填写，Agent不得自签。此更严格条件是图模块门禁，不静默修改共享schema。

环用SCC报告，不任意删边。真正需要共同学习时由人工记录折叠理由，当前没有自动聚类。现有真实教学边不含硬边，不能以空硬图声称教学必要性已验证。

controlled_fixture.json专用于结构压力测试：task_001下共享前置、替代材料覆盖、模拟已掌握概念和双节点环；全部is_fixture=true、成本是造设代理量，不是实测分钟或真人能力。禁止混入独立评价金标准。

## B反馈处理

接受B的第七CodeTask及soft边建议。兼容继续使用1.0.0；事件失败/暂停语义先沿用app/events.py（B已有反例测试），本轮不改历史schema/事件或计时字段。elapsed_seconds在A开发登记指单命令perf_counter墙钟区间，本轮没有暂停；将来真人主动/暂停时间必须分开，由B先提出字段迁移再由A升版。公共环境复用已通过的scripts/B hash锁，不重复创建pyproject或安装模型栈。
