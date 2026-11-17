"""Read-only contribution preparation using existing matching and dated snapshots."""
import hashlib,json
from datetime import datetime,timezone
from codecompass.issues.candidates import match_issues,fetch_snapshot
from codecompass.learner import mastery_gate
from .planning import CONCEPTS

STEPS=['回看相关函数','用一个小例子复现或理解问题','阅读贡献说明后再决定参与']

class Issues:
    def __init__(self,service):self.service=service
    def get(self,sid,refresh=False):
        from .service import now,dump
        s=self.service.get(sid);data=self.service.catalog.source(s['task_id'])
        repo=data['snapshot']['url'].removeprefix('https://github.com/')
        path=self.service.root/'benchmarks/B/D07/issues_snapshot.json'
        historical=json.loads(path.read_text(encoding='utf-8')) if repo=='mahmoud/boltons' and path.is_file() else None
        with self.service.store.connect() as db:
            row=db.execute('SELECT * FROM product_issue_snapshots WHERE repo=?',(repo,)).fetchone()
        attempt=row['attempted_at'] if row else None;error=row['error'] if row else None
        cached=json.loads(row['snapshot_json']) if row and row['snapshot_json'] else None
        should_fetch=False
        if refresh:

            with self.service.store.connect() as db:
                db.execute('BEGIN IMMEDIATE')
                latest=db.execute('SELECT attempted_at FROM product_issue_snapshots WHERE repo=?',(repo,)).fetchone()
                elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(latest[0])).total_seconds() if latest else 1801
                if elapsed>=1800:
                    attempt=now();should_fetch=True
                    db.execute('INSERT INTO product_issue_snapshots VALUES(?,?,NULL,NULL) ON CONFLICT(repo) DO UPDATE SET attempted_at=excluded.attempted_at',(repo,attempt))
        if should_fetch:
            try:
                fresh=fetch_snapshot(repo)
                if fresh.get('repo')!=repo:raise ValueError('仓库不匹配')

                match_issues(fresh,data['units'],[]);cached=fresh;error=None
            except Exception:error='在线刷新失败，继续使用已有快照；没有核实当前Issue状态。'
            with self.service.store.connect() as db:
                db.execute('UPDATE product_issue_snapshots SET snapshot_json=COALESCE(?,snapshot_json),error=? WHERE repo=?',(dump(cached) if cached else None,error,repo))
        snapshot=cached or historical
        if snapshot is None:
            return dict(items=[],source_mode='unavailable',captured_at=None,last_attempt=attempt,notice=error or '此仓库尚无可用Issue快照。',empty_message='暂未找到合适的贡献任务',next_learning='先完成chunked与take的小例子，再阅读该仓库贡献说明。',community_submission=False)
        ledger=self.service.store.evidence.read(s['user_id'],simulated=self.service.actor!='local_user')
        gate=mastery_gate(ledger,data['snapshot']['snapshot_id'],data['request']['target_concept_ids'],threshold=self.service.config['threshold'],quantile=self.service.config['quantile'],allow_simulated=self.service.actor!='local_user')
        result=match_issues(snapshot,data['units'],[c for c,g in gate.items() if not g['mastered']])
        chosen=(result['candidates']+[i for i in result['historical'] if i['modules']])[:3]
        items=[]
        for row in chosen:
            items.append(dict(title=row['title'],url=row['url'],number=row['number'],state_at_capture=row['state_at_capture'],captured_at=row['retrieved_at'],label='历史关闭案例，仅供学习' if row['state_at_capture']=='closed' else '快照中开放，参与前需核实',reason='原Issue提到'+ '、'.join(row['modules'])+'；这里只是模块词匹配，尚未证明具体函数相关或适合参与。',source_paths=row['modules'],source_version=data['snapshot']['commit'],gaps=[CONCEPTS.get(c,c) for c in row['candidate_concept_gaps']],preparation_steps=STEPS,contribution_guide='https://github.com/'+repo,community_submission=False))
        return dict(items=items,source_mode='refreshed_snapshot' if cached else 'historical_snapshot',captured_at=snapshot['retrieved_at'],last_attempt=attempt,notice=error or ('已读取在线快照；状态只截至抓取时刻。' if cached else '使用历史快照，状态只截至抓取时刻。'),current_state_claimed=False,snapshot_sha256=hashlib.sha256(path.read_bytes()).hexdigest() if not cached and historical else None,empty_message='暂未找到合适的贡献任务' if not items else None,next_learning='回看当前函数并核对一个最小例子；共享模块不等于适合贡献。',community_submission=False)
