# task_003 稳定去重与key定位

## 要做什么

给answer.json的outputs填写plain=list(unique_iter(['a','A','a','b']))、casefold=list(unique_iter(['a','A','a','b'], key=str.lower))、length=list(unique_iter(['hi','ok','hey','bye'], key=len))。在source_spans引用本题函数，explanation解释seen的键和输出对象区别、保持首次顺序和哈希限制。

## 需要的知识与难度

中等（AI工程估计，未测真人用时）。需区分保存的key与实际yield对象，不能只背集合去重。

需要用到：集合哈希、key回调、生成器。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/iterutils.py，第834至867行。

## 复核说明

三个输入各测试顺序、大小写键与长度键，解释项检查机制而非只抄输出。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
