const $=id=>document.getElementById(id);
let token='',profile=null,busy=false,page='home',assistantMode=null;
const userKey='codecompass-product-user';
function el(tag,text,cls){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
const iconPaths={route:'M4 5h6v6H4z M14 13h6v6h-6z M7 11v6h7 M14 5h6 M17 2v6',user:'M16 7a4 4 0 1 1-8 0a4 4 0 0 1 8 0 M4 21v-2a8 8 0 0 1 16 0v2',book:'M3 4h6a3 3 0 0 1 3 3v14a4 4 0 0 0-4-3H3z M21 4h-6a3 3 0 0 0-3 3v14a4 4 0 0 1 4-3h5z',check:'M5 12l4 4L20 5',arrow:'M4 12h16 M14 6l6 6-6 6',code:'M8 5L2 12l6 7 M16 5l6 7-6 7 M14 3l-4 18',issue:'M12 8v5 M12 17h.01 M21 12a9 9 0 1 1-18 0a9 9 0 0 1 18 0',chart:'M4 20V10 M10 20V4 M16 20v-8 M22 20H1',spark:'M12 2l3 7 7 3-7 3-3 7-3-7-7-3 7-3z',settings:'M4 6h16 M4 12h16 M4 18h16 M8 3v6 M16 9v6 M10 15v6',refresh:'M20 7v5h-5 M4 17v-5h5 M5 7a8 8 0 0 1 13-2l2 2 M19 17a8 8 0 0 1-13 2l-2-2'};
function icon(name='arrow'){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.8');svg.setAttribute('stroke-linecap','round');svg.setAttribute('stroke-linejoin','round');svg.classList.add('ui-icon');const p=document.createElementNS(svg.namespaceURI,'path');p.setAttribute('d',iconPaths[name]||iconPaths.arrow);svg.append(p);return svg;}
function button(text,fn,primary=false){const b=el('button',undefined,primary?'primary':'');const name=/Issue|讨论|实践/.test(text)?'issue':/画像|测评|调查/.test(text)?'user':/规划|路线|范围/.test(text)?'route':/讲解|助手|问题/.test(text)?'spark':/完成|保存|继续/.test(text)?'check':/源码|GitHub/.test(text)?'code':/刷新|重试/.test(text)?'refresh':'arrow';b.append(icon(name),el('span',text));b.onclick=()=>run(fn);return b;}
function notice(text){$('saved').textContent=text;}
async function request(path,data){const timeout=path.includes('assistant')||path==='route'||path.includes('issues')?60000:15000;const r=await fetch('/api/product/'+path,data?{method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':token},body:JSON.stringify(data),signal:AbortSignal.timeout(timeout)}:{signal:AbortSignal.timeout(timeout)});const value=await r.json();if(!value.ok)throw Error(value.error.message);return value.data;}
async function run(fn){if(busy)return;busy=true;$('error').hidden=true;$('retry').hidden=true;$('backTasks').hidden=true;$('loading').hidden=false;document.querySelectorAll('button').forEach(b=>{if(!b.disabled){b.dataset.busy='1';b.disabled=true;}});try{await fn();}catch(e){notice('');$('error').textContent=e.name==='TimeoutError'?'请求超时，请重新连接。':e instanceof TypeError?'无法连接本机服务，请确认服务已启动。':e.message;$('error').hidden=false;$('retry').hidden=false;$('backTasks').hidden=false;}finally{busy=false;$('loading').hidden=true;document.querySelectorAll('[data-busy]').forEach(b=>{b.disabled=false;delete b.dataset.busy;});}}
function clear(title){if(disposeSourceMap){disposeSourceMap();disposeSourceMap=null;}document.body.classList.remove('planning-overview');$('crumb').textContent='CodeCompass / '+title;$('assistantContent').replaceChildren(el('h2','学习助手'),el('p','选择学习步骤后可进行源码问答。'));$('view').replaceChildren(el('h1',title));window.scrollTo({top:0});document.querySelectorAll('[data-page]').forEach(b=>b.classList.toggle('selected',b.dataset.page===page));}
function choices(q,name,value){const f=el('fieldset');f.append(el('legend',q.prompt));if(q.code)f.append(el('pre',q.code));q.choices.forEach((text,i)=>{const label=el('label',undefined,'option');const c=el('input');c.type='radio';c.name=name;c.value=String(i);c.checked=value===i;label.append(c,el('span',text));f.append(label);});return f;}
function picked(name){const e=document.querySelector('input[name="'+name+'"]:checked');return e?Number(e.value):null;}
function external(text,url){const a=el('a',text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
function dateLabel(value){return value?new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',dateStyle:'medium',timeStyle:'short'}).format(new Date(value)):'尚未更新';}
async function home(){return sourceHome();}
function personalPage(kind,description){
 const view=$('view'),screen=el('div',undefined,'personal-page personal-'+kind);
 const head=el('div',undefined,'personal-heading'),titles=el('div');
 titles.append(view.querySelector('h1'),el('p',description));head.append(titles);
 screen.append(head);view.append(screen);return {screen,head};
}

function personalIcon(symbol){
 const badge=el('span',undefined,'personal-icon');
 badge.append(icon(symbol));return badge;
}

async function history(){
 page='history';clear('学习记录');
 if(profile)profile=await request('profile?user='+encodeURIComponent(profile.user_id));
 const {screen,head}=personalPage('history','回顾你在每个开源仓库中的学习路线。');
 const records=profile?.source_routes||[];
 const total=el('span',undefined,'history-count');
 total.append(icon('book'),el('span',`累计学习记录 ${records.length} 条`));head.append(total);
 if(!records.length){
  const empty=el('section',undefined,'history-empty');
  empty.append(personalIcon('book'),el('h2','还没有学习记录'),
   el('p','开始探索一个开源仓库，你的第一次学习经历就会出现在这里。'),
   button('进入学习工作台',sourceHome,true));
  if(!profile)empty.append(button('导入仓库',sourceImport));
  screen.append(empty);return;
 }
 const repositories=new Map((profile.repositories||[]).map(job=>[job.id,job.repository]));
 const timeline=el('ol',undefined,'history-timeline');
 const zone={timeZone:'Asia/Shanghai'};
 const dayFormat=new Intl.DateTimeFormat('zh-CN',{...zone,year:'numeric',month:'long',day:'numeric'});
 const timeFormat=new Intl.DateTimeFormat('zh-CN',{...zone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
 let previousDay;
 for(const record of records){
  const entry=el('li',undefined,'history-entry');
  const time=el('time',undefined,'history-time'),updated=record.updated_at,when=new Date(updated);
  const hasDate=Boolean(updated)&&!Number.isNaN(when.getTime());
  const day=hasDate?dayFormat.format(when):'时间未记录';
  if(hasDate)time.dateTime=updated;
  if(day!==previousDay)time.append(el('strong',day));
  if(hasDate)time.append(el('span',timeFormat.format(when)));
  previousDay=day;
  const card=el('article',undefined,'history-card'),info=el('div');
  const repository=repositories.get(record.repository_id);
  info.append(el('h2',record.goal));
  if(repository)info.append(el('code',repository));
  const open=button('查看学习记录',()=>openSourceRoute(record.id));
  card.append(personalIcon('book'),info,open);entry.append(time,card);timeline.append(entry);
 }
 screen.append(timeline);
}

function localStorageIllustration(){
 const diagram=mapSvg('svg',{viewBox:'0 0 340 270','aria-hidden':'true',focusable:'false'});
 diagram.append(mapSvg('circle',{cx:170,cy:130,r:108,class:'environment-orbit'}),
  mapSvg('circle',{cx:170,cy:130,r:75,class:'environment-orbit'}),
  mapSvg('path',{d:'M80 75 L140 110 M266 82 L200 112 M170 178 V220',class:'environment-link'}));
 for(const [x,y,symbol] of [[80,75,'route'],[266,82,'user'],[170,220,'spark']]){
  const node=mapSvg('g',{transform:`translate(${x} ${y})`});
  node.append(mapSvg('circle',{r:22,class:'environment-node'}));
  const pictogram=icon(symbol);
  pictogram.setAttribute('x','-10');pictogram.setAttribute('y','-10');
  pictogram.setAttribute('width','20');pictogram.setAttribute('height','20');node.append(pictogram);diagram.append(node);
 }
 diagram.append(mapSvg('rect',{x:123,y:95,width:94,height:73,rx:15,class:'environment-device'}),
  mapSvg('rect',{x:138,y:109,width:64,height:39,rx:4,class:'environment-screen'}),
  mapSvg('path',{d:'M158 130l8 7 14-15 M170 149v9 M157 159h26',class:'environment-mark'}));
 return diagram;
}

async function help(){
 page='help';clear('设置');
 const {screen}=personalPage('settings','管理你的学习数据与本地学习环境。');
 const layout=el('section',undefined,'environment-card'),body=el('div',undefined,'environment-body');
 const title=el('div',undefined,'environment-heading'),label=el('div');
 label.append(el('h2','学习与数据'),el('p','你的学习信息保存在本机。'));
 title.append(personalIcon('settings'),label);body.append(title);
 const rows=el('div',undefined,'environment-rows');
 for(const [name,detail,symbol] of [
  ['学习进度','保留源码研读步骤和路线进度。','route'],
  ['能力画像','保留学习调查、基础测评和主题复核。','user'],
  ['对话记录','保留与学习助手的问答记录。','spark'],
 ]){
  const row=el('div',undefined,'environment-row'),info=el('div');
  info.append(el('strong',name),el('p',detail));
  row.append(personalIcon(symbol),info,el('span','本机保存','environment-status'));rows.append(row);
 }
 body.append(rows);
 const actions=el('div',undefined,'personal-actions');
 const reconnect=button('重新连接',init);reconnect.firstElementChild.replaceWith(icon('refresh'));
 actions.append(button('更新能力画像',sourceSurvey,true),reconnect);body.append(actions);
 const figure=el('figure',undefined,'environment-figure');
 figure.append(localStorageIllustration(),el('figcaption','本地学习空间'));
 layout.append(body,figure);screen.append(layout);
}
async function init(){const uid=localStorage.getItem(userKey);const boot=await request('bootstrap'+(uid?'?user='+encodeURIComponent(uid):''));token=boot.token;profile=boot.profile;assistantMode=boot.assistant_mode;sourceAssistantMode='offline';await home();notice(profile?'学习记录已恢复':'');}
document.querySelectorAll('[data-page]').forEach(b=>{b.prepend(icon(({home:'route',profile:'user',history:'book',help:'settings'})[b.dataset.page]));b.onclick=()=>run(({home,profile:sourceProfile,history,help})[b.dataset.page]);});$('retry').onclick=()=>run(init);$('backTasks').textContent='返回工作台';$('backTasks').onclick=()=>run(home);$('assistantToggle').onclick=()=>$('assistant').classList.add('open');$('closeAssistant').onclick=()=>$('assistant').classList.remove('open');$('navToggle').onclick=()=>{const open=document.querySelector('nav').classList.toggle('open');$('navToggle').textContent=open?'收起导航':'展开导航';$('navToggle').setAttribute('aria-expanded',String(open));};run(init);
