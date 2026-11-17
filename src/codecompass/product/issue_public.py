"""Bounded unauthenticated public-page fallback when GitHub REST is unavailable."""
import json
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from urllib.parse import urlsplit


class IssuePage(HTMLParser):
    def __init__(self):super().__init__();self.capture=False;self.parts=[];self.results=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script':self.capture=dict(attrs).get('type')=='application/json';self.parts=[]
    def handle_data(self,data):
        if self.capture:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.capture:
            self.capture=False
            try:
                obj=json.loads(''.join(self.parts))
                payload=obj.get('payload',{}).get('issuesIndexContentRoute')
                if payload is not None:self.results=payload['results'];self.found=True
            except (ValueError,TypeError,KeyError):pass


def parse_page(raw,repository):
    parser=IssuePage();parser.feed(raw.decode('utf-8'));items=[]
    if not getattr(parser,'found',False):raise ValueError('Public issue page format unavailable')
    for row in parser.results:
        if row.get('itemType')!='REPO_ISSUES_DASHBOARD_ITEM_TYPE_ISSUE':continue
        issue=row.get('issue',{});n=issue.get('number');url=f'https://github.com/{repository}/issues/{n}'
        if type(n) is not int or issue.get('permalink')!=url or issue.get('repoNameWithOwner')!=repository:continue
        if issue.get('state') not in ('REPO_ISSUE_STATE_OPEN','REPO_ISSUE_STATE_CLOSED'):continue
        items.append(dict(number=n,title=str(issue.get('title',''))[:300],url=url,body='',labels=[],
                          state='closed' if issue['state']=='REPO_ISSUE_STATE_CLOSED' else 'open'))
    return items


def fetch_page(repository):
    url=f'https://github.com/{repository}/issues?q=is%3Aissue+sort%3Aupdated-desc'
    with urlopen(Request(url,headers={'User-Agent':'CodeCompass-local/1'}),timeout=15) as response:
        final=urlsplit(response.url)
        if final.scheme!='https' or final.hostname!='github.com' or not final.path.startswith('/'+repository+'/issues'):raise ValueError('Unexpected issue redirect')
        raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:raise ValueError('Issue page too large')
    return parse_page(raw,repository)
