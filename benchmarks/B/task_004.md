# task_004 默认值与路径索引调试

## 要做什么

root={'a':[{'x':None}]}。填写outputs：null=get_path(root,('a',0,'x'),default='MISSING')，missing=get_path(root,'a.0.z',default='MISSING')，string_index=get_path({'a':[10,20]},'a.1')，empty_path=get_path({'x':1},())。解释为何None不代表查找失败、字符串数字何时转换以及何时抛PathAccessError。

## 需要的知识与难度

中等（AI工程估计，未测真人用时）。需跟踪嵌套访问、异常转译以及缺省值与实际None的区别。

需要用到：字典/列表、异常处理、默认值哨兵。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/iterutils.py，第1324至1382行。

## 复核说明

缺路径、数字字符串索引、空路径分别检查不同分支，不把None都当失败。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
