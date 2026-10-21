"""Attempt one public fetch; preserve dated historical fallback on failure."""
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from codecompass.issues.candidates import fetch_snapshot


if __name__=='__main__':
    out=ROOT/'benchmarks/B/D07';out.mkdir(parents=True,exist_ok=True);dest=out/'issues_snapshot.json'
    if dest.exists():raise FileExistsError('Do not overwrite cached sources')
    try:
        data=fetch_snapshot(per_page=30);mode='FETCHED_THEN_FIXED_SNAPSHOT';error=None
        raw=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
        origin=data['source_url']
    except Exception as exc:
        origin='experiments/B/B-D03-issues01/snapshot.json';raw=(ROOT/origin).read_bytes()
        data=json.loads(raw);mode='HISTORICAL_FALLBACK_NOT_LIVE';error=dict(type=type(exc).__name__,http_status=getattr(exc,'code',None))
    dest.write_bytes(raw)
    record=dict(attempted_at=datetime.now(timezone.utc).isoformat(),mode=mode,origin=origin,error=error,
        captured_at=data['retrieved_at'],snapshot_sha256=hashlib.sha256(raw).hexdigest(),
        current_state_claimed=False,contribution_submitted=False,source_is_fixture=data['is_fixture'])
    (out/'issues_source.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(record,ensure_ascii=False))
