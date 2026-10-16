# task_009 gzip往返与字节约定

## 要做什么

对data=b'open-source navigation'，填写outputs：roundtrip=list(gunzip_bytes(gzip_bytes(data)))，empty=list(gunzip_bytes(gzip_bytes(b'')))，type_name=type(gzip_bytes(data)).__name__。解释BytesIO与压缩级别；不要把压缩后完整字节串当稳定跨版本金标准。

## 需要的知识与难度

较易（AI工程估计，未测真人用时）。两函数往返关系和BytesIO，比完整压缩格式分析简单。

需要用到：字节流、函数组合、压缩基础。这些是本题涉及的知识，不代表所有项目用户必须预先掌握。

## 怎么评分

自动检查行为输出、边界和固定源码依据；机制解释按明示rubric评分。软件开发验收与参与者作答评分分开，开发夹具通过不当真人成功。

设计时间上限25分钟，尚未真人校准。

## 固定源码

commit：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

- boltons/strutils.py，第645至664行。
- boltons/strutils.py，第630至642行。

## 复核说明

只检验往返与类型，不把受环境影响的压缩字节串作为金标准。

AI工程复核已完成；人类独立评分/真人预演未进行，正式测试尚未冻结。
