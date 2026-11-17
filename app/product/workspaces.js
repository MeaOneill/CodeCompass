                                                                                
const sourceRouteKey='codecompass-source-route';
const sourceFeatures={'python.functions':'函数与参数','python.iteration':'循环与推导式','python.generators':'生成器与惰性求值','python.classes':'类与对象','python.exceptions':'异常处理','python.containers':'容器与索引','python.decorators':'装饰器','python.async':'异步调用'};
const sourceHints={'python.functions':'先找输入参数、默认值和 return，再用一个小输入手动走读。','python.iteration':'追踪每轮循环中变量如何改变，检查空输入和停止条件。','python.generators':'找到 yield，区分创建生成器与实际取出下一个值。','python.classes':'先看实例保存什么状态，再看方法如何读取或修改它。','python.exceptions':'分别追踪正常分支、raise 和 except；判断哪些错误会向外传播。','python.containers':'标出容器保存什么，检查索引、键和边界条件。','python.decorators':'先找被包装函数，再追踪调用前后的附加行为。','python.async':'找到 await，区分声明协程与真正等待执行。'};
let sourceRoute=null,repositoryJob=null,sourceGoal='';
let sourceAssistantUnit=null,sourceAssistantMode='offline',sourceAssistantDraft='',sourceAskRetry=null;
function field(label,input){const row=el('label',undefined,'source-field');row.append(el('span',label),input);return row;}
function input(type,value=''){const node=el('input');node.type=type;node.value=value;return node;}
async function ensureLearner(){if(!profile){profile=await request('profile',{});localStorage.setItem(userKey,profile.user_id);}return profile;}
async function sourceHome(){
 repositoryJob=null;
 page='home';clear('学习工作台');
 if(profile)profile=await request('profile?user='+encodeURIComponent(profile.user_id));
 $('assistant').classList.remove('open');
 const view=$('view');
 const hasProfile=Boolean(profile?.preferences?.onboarding);
 const repositories=profile?.repositories||[];
 const routes=profile?.source_routes||[];
 const ready=repositories.filter(row=>row.status==='ready');
 const importRepository=async()=>{
  await ensureLearner();
  if(!profile.preferences.onboarding)await sourceSurvey();else await sourceImport();
 };

 const intro=el('article',undefined,'workspace-hero homepage-hero');
 const copy=el('div',undefined,'homepage-hero-copy');
 const headline=el('h2');
 headline.append(el('span','从学习目标出发，'),el('wbr'),el('span','读懂开源源码'));
 copy.append(el('span','OPEN-SOURCE LEARNING WORKSPACE','homepage-eyebrow'),
             headline,
             el('p','先找到相关实现，再按适合你的顺序理解调用关系和关键分支。'));
 const actions=el('div',undefined,'actions');
 if(ready.length===1)actions.append(button('开始规划学习路线',()=>sourceRepository(ready[0].id),true));
 actions.append(button(hasProfile?'导入自己的仓库':'建立我的能力画像',importRepository,ready.length!==1));
 if(hasProfile)actions.append(button('更新能力画像',sourceSurvey));
 copy.append(actions);intro.append(copy,homepageIllustration());view.append(intro);

 const progress=el('ol',undefined,'homepage-progress');progress.setAttribute('aria-label','源码学习进度');
 const passed=[hasProfile,ready.length>0,routes.length>0];
 const current=passed.indexOf(false);
 for(const [i,[label,glyph]] of [['建立能力画像','user'],['导入仓库','code'],['生成学习路线','route']].entries()){
  const step=el('li',undefined,passed[i]?'done':i===current?'current':'');
  if(i===current)step.setAttribute('aria-current','step');
  const mark=el('span',undefined,'homepage-step-icon');mark.append(icon(passed[i]?'check':glyph));
  step.append(mark,el('span',label));progress.append(step);
 }
 view.append(progress);
 const m=profile?.metrics;
 const stage=m?.learning.readings?m.learning.stage:m?.experience||'待建立';
 const score=m?.score??null;
 const stats=el('div',undefined,'metrics homepage-stats');
 const stageCard=metricCard('学习阶段',stage);
 const roadmapCard=metricCard('学习路线',routes.length+' 条');
 for(const [card,glyph] of [[stageCard,'chart'],[roadmapCard,'route']]){
  const badge=el('span',undefined,'homepage-stat-icon');badge.append(icon(glyph));card.prepend(badge);
 }
 const assessment=metricCard('基础测评正确率',score===null?'待测评':score+'%',(m?.correct??0)+' / '+(m?.answered??0)+' 题');
 const ring=el('span',undefined,'homepage-ring');ring.setAttribute('aria-hidden','true');
 const arc=mapSvg('svg',{viewBox:'0 0 48 48'});
 arc.append(mapSvg('circle',{cx:24,cy:24,r:19,class:'homepage-ring-track'}));
 if(score!==null)arc.append(mapSvg('circle',{cx:24,cy:24,r:19,pathLength:100,'stroke-dasharray':score+' 100',
                                            transform:'rotate(-90 24 24)',class:'homepage-ring-fill'}));
 ring.append(arc);if(score===null)ring.append(el('span','–'));assessment.prepend(ring);
 stats.append(stageCard,assessment,roadmapCard);view.append(stats);
 const group=el('section',undefined,'homepage-library');
 group.append(el('h2',repositories.length?'已导入的仓库':'仓库'));
 if(!repositories.length){
  const empty=el('div',undefined,'homepage-empty');
  const glyph=el('span',undefined,'homepage-stat-icon');glyph.append(icon('code'));
  const text=el('div');text.append(el('strong','还没有导入仓库'),
   el('p',hasProfile?'导入公开 Python 仓库后，即可选定源码和学习目标。':'建立能力画像后，就可以导入公开 Python 仓库。'));
  empty.append(glyph,text);group.append(empty);
 }
 const statuses={ready:'可规划',importing:'分析中',failed:'导入失败',interrupted:'需要重试'};
 for(const row of repositories.slice(0,12)){
  const item=el('div',undefined,'homepage-library-row');
  const name=el('span',row.repository);
  const status=el('span',statuses[row.status]||row.status,'homepage-status');
  if(row.status==='ready')status.classList.add('ready');
  const action=button(row.status==='ready'?'规划路线':'查看状态',()=>sourceRepository(row.id));
  action.setAttribute('aria-label',(row.status==='ready'?'规划路线':'查看状态')+' · '+row.repository);
  item.append(name,status,action);group.append(item);
 }
 view.append(group);
 if(routes.length){
  const history=el('section',undefined,'homepage-library');
  history.append(el('h2','进行中的学习路线'));
  for(const row of routes.slice(0,12)){
   const item=el('div',undefined,'homepage-library-row');
   item.append(el('span',row.goal),button('打开路线',()=>openSourceRoute(row.id)));history.append(item);
  }
  view.append(history);
 }
}

function homepageIllustration(){
 const s=mapSvg('svg',{viewBox:'0 0 420 246','aria-hidden':'true',class:'homepage-illustration'});
 s.append(
  mapSvg('path',{d:'M13 198 C92 177 85 54 186 39 S302 115 403 63 M34 223 C133 218 119 99 220 85 S315 156 393 133',
                 fill:'none',stroke:'#c5e3d3','stroke-width':1.4,'stroke-dasharray':'4 6'}),
  mapSvg('rect',{x:54,y:36,width:263,height:161,rx:15,fill:'#c5e5d6',opacity:.5}),
  mapSvg('rect',{x:43,y:25,width:263,height:161,rx:15,fill:'#ffffff',stroke:'#b9d9cb'}),
  mapSvg('path',{d:'M44 62H305',stroke:'#e0eee6'}));
 for(const [x,fill] of [[60,'#a8ceb9'],[70,'#c2dccd'],[80,'#d4e8df']])s.append(mapSvg('circle',{cx:x,cy:44,r:2.6,fill}));
 for(const [x,y,w,fill] of [[65,83,58,'#72b59b'],[132,83,87,'#b9cfdc'],[87,105,91,'#94c7b3'],[87,126,137,'#cadce5'],
                           [103,146,75,'#82bca5'],[65,165,37,'#c5d9e4']]){
  s.append(mapSvg('rect',{x,y,width:w,height:5,rx:2.5,fill}));
 }
 s.append(
  mapSvg('path',{d:'M261 112 H324 V91 H363 M324 112 V160 H368 M324 160 V199 H250',
                 fill:'none',stroke:'#65a98e','stroke-width':2,'stroke-linecap':'round','stroke-linejoin':'round'}),
  mapSvg('rect',{x:248,y:100,width:26,height:25,rx:6,fill:'#edf8f2',stroke:'#8bc1a8'}),
  mapSvg('path',{d:'M257 108l-4 4 4 4m8-8 4 4-4 4',fill:'none',stroke:'#418970','stroke-width':1.4}),
  mapSvg('rect',{x:347,y:76,width:53,height:30,rx:7,fill:'#edf8f2',stroke:'#8bc1a8'}),
  mapSvg('path',{d:'M358 91h9m5 0h17',stroke:'#6eac95','stroke-width':2.4,'stroke-linecap':'round'}),
  mapSvg('rect',{x:347,y:146,width:53,height:32,rx:7,fill:'#fff',stroke:'#a5ccbb'}),
  mapSvg('path',{d:'M359 158h28m-28 7h19',stroke:'#94b9ac','stroke-width':2.4,'stroke-linecap':'round'}),
  mapSvg('rect',{x:210,y:188,width:58,height:28,rx:7,fill:'#e6f5ee',stroke:'#92c4ad'}),
  mapSvg('path',{d:'M221 202l4 4 7-8m7 4h17',fill:'none',stroke:'#609e86','stroke-width':1.8,'stroke-linecap':'round'})
 );
 return s;
}
function guidedSteps(phases,stage,label){
 const steps=el('ol',undefined,'profile-flow-steps');steps.setAttribute('aria-label',label);
 const current=phases.findIndex(([id])=>id===stage);
 for(const [i,[,label]] of phases.entries()){
  const step=el('li',undefined,i<current?'done':i===current?'current':undefined);
  if(i===current)step.setAttribute('aria-current','step');
  const marker=el('span',undefined,'profile-flow-marker');
  marker.setAttribute('aria-hidden','true');
  if(i<current)marker.append(icon('check'));else marker.textContent=String(i+1);
  step.append(marker,el('span',label));steps.append(step);
 }
 return steps;
}
function profileFlow(stage){
 const flow=el('div',undefined,'profile-flow');flow.dataset.stage=stage;
 const phases=[['survey','信息填写'],['assessment','基础测评'],['result','测评结果']];
 flow.append(guidedSteps(phases,stage,'能力画像流程'));$('view').append(flow);
 return flow;
}

async function sourceSurvey(){
 await ensureLearner();page='profile';clear('能力画像');
 const flow=profileFlow('survey'),card=el('article',undefined,'profile-flow-panel');
 const old=profile.preferences.onboarding||{};
 card.append(el('p','填写你的 Python 学习经历，系统将据此安排后续源码学习。','profile-flow-intro'));
 const experience=el('select');
 for(const [value,label] of [['new','初学者'],['some','有实践经验'],['comfortable','较熟练']])experience.append(new Option(label,value));
 experience.value=old.experience||'new';
 const months=el('select');
 for(const [value,label] of [['0','尚未开始'],['1-6','不到半年'],['6-24','半年至两年'],['24+','两年以上']])months.append(new Option(label,value));
 months.value=old.months||'0';
 const fields=el('div',undefined,'profile-flow-fields');
 fields.append(field('Python 使用经验',experience),field('学习时长',months));card.append(fields);
 const familiarity=el('fieldset',undefined,'profile-topic-group');
 familiarity.append(el('legend','熟悉的知识主题'));
 const grid=el('div',undefined,'profile-topic-grid');
 const checks=[];
 for(const [key,label] of Object.entries(sourceFeatures)){
  const option=input('checkbox');option.checked=(old.familiar||[]).includes(key);checks.push([key,option]);
  const choice=el('label',undefined,'option');choice.append(option,el('span',label));grid.append(choice);
 }
 familiarity.append(grid);card.append(familiarity);
 const actions=el('div',undefined,'actions profile-flow-actions');
 actions.append(button('进入基础测评',async()=>{
  profile=await request('onboarding',{user_id:profile.user_id,revision:profile.preferences.revision||0,
   value:{experience:experience.value,months:months.value,familiar:checks.filter(([,option])=>option.checked).map(([key])=>key)}});
  await sourceAssessment();
 },true),button('返回',sourceHome));
 card.append(actions);flow.append(card);
}

async function sourceAssessment(){
 const attempt=await request('assessment',{user_id:profile.user_id});
 clear('基础测评');
 const flow=profileFlow('assessment'),questions=el('div',undefined,'profile-question-list');
 const heading=el('div',undefined,'profile-assessment-summary');
 heading.append(el('p','请选择代码运行结果。遇到暂时不会的题目，可以选择「暂不了解」。','profile-flow-intro'));
 const progress=el('progress');progress.setAttribute('aria-labelledby','profile-assessment-progress');
 progress.max=attempt.questions.length||1;
 const count=el('span');count.id='profile-assessment-progress';
 const progressLabel=el('div',undefined,'profile-assessment-count');
 progressLabel.append(el('strong','测评进度'),count);heading.append(progressLabel,progress);

 function answers(){return attempt.questions.map((_,i)=>{const value=picked('entry'+i);return Number.isInteger(value)?value:null;});}
 function updateProgress(){
  const answered=answers().filter(value=>value!==null).length;
  progress.value=answered;
  count.textContent='已作答 '+answered+' / '+attempt.questions.length+' 题';
 }
 attempt.questions.forEach((q,i)=>{
  const group=choices(q,'entry'+i,null);
  const legend=group.querySelector('legend');
  const number=el('span','第 '+(i+1)+' 题','profile-question-number');
  legend.prepend(number);
  const unknown=input('radio','unknown');unknown.name='entry'+i;unknown.checked=true;
  const choice=el('label',undefined,'option profile-question-unknown');
  choice.append(unknown,el('span','暂不了解'));group.append(choice);
  const card=el('article',undefined,'profile-flow-panel profile-question-card');
  card.append(group);questions.append(card);
 });
 questions.addEventListener('change',updateProgress);
 const actions=el('div',undefined,'actions profile-flow-actions');
 actions.append(button('保存结果，开始规划',async()=>{
  const result=await request('assessment',{user_id:profile.user_id,attempt_id:attempt.id,answers:answers()});
  profile=await request('profile?user='+encodeURIComponent(profile.user_id));
  notice('学习画像已保存');
  sourceAssessmentResult(result);
 },true),button('跳过测评',sourceImport));
 flow.append(heading,questions,actions);
 updateProgress();
}

function sourceAssessmentResult(result){
 clear('测评结果');
 const flow=profileFlow('result');
 const {answered,total,correct,topics}=result.summary;
 const summary=el('article',undefined,'profile-flow-panel profile-result-summary');
 summary.append(el('h2','已作答 '+answered+' / '+total+' 题'));
 summary.append(el('p',answered?'答对 '+correct+' / '+answered+' 题':'本次未作答，已保存填写的学习经历。'));
 const group=el('section',undefined,'profile-flow-panel profile-result-topics');
 group.append(el('h2','知识主题建议'));
 const list=el('ul',undefined,'profile-result-list');
 for(const [key,row] of Object.entries(topics)){
  const [text,tone]=row.answered===0?['学习时逐步了解','neutral']:
   row.correct<row.answered?['建议先巩固基础','review']:['可以结合源码继续深入','continue'];
  const item=el('li');
  item.append(el('strong',sourceFeatures[key]||key),el('span',text,'profile-result-pill '+tone));list.append(item);
 }
 group.append(list);
 const detail=el('section',undefined,'profile-flow-panel profile-result-detail');
 detail.id='profile-result-detail';detail.hidden=true;detail.tabIndex=-1;
 detail.append(el('h2','答题解析'));
 const explanations=el('ol',undefined,'profile-result-explanations');
 for(const row of result.feedback){
  const item=el('li');
  item.append(el('strong',row.correct===null?'暂不了解':row.correct?'回答正确':'回答有误'),el('p',row.explanation));
  explanations.append(item);
 }
 detail.append(explanations);
 const actions=el('div',undefined,'actions profile-flow-actions');
 const review=button('查看答题解析',()=>{
  detail.hidden=false;review.setAttribute('aria-expanded','true');detail.focus();
 });
 review.setAttribute('aria-controls',detail.id);review.setAttribute('aria-expanded','false');
 actions.append(button('导入仓库',sourceImport,true),review);
 flow.append(summary,group,actions,detail);
}
function repositoryFlow(stage){
 const flow=el('div',undefined,'repository-flow');flow.dataset.stage=stage;
 const phases=[['import','导入仓库'],['analysis','分析源码'],['goal','设置学习目标']];
 flow.append(guidedSteps(phases,stage,'仓库学习流程'));
 $('view').append(flow);return flow;
}
function repositoryHeading(glyph,title,description){
 const head=el('div',undefined,'repository-heading');
 const mark=el('span',undefined,'repository-mark');mark.append(icon(glyph));
 const text=el('div');text.append(el('h2',title));
 if(description)text.append(el('p',description));
 head.append(mark,text);return head;
}

async function sourceImport(){
 page='home';repositoryJob=null;clearTimeout(repositoryRefreshTimer);
 if(!profile?.preferences?.onboarding)return sourceSurvey();
 clear('导入仓库');
 const flow=repositoryFlow('import'),card=el('article',undefined,'repository-card repository-import-card');
 const head=repositoryHeading('code','连接 GitHub 仓库','输入公开 Python 仓库的地址，开始分析源码。');
 const artwork=el('div',undefined,'repository-artwork');artwork.setAttribute('aria-hidden','true');
 artwork.append(icon('code'),icon('route'),icon('book'));head.append(artwork);card.append(head);
 const form=el('div',undefined,'repository-import-form'),url=input('url');
 url.placeholder='https://github.com/作者/仓库';url.maxLength=200;
 const hint=el('p','例如：https://github.com/pallets/itsdangerous','repository-hint');
 hint.id='repository-url-hint';
 const error=el('p',undefined,'repository-field-error');error.id='repository-url-error';error.setAttribute('role','alert');error.hidden=true;
 url.setAttribute('aria-describedby',hint.id);
 url.oninput=()=>{url.removeAttribute('aria-invalid');url.setAttribute('aria-describedby',hint.id);error.hidden=true;};
 const actions=el('div',undefined,'actions repository-actions');
 actions.append(button('导入并分析源码',async()=>{
  let job;
  try{
   job=await request('repository',{user_id:profile.user_id,url:url.value,request_id:crypto.randomUUID()});
  }catch(e){
   if(e instanceof TypeError||e.name==='TimeoutError')throw e;
   error.textContent=e.message;error.hidden=false;
   url.setAttribute('aria-invalid','true');url.setAttribute('aria-describedby',hint.id+' '+error.id);url.focus();return;
  }
  await sourceRepository(job.id);
 },true),button('返回我的路线',sourceHome));
 form.append(field('GitHub 仓库链接',url),hint,error,actions);
 card.append(form);flow.append(card);
}

let repositoryRefreshTimer;
async function sourceRepository(id){
 clearTimeout(repositoryRefreshTimer);
 const job=await request('repository?user='+encodeURIComponent(profile.user_id)+'&id='+encodeURIComponent(id));
 repositoryJob=job;
 if(job.status==='importing'){
  let flow=$('view').querySelector('.repository-flow[data-stage="analysis"]');
  if(flow?.dataset.repositoryId!==id){
   clear(job.repository);flow=repositoryFlow('analysis');flow.dataset.repositoryId=id;
   const card=el('article',undefined,'repository-card repository-analysis-card');
   const label=repositoryHeading('refresh','正在分析仓库');
   const status=el('p',job.message,'repository-analysis-message');
   status.setAttribute('role','status');
   const progress=el('progress',undefined,'repository-progress');progress.setAttribute('aria-label','正在分析源码');
   const actions=el('div',undefined,'actions repository-actions');
   actions.append(button('刷新分析进度',()=>sourceRepository(id),true),button('返回，稍后继续',sourceHome));
   card.append(label,status,progress,actions);flow.append(card);
  }else{
   const status=flow.querySelector('.repository-analysis-message');
   if(status.textContent!==job.message)status.textContent=job.message;
  }
  const refresh=()=>{
   if(!flow.isConnected||repositoryJob?.id!==id)return;
   if(busy||document.visibilityState!=='visible'){repositoryRefreshTimer=setTimeout(refresh,2500);return;}
   run(()=>sourceRepository(id));
  };
  repositoryRefreshTimer=setTimeout(refresh,2500);return;
 }

 clear(job.repository);
 if(job.status!=='ready'){
  const flow=repositoryFlow('analysis'),card=el('article',undefined,'repository-card');
  const message=el('p',job.message,'repository-analysis-message');message.setAttribute('role','status');
  const actions=el('div',undefined,'actions repository-actions');
  actions.append(button('重新导入',sourceImport,true),button('返回',sourceHome));
  card.append(repositoryHeading('issue',job.status==='interrupted'?'分析已中断':'仓库导入未完成'),message,actions);
  flow.append(card);return;
 }

 const flow=repositoryFlow('goal'),overview=el('section',undefined,'repository-overview');
 const facts=el('div',undefined,'repository-facts');
 const parseErrors=job.parse_manifest.filter(file=>file.status==='parse_error');
 const summary=repositoryHeading('check','分析完成');
 summary.classList.add('repository-status-head');
 const parsed=metricCard('已解析源码文件',job.snapshot.files.length-parseErrors.length+' 个');
 const mode=metricCard('分析方式','只读静态分析');
 facts.append(parsed,mode);
 overview.append(summary,facts);
 if(job.license_status_label)overview.append(el('p',job.license_status_label,'repository-hint'));
 if(job.import_mode==='cached')overview.append(el('p','已载入本机保存的源码版本。','repository-hint'));
 if(parseErrors.length)overview.append(el('p',parseErrors.length+' 个文件语法解析失败，不参与符号定位；其余文件仍可选择。','repository-hint'));
 flow.append(overview);

 const card=el('article',undefined,'repository-card repository-goal-card');
 card.append(repositoryHeading('route','设置你的学习目标','你想先读懂哪一部分源码？'));
 const goal=el('textarea');goal.value=sourceGoal;goal.placeholder='例如：理解项目的核心流程，或描述需要学习的功能';goal.maxLength=500;
 card.append(field('学习目标',goal));
 const quick=el('div',undefined,'repository-quick');
 for(const [label,text,description] of [
  ['核心流程','学习这个仓库的核心内容','优先理解项目主要执行流程'],
  ['完整学习','完整学习这个仓库','了解仓库的整体结构与功能']
 ]){
  const action=button(label,()=>{goal.value=text;});
  action.setAttribute('aria-label',label);
  const title=action.querySelector('span');
  const copy=el('span',undefined,'repository-quick-copy');
  title.replaceWith(copy);copy.append(title,el('small',description));quick.append(action);
 }
 card.append(quick);

 const search=input('search');search.placeholder='搜索文件路径、函数或类名';
 const list=el('div',undefined,'repository-symbol-list'),selection=new Set();
 const count=el('p','尚未指定源码目标','repository-hint');
 let planRequestId=crypto.randomUUID(),planPayload='';
 const matching=()=>job.symbols.filter(s=>!s.test_source&&(s.path+' '+s.name+' '+s.doc).toLowerCase().includes(search.value.toLowerCase()));
 const updateCount=()=>{count.textContent=selection.size?'已选择 '+selection.size+' 项':'按学习目标自动选择';};
 function show(){
  list.replaceChildren();const matches=matching();
  for(const s of matches.slice(0,100)){
   const option=input('checkbox');option.checked=selection.has(s.id);
   option.onchange=()=>{if(option.checked)selection.add(s.id);else selection.delete(s.id);updateCount();};
   const label=el('label',undefined,'option');label.append(option,el('span',s.path+' · '+s.name));list.append(label);
  }
  updateCount();
  if(matches.length>100)list.append(el('p','搜索可查看其余 '+(matches.length-100)+' 项。'));
 }
 search.oninput=show;show();
 const advanced=el('details',undefined,'repository-range');
 const controls=el('div',undefined,'actions repository-range-actions');
 controls.append(button('全选当前结果',()=>{matching().forEach(s=>selection.add(s.id));show();}),
                 button('清空选择',()=>{selection.clear();show();}));
 advanced.append(el('summary','自选学习范围'),field('搜索源码',search),controls,count,list);
 card.append(advanced);
 const clarification=el('p',undefined,'repository-field-error');clarification.setAttribute('role','status');
 const actions=el('div',undefined,'actions repository-actions');
 actions.append(button('生成学习路线',async()=>{
  sourceGoal=goal.value;
  const body={user_id:profile.user_id,repository_id:id,goal:goal.value,selected:[...selection],budget:null};
  const payload=JSON.stringify(body);
  if(planPayload&&payload!==planPayload)planRequestId=crypto.randomUUID();
  planPayload=payload;
  const value=await request('route',{...body,request_id:planRequestId});
  if(value.needs_selection){clarification.textContent=value.message;return;}
  sourceRoute=value;localStorage.setItem(sourceRouteKey,value.id);await sourceRouteView();
 },true),button('返回',sourceHome));
 card.append(clarification,actions);flow.append(card);
}

async function openSourceRoute(id){sourceRoute=await request('route?user='+encodeURIComponent(profile.user_id)+'&id='+encodeURIComponent(id));localStorage.setItem(sourceRouteKey,id);await sourceRouteView();}
async function sourceFeedback(action,unit){const route=sourceRoute;sourceRoute=await request('route-feedback',{user_id:profile.user_id,route_id:route.id,revision:route.revision,request_id:crypto.randomUUID(),action,unit_id:unit});notice('反馈和路线已保存');await sourceRouteView();}
async function sourceRouteView(){
 const r=sourceRoute;const s=r.state;const p=s.result;clear('你的学习路线');$('view').append(el('h2',s.goal),el('p',s.repository));
 const overview=el('article');overview.append(el('h3',p.status==='FEASIBLE'?(p.remaining.length?'学习安排已就绪':'本次学习已完成'):'需要调整学习安排'),el('p',`已完成 ${s.completed.length} 步 · 接下来 ${p.remaining.length} 步`));
 if(s.data.self_report_familiar.length)overview.append(el('p','根据你的自述，减少这些基础讲解：'+s.data.self_report_familiar.map(c=>sourceFeatures[c]||c).join('、')));
 if(r.profile_changed)overview.append(el('p','你的画像已有新变化，可重新规划。'));
 if(s.planning_error)overview.append(el('p',s.planning_error));
 if(p.status!=='FEASIBLE')overview.append(el('p','可返回仓库，增大学习范围或缩小目标后重新生成；当前记录保留。'));
 overview.append(button('根据最新画像重新规划',()=>sourceFeedback('replan')),button('重新选择目标或范围',()=>sourceRepository(r.repository_id)),button('看看关联的公开 Issue',()=>sourceIssues(false)),button('返回我的路线',sourceHome));$('view').append(overview);
 if(s.completed.length){const done=el('details');done.append(el('summary','已完成的步骤'));s.completed.forEach(id=>done.append(el('p',s.data.views[id].path+' · '+s.data.views[id].title.replace('基础例子 · ','基础研读 · '))));$('view').append(done);}
 p.remaining.forEach((id,i)=>{const v=s.data.views[id];const card=el('article');card.append(el('span',`${i+1} · ${({foundation:'补充基础',related:'关联实现',target:'目标源码'})[v.kind]}`,'badge'),el('h3',v.title),el('p',`${v.path} · 第 ${v.span.start_line}–${v.span.end_line} 行`),external('到GitHub查看',v.url));
  v.concepts.forEach(c=>{if(sourceHints[c])card.append(el('p',sourceFeatures[c]+'：'+sourceHints[c]));});
  const details=el('details');details.open=i===0;details.append(el('summary','阅读源码'),el('pre',v.code));card.append(details);
  card.append(button('问助手：这段源码',async()=>{sourceAssistantUnit=id;await renderSourceAssistant();$('assistant').classList.add('open');}));
  if(i===0&&p.status==='FEASIBLE'&&!s.planning_error){card.append(button('读完这一步，继续',()=>sourceFeedback('read',id),true));} $('view').append(card);
 });
 await renderSourceAssistant();
}
async function renderSourceAssistant(){
 const s=sourceRoute.state;const ids=[...s.result.remaining,...s.completed];
 if(!ids.includes(sourceAssistantUnit))sourceAssistantUnit=ids[0];
 const target=$('assistantContent'),studio=$('view').querySelector('.reading-studio');
 if(studio){
  const head=el('div',undefined,'reading-assistant-head'),symbol=el('span',undefined,'reading-assistant-icon');
  symbol.append(icon('spark'));
  head.append(symbol,el('h2','源码学习助手'));target.replaceChildren(head);
 }else target.replaceChildren(el('h2','✧ 源码学习助手'));
 if(!sourceAssistantUnit){target.append(el('p','生成学习路线后可进行源码问答。'));return;}
 const history=await request('source-assistant?user='+encodeURIComponent(profile.user_id)+'&route='+encodeURIComponent(sourceRoute.id));
 if(studio)target.append(el('p','围绕所选步骤提问','reading-assistant-label'));
 const unitSelect=el('select');unitSelect.setAttribute('aria-label','提问的源码步骤');for(const id of ids){const option=el('option',s.data.views[id].title.replace('基础例子 · ','基础研读 · '));option.value=id;unitSelect.append(option);}unitSelect.value=sourceAssistantUnit;unitSelect.onchange=()=>{sourceAssistantUnit=unitSelect.value;run(renderSourceAssistant);};target.append(unitSelect);
 if(history.mode!=='live')sourceAssistantMode='offline';
 target.append(el('span',sourceAssistantMode==='offline'?'本地源码讲解':'DeepSeek 讲解','badge'));
 if(history.mode==='live'){
  const mode=el('select');mode.setAttribute('aria-label','源码助手回答方式');
  mode.append(new Option('本地源码讲解','offline'),new Option('DeepSeek 讲解','auto'));
  mode.value=sourceAssistantMode;mode.onchange=()=>{sourceAssistantMode=mode.value;run(renderSourceAssistant);};target.append(mode);
  if(sourceAssistantMode==='auto'){
   const privacy=el('details');privacy.append(el('summary','DeepSeek 会接收哪些内容？'),el('p','发送时会提供当前问题、源码片段、学习目标和最近对话。'));target.append(privacy);
  }
 }
 const prompts=el('div',undefined,'assistant-topics');
 for(const q of ['函数全景','分阶段执行流程','阅读路线依据'])prompts.append(button(q,()=>askSourceAssistant(q)));
 target.append(prompts);
 const messages=el('div',undefined,'messages');for(const row of history.messages.filter(r=>r.unit_id===sourceAssistantUnit)){
  const card=el('article');card.append(el('p','问题：'+row.message),el('span',row.status==='completed'?(row.mode==='live'?'实时讲解 · AI生成':'本地讲解'):row.status==='partial'?'讲解未完 · AI生成':'请求未完成','badge'),renderReply(row.reply));
  if(row.retryable)card.append(button(row.status==='partial'?'继续讲解':'重新请求',()=>askSourceAssistant(row.status==='partial'?'请继续尚未完成的讲解。':row.message)));
  for(const ref of row.sources||[])card.append(external(ref.title+' · '+ref.start_line+'–'+ref.end_line+'行'+(ref.truncated?'（片段）':''),ref.url));messages.append(card);
 }target.append(messages);
 const question=el('textarea');question.setAttribute('aria-label','源码问题');question.placeholder='输入源码问题';question.maxLength=2000;question.value=sourceAssistantDraft;question.oninput=()=>sourceAssistantDraft=question.value;
 const send=button('发送源码问题',()=>askSourceAssistant(question.value),true);
 if(studio){
  const composer=el('div',undefined,'reading-assistant-composer');
  composer.append(question,send);target.append(composer);
 }else target.append(question,send);
}
async function askSourceAssistant(message){
 if(!message.trim())throw Error('请填写问题');
 const payload={user_id:profile.user_id,route_id:sourceRoute.id,unit_id:sourceAssistantUnit,message,mode:sourceAssistantMode};const key=JSON.stringify(payload);
 if(!sourceAskRetry||sourceAskRetry.key!==key)sourceAskRetry={key,id:crypto.randomUUID()};
 const result=await request('source-assistant',{...payload,request_id:sourceAskRetry.id});sourceAskRetry=null;sourceAssistantDraft='';notice(result.status==='completed'?'讲解已更新':result.reply);await renderSourceAssistant();
}
async function sourceIssues(refresh){
 const value=await request('source-issues?user='+encodeURIComponent(profile.user_id)+'&id='+encodeURIComponent(sourceRoute.id)+(refresh?'&refresh=1':''));clear('关联的公开 Issue');$('view').append(el('p','更新于：'+dateLabel(value.captured_at)));
 if(value.error)$('view').append(el('p',value.error));if(!value.items.length)$('view').append(el('article','暂未找到与当前学习内容相关的 Issue，可以到仓库查看全部讨论。'));
 for(const item of value.items){const card=el('article');card.append(el('h2',item.title),external('查看 Issue #'+item.number,item.url),el('p','相关内容：'+item.matched_terms.join('、')+' '+item.matched_paths.join('、')));const steps=el('ol');item.preparation.forEach(s=>steps.append(el('li',s)));card.append(steps);$('view').append(card);}
 $('view').append(button('刷新讨论',()=>sourceIssues(true),true),external('查看仓库的全部 Issue',value.repository_url),button('返回源码路线',sourceRouteView));
}
