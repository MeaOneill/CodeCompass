# B-D01开发运行登记索引

本轮证据均development_validation，正式实验0。没有真人/模型效果数据，metrics/cost/未知模型与seed为null。

- B-D01-20261016-check01：首次CLI/导入/真实样例/A验证/pip检查通过；pytest=1，16通过，tmp_path权限错误保留原始stdout/stderr。
- B-D01-20261016-check02：临时目录改在项目忽略tmp后，六命令全部exit0，pytest18通过。每条实际命令、UTC起止/耗时/退出码、Python/机器及输入内容hash见registration和input_manifest。实际本地日期为北京时间10月16日。实现当时未提交code_commit=null，dependency_commit仅指A基线，不能当作B实现版本。
- B-D01-20261016-environment：CIM、pip、远程读取等原始输出与独立退出码；13个wheel SHA256清单。成功网络探针在授权外层运行，不掩盖受限shell失败。
- B-D01-20261016-local-replay：实际Git检查点全新本地clone、SHA比对、新venv、--no-index/--require-hashes安装及运行；是否通过以registration exit_code为准，同机演练不计异机实验。
- B-D01-20261016-closeout：收尾生成原始结果hash清单和真实成功/失败事件；无真实暂停/恢复运行，不将格式夹具写入真实记录。

启动观察（早于捕获脚本，来自本轮工具实际输出，不补造逐命令退出码）：普通git fetch/ls-remote提示127.0.0.1:7890无法连接，直连覆盖测试提示getaddrinfo thread failed；初次venv ensurepip返回1、无pip；受限CIM无法访问资源。随后授权外层fetch/安装/CIM成功。日志不含令牌；未更改全局代理/身份/依赖。原始失败pytest traceback包含用户本机路径，仅供团队开发记录，不直接作为匿名评审截图。

配置追溯：check01/02使用工作树pytest.ini，第一次默认临时目录，第二次实际命令显式传--basetemp。原input_manifest未单列根pytest.ini，其配置差异由保留命令/失败日志及开发日志追溯；恢复演练以完整实际Git检查点（含pytest.ini与hash锁）为权威。未来捕获应将根配置也纳入输入清单，此限制不隐去。

收尾实际复验：B-D01-20261016-local-replay02=exit0（检查点c0e673b，8命令、18测试）。首次local-replay=exit1保留；closeout派生4条真实事件经校验，raw_manifest保留原始结果hash，不将B环境或接收演练称正式实验。

## B-D02运行登记

preflight：指定A前置31测试/样例/947span通过。response-keycheck01：10份行为key对固定原函数核对通过，不作学习评分。evaluation01/02/03：候选22span、14开发夹具，累计测试分别53/54/57通过，全部development_validation。B0-shared01/02：缺成本INPUT_INCOMPLETE/exit2；B0-lines01/02：显式行数成本提案ROUTE_PREFIX/exit0，formal_comparison_eligible=false。01为探索输出，02另存输入/配置；不覆写旧记录。

verification捕获CLI/pip/A图/两种B0/首版严格审计，预期exit2的缺依赖和整体验收未过不当成功实验。audit01/02/03技术检查通过，whole_task_gate_passed=false且next_day_allowed=false；57不是任务或人数。public-demo01可由用户复跑，无需私有key。评分器成功夹具仍PENDING_HUMAN_REVIEW，真实人类评分/预演/正式实验均未发生。

私有输入key与含答案夹具不在Git；公开结果保留其hash和门禁，不能宣称另机已持有。新clone公开恢复与closeout的原始hash/事件记录收尾追加。每次用新run_id，不删除失败或覆盖原始结果。

最终复检evaluation04=58累计测试、14开发夹具、22span；audit04工程通过/整体未过(exit2)。添加候选导入异常、完善响应人类回执和公开演示状态门禁后运行，旧记录保留。环境快照另存B-D02-20261016-environment，标记收尾时检测而非伪填旧运行时点。

自主收尾：quality01/02各执行57项负例挑战，识别全部；质量02补齐task001完整源码/概念并逐题给出AI难度理由。evaluation05/06累计60测试、14夹具期待通过；06验证24span。B0-shared03仍预期缺成本exit2，lines03基于固定README/RST顺序运行。autonomous-audit01按D02开发范围验收exit0/next_day_allowed=true，formal_study_ready=false；此前将真人预演混入开发门禁的记录不删除。

B-D03：integration02为现行数据源（真实源码/任务 + 模拟回答 + 真实公开Issue）；preflight01是A交付重放输出；verification01记录10命令退出与stdout/stderr，A固定输出由B原样移至其A-replay子目录；audit01保留失败、audit02为修复后审计。integration01为早期代码记录，不作当前通过证据。无正式实验或真人数据，SQLite在忽略tmp。

B-D04：现行comparison03为6组开发比较（真实2题×2模拟画像+shared/cost_gap夹具）；B1未配置，六槽NOT_CONFIGURED且指标NA。fixtures01为7种transport软件挑战+手算，真实调用0，不能并入真实B1结果。accept01保留初次A审计路径拒绝exit2和重试通过；verification01记录160测试/九命令期待退出。旧comparison01/02与初图保留，非最终哈希验收。当前/恢复复检按交接收尾更新。

B-D04最终复检verification02九命令均符合预期；已提交01404b8同机新clone恢复到replay01，160测试/九命令/24槽重算一致，原始记录随分支共享。最终放行见closeout/recovery_gate.json。B1真实未运行与工程通过分别记录，不冒充强LLM对照完成。
