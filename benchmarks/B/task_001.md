# task_001 惰性count限制

## 要做什么

给分块读取函数chunked_iter增加count参数：最多输出count组，达到限制就停止读取输入。

具体要求：

- 仅修改chunked_iter及必要文档/测试，增加count=None；chunked公共签名及现有结果保持兼容。
- count=None保持原语义；非负内置整数（排除bool）限制最多输出count个块；0输出空且不消费源；超过可用块数自然结束。
- 负count整数ValueError，其他类型（bool/float/str等）TypeError；允许首次next/列表化时抛错。size及原未知kw报错保持不变。
- 保持惰性：创建生成器不消费源；输出c个完整块后迭代到结束不得读取第c*size之后的元素；不能list(src)物化或产生再丢弃第c+1块。
- fill未传与fill=None不同；填充仅作用真实短尾块，不能为凑count凭空增加块；str/bytes返回类型与原版一致。
- 提交最小复现、回归测试和固定版本行号解释；不声称本任务已获上游确认或存在开放Issue。

## 需要的知识与难度

较难（AI工程估计，未测真人用时）。需要同时控制生成器惰性、count边界、输入消费和包装器兼容，难点不只是新增参数。

需要用到：函数与参数、迭代器、生成器/yield、itertools.islice。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/iterutils.py，第286至306行。
- boltons/iterutils.py，第316至358行。
- boltons/iterutils.py，第61至76行。
- boltons/iterutils.py，第309至313行。

## 复核说明

适合已学过生成器的Python使用者；不能将只学过基本语法视为同等基础。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
