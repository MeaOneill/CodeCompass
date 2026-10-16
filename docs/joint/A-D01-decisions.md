# A-D01联合记录与决定

记录人：成员A / Codex Agent A；B与人类尚未审核或签署。

ADR-001：说明书六对象、任务卡要求七。候选为保留六种或补任务对象；决定保留六种并补CodeTask。依据任务卡交付要求而非实验效果；影响B按七对象实现加载器。若B反对，先在docs/requests登记，A升版。

ADR-002：比较boltons、more-itertools、Click固定快照/LICENSE/pyproject/源码规模，见benchmarks/sources/candidates.json。boltons局部TODO明确，惰性可独立检验；more-itertools函数集中于较长模块，亦可备用；Click涉及Context、命令解析和终端行为，首日耦合更大。选择基于工程判断及导入smoke，不是学习效果或安装性能结论。

ADR-003：教学关系pending、hard=false；AI提议不冒充人工金标准。base_cost无校准保留null，B复核前不用于硬规划。

分支采用Codex默认前缀codex/A-D01-contracts，对应规划task/A-D01-contracts角色；未合main、未打协议冻结标签。
