# task_011 整数区间解析与重复保留

## 要做什么

填写outputs：reverse=parse_int_list('5-3,1')，duplicates=parse_int_list('2,1,2')，formatted=format_int_list([1,2,3,5])，empty=parse_int_list('')。解释排序不等于去重、反向范围取min/max及区间闭端点。

## 需要的知识与难度

中等（AI工程估计，未测真人用时）。需要区分区间闭端点、排序和去重，观察分支组合。

需要用到：range、排序、字符串解析。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/strutils.py，第886至920行。
- boltons/strutils.py，第923至1010行。

## 复核说明

明确反向范围与重复保留，不预设文档描述等于去重。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
