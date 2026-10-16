# task_009 gzip往返与字节约定

对data=b'open-source navigation'，填写outputs：roundtrip=list(gunzip_bytes(gzip_bytes(data)))，empty=list(gunzip_bytes(gzip_bytes(b'')))，type_name=type(gzip_bytes(data)).__name__。解释BytesIO与压缩级别；不要把压缩后完整字节串当稳定跨版本金标准。

固定版本：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

状态：未人工审核、未预演、未正式冻结。来源与评分组见task_catalog.json。
