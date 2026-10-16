"""Cache lawful primary sources locally; commit only URL/hash/access provenance."""
from pathlib import Path
import subprocess,shutil,json,datetime,hashlib
R=Path(__file__).resolve().parents[2]
SOURCES={
 'KnowLP_html':'https://arxiv.org/html/2506.22303v2',
 'U_GLAD_html':'https://arxiv.org/html/2604.14613v1',
 'GraphCodeBERT_html':'https://arxiv.org/html/2009.08366',
 'code2vec_pdf':'https://arxiv.org/pdf/1803.09473',
 'KnowLP_commit':'https://api.github.com/repos/chanllon/KnowLP/commits/HEAD',
 'GraphCodeBERT_commit':'https://api.github.com/repos/microsoft/CodeBERT/commits/HEAD',
 'code2vec_commit':'https://api.github.com/repos/tech-srl/code2vec/commits/HEAD',
}

def main():
 cache=R/'tmp/A-D02-literature';cache.mkdir(parents=True,exist_ok=True)
 records=[]
 for name,url in SOURCES.items():
  out=cache/(name+('.pdf' if name.endswith('pdf') else '.json' if name.endswith('commit') else '.html'))
  cmd=[shutil.which('curl.exe') or 'curl','--fail','--location','--silent','--show-error','--max-time','45','--proxy','http://127.0.0.1:7890',url,'--output',str(out)]
  p=subprocess.run(cmd,capture_output=True,text=True)
  row={'source_id':name,'url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':p.returncode,'error':p.stderr or None,'cache_path':out.relative_to(R).as_posix(),'redistribution':'local_reference_cache_only_not_in_git'}
  if p.returncode==0:
   data=out.read_bytes();row.update(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
   if name.endswith('commit'):
    obj=json.loads(data);row.update(repository_commit=obj['sha'],commit_html_url=obj['html_url'])
  records.append(row)
  print(name,p.returncode,row.get('repository_commit',''),flush=True)
 dest=R/'docs/references/A-D02-source_provenance.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((json.dumps(records,ensure_ascii=False,indent=2)+'\n').encode())

if __name__=='__main__':main()
