"""Usability revision must preserve old assets, POST protection and planner output."""
import json
from pathlib import Path
import re
import threading
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import pytest
from scripts.A.cases_d07 import Clock
from scripts.A.relay_d07 import StableRelayCollector
from scripts.A.serve_d07_submission_v1 import make_server,UI_VERSION
ROOT=Path(__file__).resolve().parents[2]

def test_format_ui_does_not_change_planner_or_transport(tmp_path):
    c=StableRelayCollector(ROOT,tmp_path/'ui.db',actor='test_fixture',clock=Clock())
    server=make_server(c,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        html=urlopen(base).read().decode()
        assert html.index('/app.js')<html.index('/submission-v1.js') and '/a07.js' in html
        assert urlopen(base+'/app.js').read()==(ROOT/'app/B_D06_v2/app.js').read_bytes()
        assert urlopen(base+'/a07.js').read()==(ROOT/'app/A_D07/a07.js').read_bytes()
        token=re.search(r'name="session-token" content="([^"]+)"',html).group(1)
        with pytest.raises(HTTPError) as err:
            urlopen(Request(base+'/api/start',data=b'{}'))
        assert err.value.code==403
        view=json.load(urlopen(Request(base+'/api/start',data=json.dumps(dict(task='task_003',method='Ours')).encode(),headers={'X-Session-Token':token,'Content-Type':'application/json'})))
        assert view['submission_ui_version']==UI_VERSION and view['runtime_version']=='A-D07-runtime-v1'
        assert view['route']==['task_003__unique_iter'] and view['spent']==0 and view['actor']=='test_fixture'
        assert urlopen(base+'/submission-v1.js').headers['Content-Type'].startswith('text/javascript')
    finally:server.shutdown();server.server_close();thread.join()
