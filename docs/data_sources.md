# A-D01仓库与数据来源

来源是公开上游仓库的固定提交。本轮已下载三份完整浅克隆到被忽略的third_party/checkouts，未执行构建脚本或pip安装这些仓库。依赖成本判断来自固定pyproject和实际源码导入，不能写成安装耗时。各一次导入仅是环境smoke，不能用三次值排名性能。

| 候选 | 固定commit | 许可证 | Python文件/行数（含测试） | 目标模块行数 | 局部任务与选择 |
|---|---|---|---|---|---|
| [boltons](https://github.com/mahmoud/boltons) | `4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d` | [BSD-3-Clause](https://github.com/mahmoud/boltons/blob/4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d/LICENSE) | 65 / 24552 | 1659 | 选用：chunked_iter的count TODO，惰性消费/API兼容可独立检验 |
| [more-itertools](https://github.com/more-itertools/more-itertools) | `4aeb4338ae1407d8da9723e86da99efeb446f719` | [MIT](https://github.com/more-itertools/more-itertools/blob/4aeb4338ae1407d8da9723e86da99efeb446f719/LICENSE) | 7 / 16726 | 5644 | 备用：迭代分组/窗口功能；more.py较集中 |
| [click](https://github.com/pallets/click) | `2247b35ea1c47c727d7a06e51fa280e12a863ff6` | [BSD-3-Clause](https://github.com/pallets/click/blob/2247b35ea1c47c727d7a06e51fa280e12a863ff6/LICENSE.txt) | 91 / 30378 | 4038 | 候选：选项处理/Context；涉及终端与命令上下文，首日不选 |

三项目均为纯Python；固定元数据未声明必需运行依赖。常规包安装需flit_core构建隔离，开发测试还需pytest；这些包安装与完整测试本轮均未运行。Python3.12下三项目本地源码导入exit=0，原始时长与来源位置见candidates.json。未来B须按目标环境实测锁定，不能把本机工具Python当完整研发环境验收。

## 许可与再分发

boltons采用BSD-3-Clause，保留版权、三项条款与免责声明；二进制分发随附许可，不用贡献者名背书。本轮benchmarks/sources/boltons保留完整LICENSE和四份未经修改Git blob，仅是局部源码包，snapshot_scope明确partial_source_bundle。文件hash与blob SHA见snapshot.json；不是把第三方代码当团队实现。

more-itertools采用MIT，保留版权与许可；Click采用BSD-3-Clause。后两者当前仅保存来源、commit、许可hash和元数据，不随项目复制完整仓库。公开本项目时仍须B核对依赖/资源许可及本项目自有许可，不因公开GitHub就默认任意再分发。

## 恢复

task_001的四份源码/许可和snapshot.json随团队任务分支共享，B无需先下载完整上游即可验证定位。需要完整仓库时在third_party/checkouts/boltons克隆并checkout指定commit，不能使用浮动HEAD替代。prepare_sources.py只接受PINS中三份固定HEAD，用CODECOMPASS_GIT指定Git可执行文件。若当前浅克隆取不到commit，另行fetch该commit，不覆盖已有修改。

独立评分源码归B实现；本轮没有真人作答数据。任务来自固定源码TODO，不是已核实开放Issue；后续Issue准备应另存真实状态与抓取时间。data_sources.csv可供报告T06引用。
