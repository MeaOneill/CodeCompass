# task_012 前缀切片与自然语言列表

## 要做什么

填写outputs：prefix=removeprefix('foobar','foo')，not_chars=removeprefix('barfoo','foo')，two=human_readable_list(['a','b'])，three=human_readable_list(['a','b','c'],oxford=False)。解释精确前缀与lstrip字符集合的区别，并定位两元素及oxford分支。

## 需要的知识与难度

较易（AI工程估计，未测真人用时）。精确前缀切片及列表长度分支，源码范围局部。

需要用到：切片、startswith、字符串拼接。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/strutils.py，第1288至1300行。
- boltons/strutils.py，第1302至1329行。

## 复核说明

不将removeprefix等同lstrip；两元素和oxford分支各有独立要求。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
