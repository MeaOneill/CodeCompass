# B会话事件规则草案

共享权威为A contracts 1.0.0的ExperimentEvent，原schema未修改。`session_event.schema.json`引用它并收紧成功/失败/暂停/恢复条件；`app.events.validate_event`实际校验相同字段语义。`event_examples.json`全部is_fixture=true，时间与命令是序列化样例，不是真实运行证据；成功样例使用另一run_id，避免失败后又成功的终态歧义。

event_id标识单事件，run_id标识运行；actor记录真实角色、Owner、机器、执行者与可核实模型（本轮精确型号未知为null）。timestamp带时区用于审计，不靠跨机器墙钟差计算耗时。elapsed_seconds为本进程monotonic测得的累计主动运行秒数，未计时为null；恢复时读取检查点的累计值再加新进程增量，不恢复旧monotonic起点。成功exit_code=0且error=null；失败保留非零退出码或显式错误；metrics未知为null，不把启动/加载成功写成学习成功。

paused/resumed必须有resume_from，它是仓库相对检查点引用；接收者先核对分支SHA、输入/配置hash与已有进程，再恢复，不能重复启动同一run。检查点拟包含last_event_id、累积主动秒数、暂停墙钟、待做动作、数据/配置hash和原始记录路径。恢复校验失败产生failed并停止；终态不覆写，以新run_id重试关联旧run。

当前没有完整会话状态机或持久化运行服务。跨事件顺序、event_id幂等、计时累加/暂停恢复的端到端验证留到采集实现日；本轮验证单事件格式和非法状态拒绝。暂停总时长、恢复父事件和不可变检查点hash需要字段扩展，已在B-D01接口请求登记，由A升版；本轮不偷偷增加additionalProperties。

真实命令记录在experiments/B对应registration和stdout/stderr；工作树未提交时code_commit=null，内容版本用input_manifest hash识别。正式数据/配置/代码hash齐全才进入正式实验；本轮不是正式实验。
