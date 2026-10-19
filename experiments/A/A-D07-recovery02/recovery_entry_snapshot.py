import hashlib,json,os,subprocess,sys,time,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];clone=root/'tmp/A-D07-replay-36e100'
(clone/'tmp').mkdir(exist_ok=True)
out=root/'experiments/A/A-D07-recovery02';out.mkdir(exist_ok=False)
env={k:v for k,v in os.environ.items() if not any(s in k.upper() for s in ('API_KEY','TOKEN','SECRET','PASSWORD'))}
env.update(PYTHONPATH=str(clone/'src')+os.pathsep+str(clone),PYTHONUTF8='1',PYTHONIOENCODING='utf-8',NO_PROXY='127.0.0.1,localhost')
commands=[('version',[sys.executable,'scripts/A/audit_d07_version.py','--output',str(out/'version-audit.json')]),
 ('new_tests',[sys.executable,'-m','pytest','tests/A/test_runtime_d07.py','tests/A/test_runtime_d07_http.py','-q',
     '--basetemp='+str(clone/'tmp/A-D07-committed-tests')]),
 ('saved_replay',[sys.executable,'scripts/A/audit_d07.py','--run-id','A-D07-development05','--output',str(out/'saved-smoke-audit.json')]),
 ('rerun',[sys.executable,'scripts/A/run_d07.py','--run-id','A-D07-clone-replay01'])]
receipts=[]
for name,argv in commands:
    start=time.perf_counter();p=subprocess.run(argv,cwd=clone,env=env,capture_output=True)
    (out/(name+'.stdout.log')).write_bytes(p.stdout);(out/(name+'.stderr.log')).write_bytes(p.stderr)
    receipts.append(dict(name=name,argv=argv,exit_code=p.returncode,elapsed_seconds=time.perf_counter()-start))
    print(name,p.returncode,flush=True)
    if p.returncode:break

def load(p):return json.loads(p.read_text(encoding='utf-8'))

def stable(value):
    if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k!='evidence_ids'}
    if isinstance(value,list):return [stable(v) for v in value]
    return value

def semantic(raw):
    v=raw['view']
    return dict(view={k:v[k] for k in ('task','method','actor','status','phase','route','completed','spent','quiz_done',
                     'outcome','score_status','success','route_explanations')},feedback=stable(v['feedback']),
       traces=[dict(status=t['status'],route=t['route'],cost=t['cost'],context=stable(t['context'])) for t in raw['traces']],
       quiz_changed_remaining=raw['quiz_changed_remaining'])

matches=[]
replayed=clone/'experiments/A/A-D07-clone-replay01'
if len(receipts)==4 and all(r['exit_code']==0 for r in receipts):
    original=clone/'experiments/A/A-D07-development05'
    for p in sorted((original/'closed_loops').rglob('*.json')):
        new=replayed/'closed_loops'/p.relative_to(original/'closed_loops')
        matches.append(dict(path=p.relative_to(original).as_posix(),same=semantic(load(p))==semantic(load(new))))
    assert all(r['same'] for r in matches)
    assert len(matches)==72
    with zipfile.ZipFile(out/'replayed_development.zip','w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(replayed.rglob('*')):
            if p.is_file() and 'code_snapshot' not in p.parts:z.write(p,p.relative_to(replayed))
passed=len(receipts)==4 and all(r['exit_code']==0 for r in receipts) and len(matches)==72 and all(r['same'] for r in matches)
result=dict(passed=passed,checkpoint=subprocess.check_output(['git','rev-parse','HEAD'],cwd=clone,text=True).strip(),
 method='same-machine clean local clone; original interpreter reused; no credentials/private final key copied',
 commands=receipts,semantic_replay_matches=sum(r['same'] for r in matches),comparisons=matches,
 comparison_scope='route/status/goal context/evidence numeric gate/cost/completed/feedback/source explanations; only random transport/session identities and evidence IDs and processing latency excluded',
 new_model_calls=0,real_human_pretests='NOT_RUN',independent_person_review='NOT_REVIEWED',formal_G2_passed=False,
 zip_sha256=hashlib.sha256((out/'replayed_development.zip').read_bytes()).hexdigest() if (out/'replayed_development.zip').exists() else None)
(out/'recovery_receipt.json').write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
print(json.dumps(dict(passed=passed,matches=result['semantic_replay_matches'])))
raise SystemExit(0 if passed else 1)
