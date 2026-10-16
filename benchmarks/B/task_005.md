# task_005 缩写与分隔符转换定位

## 要做什么

填写outputs：acronym=camel2under('HTTPServer2Thing')，simple=under2camel('parse_http_body')，underscores=under2camel('__edge__')。引用正则使用位置；解释缩写边界和空片段的处理，不假定两个函数总互逆。

## 需要的知识与难度

较易（AI工程估计，未测真人用时）。局部正则和split/join转换，修改规模小但需注意缩写边界。

需要用到：字符串操作、正则基础。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/strutils.py，第69至76行。
- boltons/strutils.py，第79至86行。

## 复核说明

两个转换不是严格互逆，解释项必须指出边界。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
