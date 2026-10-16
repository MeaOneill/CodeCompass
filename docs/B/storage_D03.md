# B证据存储与公开样例恢复

实现 `src/codecompass/app/evidence_store.py`，调用A的 `initial_state/update_evidence/planning_rows/beta_quantile`，不复制learner算法。仅使用Python标准库SQLite和现有依赖，无新增安装/锁文件。运行入口 `scripts/B/demo_d03.py --help`；网络入口 `scripts/B/issues_d03.py --help`。

匿名用户+simulated布尔值组成账户键；同一事务写ledger、按project/concept的a/b缓存和尝试日志。缓存与原始ledger不一致时读取失败。每个连接及时关闭。并发写由BEGIN IMMEDIATE串行化；失败整个批次回滚。读取使用事务快照，避免读到新ledger/旧posterior组合。没有HTTP认证/多租户服务，匿名ID由调用者提供，这是本地CLI数据隔离，不宣称网络访问控制。

个人SQLite及-journal/-wal/-shm被忽略，示例数据库也只存 `tmp/<run_id>/personal.sqlite3`。共享内容为 `experiments/B/B-D03-integration02/events.json`，24次模拟尝试中22次接受、一次同题重复、一次阅读忽略；`human_answers=0`。禁止将它们作为真实人类记录导入。

开发者恢复该模拟样例（用户不需要执行）：

```python
import json
from pathlib import Path
from codecompass.app.evidence_store import EvidenceStore
sample = json.loads(Path('experiments/B/B-D03-integration02/events.json').read_text(encoding='utf-8'))
assert sample['is_simulated'] is True
store = EvidenceStore('tmp/local-import/personal.sqlite3')
ledger, decisions = store.submit_many('sim-anon-B03-01', [row['evidence'] for row in sample['events']], simulated=True)
assert len(ledger['records']) == 22
```

上面是ledger0.1.0接口导入，不导入a/b外部数值；a/b由A函数重算。原始source_mode、item_id、project、时间和is_fixture保留。重复整批导入接受数不再增加；同evidence_id改内容拒绝。真人输入须独立匿名空间、is_fixture=false、simulated=false，且来源仍标REAL_INPUT_UNVERIFIED；软件字段不等于审核者身份或真实独立答题已核实。

Issue快照只取公开题文与元数据，剔除作者、头像、联系方式字段和评论，不访问私有仓库。保留原URL而不将题文当项目原创；Issue内容并未据仓库BSD许可自动重新授权，报告优先引用链接和摘要，公开样例只用于来源复核。抓取失败应保留非零退出，不自动生成虚构Issue或将旧快照标实时。准备CLI读取固定快照，模块匹配不执行题文代码，不发社区消息，不读私有评分key。
