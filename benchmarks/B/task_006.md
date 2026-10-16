# task_006 slug返回类型与标点边界

## 要做什么

填写outputs：normal=slugify('Hello, World!')，empty=slugify('')，punct=slugify('!!!')，ascii_bytes=list(slugify('Café',ascii=True))。解释ascii=True的返回类型为何影响JSON/文本调用方以及空串与全标点输入差异。

## 需要的知识与难度

中等（AI工程估计，未测真人用时）。分支优先级、标点与空串、字节/文本返回类型同时出现。

需要用到：条件表达式、bytes/str、正则分割。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/strutils.py，第89至112行。
- boltons/strutils.py，第115至123行。
- boltons/strutils.py，第416至446行。

## 复核说明

题面用字节列表表示ascii结果，避免JSON无法表达bytes的歧义。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
