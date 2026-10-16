# task_001教学建议依据

本轮没有人类先修金标准，human_review_record=null，现有两边继续soft/pending。B-D01 Agent工程反馈只是阅读合理性建议，不是人类确认；不得把审核状态改approved。

| 候选边 | 固定源码依据 | 推断及边界 | 人类必要性审核 |
|---|---|---|---|
| u_iterable → u_chunked_iter | iterutils.py L61–76说明可迭代检查；L330调用检查，L349–357迭代取块 | 先理解迭代协议有助解释生成器消费；这是教学判断，并非函数调用自动导出先修 | 未审核 |
| u_chunked_iter → u_chunked | iterutils.py L316–358生成器；L302调用、L303–306列表/islice包装 | 先读生成器有助解释包装器count和消费；有基础者可能直接理解，不能一律hard | 未审核 |

源码均为boltons commit 4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d；span/hash在task_001_units和本轮节点中。代码事实与建议分别存edges.json、teaching_edges.json。未来人类需记录是否必要、反例、审核者与时间，才能申请硬化；自称human-review字符串不能代替实际审核。

受控夹具的教学边是显式合成，不能援引为真实仓库教学事实。检测到的cycle_X/cycle_Y仅为环处理演示，未自动删边/聚类，无真人已掌握状态。
