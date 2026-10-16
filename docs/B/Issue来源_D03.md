# B-D03 Issue来源与匹配边界

只读API：`https://api.github.com/repos/mahmoud/boltons/issues?state=all&per_page=50&sort=updated&direction=desc`；HTTP200。获取UTC `2026-10-16T14:59:14.062900+00:00`（北京时间22:59:14）。只请求一页，过滤PR后7条；不是全量仓库目录。原状态/题文/时间和URL在 `experiments/B/B-D03-issues01/snapshot.json`，公开作者与联系字段未保留。响应原字节hash在快照；Git只保存去作者后的样例，不能用去作者JSON去验证原HTTP字节hash。

| Issue | 捕获状态 | 模块依据 / 处理 |
|---|---|---|
| [#581](https://github.com/mahmoud/boltons/issues/581) | open | 题文ioutils.SpooledStringIO；当前路线未覆盖，未匹配 |
| [#579](https://github.com/mahmoud/boltons/issues/579) | open | 安全报告渠道请求；不涉及当前学习单元，未匹配，不代发漏洞 |
| [#566](https://github.com/mahmoud/boltons/issues/566) | open | 题文timeutils.dt_to_timestamp；当前路线未覆盖，未匹配 |
| [#565](https://github.com/mahmoud/boltons/issues/565) | open | 题文strutils.MultiReplace；当前路线未覆盖，未匹配 |
| [#311](https://github.com/mahmoud/boltons/issues/311) | open | ranges交并集功能需求，原文无当前模块词；不猜实现模块，未匹配 |
| [#553](https://github.com/mahmoud/boltons/issues/553) | open | 题文iterutils.redundant，模块词命中；固定源码函数始于iterutils.py:870，不在当前3个学习单元 |
| [#551](https://github.com/mahmoud/boltons/issues/551) | open | 题文iterutils.untyped_sorted，模块词命中；固定源码函数始于iterutils.py:1598，不在当前3个学习单元 |

最后两条只是贡献准备候选，未核实版本复现、上游意愿或重叠PR，**没有已确认适合当前学习者的Issue**。匹配输出的概念缺口来自模拟ledger，仅为当前模块学习缺口；不等于这两个Issue的独立先修金标准。没有独立相关性标签，因此不计算推荐准确率/Recall/NDCG。

历史关闭项在真实快照中为0；自动化测试用明确fixture验证关闭项只进historical且标HISTORICAL_CLOSED_NOT_ACTIONABLE，不冒充抓取到真实关闭Issue。运行prepare总是固定快照重放，必须标原获取时间。今后贡献之前由成员重新打开链接核验状态；本轮未做任何社区提交。

CLI准备样例：`python scripts/B/issues_d03.py prepare --snapshot experiments/B/B-D03-issues01/snapshot.json --output tmp/issue-preview-new.json`。输出候选URL、状态、模块、模拟缺口和4步准备清单；不执行Issue题文代码，不把模型回答当源码定位或贡献成功。
