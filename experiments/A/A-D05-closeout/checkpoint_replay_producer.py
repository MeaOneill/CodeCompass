from pathlib import Path
import subprocess,json,zipfile,hashlib,shutil,os,datetime as dt
root=Path.cwd();out=root/'experiments/A/A-D05-closeout'
sha=subprocess.check_output(['git','rev-parse','HEAD'],encoding='utf-8').strip()
archive=root/'tmp/A-D05-business-checkpoint01.zip';replay=root/'tmp/A-D05-business-replay01'
assert not archive.exists() and not replay.exists()
cmd=['git','-c','core.autocrlf=false','archive','--format=zip','--output',str(archive),sha]
result=subprocess.run(cmd,capture_output=True)
(out/'archive.stdout.log').write_bytes(result.stdout);(out/'archive.stderr.log').write_bytes(result.stderr)
assert result.returncode==0
items=[]
for line in filter(None,subprocess.check_output(['git','ls-tree','-r','-z',sha]).split(b'\0')):
    meta,path=line.split(b'\t',1);mode,kind,oid=meta.split()
    if kind==b'blob':items.append((path.decode('utf-8'),oid))
batch=subprocess.check_output(['git','cat-file','--batch'],input=b''.join(oid+b'\n' for _,oid in items))
offset=0;byte_checks=[]
with zipfile.ZipFile(archive) as z:
    for path,oid in items:
        end=batch.index(b'\n',offset);size=int(batch[offset:end].split()[2]);blob=batch[end+1:end+1+size];offset=end+size+2
        assert z.read(path)==blob,path
        byte_checks.append(dict(path=path,sha256=hashlib.sha256(blob).hexdigest(),passed=True))
    replay.mkdir()
    for info in z.infolist():assert (replay/info.filename).resolve().is_relative_to(replay.resolve())
    z.extractall(replay)
env=dict(os.environ);env.update(PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
command=[str(root/'.venv/Scripts/python.exe'),'scripts/A/verify_d05.py','--run-id','A-D05-committed-verification01','--source-run','A-D05-development01']
result=subprocess.run(command,cwd=replay,env=env,capture_output=True)
(out/'checkpoint-verification.stdout.log').write_bytes(result.stdout);(out/'checkpoint-verification.stderr.log').write_bytes(result.stderr)
origin=replay/'experiments/A/A-D05-committed-verification01';destination=out/'committed_replay'
shutil.copytree(origin,destination)
registration=json.loads((destination/'registration.json').read_text(encoding='utf-8'))
record=dict(time=dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat(),checkpoint=sha,
    archive_command=cmd,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    verification_command=command,exit_code=result.returncode,byte_checks=byte_checks,
    committed_copy_replay_passed=result.returncode==0 and registration['engineering_passed'],
    kind='same-machine committed source archive + existing A isolated Python3.12.10 hash-locked environment; not cross-machine or human review',
    note='Archive has no .git; verification resolves enclosing A worktree HEAD at this checkpoint. Every archived file independently checked against checkpoint Git blobs.',
    scope='209 tests, all 768 saved-session independent replays and legacy audits, live CLI calls; full configuration generation is not re-run',model_api_calls=0)
(out/'checkpoint_replay.json').write_bytes((json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
shutil.copyfile(Path(__file__),out/'checkpoint_replay_producer.py')
print(json.dumps(dict(checkpoint=sha,exit_code=result.returncode,byte_checks=len(byte_checks),passed=record['committed_copy_replay_passed']),ensure_ascii=False))
raise SystemExit(result.returncode)
