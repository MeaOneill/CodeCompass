"""Single-package delivery and fixed local checks. Never import learner code in HTTP."""
import base64,hashlib,io,json,os,secrets,stat,subprocess,sys,time,zipfile
from pathlib import Path
from scripts.B.starter_d07 import starter as legacy_starter,PREPARE

FILES=('candidate.py','explanation.md','regression_tests.py','patch.diff','commands_and_elapsed.json','manifest.json')
CHECK_VERSION='P02-public-check-20261024-v1'
MAX_ZIP=3*1024*1024;MAX_TOTAL=10*1024*1024

def digest(raw):return hashlib.sha256(raw).hexdigest()
def validate_package(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_ZIP:raise ValueError('提交包不得超过3MB')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries=z.infolist();names=[i.filename for i in entries]
            for i in entries:
                name=i.filename
                if name not in FILES or ':' in name or '\\' in name or '/' in name or name.startswith('.') or stat.S_ISLNK(i.external_attr>>16):raise ValueError('包内含不允许的路径、文件或符号链接：'+name[:80])
                if i.flag_bits&1:raise ValueError('不接收加密提交包')
            if len(names)!=len(set(names)):raise ValueError('提交包包含重复文件')
            missing=set(FILES)-set(names)
            if missing:raise ValueError('提交包缺少文件：'+', '.join(sorted(missing)))
            if sum(i.file_size for i in entries)>MAX_TOTAL:raise ValueError('提交包解压后不得超过10MB')
            data={i.filename:z.read(i) for i in entries}
    except (zipfile.BadZipFile,RuntimeError,NotImplementedError):raise ValueError('无法读取zip提交包')
    try:
        for raw_file in data.values():raw_file.decode('utf-8')
        manifest=json.loads(data['manifest.json'])
        if not isinstance(manifest,dict):raise ValueError('manifest必须为JSON对象')
        if manifest.get('task_id')!='P02_window_fix':raise ValueError('manifest任务不匹配')
        hashes={n:digest(data[n]) for n in FILES if n!='manifest.json'}
        if manifest.get('files')!=hashes:raise ValueError('manifest文件校验不匹配，请重新运行prepare_submission.py')
        if not isinstance(json.loads(data['commands_and_elapsed.json']),dict):raise ValueError('运行记录必须为JSON对象')
    except (UnicodeError,json.JSONDecodeError):raise ValueError('文件需为UTF-8文本，manifest和运行记录需为JSON')
    return data

def starter(root,tid):
    if tid!='P02_window_fix':raise ValueError('这个任务尚无起始包')
    source=zipfile.ZipFile(io.BytesIO(legacy_starter(root,'task_002')))
    contents={n:source.read(n) for n in source.namelist()}
    prepare=PREPARE[:PREPARE.index("print('Recorded actual test run")]
    prepare+="""
import hashlib,zipfile
names=['candidate.py','explanation.md','regression_tests.py','patch.diff','commands_and_elapsed.json']
manifest={'task_id':'P02_window_fix','files':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names}}
(root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(root/'submission.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names+['manifest.json']:z.write(root/name,name)
print('submission.zip 已生成。自己的测试记录不等于平台检查通过。退出码:',result['exit_code'])
"""
    contents['prepare_submission.py']=prepare.encode()
    contents['START_HERE.md']="""# 给窗口函数增加输入检查

candidate.py是未修改的固定源码；original.py为对照，不要修改。
仅修改windowed_iter的输入检查，保留正常窗口、空/短输入、fill省略与None、相关包装函数及无限输入有限前缀行为。
size只接受内置正整数，bool不算；类型不合适抛TypeError，非正整数抛ValueError。

1. 阅读网页的三个单元，在candidate.py中找到目标函数。
2. 修改代码，在explanation.md记下理由，补充regression_tests.py。
3. 在本目录运行 python prepare_submission.py。它运行你自己的测试、保存真实输出、生成patch.diff，并自动打成一个submission.zip。
4. 网页只需选择submission.zip。可填写说明、保存草稿，然后明确点击“运行练习检查”。

平台只运行固定的公开检查；你自己的测试记录单独展示。运行的是本机学习代码子进程，不是用于运行敌意代码的安全沙箱。检查失败可以修改后重试，文字解释只记为已记录。
""".encode()
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name,content in contents.items():z.writestr(name,content)
    return out.getvalue()

class Submissions:
    def __init__(self,service):self.service=service
    def submit(self,sid,rid,revision,package=None,run_checks=False,note='',existing=None):
        from .service import Conflict,dump,now
        if type(run_checks) is not bool or not isinstance(note,str) or len(note)>6000:raise ValueError('检查操作或说明不合法')
        self.service._request(rid,revision,{})
        if package is not None:
            if not isinstance(package,str) or len(package)>MAX_ZIP*4//3+8:raise ValueError('提交包不得超过3MB')
            try:raw=base64.b64decode(package,validate=True)
            except ValueError:raise ValueError('提交包编码不正确')
        else:
            with self.service.store.connect() as db:
                self.service.load(db,sid)
                row=db.execute('SELECT submission_id FROM product_submissions WHERE submission_id=? AND session_id=?',(existing,sid)).fetchone()
                if not row:raise ValueError('请先选择或保存一个提交包')
            raw=(Path(self.service.store.path).parent/'submissions'/row['submission_id']/'package.zip').read_bytes()
        files=validate_package(raw);payload_hash=digest(dump([revision,digest(raw),run_checks,note]).encode())
        with self.service.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');s=self.service.load(db,sid)
            old=db.execute('SELECT * FROM product_submissions WHERE session_id=? AND request_id=?',(sid,rid)).fetchone()
            if old:
                if old['payload_hash']!=payload_hash:raise Conflict('请求编号已用于其他提交',self.service.view(s))
                return dict(submission=json.loads(old['result_json']) if old['result_json'] else dict(submission_id=old['submission_id'],check_status=old['status']),session=self.service.view(s))
            if s['revision']!=revision:raise Conflict('记录已更新，请保留提交包并重试',self.service.view(s))
            if s['read_only'] or s['task_id']!='P02_window_fix' or s['status']!='active' or s['phase']!='practice':raise ValueError('请完成阅读后在动手练习阶段提交')
            subid='sub_'+secrets.token_hex(16)
            db.execute('INSERT INTO product_submissions VALUES(?,?,?,?,?,?,?)',(subid,sid,rid,payload_hash,'running',None,now()))
        folder=Path(self.service.store.path).parent/'submissions'/subid;folder.mkdir(parents=True)
        (folder/'package.zip').write_bytes(raw)
        for name,content in files.items():(folder/name).write_bytes(content)
        result=dict(submission_id=subid,files_saved=True,file_hashes={n:digest(raw_file) for n,raw_file in files.items()},check_version=CHECK_VERSION,check_status='not_run',categories={},exit_code=None,elapsed_seconds=None,output_summary='',explanation_recorded=bool(files['explanation.md'].strip() or note.strip()),note=note,user_test_record=json.loads(files['commands_and_elapsed.json']))
        if run_checks:
            try:result.update(self.check(folder))
            except Exception:result.update(check_status='error',categories={'worker':dict(status='error',message='检查器未能完成，文件已保存，可重试')},output_summary='本次检查启动或结果读取失败，未标为通过。')
        (folder/'result.json').write_text(dump(result),encoding='utf-8')
        with self.service.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');latest=self.service.load(db,sid)
            db.execute('UPDATE product_submissions SET status=?,result_json=? WHERE submission_id=?',(result['check_status'],dump(result),subid))
            if latest['status']=='active' and latest['phase']=='practice' and latest['revision']==revision:
                latest['state']['submission']=result;latest['revision']+=1;latest['updated_at']=now()
                if result['check_status']=='passed':latest['phase']='review';latest['status']='completed'
                self.service.save(db,latest)
            return dict(submission=result,session=self.service.view(latest))
    def check(self,folder):
        original_data=self.service.catalog.source('P02_window_fix')
        original=self.service.root/original_data['source_root']/'boltons/iterutils.py'
        cmd=[sys.executable,'-I',str(self.service.root/'scripts/product_practice_worker.py'),'--candidate',str((folder/'candidate.py').resolve()),'--original',str(original.resolve()),'--output',str((folder/'check.json').resolve())]
        env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP','PATH','PATHEXT','COMSPEC')}
        began=time.perf_counter();process=subprocess.Popen(cmd,cwd=folder,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        status='error'
        try:
            stdout,stderr=process.communicate(timeout=30)
            categories=json.loads((folder/'check.json').read_text(encoding='utf-8')) if (folder/'check.json').exists() else {'worker':dict(status='error',message='检查器没有产生结果')}
            status='passed' if process.returncode==0 and categories and all(v['status']=='passed' for v in categories.values()) else 'failed'
        except subprocess.TimeoutExpired:
            if os.name=='nt':subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
            else:process.kill()
            stdout,stderr=process.communicate();categories={'worker':dict(status='error',message='检查超过30秒，已结束本次检查子进程')};status='timeout'
        (folder/'stdout.log').write_bytes(stdout);(folder/'stderr.log').write_bytes(stderr)
        return dict(check_status=status,categories=categories,exit_code=process.returncode,elapsed_seconds=time.perf_counter()-began,output_summary=(stdout+stderr).decode('utf-8',errors='replace')[-6000:])
    def export(self,sid):
        from .service import dump
        s=self.service.get(sid);out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('learning-record.json',dump(s))
            data=self.service.catalog.source(s['task_id'])
            z.writestr('sources.json',dump(dict(task_id=s['task_id'],repository=data['snapshot']['url'],snapshot_id=data['snapshot']['snapshot_id'],commit=data['snapshot']['commit'],license=data['snapshot']['license'],unit_sources=[dict(unit_id=u['id'],source_spans=u['source_spans']) for u in data['units']],supporting_context=data.get('source_context',[]))))
            with self.service.store.connect() as db:
                answers=[json.loads(r[0]) for r in db.execute('SELECT value_json FROM product_answers WHERE session_id=? ORDER BY seq',(sid,))]
            z.writestr('answers.json',dump(answers))
            z.writestr('assistant.json',dump(self.service.assistant.history(sid)['messages']))
            z.writestr('README.txt','本机学习成果。公开练习检查不是正式研究成绩；阅读覆盖不等于全部知识掌握。')
            sub=s['state'].get('submission')
            if sub:
                folder=Path(self.service.store.path).parent/'submissions'/sub['submission_id']
                for name in (*FILES,'result.json'):
                    if (folder/name).is_file():z.write(folder/name,'submission/'+name)
        return out.getvalue()
