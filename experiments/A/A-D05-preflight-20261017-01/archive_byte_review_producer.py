from pathlib import Path
import subprocess,json,hashlib,zipfile,re,datetime as dt
root=Path.cwd(); out=root/'experiments/A/A-D05-preflight-20261017-01'
old=json.loads((out/'checkpoint_replay.json').read_text(encoding='utf-8'))
assert not (out/'checkpoint_replay_failed01.json').exists()
(out/'checkpoint_replay.json').rename(out/'checkpoint_replay_failed01.json')
sha=old['checkpoint']
raw=root/'tmp/A-D05-raw-checkpoint01.zip'
result=subprocess.run(['git','-c','core.autocrlf=false','archive','--format=zip','--output',str(raw),sha],capture_output=True)
(out/'raw-archive.stdout.log').write_bytes(result.stdout); (out/'raw-archive.stderr.log').write_bytes(result.stderr)
assert result.returncode==0
with zipfile.ZipFile(raw) as z:
    items=[]
    for entry in filter(None,subprocess.check_output(['git','ls-tree','-r','-z',sha]).split(b'\0')):
        meta,path=entry.split(b'\t',1); mode,kind,oid=meta.split()
        if kind==b'blob': items.append((path.decode('utf-8'),oid))
    batch=subprocess.check_output(['git','cat-file','--batch'],input=b''.join(oid+b'\n' for _,oid in items))
    offset=0; rows=[]; corrections=[]
    failed_paths={r['path'] for r in old['byte_checks'] if not r['passed']}
    for path,oid in items:
        end=batch.index(b'\n',offset); size=int(batch[offset:end].split()[2]); blob=batch[end+1:end+1+size]; offset=end+size+2
        data=z.read(path)
        assert data==blob,path
        rows.append(dict(path=path,sha256=hashlib.sha256(blob).hexdigest(),passed=True))
        if path in failed_paths:
            prev=(root/'tmp/A-D05-archive-replay01'/path).read_bytes()
            assert prev.replace(b'\r\n',b'\n')==blob,path
            assert not path.startswith(('src/','scripts/','tests/','app/','schemas/','benchmarks/','configs/','experiments/','report_materials/'))
            corrections.append(path)
passed=all(c['exit_code']==c['expected_exit'] and c.get('status_found',True) for c in old['commands'])
record=dict(old,passed=passed,byte_checks=rows,raw_archive_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
            archive_correction=dict(initial_failed_record='checkpoint_replay_failed01.json',cause='core.autocrlf=true converted unpinned documentation to CRLF on archive; only newline differences',
                                    corrected_command=['git','-c','core.autocrlf=false','archive','--format=zip','--output',str(raw),sha],
                                    changed_documentation_paths=corrections,product_source_and_data_unchanged=True,
                                    note='Tests/audits executed on first archive; all its product source/data bytes matched checkpoint. Raw archive then verified every Git blob without changing product files. No third full test run required.'))
(out/'checkpoint_replay.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

base='18f08779b0e32f0c91f48827ef0b7d50cb223ad4'
assert subprocess.check_output(['git','remote','get-url','origin'],encoding='utf-8').strip()=='https://github.com/MeaOneill/CodeCompass.git'
assert subprocess.run(['git','merge-base','--is-ancestor',base,sha]).returncode==0
paths=list(filter(None,subprocess.check_output(['git','diff','--name-only','-z',base,sha]).decode().split('\0')))
payload=[]
for p in paths:
    data=subprocess.check_output(['git','show',sha+':'+p])
    assert not re.search(rb'sk-[A-Za-z0-9_-]{24,}',data),p
    assert not re.search(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',data),p
    assert p.startswith(('docs/A/','docs/joint/A-','scripts/A/','experiments/A/A-D05-preflight-20261017-01/','report_materials/A/','CodeCompass计划/tracking/')),p
    already_remote=False
    if p.startswith('docs/A/handoffs/A_账号'):
        assert subprocess.check_output(['git','show','origin/codex/A-account-handoff-20261017:'+p])==data
        already_remote=True
    payload.append(dict(path=p,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),already_on_remote_handoff_branch=already_remote))
review=dict(destination='https://github.com/MeaOneill/CodeCompass.git',
            trust_basis='Exact repository supplied by user in handoff; existing origin and fetched B delivery; not a new destination',
            scope_basis='User requests all pre-A-D05 work; handoff section eight item ten and project daily workflow require task-branch commit/push; no main merge or B push',
            base=base,checkpoint=sha,new_commits=subprocess.check_output(['git','rev-list','--count',base+'..'+sha],encoding='utf-8').strip(),
            files=payload,total_bytes=sum(x['bytes'] for x in payload),
            inspected='New delta only: A-authored task docs, offline logs/audits, public source hashes and metadata. No keys, databases, private answers, environments, or B personal records. Two restored account documents already byte-identical on origin A handoff branch.',
            automatic_approval='First push rejected; no remote write occurred. Verified payload and destination before any retry.')
(out/'publication_review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(committed_replay_passed=passed,exact_blob_checks=len(rows),newline_only_docs=len(corrections),publication_files=len(payload),publication_bytes=review['total_bytes']),ensure_ascii=False))
