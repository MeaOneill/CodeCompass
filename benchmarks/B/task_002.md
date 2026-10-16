# task_002 滑动窗口size边界防护

## 要做什么

仅修改windowed_iter：size只接受内置正int，排除bool；非int TypeError，<=0 ValueError。保持正常窗口、短源/空源、fill省略与显式None、pairwise end及无限输入前缀兼容。说明tee和填充哨兵的作用。

## 需要的知识与难度

中等（AI工程估计，未测真人用时）。修改局限于入口类型校验，但必须保持tee窗口、默认哨兵和调用包装器兼容。

需要用到：异常类型、bool与int关系、迭代器、默认参数哨兵。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/iterutils.py，第472至510行。
- boltons/iterutils.py，第464至469行。
- boltons/iterutils.py，第415至436行。

## 复核说明

理解tee可阅读标准库资料；要求明确只接受内置int，避免校验歧义。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
