# 独立评分与分歧登记

沿用B-D02独立评分器与rubric，不用A图谱/路径目标作为答案金标准。每题原成功条件、时间上限在task_specifications.json；完整rubric由task_catalog hash绑定。

响应型题独立outputs exact与source_spans exact合计8分，解释全对2分否则0，总分>=9；两位真实盲评者必须都评解释，通过条件等价于10/10。两人分歧时PENDING，保留原值，由预先登记的第三裁决者另写新回执；不能平均或删难题。补丁dev01/02仍用各自R1—R6关键组与>=9/10规则，不套响应题8+2结构。

新scripts/B/score_d06.py提供独立响应评分CLI，仅评估侧接显式key，不通过app运行；自动检查失败保留，缺人类评分保持PENDING。当前任务人工reviewer均null，分歧状态NOT_REVIEWED，空分歧表不表示达成一致。

盲评文件应移除方法、轮次与身份信息，只含task_id、submission_hash和输出/解释/源码。组织者本地持有trial/pair/方法映射，合并结果时核对提交hash、评分器版本与时间完整性；不能凭点击提交自动赋success=true。可见源码本来含上游例子，不能假称上游知识保密，私有独立key仍不进入提示词。

review_template.csv供题目/源码与rubric预审；score_sheet_template.csv供实际提交评分。空模板没有任何假分数、真人名字或伪造同意。正式评分收集必须等联合G2与批准的任务集。
