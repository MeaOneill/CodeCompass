# task_002 滑动窗口size边界防护

仅修改windowed_iter：size只接受内置正int，排除bool；非int TypeError，<=0 ValueError。保持正常窗口、短源/空源、fill省略与显式None、pairwise end及无限输入前缀兼容。说明tee和填充哨兵的作用。

固定版本：4e5faa3d7e4008d89e0d8bf1ea87b6d9a061a16d

状态：未人工审核、未预演、未正式冻结。来源与评分组见task_catalog.json。
