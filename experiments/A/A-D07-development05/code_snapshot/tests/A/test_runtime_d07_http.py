"""Opt-in UI uses the validated collector and preserves HTTP access boundaries."""
import json
from pathlib import Path
import re
import threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError

import pytest

from scripts.A.relay_d07 import StableRelayCollector
from scripts.A.serve_d07 import make_server
from scripts.A.cases_d07 import Clock

ROOT=Path(__file__).resolve().parents[2]


def test_versioned_page_and_source_reason_api(tmp_path):
    collector=StableRelayCollector(ROOT,tmp_path/'db',actor='test_fixture',clock=Clock())
    server=make_server(collector,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        html=urlopen(base+'/').read().decode('utf-8')
        assert 'A-D07 · 开发烟雾与预演候选' in html and '/a07.js' in html and '/a07.css' in html
        assert 'minmax(0,1fr)' in urlopen(base+'/a07.css').read().decode()
        token=re.search(r'name="session-token" content="([^"]+)"',html).group(1)
        with pytest.raises(HTTPError) as err:
            urlopen(Request(base+'/api/start',data=b'{}',headers={'Content-Type':'application/json'}))
        assert err.value.code==403
        response=json.load(urlopen(Request(base+'/api/start',data=json.dumps(dict(task='task_001',method='Ours')).encode(),
            headers={'Content-Type':'application/json','X-Session-Token':token})))
        assert response['runtime_version']=='A-D07-runtime-v1' and response['actor']=='test_fixture'
        assert len(response['route_explanations'])==len(response['route'])
        assert all(row['base_proxy_cost']>0 and row['source_versions'][0]['commit']==response['task']['repo_commit']
                   for row in response['route_explanations'])
    finally:
        server.shutdown();server.server_close();thread.join()
