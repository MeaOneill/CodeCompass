"""Independent exported event/timing/association audit; never calls a planner."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from codecompass.app.experiment import digest


def audit(folder):
    folder=Path(folder);errors=[];checks=0
    def check(ok,message):
        nonlocal checks
        checks+=1
        if not ok:errors.append(message)
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for name,sha in manifest['files'].items():
        path=(folder/name).resolve()
        check(path.parent==folder.resolve(),'unsafe manifest path')
        if path.parent!=folder.resolve():continue
        check(hashlib.sha256(path.read_bytes()).hexdigest()==sha,'file hash '+name)
    sessions=json.loads((folder/'sessions.json').read_text(encoding='utf-8'))
    events=json.loads((folder/'events.json').read_text(encoding='utf-8'))
    groups=json.loads((folder/'participants.json').read_text(encoding='utf-8'))
    check({g['participant'] for g in groups}=={s['participant'] for s in sessions},'participant grouping')
    for g in groups:
        rs=[s for s in sessions if s['participant']==g['participant']]
        check(g['sessions']==len(rs) and g['methods']==sorted({s['method'] for s in rs}),'group counts')
        check(g['success_rate'] is None and g['scored']==0 and g['formal_participant'] is False,'no fabricated study results')
    check(len({s['session_id'] for s in sessions})==len(sessions),'duplicate sessions')
    check(all(e['session_id'] in {s['session_id'] for s in sessions} for e in events),'orphan events')
    for s in sessions:
        check(s['actor']==manifest['actor'],'mixed provenance')
        es=[e for e in events if e['session_id']==s['session_id']];prev=None;elapsed=0;quiz=False;answers=0;ended=False;status='ACTIVE';quiz_time=None
        check(len(es)==s['event_count'],'event count');check(bool(es) and es[0]['kind']=='start','start first')
        for i,e in enumerate(es,1):
            check(e['seq']==i and e['previous_hash']==prev,'chain order');check(e['hash']==digest({k:v for k,v in e.items() if k!='hash'}),'event hash');prev=e['hash']
            check(all(e[k]==s[k] for k in ('session_id','participant','task_id','method','actor')),'association')
            t=e['elapsed_observed'];check(type(t) in (float,int) and math.isfinite(t) and t>=elapsed,'nonnegative monotonic elapsed')
            if status=='PAUSED':check(t==elapsed,'paused interval added to active time')
            elapsed=t
            check(not ended,'event after terminal')
            if e['kind']=='quiz_start':check(not quiz,'duplicate quiz');quiz=True;quiz_time=t
            if e['kind']=='quiz_submit':
                answers+=1;check(quiz and answers==1,'answer without quiz/repeat')
                d=e['payload']['duration_seconds'];check(d is None or d>=0,'quiz duration')
                if d is not None and quiz_time is not None:check(abs(d-(t-quiz_time))<1e-6,'quiz duration differs from event time')
            if e['kind']=='feedback':check(answers==1,'feedback without scored quiz')
            if e['kind']=='replan':check(answers==1,'replan without evidence')
            if e['kind']=='reading_complete':check(e['payload']['mastery_updated'] is False,'reading cannot update mastery')
            if status=='PAUSED' and e['kind'] not in ('resume','restart','withdraw','clock_anomaly'):
                check(False,'action during pause')
            status=e['status'];ended=status in ('SUBMITTED','TIMED_OUT','WITHDRAWN','FAILED')
        check(s['success'] is None,'unscored final success')
        check(s['duration_seconds'] is None or s['duration_seconds']>=elapsed,'duration before last event')
        check(s['duration_valid'] or s['duration_seconds'] is None,'invalid time presented as complete')
        check(s['status'] not in ('ACTIVE','PAUSED') or s['duration_seconds'] is None,'unfinished zero/final duration')
        if es:check(es[-1]['status']==s['status'],'terminal state mismatch')
    # Task-card step 4 requires one complete manual core flow. Pause/resume is
    # independently audited and may occur in a preserved withdrawn session.
    # Do not splice separate sessions into a fabricated complete submission.
    required=['start','read','reading_complete','quiz_start','quiz_submit','feedback','replan','final_submit']
    manual=[]
    for s in sessions:
        if s['actor']!='human_manual' or s['status']!='SUBMITTED' or not s['duration_valid']:continue
        kinds=[e['kind'] for e in events if e['session_id']==s['session_id']]
        cursor=0
        for kind in kinds:
            if cursor<len(required) and kind==required[cursor]:cursor+=1
        if cursor==len(required):manual.append(s['session_id'])
    pause_flows=0
    for s in sessions:
        if s['actor']!='human_manual' or not s['duration_valid']:continue
        kinds=[e['kind'] for e in events if e['session_id']==s['session_id']]
        if 'pause' in kinds and 'resume' in kinds and kinds.index('pause')<kinds.index('resume'):
            pause_flows+=1
    return dict(passed=not errors,checks=checks,errors=errors,sessions=len(sessions),events=len(events),
                acceptance_rule='B-D05-manual-core-v2; pause/resume reported separately, no session splicing',
                manual_pause_resume_flows=pause_flows,
                complete_manual_flows=len(manual),manual_flow_passed=bool(manual) and not errors,
                human_manual_sessions=sum(s['actor']=='human_manual' for s in sessions),independent_human_review='NOT_REVIEWED')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--require-manual-flow',action='store_true');a=p.parse_args()
    result=audit(a.source);a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps(result,ensure_ascii=False));return 0 if result['passed'] and (not a.require_manual_flow or result['manual_flow_passed']) else 1


if __name__=='__main__':raise SystemExit(main())
