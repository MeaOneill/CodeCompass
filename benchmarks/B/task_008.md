# task_008 ANSI清理与bytes边界

填写outputs：text=strip_ansi('A\x1b[31mB\x1b[0mC')（转义序列为真实ESC），bytes=list(strip_ansi(b'X\x1b[1mY\x1b[0m'))，plain=strip_ansi('plain')。解释文本与字节实现路径及函数支持边界，不声称清理任意终端协议。

固定版本：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

状态：未人工审核、未预演、未正式冻结。来源与评分组见task_catalog.json。
