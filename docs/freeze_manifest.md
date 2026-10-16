# A-D01接口冻结清单

版本1.0.0：A提出，可供加载，待B独立复核，不等于D06正式实验协议冻结。

冻结本轮交接：schema七对象字段/空值/provenance规则，task_001固定commit与源码hash，dev划分。交接输入哈希见experiments/A/A-D01-20261016-foundation/input_manifest.json（收尾生成）。

尚未冻结：真人时长/难度、评分器实现、硬教学边、base_cost、预算、算法参数、正式测试集。变更要角色请求与升版，不静默改接口；不得创建正式协议标签。

## A-D03开发快照（非D06正式冻结）

前置B-D02=fc6485329691efda2662e21116d8f23e329b4d96。schema兼容扩展1.1.0；配置A-D03-dev-0.1；ledger0.1.0；源boltons=4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d。最终短测A-D03-short-tests04的input_manifest与code_snapshot逐文件保存精确字节；成本inclusive源码行数proxy_cost，预算100；门控q=.1/τ=.7。真实教学边仍soft/pending，未审批硬边不得用于正式约束。没有冻结正式实验/人类题目金标准。
