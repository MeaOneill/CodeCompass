# task_004 默认值与路径索引调试

root={'a':[{'x':None}]}。填写outputs：null=get_path(root,('a',0,'x'),default='MISSING')，missing=get_path(root,'a.0.z',default='MISSING')，string_index=get_path({'a':[10,20]},'a.1')，empty_path=get_path({'x':1},())。解释为何None不代表查找失败、字符串数字何时转换以及何时抛PathAccessError。

固定版本：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

状态：未人工审核、未预演、未正式冻结。来源与评分组见task_catalog.json。
