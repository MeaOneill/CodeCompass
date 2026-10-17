from pathlib import Path
import subprocess, json, os, hashlib, zipfile, shutil, datetime as dt

root=Path.cwd()
out=root/'experiments/A/A-D05-preflight-20261017-01'
sha=subprocess.check_output(['git','rev-parse','HEAD'],encoding='utf-8').strip()
archive=root/'tmp/A-D05-committed-checkpoint01.zip'
replay=root/'tmp/A-D05-archive-replay01'
assert not archive.exists() and not replay.exists()
proc=subprocess.run(['git','archive','--format=zip','--output',str(archive),sha],capture_output=True)
(out/'archive.stdout.log').write_bytes(proc.stdout)
(out/'archive.stderr.log').write_bytes(proc.stderr)
assert proc.returncode==0
replay.mkdir()
with zipfile.ZipFile(archive) as z:
    for item in z.infolist():
        target=(replay/item.filename).resolve()
        assert target.is_relative_to(replay.resolve())
    z.extractall(replay)
env=dict(os.environ)
env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONPATH=str(replay/'src'),TEMP=str(root/'tmp'),TMP=str(root/'tmp'))
py=str(root/'.venv/Scripts/python.exe')
cmd=[py,'scripts/A/accept_b04.py','--run-id','A-D05-committed-replay-01']
result=subprocess.run(cmd,cwd=replay,env=env,capture_output=True)
(out/'checkpoint-runner.stdout.log').write_bytes(result.stdout)
(out/'checkpoint-runner.stderr.log').write_bytes(result.stderr)
checks=[dict(name='committed-source acceptance',argv=cmd,exit_code=result.returncode,expected_exit=0)]
for name,args,expected,status in [
    ('guide-unique',['--case','unique_chain'],0,'FEASIBLE'),
    ('guide-narrow',['--case','greedy_failure','--beam-width','1','--candidate-limit','1','--certify-small'],0,'NO_FEASIBLE_FOUND'),
    ('guide-unreachable',['--case','unreachable','--certify-small'],0,'INFEASIBLE_PROVEN'),
    ('guide-timeout',['--time-limit','0'],0,'TIMEOUT'),
    ('invalid-width',['--beam-width','0'],2,None),
]:
    command=[py,'scripts/A/demo_d04.py',*args]
    result=subprocess.run(command,cwd=replay,env=env,capture_output=True)
    (out/(name+'.stdout.log')).write_bytes(result.stdout)
    (out/(name+'.stderr.log')).write_bytes(result.stderr)
    checks.append(dict(name=name,argv=command,exit_code=result.returncode,expected_exit=expected,
                       expected_beam_status=status,status_found=status is None or ('beam: '+status) in result.stdout.decode('utf-8')))
src=replay/'experiments/A/A-D05-committed-replay-01'
dest=out/'committed_replay'
shutil.copytree(src,dest)
# Compare archive files to committed Git blob bytes in a single cat-file batch.
entries=subprocess.check_output(['git','ls-tree','-r','-z',sha]).split(b'\0')
items=[]
for entry in filter(None,entries):
    meta,path=entry.split(b'\t',1)
    mode,kind,oid=meta.split()
    if kind==b'blob': items.append((path.decode('utf-8'),oid))
batch=subprocess.check_output(['git','cat-file','--batch'],input=b''.join(oid+b'\n' for _,oid in items))
offset=0
byte_checks=[]
for path,oid in items:
    end=batch.index(b'\n',offset)
    header=batch[offset:end].split()
    size=int(header[2]); blob=batch[end+1:end+1+size]; offset=end+size+2
    actual=(replay/path).read_bytes()
    byte_checks.append(dict(path=path,sha256=hashlib.sha256(blob).hexdigest(),passed=blob==actual))
record=dict(checkpoint=sha,kind='same-machine committed Git archive; fresh source, existing A isolated hash-locked environment',
            root=str(replay),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
            note='Archive has no .git; runner resolves enclosing A worktree metadata at this checkpoint. Each archive file independently compared with checkpoint Git blobs.',
            commands=checks,byte_checks=byte_checks,model_api_calls=0,
            passed=all(c['exit_code']==c['expected_exit'] and c.get('status_found',True) for c in checks) and all(c['passed'] for c in byte_checks),
            finished_at=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat())
(out/'checkpoint_replay.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(checkpoint=sha,passed=record['passed'],byte_checks=len(byte_checks),commands=checks),ensure_ascii=False),flush=True)
raise SystemExit(0 if record['passed'] else 1)
