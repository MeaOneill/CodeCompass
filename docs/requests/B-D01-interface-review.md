# B-D01契约与依赖反馈

依赖提交54613cf136d788bde7c46454d3d7b9e29f295a9b，contracts 1.0.0。B接受补充CodeTask作为第七对象的工程决定；未修改A契约/样例/任务/教学边。Schema与只读加载结果见本轮运行登记，不将AI自检称人类审核。

请求A-D02集成：

- 事件计时：elapsed_seconds明确是主动运行秒数还是含暂停墙钟；后续需独立active_seconds/paused_seconds、parent_event_id及checkpoint_hash/格式版本。B当前使用既有elapsed_seconds和resume_from，单事件规则草案位于docs/B；不擅自加共享字段。
- 失败语义：将succeeded=exit0无error、failed=非零或error、paused/resumed=有checkpoint写入共享schema的条件规则，B已有实际反例测试。跨事件状态机后续由B实现。
- 样例与真数据：保持fixture标识；PlanResult夹具不得进入运行成功表。学习单元base_cost=null应在A规划入口报缺失输入；不按零成本处理。
- task_001概念与教学边：源码定位和静态调用可校验；`u_iterable→u_chunked_iter→u_chunked`是合理阅读建议，B建议继续soft。阅读顺序不等于硬教学必要性，未有人类确认，B不替人签approved。25分钟、分组全有或全无评分及R5解释评分一致性仍需预演；本轮不实现D02评分器。
- B在scripts/B提供隔离环境锁定草案，公共依赖锁由A集成。D01运行只需jsonschema；pytest用于验证，Pillow用于结构图，不要求安装Streamlit/NetworkX/模型客户端。请A确认公共打包元数据（尚无pyproject）；B用PYTHONPATH=src与python -m app，不改A模块。

独立性：这是B Agent对A文件的运行复核与工程反馈，无独立人类审核，也不等于任务/算法效果评审。A-D02首动作：核对B分支最终SHA、运行只读smoke，再处理本请求并登记契约是否升版。

B范围Git字节规则：为避免Windows autocrlf改变B原始日志和图源hash，本轮在.gitattributes仅追加B目录规则：源码/图源固定LF，experiments/B原始字节不转换且允许原始日志行尾空格。保留A已有规则，不改A文件属性；diff检查中的原始pytest traceback空白不通过删改证据来消除。
