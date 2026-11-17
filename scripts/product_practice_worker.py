"""Fixed public checks for trusted local learner code; process isolation is not a security sandbox."""
import argparse,importlib.util,itertools,json,time
from pathlib import Path

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def run(candidate,original):
    m=load(candidate,'candidate');ref=load(original,'reference')
    def same(src,size,**kw):
        assert list(m.windowed_iter(src,size,**kw))==list(ref.windowed_iter(src,size,**kw)),'正常输出与固定源码不一致'
    def ordinary():
        for n in (1,2,3):same([1,2,3,4],n)
    def empty():
        same([],2);same([],2,fill=None)
    def short():
        same([1],3);same([1],3,fill=None)
    def fill():
        same([1,2,3],2);same([1,2,3],2,fill=None);same([1,2,3],2,fill=-1)
    def invalid(values,kind):
        for value in values:
            try:list(m.windowed_iter([1,2],value))
            except Exception as e:
                assert type(e) is kind,'异常类型应为'+kind.__name__;continue
            raise AssertionError('没有拒绝不合法参数 '+repr(value))
    def infinite():
        assert list(itertools.islice(m.windowed_iter(itertools.count(),2),3))==[(0,1),(1,2),(2,3)]
    def wrappers():
        for end in (None,-99):assert m.pairwise([1,2],end=end)==ref.pairwise([1,2],end=end)
        assert m.windowed([1,2,3],2)==ref.windowed([1,2,3],2)
    cases={'ordinary':ordinary,'empty':empty,'short':short,'fill':fill,'bool':lambda:invalid([True,False],TypeError),'types':lambda:invalid(['2',2.0,None],TypeError),'range':lambda:invalid([0,-1],ValueError),'infinite':infinite,'wrappers':wrappers}
    results={}
    for name,fn in cases.items():
        try:fn();results[name]=dict(status='passed',message='通过')
        except AssertionError as e:results[name]=dict(status='failed',message=str(e)[:500])
        except Exception as e:results[name]=dict(status='error',message=type(e).__name__+': '+str(e)[:500])
    return results
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--original',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:result=run(a.candidate,a.original)
    except Exception as e:result={'load':dict(status='error',message=type(e).__name__+': '+str(e)[:500])}
    a.output.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    raise SystemExit(0 if result and all(v['status']=='passed' for v in result.values()) else 1)
