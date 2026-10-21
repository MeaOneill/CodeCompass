import contextlib,hashlib,io,json
from pathlib import Path
p=Path('C:/CodeCompass/CodeCompass-A-D05/benchmarks/dev/A_D07_v3/bank.json')
b=json.loads(p.read_text(encoding='utf-8')); rows=[]
for item in b['items']:
    captured=io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):exec(compile(item['code'],item['item_id'],'exec'),{})
        actual=captured.getvalue().strip(); error=None
    except Exception as exc:actual=captured.getvalue().strip();error=type(exc).__name__+': '+str(exc)
    rows.append(dict(item_id=item['item_id'],code_repr=repr(item['code']),actual=actual,error=error,expected=item['oracle_output'],answer=item['answer'],answer_text=item['choices'][item['answer']],passed=error is None and actual==item['oracle_output'] and item['choices'].count(actual)==1 and item['choices'][item['answer']]==actual))
result=dict(hash=hashlib.sha256(p.read_bytes()).hexdigest(),expected_hash=p.with_suffix('.sha256').read_text().strip(),rows=rows)
Path('tmp/independent-audit/bank-oracle.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
raise SystemExit(0 if all(r['passed'] for r in rows) else 1)
