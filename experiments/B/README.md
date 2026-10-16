# B-D01开发运行登记索引

本轮证据均development_validation，正式实验0。没有真人/模型效果数据，metrics/cost/未知模型与seed为null。

- B-D01-20261016-check01：首次CLI/导入/真实样例/A验证/pip检查通过；pytest=1，16通过，tmp_path权限错误保留原始stdout/stderr。
- B-D01-20261016-check02：临时目录改在项目忽略tmp后，六命令全部exit0，pytest18通过。每条实际命令、UTC起止/耗时/退出码、Python/机器及输入内容hash见registration和input_manifest。实际本地日期为北京时间10月16日。实现当时未提交code_commit=null，dependency_commit仅指A基线，不能当作B实现版本。
- B-D01-20261016-environment：CIM、pip、远程读取等原始输出与独立退出码；13个wheel SHA256清单。成功网络探针在授权外层运行，不掩盖受限shell失败。
- B-D01-20261016-local-replay：实际Git检查点全新本地clone、SHA比对、新venv、--no-index/--require-hashes安装及运行；是否通过以registration exit_code为准，同机演练不计异机实验。
- B-D01-20261016-closeout：收尾生成原始结果hash清单和真实成功/失败事件；无真实暂停/恢复运行，不将格式夹具写入真实记录。

启动观察（早于捕获脚本，来自本轮工具实际输出，不补造逐命令退出码）：普通git fetch/ls-remote提示127.0.0.1:7890无法连接，直连覆盖测试提示getaddrinfo thread failed；初次venv ensurepip返回1、无pip；受限CIM无法访问资源。随后授权外层fetch/安装/CIM成功。日志不含令牌；未更改全局代理/身份/依赖。原始失败pytest traceback包含用户本机路径，仅供团队开发记录，不直接作为匿名评审截图。

配置追溯：check01/02使用工作树pytest.ini，第一次默认临时目录，第二次实际命令显式传--basetemp。原input_manifest未单列根pytest.ini，其配置差异由保留命令/失败日志及开发日志追溯；恢复演练以完整实际Git检查点（含pytest.ini与hash锁）为权威。未来捕获应将根配置也纳入输入清单，此限制不隐去。
