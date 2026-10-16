# task_003 稳定去重与key定位

给answer.json的outputs填写plain=list(unique_iter(['a','A','a','b']))、casefold=list(unique_iter(['a','A','a','b'], key=str.lower))、length=list(unique_iter(['hi','ok','hey','bye'], key=len))。在source_spans引用本题函数，explanation解释seen的键和输出对象区别、保持首次顺序和哈希限制。

固定版本：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

状态：未人工审核、未预演、未正式冻结。来源与评分组见task_catalog.json。
