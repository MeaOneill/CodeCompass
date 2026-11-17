"""Read-only, cached Issue suggestions for imported repositories, with evidence gaps."""
import json
import re
import threading
import math
import ast
import textwrap
from .repositories import FEATURES,features
from datetime import datetime, timezone
from .repositories import fetch
from .workspaces import stamp
from .issue_public import fetch_page


class SourceIssues:
    def __init__(self,workspaces):
        self.workspaces=workspaces;self.lock=threading.Lock()

    def get(self,uid,route_id,refresh=False):
        route=self.workspaces.route(uid,route_id);state=route['state']
        cache_path=self.workspaces.root/route['repository_id']/'issues.json'
        with self.lock:
            cache=json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else dict(items=[],captured_at=None,attempted_at=None)
            elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(cache['attempted_at'])).total_seconds() if cache.get('attempted_at') else float('inf')
            if refresh and (elapsed>=1800 or cache.get('attempted_version')!=2):
                cache['attempted_at']=stamp()
                cache['attempted_version']=2
                try:
                    rows=[]
                    for page in range(1,4):
                        batch=json.loads(fetch(f"https://api.github.com/repos/{state['repository']}/issues?state=all&per_page=100&sort=updated&page={page}",2*1024*1024))
                        if not isinstance(batch,list):raise ValueError('Unexpected Issue response')
                        rows.extend(batch)
                        if len(batch)<100:break
                    items=[]
                    for r in rows:
                        number=r.get('number')
                        if 'pull_request' in r or r.get('state') not in ('open','closed') or type(number) is not int: continue
                        expected=f"https://github.com/{state['repository']}/issues/{number}"
                        if r.get('html_url')!=expected: continue
                        items.append(dict(number=number,title=str(r.get('title',''))[:300],url=expected,
                                          body=str(r.get('body') or '')[:12000],labels=[str(x.get('name','')) for x in r.get('labels',[])][:20],state=r['state']))
                    cache.update(items=items,captured_at=stamp(),error=None,source='github-rest')
                except Exception:
                    try:cache.update(items=fetch_page(state['repository']),captured_at=stamp(),error=None,source='github-public-page')
                    except Exception:
                        cache['error']=('暂时无法连接 GitHub，以下是上次获取的 Issue。' if cache['items'] else
                                        '暂时无法连接 GitHub，暂未获取到 Issue。请联网后重试。')
                cache_path.write_text(json.dumps(cache,ensure_ascii=False),encoding='utf-8')
        targets=[state['data']['views'][x] for x in state['result']['remaining']+state['completed'] if state['data']['views'][x]['kind'] in ('target','related')]
        terms=set(re.findall('[a-z][a-z0-9_]{2,}',state['goal'].lower()))
        terms.update(v['title'].lower() for v in targets)
        for v in targets:
            terms.update(w for w in re.split(r'[._]+',v['title'].lower()) if len(w)>=4)
        aliases={'文本':('text','string','unicode','slug'),'字符':('character','unicode','symbol'),
                 '替换':('replace','replacement'),'清理':('whitespace','strip','sanitize','clean'),
                 '编码':('encoding','decode','unicode'),'列表':('list','index'),'迭代':('iterator','iterable','yield')}
        for zh,words in aliases.items():
            if zh in state['goal']:terms.update(words)
        terms.difference_update({'issue','issues','github','python','code','source','learn','learning','understand','core','project'})
        suggestions=[]
        gaps=[c for c,g in state['result']['gate'].items() if c.startswith('python.') and not g['mastered']]
        with self.workspaces.store.connect() as db:prefs=self.workspaces.preferences(db,uid)
        assessment=prefs.get('assessment',{}).get('topics',{})
        topic_terms={'python.containers':('list','dict','set','index'),'python.iteration':('iterat','loop','iterable'),
          'python.generators':('generator','yield','lazy'),'python.functions':('function','parameter','argument'),
          'python.classes':('class','instance','object'),'python.exceptions':('exception','error','raise'),
          'python.decorators':('decorator','wrap'),'python.async':('async','await','coroutine')}
        completed_concepts=set();goal_concepts=set(state['data'].get('intent',{}).get('topics',[]))
        for x in state['completed']+state['result']['remaining']:
            try:concepts=set(features(ast.parse(textwrap.dedent(state['data']['views'][x]['code'])).body[0]))
            except (SyntaxError,IndexError,RecursionError):concepts=set()
            goal_concepts.update(concepts)
            if x in state['completed']:completed_concepts.update(concepts)
        for item in cache['items']:
            text=(item['title']+' '+item['body']).lower()
            maintenance=r'\b(?:pip install|licen\w*|release|git tag|manpage|workflow badge|tarball|pypi)'
            if re.search(maintenance,item['title'].lower()) and not re.search(maintenance,state['goal'].lower()) and not any(t in state['goal'] for t in ('安装','发布','许可证','依赖','文档')):continue
            hits=sorted(t for t in terms if t in text)
            paths=sorted({v['path'] for v in targets if v['path'] in text or v['path'].rsplit('/',1)[-1] in text})
            score=len(hits)+2*len(paths)
            required=[c for c,words in topic_terms.items() if any(re.search(r'\b'+w,text) for w in words)]
            topic_matches=set(required)&goal_concepts
            if not score and not topic_matches:continue

            symbol_score=100*(1-math.exp(-len(hits)/2))
            file_score=100*len(paths)/max(1,len({v['path'] for v in targets}))
            concept_score=100*len(set(required)&goal_concepts)/len(required) if required else None
            relevance=(.7*symbol_score+.3*file_score) if concept_score is None else .55*symbol_score+.25*file_score+.2*concept_score
            learning=100*len(set(required)&completed_concepts)/len(required) if required else None
            measured=[assessment[c] for c in required if assessment.get(c,{}).get('answered',0)]
            ability=100*sum(r['correct'] for r in measured)/sum(r['answered'] for r in measured) if measured else None
            components=dict(content=round(relevance),learning=round(learning) if learning is not None else None,ability=round(ability) if ability is not None else None)
            weights=dict(content=.6,learning=.25,ability=.15)
            weight_sum=sum(weights[k] for k,v in components.items() if v is not None)
            match=round(sum(weights[k]*v for k,v in components.items() if v is not None)/weight_sum)
            suggestions.append(dict(number=item['number'],title=item['title'],url=item['url'],labels=item['labels'],score=score,
                                    state=item.get('state','open'),recommendation_kind='practice' if item.get('state','open')=='open' else 'retrospective',
                                    match_percent=match,match_components=components,match_weights={k:round(weights[k]/weight_sum,4) for k,v in components.items() if v is not None},
                                    ability_items=sum(r['answered'] for r in measured),
                                    scoring_version='content-learning-assessment-v1',required_topics=[FEATURES[c] for c in required],
                                    matched_terms=hits,matched_paths=paths,knowledge_gaps=gaps,
                                    reason='关联关键词：'+'、'.join(hits or [FEATURES[c] for c in sorted(topic_matches)]),
                                    preparation=['重新核对 Issue 当前状态与讨论','阅读关联固定版本源码，再比对仓库最新版本','尝试复现问题并阅读贡献说明，决定是否参与']))
        return dict(items=sorted(suggestions,key=lambda x:(x['state']!='open',-x['match_percent'],-x['score'],x['number']))[:5],captured_at=cache['captured_at'],
                    attempted_at=cache['attempted_at'],error=cache.get('error'),
                    candidate_count=len(cache['items']),source=cache.get('source','cached'),
                    notice='优先推荐开放问题；已关闭问题用于历史复盘。',
                    repository_url='https://github.com/'+state['repository']+'/issues',
                    empty_message='当前快照没有可靠关联的 Issue；这不代表该仓库没有 Issue，也不需要为完成路线强行贡献。')
