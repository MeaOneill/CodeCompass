import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import pytest
from scripts.B.starter_d07 import starter

ROOT=Path(__file__).resolve().parents[2]

def test_public_starter_keeps_source_and_records_real_failure(tmp_path):
    z=zipfile.ZipFile(io.BytesIO(starter(ROOT,'task_002')))
    assert set(z.namelist())=={'candidate.py','original.py','LICENSE','START_HERE.md','prepare_submission.py','explanation.md','regression_tests.py','source.json'}
    assert z.read('candidate.py')==z.read('original.py')==(ROOT/'benchmarks/sources/boltons/boltons/iterutils.py').read_bytes()
    z.extractall(tmp_path)
    for code in ("print('ok')", "raise RuntimeError('intentional negative case')"):
        (tmp_path/'regression_tests.py').write_text(code,encoding='utf-8')
        r=subprocess.run([sys.executable,'prepare_submission.py'],cwd=tmp_path,capture_output=True,timeout=10)
        assert r.returncode==0
    runs=sorted((tmp_path/'runs').glob('*.json'))
    assert len(runs)==2
    a,b=[json.loads(p.read_text(encoding='utf-8')) for p in runs]
    assert a['exit_code']==0 and b['exit_code']!=0
    assert all(r['elapsed_seconds']>=0 and r['final_grade'] is None for r in [a,b])
    assert (tmp_path/'patch.diff').read_text()==''

def test_starter_rejects_unregistered_or_path_task():
    for task in ('../private','task_001','B07_more_chunked'):
        with pytest.raises(ValueError):starter(ROOT,task)
