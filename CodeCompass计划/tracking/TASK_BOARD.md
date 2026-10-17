# 任务板

状态从TODO开始；领取时填写Owner/机器/分支/base commit/心跳，不能两人同时认领。

| ID | 日期 | 角色 | Owner | 状态 | 分支/base | 最后检查点 |
|---|---|---|---|---|---|---|
| D01-A | 2026-10-15（10/16补做） | A | 成员A / Codex Agent A / LAPTOP-LUQPS3EV | READY_FOR_REVIEW | codex/A-D01-contracts / fd7b3e6 | 认领 2026-10-16T13:42:31.873649+08:00；docs/A/session.json |
| D01-B | 2026-10-15 | B | 成员B / 糯糯 / Codex Agent B | READY_FOR_REVIEW | task/B-D01-foundation / 54613cf136d788bde7c46454d3d7b9e29f295a9b | 2026-10-16：check02及local-replay02通过；最终同步见docs/B回执 |
| D02-A | 2026-10-16 | A | 成员A / Codex Agent A / LAPTOP-LUQPS3EV | READY_FOR_REVIEW | codex/A-D02-graph / 9d911895 | 2026-10-16T16:47:19.722142+08:00；31测试与图源自审通过，未独立审核 |
| D02-B | 2026-10-16 | B | 成员B / 糯糯 / Codex Agent B | READY_FOR_REVIEW | task/B-D02-evaluation / 30069ce468a52b68a0d3bfb62bb49b1cce0f2104 | 60测试/14夹具/57负例及逐题AI复核通过；允许A-D03开发，正式实验另验 |
| D03-A | 2026-10-17（10/16执行） | A | 成员A / Codex Agent A / LAPTOP-LUQPS3EV | READY_FOR_REVIEW | codex/A-D03-planner / fc648532 | 103测试复测/41负例；已放行B-D03，偶发超时已披露；未人类审 |
| D03-B | 2026-10-17 | B | 待认领 | TODO | 未建立 | 未执行 |
| D04-A | 2026-10-18（10/16执行） | A | 成员A / Codex Agent A / LAPTOP-LUQPS3EV | READY_FOR_REVIEW | codex/A-D04-search / 5b3db984 | 142测试/206篡改；归档重算通过，放行B-D04 |
| D04-B | 2026-10-18 | B | 待认领 | TODO | 未建立 | 未执行 |
| D05-A | 2026-10-19 | A | 待认领 | TODO | 未建立 | 未执行 |
| D05-B | 2026-10-19 | B | 待认领 | TODO | 未建立 | 未执行 |
| D06-A | 2026-10-20 | A | 待认领 | TODO | 未建立 | 未执行 |
| D06-B | 2026-10-20 | B | 待认领 | TODO | 未建立 | 未执行 |
| D07-A | 2026-10-21 | A | 待认领 | TODO | 未建立 | 未执行 |
| D07-B | 2026-10-21 | B | 待认领 | TODO | 未建立 | 未执行 |
| D08-A | 2026-10-22 | A | 待认领 | TODO | 未建立 | 未执行 |
| D08-B | 2026-10-22 | B | 待认领 | TODO | 未建立 | 未执行 |
| D09-A | 2026-10-23 | A | 待认领 | TODO | 未建立 | 未执行 |
| D09-B | 2026-10-23 | B | 待认领 | TODO | 未建立 | 未执行 |
| D10-A | 2026-10-24 | A | 待认领 | TODO | 未建立 | 未执行 |
| D10-B | 2026-10-24 | B | 待认领 | TODO | 未建立 | 未执行 |
| D11-A | 2026-10-25 | A | 待认领 | TODO | 未建立 | 未执行 |
| D11-B | 2026-10-25 | B | 待认领 | TODO | 未建立 | 未执行 |
| D12-A | 2026-10-26 | A | 待认领 | TODO | 未建立 | 未执行 |
| D12-B | 2026-10-26 | B | 待认领 | TODO | 未建立 | 未执行 |
| D13-A | 2026-10-27 | A | 待认领 | TODO | 未建立 | 未执行 |
| D13-B | 2026-10-27 | B | 待认领 | TODO | 未建立 | 未执行 |
| D14-A | 2026-10-28 | A | 待认领 | TODO | 未建立 | 未执行 |
| D14-B | 2026-10-28 | B | 待认领 | TODO | 未建立 | 未执行 |
| D15-A | 2026-10-29 | A | 待认领 | TODO | 未建立 | 未执行 |
| D15-B | 2026-10-29 | B | 待认领 | TODO | 未建立 | 未执行 |
| D16-值班 | 2026-10-30 | 值班 | 待认领 | TODO | 未建立 | 未执行 |

A-D01心跳 2026-10-16T13:53:01.661866+08:00，真实机器LAPTOP-LUQPS3EV；自检通过/未独立审核；B-D01待接管。

B署名 B-D03 2026-10-16T15:08:49.943358+00:00：Owner成员B/糯糯；机器糯糯；Executor Codex Agent B；分支codex/B-D03-integration；base cf02b664aea81f91aa8e7423a8aa891367c73b7e。READY_FOR_REVIEW，108回归测试/10命令期待通过；最终恢复及同步待收尾。新ledger持久化/重启/Issue准备/G1见docs/B/handoffs/B-D03.md；不变更A Owner或旧main，不将模拟回答当真人。

B署名B-D03收尾 2026-10-16T15:28:28.510192+00:00：READY_FOR_REVIEW，G1工程通过，允许进入A-D04。检查点8ed3226ec2f585eb9cfa3d584a1eaacfd900c008=remote；同机新clone108测试/10命令通过。精确最终回执SHA见通知，A异机接收/人类审核未确认，未合main。下一棒先核对B-D03交接命令后推进搜索，不从旧main开始。

B署名B-D04 2026-10-17T11:29:50.112581+08:00：Owner成员B/糯糯，机器糯糯，Codex Agent B；分支codex/B-D04-baselines，base A-D04 722b9c46676d05b7492f7250b58a9d61c60d5124。READY_FOR_REVIEW，160测试/统一比较已过；最终恢复同步待收尾。B1真实未配置，强LLM对照欠缺，按任务卡先跑本地方法及独立指标；不将夹具当模型结果。交接docs/B/handoffs/B-D04.md，不变更A Owner。
