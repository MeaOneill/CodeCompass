                                                                          
let activeReadingUnit=null;
function orderReason(reason){
 if(!reason)return null;
 const block=el('div',undefined,'lesson-purpose order-reason');block.append(el('h3','推荐阅读顺序依据'));
 if(reason.before.length)block.append(el('p','源码依赖：后续的 '+reason.before.join('、')+' 会调用这段实现。先读这里，有助于理解调用处。'));
 if(reason.root_exposure_topic_count)block.append(el('p',`起点需要补充：当前路线没有合适的前置材料，涉及 ${reason.root_exposure_topic_count} 个待补学主题。`));
 for(const supply of reason.concept_supply||[]){
  const topic=sourceFeatures[supply.topic]||supply.topic;
  block.append(el('p','基础铺垫：'+topic+'已由 '+supply.suppliers.map(s=>s.title).join('、')+' 提供。'));
 }
 block.append(el('p',`本步新接触 ${reason.new_features.length} 项语法特征。`));
 return block;
}
function metricCard(label,value,detail=''){const c=el('div',undefined,'metric-card');c.append(el('span',label,'metric-label'),el('strong',value),el('span',detail,'metric-detail'));return c;}
function routeStages(phase){const row=el('div',undefined,'journey-steps');const current=phase==='planning'?0:phase==='issues'?2:phase==='review'?3:1;[['route','学习规划'],['book','源码研读'],['issue','Issue实践'],['chart','学习报告']].forEach(([name,label],i)=>{const c=el('div',undefined,'journey-step'+(i===current?' current':i<current?' done':''));c.append(icon(name),el('span',label));row.append(c);});return row;}
function profilePanel(metrics){
 const section=el('div',undefined,'profile-grid capability-topics');
 const symbols={'python.functions':'code','python.iteration':'refresh','python.generators':'route',
  'python.classes':'user','python.exceptions':'issue','python.containers':'book',
  'python.decorators':'spark','python.async':'chart'};
 for(const row of metrics.topics){
  const card=el('article',undefined,'skill-card capability-topic');
  const assessed=row.score!==null;
  if(row.reading_count)card.classList.add('has-reading');
  if(assessed)card.classList.add('is-assessed');
  const heading=el('div',undefined,'capability-topic-heading'),title=el('h3');
  title.append(personalIcon(symbols[row.concept]||'book'),el('span',row.title));
  heading.append(title,el('span',assessed?'已测评':'未测评','capability-assessment'));card.append(heading);
  const assessment=el('div',undefined,'capability-topic-score');
  if(assessed){
   const score=el('div',undefined,'capability-score-line');
   score.append(el('strong',row.score+'%'),el('span',`答对 ${row.correct} / ${row.answered} 题`));
   const track=el('progress');track.max=100;track.value=row.score;track.setAttribute('aria-label',row.title+'基础测评正确率');
   assessment.append(score,track);
  }else{
   assessment.append(el('span','尚无答题记录'));
   if(row.self_report)assessment.append(el('span','自评熟悉','capability-self-report'));
  }
  const growth=el('div',undefined,'capability-topic-growth');
  growth.append(el('strong',row.growth_status),el('span',`已读 ${row.reading_count} 处源码 · ${row.repositories} 个仓库`));
  card.append(assessment,growth);
  if(row.review_question){
   const review=profileCheck(row);review.classList.add('capability-review');card.append(review);
  }
  section.append(card);
 }
 return section;
}

async function sourceProfile(){
 page='profile';await ensureLearner();
 profile=await request('profile?user='+encodeURIComponent(profile.user_id));clear('能力画像');
 const {screen,head}=personalPage('profile','持续记录你的学习轨迹，了解不同主题的掌握情况。');
 head.append(personalIcon('user'));
 const m=profile.metrics,overview=el('div',undefined,'capability-overview');
 for(const [title,value,detail,symbol] of [
  ['起点阶段',m.experience,'当前能力起点','book'],
  ['基础测评正确率',m.score===null?'待测评':m.score+'%',`答对 ${m.correct} / ${m.answered} 题`,'check'],
  ['主题维度',m.topics.length+' 项','覆盖的主题维度','route'],
 ]){
  const card=metricCard(title,value,detail);card.append(personalIcon(symbol));overview.append(card);
 }
 const band=el('dl',undefined,'capability-band');
 for(const [label,value,symbol] of [
  ['当前学习阶段',m.learning.stage,'route'],['累计源码研读',m.learning.readings+' 处','code'],
  ['已学习仓库',m.learning.repositories+' 个','book'],['主题复核通过',m.learning.verified_topics+' 项','check'],
 ]){
  const item=el('div'),content=el('div');
  content.append(el('dt',label),el('dd',value));item.append(icon(symbol),content);band.append(item);
 }
 const topics=el('section',undefined,'capability-subjects');
 topics.append(el('h2','主题能力分布'),profilePanel(m));
 const guidance=el('section',undefined,'capability-guidance'),copy=el('div'),actions=el('div',undefined,'personal-actions');
 copy.append(el('h2','继续完善你的能力画像'),el('p','通过主题测评和源码学习，逐步补充你的学习记录。'));
 actions.append(button('更新调查与测评',sourceSurvey,true),button('进入仓库学习',sourceHome));
 guidance.append(personalIcon('chart'),copy,actions);
 screen.append(overview,band,topics,guidance);
}
async function openSourceRoute(id){sourceRoute=await request('route?user='+encodeURIComponent(profile.user_id)+'&id='+encodeURIComponent(id));activeReadingUnit=null;localStorage.setItem(sourceRouteKey,id);if(sourceRoute.insights.learning_phase==='issues')return sourceIssues(true);await sourceRouteView();}
async function sourceFeedback(action,unit,preparation){const r=sourceRoute;sourceRoute=await request('route-feedback',{user_id:profile.user_id,route_id:r.id,revision:r.revision,request_id:crypto.randomUUID(),action,unit_id:unit,preparation});activeReadingUnit=null;sourceAssistantUnit=null;notice('学习记录已保存');if(sourceRoute.insights.learning_phase==='issues')return sourceIssues(true);await sourceRouteView();}
async function sourceRouteView(){
 const r=sourceRoute,s=r.state,p=s.result,m=r.insights.route;if(!s.learning_started&&!s.completed.length&&p.remaining.length)return sourceMapView();page='home';
 const reading=r.insights.learning_phase==='reading'&&p.status==='FEASIBLE'&&!s.planning_error&&p.remaining.length;
 const reviewing=r.insights.learning_phase==='review';
 clear(reading?'源码研读':'学习路线');
 if(reviewing)return renderLearningReport(r);
 if(reading){
  $('crumb').textContent='CodeCompass / 学习工作台 / 源码研读';
  return readingStudio(r);
 }
 $('view').append(el('h2',s.goal),el('p',s.repository,'repository-label'),routeStages(r.insights.learning_phase));
 const stats=el('div',undefined,'metrics');stats.append(metricCard('目标覆盖率',m.goal_coverage+'%',`${m.covered_goals} / ${m.total_goals} 个目标`),metricCard('基础覆盖率',m.foundation_coverage+'%'),metricCard('候选筛选',m.candidates+' → '+m.selected,'源码材料'),metricCard('学习进度',m.progress+'%',`${m.completed} / ${m.total} 步`));$('view').append(stats);
 if(r.insights.source_graph)$('view').append(el('p',`仓库结构分析：${r.insights.source_graph.nodes} 个源码节点 · ${r.insights.source_graph.edges} 条结构关系`,'muted'));
 $('view').append(routeSummary(r));
 if(p.status!=='FEASIBLE'||s.planning_error){$('view').append(el('article',s.planning_error||'请调整学习范围后重新规划。'));return;}
 if(!p.remaining.length){$('view').append(el('article','源码研读已完成，请进入 Issue 实践。'),button('进入 Issue 实践',()=>sourceIssues(true),true));return;}
}

function routeSummary(r){
 const m=r.insights.route,summary=el('article',undefined,'route-summary');
 summary.append(el('h2','路径推荐依据'),el('p',`根据能力画像与学习目标，从 ${m.candidates} 项候选材料中安排 ${m.selected} 个步骤，覆盖 ${m.files} 个源码文件。`));
 const detail=el('details');
 detail.append(el('summary','查看规划指标'),el('p',`剩余学习负荷 ${m.workload} · 路线评价值 ${m.objective}`),
  el('p','评价值综合阅读负荷、重复概念与路线调整成本。覆盖率按已安排的目标与基础内容计算。'));
 summary.append(detail,button('查看整体规划图',sourceMapView),button('更新学习路线',()=>sourceFeedback('replan')),
  button('调整学习目标',()=>sourceRepository(r.repository_id)));
 return summary;
}

async function renderLearningReport(r){
 const {state:s,insights}=r,m=insights.route,view=$('view');
 notice('学习记录已保存');
 const studio=el('section',undefined,'report-studio'),hero=el('div',undefined,'report-hero');
 const intro=el('div'),heading=view.querySelector('h1');heading.textContent='学习报告';
 const label=el('span',undefined,'report-success-tag');label.append(icon('check'),el('span','源码研读已完成'));
 intro.append(label,heading,el('p',s.goal,'report-goal'),el('code',s.repository,'report-repository'));
 const progress=el('figure',undefined,'report-ring'),svg=mapSvg('svg',{viewBox:'0 0 126 126','aria-hidden':'true'});
 const ring=(className,radius,extra={})=>mapSvg('circle',{cx:63,cy:63,r:radius,class:className,...extra});
 svg.append(ring('report-ring-core',44),ring('report-ring-track',51),
  ring('report-ring-value',51,{pathLength:100,'stroke-dasharray':`${m.progress} 100`,transform:'rotate(-90 63 63)'}));
 const progressText=el('figcaption');
 progressText.append(el('strong',m.progress+'%'),el('span',m.progress===100?'学习完成':'学习进度'));
 progress.append(svg,progressText);hero.append(intro,progress);
 const stages=routeStages('review');stages.querySelector('.current').setAttribute('aria-current','step');
 studio.append(hero,stages);
 const metrics=el('div',undefined,'metrics report-metrics');
 for(const [label,value,detail,symbol,percentage] of [
  ['目标覆盖率',m.goal_coverage+'%',`${m.covered_goals} / ${m.total_goals} 个目标`,'route',m.goal_coverage],
  ['基础覆盖率',m.foundation_coverage+'%','已覆盖的基础内容','book',m.foundation_coverage],
  ['候选筛选',m.candidates+' → '+m.selected,'源码材料','code',null],
  ['学习进度',m.progress+'%',`${m.completed} / ${m.total} 步`,'check',m.progress],
 ]){
  const card=metricCard(label,value,detail),badge=icon(symbol);badge.classList.add('report-metric-icon');card.prepend(badge);
  if(percentage!==null){
   const bar=el('progress');bar.max=100;bar.value=percentage;bar.setAttribute('aria-label',label);card.append(bar);
  }
  metrics.append(card);
 }
 studio.append(metrics);
 const prepared=s.issue_status==='completed'&&s.issue_preparation,skipped=s.issue_status==='skipped';
 const completion=el('article',undefined,'completion-card report-completion'),title=el('div',undefined,'report-completion-title'),titleText=el('div');
 const mark=el('span',undefined,'report-completion-icon');mark.append(icon('check'));
 titleText.append(el('h2',prepared?'源码学习与实践准备已完成':'源码学习已完成'),
  el('p',`已研读 ${s.completed.length} 个源码步骤 · 已跳过 ${Object.keys(s.skipped_foundations||{}).length} 个基础步骤`));
 title.append(mark,titleText);completion.append(title);
 const result=el('div',undefined,'report-issue-result');
 if(prepared){
  const prep=s.issue_preparation;
  result.append(el('h3','实践准备成果'),external('#'+prep.number+' '+prep.title,prep.url),
   el('p',prep.state==='closed'?'已关闭问题复盘':'开放问题实践准备'),el('p',prep.note,'report-preparation-note'),
   el('p','已完成：阅读讨论、定位源码与测试、形成复现或复盘思路。'));
 }else{
  const status=el('div',undefined,'report-issue-heading');
  status.append(icon('issue'),el('h3',skipped?'Issue 实践已跳过':'Issue 准备已结束'));
  if(skipped)status.append(el('span','已跳过','report-neutral-tag'));
  result.append(status,el('p',skipped?'本次未提交实践准备记录。':'此历史记录未附准备成果。'));
 }
 const actions=el('div',undefined,'actions report-actions');
 actions.append(button('查看关联 Issue',()=>sourceIssues(false)),button('学习其他仓库',sourceImport,true));
 completion.append(result,actions);studio.append(completion);
 const process=el('section',undefined,'report-process');
 process.append(el('h2','学习过程摘要'));
 const facts=el('dl',undefined,'report-facts');
 for(const [label,value] of [
  ['学习主题',s.goal],['研读步骤',m.completed+' 步'],['涉及源码文件',m.files+' 个'],
  ['Issue 实践',prepared?'已完成':skipped?'已跳过':'已结束'],['源码研读','已完成'],
 ]){
  const fact=el('div');fact.append(el('dt',label),el('dd',value));facts.append(fact);
 }
 if(insights.source_graph){
  const {nodes,edges}=insights.source_graph,fact=el('div');
  fact.append(el('dt','仓库结构分析'),el('dd',`${nodes} 个源码节点 · ${edges} 条结构关系`));facts.append(fact);
 }
 process.append(facts);studio.append(process,routeSummary(r));view.append(studio);
 await renderSourceAssistant();
}

let lastReadingProgress=null;
function readingHero(r){
 const m=r.insights.route,hero=el('section',undefined,'reading-hero');
 const intro=el('div',undefined,'reading-intro');
 intro.append(el('span','Reading Studio','reading-eyebrow'),$('view').querySelector('h1'),
  el('p','沿着你的学习路线，一步步读懂真实源码。'));
 const context=el('div',undefined,'reading-hero-context');
 const repo=el('span',undefined,'reading-repo');repo.append(icon('code'),el('span',r.state.repository));
 context.append(repo,el('span',r.state.goal,'reading-goal-tag'));intro.append(context);
 const facts=el('div',undefined,'reading-facts');
 for(const [label,value,symbol] of [['学习目标',m.total_goals,'route'],['源码文件',m.files,'code'],['学习步骤',m.total,'book']]){
  const fact=el('div',undefined,'reading-fact');fact.append(icon(symbol),el('strong',String(value)),el('span',label));facts.append(fact);
 }
 intro.append(facts);
 const progress=el('figure',undefined,'reading-progress');
 const svg=mapSvg('svg',{viewBox:'0 0 200 200','aria-hidden':'true'});
 const circle=(radius,cls,extra={})=>mapSvg('circle',{cx:100,cy:100,r:radius,class:cls,...extra});
 svg.append(circle(62,'reading-ring-core'),circle(75,'reading-ring-track'));
 const arc=circle(75,'reading-ring-value',{pathLength:100,transform:'rotate(-90 100 100)',
  'stroke-dasharray':'100 100','stroke-dashoffset':100-m.progress});
 svg.append(arc);
 for(let i=0;i<m.total;i++){
  svg.append(mapSvg('line',{x1:100,y1:7,x2:100,y2:14,transform:`rotate(${360*i/m.total} 100 100)`,
   class:i<m.completed?'reading-tick done':'reading-tick'}));
 }
 if(m.completed<m.total){
  svg.append(mapSvg('circle',{cx:100,cy:10,r:3.5,
   transform:`rotate(${360*m.completed/m.total} 100 100)`,class:'reading-ring-next'}));
 }
 const gauge=el('div',undefined,'reading-gauge'),value=el('div',undefined,'reading-gauge-value');
 value.append(el('strong',m.progress+'%'),el('span','学习进度'));gauge.append(svg,value);
 progress.append(gauge,el('figcaption',`已完成 ${m.completed} / ${m.total} 步`));hero.append(intro,progress);
 const prior=lastReadingProgress?.route===r.id?lastReadingProgress.value:0;
 if(prior!==m.progress&&!matchMedia('(prefers-reduced-motion: reduce)').matches){
  arc.animate([{strokeDashoffset:100-prior},{strokeDashoffset:100-m.progress}],{duration:520,easing:'ease-out'});
 }
 lastReadingProgress={route:r.id,value:m.progress};
 return hero;
}

function readingPhase(number,title,symbol,hint){
 const section=el('section',undefined,'reading-phase');
 const marker=el('span',String(number).padStart(2,'0'),'reading-phase-number');
 marker.setAttribute('aria-hidden','true');
 const heading=el('div',undefined,'reading-phase-heading'),name=el('h3');
 name.append(icon(symbol),el('span',title));
 heading.append(name,el('p',hint));section.append(marker,heading);
 return section;
}

function readingExample(example){
 const block=el(example.review?'details':'section',undefined,'concept-block reading-concept');
 if(example.review)block.append(el('summary','复习：'+example.title));
 else{
  const title=el('h4');title.append(icon('book'),el('span',example.title));block.append(title);
 }
 block.append(el('p',example.goal));
 const pair=el('div',undefined,'example reading-example');
 for(const [label,body,style] of [['示例代码',example.code,'input'],['运行输出',example.output,'output']]){
  const pane=el('div',undefined,'reading-example-'+style);
  pane.append(el('span',label),el('pre',body));pair.append(pane);
 }
 const note=el('div',undefined,'reading-example-note');
 note.append(icon('spark'),el('p',example.explanation));block.append(pair,note);
 return block;
}

function readingSource(v,lesson){
 const source=el('details',undefined,'reading-source');source.open=true;
 const code=numberedSource(v),editor=el('div',undefined,'reading-editor');
 const top=el('div',undefined,'reading-editor-bar');
 const file=el('div',undefined,'reading-file-tab');file.append(icon('code'),el('code',v.path));
 const tools=el('div',undefined,'reading-editor-tools');
 const copied=el('span',undefined,'reading-copy-status');copied.setAttribute('role','status');
 const copy=button('复制代码',async()=>{
  await navigator.clipboard.writeText(v.code);copied.textContent='已复制';
 });
 tools.append(el('span',`${v.span.start_line}–${v.span.end_line} 行`),copy,external('在 GitHub 中查看',v.url),copied);
 top.append(file,tools);editor.append(top,code);source.append(el('summary','阅读源码'),editor);
 const guide=el('details',undefined,'reading-guide');guide.open=true;
 guide.append(el('summary','执行流程与函数信息'));
 if(lesson.signature)guide.append(el('code',lesson.signature,'reading-signature'));
 const points=el('ol',undefined,'source-phases reading-execution');
 lesson.source_steps.forEach((step,index)=>{
  const kind=/分支|检查/.test(step.title)?'decision':/返回|出口/.test(step.title)?'result':'process';
  const item=el('li',undefined,'reading-execution-'+kind);
  const control=button(step.title||'源码片段',()=>{
   source.open=true;
   code.querySelectorAll('.highlight').forEach(row=>row.classList.remove('highlight'));
   const row=code.querySelector('[data-line="'+step.line+'"]');
   if(row){
    row.classList.add('highlight');
    row.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'center'});
   }
  });
  const lines=step.end_line&&step.end_line!==step.line?`${step.line}–${step.end_line}`:step.line;
  control.replaceChildren(el('span',step.title||'源码片段'),el('span',`第 ${lines} 行`,'reading-line-chip'));
  item.append(el('span',String(index+1).padStart(2,'0'),'reading-execution-number'),control,el('p',step.text));points.append(item);
 });
 guide.append(points);
 if(lesson.source_summary){
  const original=el('details',undefined,'source-doc');
  original.append(el('summary','仓库原始文档注释'),el('p',lesson.source_summary));guide.append(original);
 }
 return [guide,source];
}

async function readingStudio(r){
 const {state:s,insights}=r,p=s.result,m=insights.route,view=$('view');
 const all=[...s.completed,...p.remaining];
 if(!all.includes(activeReadingUnit))activeReadingUnit=p.remaining[0];
 const uid=activeReadingUnit,v=s.data.views[uid],l=insights.lessons[uid];
 const current=uid===p.remaining[0],complete=s.completed.includes(uid),stepNumber=all.indexOf(uid)+1;
 sourceAssistantUnit=uid;
 const studio=el('div',undefined,'reading-studio'),steps=routeStages('reading');
 steps.querySelector('.current').setAttribute('aria-current','step');
 studio.append(readingHero(r),steps);
 const route=el('section',undefined,'reading-route');
 const routeHeader=el('div',undefined,'reading-route-header');
 routeHeader.append(el('h2','本次学习路线'),el('p',`从 ${m.candidates} 项候选材料中安排 ${m.selected} 个学习步骤，覆盖 ${m.files} 个源码文件。`));
 if(insights.source_graph){
  const {nodes,edges}=insights.source_graph;
  routeHeader.append(el('p',`仓库结构分析 · ${nodes} 个源码节点 · ${edges} 条结构关系`,'reading-repo-facts'));
 }
 const details=el('details',undefined,'reading-route-details');
 details.append(el('summary','查看路径推荐依据与规划指标'),
  el('p','系统根据能力画像和学习目标安排阅读顺序。'),
  el('p',`目标覆盖率 ${m.goal_coverage}%（${m.covered_goals} / ${m.total_goals}） · 基础覆盖率 ${m.foundation_coverage}% · 候选筛选 ${m.candidates} → ${m.selected}`),
  el('p',`剩余学习负荷 ${m.workload} · 路线评价值 ${m.objective}`),
  el('p','评价值综合阅读负荷、重复概念与路线调整成本。覆盖率按已安排的目标与基础内容计算。'));
 const controls=el('div',undefined,'reading-route-actions');
 controls.append(button('查看整体规划图',sourceMapView),button('更新学习路线',()=>sourceFeedback('replan')),button('调整学习目标',()=>sourceRepository(r.repository_id)));
 route.append(routeHeader,details,controls);studio.append(route);
 const navigation=el('div',undefined,'lesson-navigation reading-navigation'),picker=el('details');
 const navigationTitle=el('summary','查看全部步骤');
 navigationTitle.append(el('span',`已完成 ${m.completed} / ${m.total}`));picker.append(navigationTitle);
 const stepProgress=el('div',undefined,'reading-step-progress');
 stepProgress.setAttribute('role','progressbar');
 stepProgress.setAttribute('aria-label','学习步骤进度');
 stepProgress.setAttribute('aria-valuenow',String(m.completed));
 stepProgress.setAttribute('aria-valuemax',String(m.total));
 for(const id of all)stepProgress.append(el('span',undefined,s.completed.includes(id)?'done':'pending'));
 const list=el('ol',undefined,'reading-step-list');
 all.forEach((id,index)=>{
  const source=s.data.views[id],item=el('li');
  const jump=button(source.title,async()=>{activeReadingUnit=id;sourceAssistantUnit=id;await sourceRouteView();});
  const label=id===p.remaining[0]?'当前步骤':s.completed.includes(id)?'已完成':'未开始';
  if(id===uid){jump.classList.add('current');jump.setAttribute('aria-current','step');}
  const stepLabel=el('span',source.title.replace('基础例子 · ','基础研读 · '));
  stepLabel.append(el('code',source.path));
  jump.replaceChildren(el('span',String(index+1).padStart(2,'0'),'reading-list-number'),stepLabel,el('small',label));
  item.append(jump);list.append(item);
 });
 picker.append(list);navigation.append(picker,stepProgress);studio.append(navigation);
 const card=el('article',undefined,'active-lesson reading-lesson');
 const header=el('div',undefined,'reading-step-header');
 const n=el('span',String(stepNumber).padStart(2,'0'),'reading-step-number');n.setAttribute('aria-hidden','true');
 const body=el('div',undefined,'reading-step-body');
 const status=el('div',undefined,'reading-step-status');
 status.append(el('span',current?'当前步骤':complete?'已完成步骤':'预览步骤','badge'),el('span',`第 ${stepNumber} / ${m.total} 步`));
 body.append(status,el('h2',l.title),el('p',l.objective,'lesson-objective'));
 const meta=el('div',undefined,'reading-step-meta');
 const location=el('span',undefined,'reading-location');
 location.append(icon('code'),el('code',v.path),el('span',`${v.span.start_line}–${v.span.end_line} 行`));meta.append(location);
 for(const topic of l.concepts)meta.append(el('span',topic,'reading-topic'));
 body.append(meta);header.append(n,body);card.append(header);
 const timeline=el('div',undefined,'reading-timeline');
 const context=readingPhase(1,'学习目标关联','route','理解这段实现为什么出现在你的路线里。');
 context.classList.add('current');
 const contextGrid=el('div',undefined,'reading-context');
 const relation=el('div',undefined,'lesson-purpose');
 relation.append(el('h4','本步与学习目标的关联'),el('p',l.reason),el('p','学习目标：'+l.goal_link));
 contextGrid.append(relation);
 const order=orderReason(p.reading_order?.explanations?.[uid]);if(order)contextGrid.append(order);
 context.append(contextGrid);timeline.append(context);
 if(l.examples.length){
  const knowledge=readingPhase(2,'基础知识讲解','book','读源码前，先用简短示例熟悉相关概念。');
  const examples=el('details',undefined,'reading-knowledge');examples.open=true;
  examples.append(el('summary',`查看 ${l.examples.length} 个知识主题`),...l.examples.map(readingExample));
  knowledge.append(examples);timeline.append(knowledge);
 }
 const source=readingPhase(timeline.children.length+1,'源码导读','code','按执行顺序理解实现，点击行号可定位源码。');
 source.append(...readingSource(v,l));timeline.append(source);
 const check=readingPhase(timeline.children.length+1,'学习验收','check','回顾本步要点，再继续你的学习路线。');
 const checkPanel=el('div',undefined,'reading-check-panel');
 const standard=el('div',undefined,'reading-standard');
 standard.append(icon('check'),el('div'));
 standard.lastElementChild.append(el('h4','完成标准'),el('p',l.completion));checkPanel.append(standard);
 const checks=el('details',undefined,'learning-checks');
 checks.append(el('summary','主题复核（可选）'),el('p','检验本步涉及的基础概念，并更新能力画像。'));
 for(const q of l.practice){
  const box=el('section'),title=sourceFeatures[q.concept]||q.concept;
  box.append(el('h4',title));
  if(q.result)box.append(el('p',(q.result.correct?'复核通过：':'建议复习：')+q.result.explanation));
  else{
   box.append(el('pre',q.code));
   const choices=el('select');choices.setAttribute('aria-label',title+'复核答案');
   choices.append(new Option('请选择运行结果',''));q.choices.forEach((t,i)=>choices.append(new Option(t,String(i))));
   box.append(choices,button('提交'+title+'复核',async()=>{
    if(choices.value==='')throw Error('请选择运行结果');
    sourceRoute=await request('learning-check',{user_id:profile.user_id,route_id:r.id,unit_id:uid,concept:q.concept,answer:Number(choices.value)});
    await sourceFeedback('replan');
   }));
  }
  checks.append(box);
 }
 if(l.practice.length)checkPanel.append(checks);
 const actions=el('div',undefined,'actions reading-check-actions');
 actions.append(button('源码问答',async()=>{await renderSourceAssistant();$('assistant').classList.add('open');}));
 if(current){
  const next=p.remaining.length>1;
  const finish=button(next?'完成本步并继续':'完成本步',()=>sourceFeedback('read',uid),true);
  if(next)finish.append(icon('arrow'));
  actions.append(finish);
 }else actions.append(button('返回当前步骤',async()=>{activeReadingUnit=null;await sourceRouteView();}));
 checkPanel.append(actions);check.append(checkPanel);timeline.append(check);
 timeline.addEventListener('focusin',event=>{
  const phase=event.target.closest('.reading-phase');
  if(phase){timeline.querySelector('.current')?.classList.remove('current');phase.classList.add('current');}
 });
 card.append(timeline);studio.append(card);view.append(studio);
 await renderSourceAssistant();
}

function issueScreen(){
 const view=$('view'),studio=el('div',undefined,'issue-studio');
 const heading=view.querySelector('h1'),hero=el('div',undefined,'issue-page-title');
 hero.append(heading);studio.append(hero);
 const steps=routeStages('issues');
 if(sourceRoute.state.result.remaining.length)steps.children[1].classList.remove('done');
 steps.querySelector('.current').setAttribute('aria-current','step');
 for(const item of steps.children){
  if(item.classList.contains('done')){
   const mark=icon('check');mark.classList.add('issue-stage-check');item.append(mark);
  }
 }
 studio.append(steps);view.append(studio);return studio;
}

function issueLoading(){
 const panel=el('section',undefined,'issue-loader');
 panel.setAttribute('role','status');panel.setAttribute('aria-live','polite');
 const ring=el('span',undefined,'issue-spinner');ring.setAttribute('aria-hidden','true');
 panel.append(ring,el('h2','正在匹配关联问题…'));
 const steps=el('ol',undefined,'issue-load-steps');
 for(const [label,detail,symbol] of [
  ['读取学习记录','已读取本机学习路线与进度。','check'],
  ['分析学习覆盖','评估已研读的源码与主题。','chart'],
  ['匹配关联 Issue','根据学习内容查找相关问题。','issue'],
 ]){
  const step=el('li');step.append(icon(symbol),el('strong',label),el('span',detail));steps.append(step);
 }
 steps.lastElementChild.setAttribute('aria-current','step');
 panel.append(steps);
 const skeletons=el('div',undefined,'issue-skeletons');skeletons.setAttribute('aria-hidden','true');
 for(const kind of ['match','form']){
  const card=el('div',undefined,'issue-skeleton '+kind);
  card.append(el('i'),el('i'),el('div'));
  card.lastElementChild.append(el('i'),el('i'),el('i'));skeletons.append(card);
 }
 return [panel,skeletons];
}

const issueMetrics={content:['内容关联','route'],learning:['学习覆盖','book'],ability:['测评适配','check']};
function issueStatus(item){return item.state==='closed'?'已关闭 · 历史复盘':'开放问题';}
function issueMatch(item,choose,priority){
 const card=el('article',undefined,'issue-card issue-feature');
 const heading=el('div',undefined,'issue-feature-head'),identity=el('div');
 const tags=el('div',undefined,'issue-card-tags'),selected=el('span','当前选择','issue-current-tag');
 selected.hidden=true;
 tags.append(el('span','#'+item.number,'issue-number'));
 if(priority)tags.append(el('span','优先推荐','issue-priority-tag'));
 tags.append(selected);identity.append(tags,el('h2',item.title));
 const score=el('div',undefined,'issue-match-score');
 score.append(el('strong',item.match_percent+'%'),el('span','匹配度'));heading.append(identity,score);card.append(heading);
 const meta=el('div',undefined,'issue-feature-meta');
 meta.append(el('span',issueStatus(item),'issue-status '+item.state),external('查看 Issue #'+item.number,item.url));
 const keywords=el('div',undefined,'issue-keywords');
 if(item.matched_terms.length)keywords.append(el('span','关联关键词'),...item.matched_terms.map(term=>el('code',term)));
 card.append(meta,keywords);
 if(item.reason!=='关联关键词：'+item.matched_terms.join('、'))card.append(el('p',item.reason,'issue-reason'));
 const metrics=el('div',undefined,'issue-metrics');
 for(const [key,[label,symbol]] of Object.entries(issueMetrics)){
  const metric=el('div',undefined,'issue-metric'),name=el('div');
  name.append(icon(symbol),el('span',label));
  const value=item.match_components[key];metric.append(name,el('strong',value===null?(key==='ability'?'未测评':'待识别'):value+'%'));
  if(value!==null){
   const bar=el('progress');bar.max=100;bar.value=value;bar.setAttribute('aria-label',label);metric.append(bar);
  }
  metrics.append(metric);
 }
 const why=el('details',undefined,'issue-why');why.open=true;
 const grid=el('dl',undefined,'issue-why-grid');
 const association=el('dd'),references=[...item.matched_terms,...item.matched_paths];
 association.append(...(references.length?references.map(term=>el('code',term)):[el('span','暂无关联项')]));
 const weights=el('dd'),labels=el('div',undefined,'issue-weight-labels'),bar=el('div',undefined,'issue-weight-bar');
 bar.setAttribute('aria-hidden','true');
 for(const [key,weight] of Object.entries(item.match_weights)){
  const label=issueMetrics[key][0],percent=Math.round(weight*100);
  labels.append(el('span',label+' '+percent+'%'));
  const segment=el('span',undefined,'weight-'+key);segment.style.flexGrow=String(weight);bar.append(segment);
 }
 weights.append(labels,bar);
 for(const [name,content] of [['源码关联',association],['计算权重',weights],['关联测评题数',el('dd',String(item.ability_items))]]){
  const row=el('div');row.append(el('dt',name),content);grid.append(row);
 }
 why.append(el('summary','匹配依据'),grid);card.append(metrics,why);
 if(choose){
  const pick=button('选择此问题',()=>choose(item),true);pick.setAttribute('aria-pressed','false');
  pick.classList.add('issue-pick');card.append(pick);
 }
 return card;
}

async function sourceIssues(refresh){
 notice('');clear('Issue 实践');
 const studio=issueScreen(),body=el('div',undefined,'issue-page-body');
 body.append(...issueLoading());studio.append(body);
 let result;
 try{
  result=await request('source-issues?user='+encodeURIComponent(profile.user_id)+'&id='+encodeURIComponent(sourceRoute.id)+(refresh?'&refresh=1':''));
 }catch(error){
  body.replaceChildren(button('重试匹配',()=>sourceIssues(refresh)));
  throw error;
 }
 body.replaceChildren();
 const overview=el('section',undefined,'issue-overview'),intro=el('div',undefined,'issue-intro');
 const overviewIcon=el('span',undefined,'issue-overview-icon');overviewIcon.append(icon('issue'));
 const titles=el('div');
 titles.append(el('h2','关联开源问题'),el('p','根据当前源码学习记录，推荐可实践的真实 Issue。'));
 intro.append(overviewIcon,titles);
 const stage=el('div',undefined,'issue-stage-position');
 const stageText=el('div');stageText.append(el('span','当前学习阶段'),el('strong','选择适合的实践问题','issue-stage-label'));
 stage.append(el('strong','3 / 4'),stageText);overview.append(intro,stage);body.append(overview);
 if(result.error)body.append(el('p',result.error,'issue-warning'));
 const items=result.items,canPrepare=!sourceRoute.state.result.remaining.length;
 const actions=el('div',undefined,'issue-refresh');
 const refreshLinks=el('div');
 refreshLinks.append(button('刷新匹配',()=>sourceIssues(true)),external('仓库全部 Issue',result.repository_url));
 actions.append(el('span','更新时间：'+dateLabel(result.captured_at)),refreshLinks);
 const skip=button('跳过 Issue 实践',()=>sourceFeedback('skip_issues'));
 if(!items.length){
  body.append(el('article','尚未检索到可用问题，请稍后刷新。','issue-empty'),actions);
  body.append(canPrepare?skip:button('返回源码研读',sourceRouteView));
 }else renderIssuePractice(body,items,canPrepare,actions,skip);
 await renderSourceAssistant().catch(()=>{
  $('assistantContent').append(button('重试加载学习助手',renderSourceAssistant));
 });
}

function renderIssuePractice(body,items,canPrepare,refresh,skip){
 const candidates=el('section',undefined,'issue-stream');
 const heading=el('div',undefined,'issue-stream-heading'),titles=el('div');
 titles.append(el('h2','候选 Issue'),el('p','按系统推荐顺序排列，可直接比较各项匹配依据。'));
 heading.append(titles,el('span',`共 ${items.length} 个候选`,'issue-stream-count'));candidates.append(heading);
 const selection=el('select');selection.setAttribute('aria-label','实践问题');
 selection.append(new Option('请选择实践问题',''),...items.map(item=>new Option('#'+item.number+' '+item.title,String(item.number))));
 const prep=el('article',undefined,'issue-preparation'),checks=[],cards=[];
 const note=el('textarea');note.setAttribute('aria-label','实践准备记录');note.maxLength=2000;
 note.placeholder='记录关联源码、复现输入或历史问题的复盘结论。';
 const binding=el('p',undefined,'issue-form-binding');binding.setAttribute('aria-live','polite');
 const finish=button('保存准备记录并完成',()=>sourceFeedback('finish_issues',undefined,{
  number:Number(selection.value),checks:checks.map(c=>c.checked),note:note.value
 }),true);
 function choose(item){
  selection.value=String(item.number);syncSelection();
  prep.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
 }
 function updatePreparation(){
  finish.disabled=!selection.value||checks.some(c=>!c.checked)||note.value.trim().length<10;
 }
 function syncSelection(){
  updatePreparation();
  const item=items.find(candidate=>String(candidate.number)===selection.value);
  binding.textContent=item?`已选 #${item.number} · ${item.title}`:'请先从候选 Issue 中选择一个问题。';
  for(const [card,number] of cards){
   const selected=String(number)===selection.value,pick=card.querySelector('.issue-pick');
   card.classList.toggle('selected-issue',selected);
   card.querySelector('.issue-current-tag').hidden=!selected;
   if(pick){
    pick.setAttribute('aria-pressed',String(selected));
    pick.lastElementChild.textContent=selected?'已选择此问题':'选择此问题';
   }
  }
 }
 items.forEach((item,index)=>{
  const card=issueMatch(item,canPrepare?choose:null,index===0);
  cards.push([card,item.number]);candidates.append(card);
 });
 body.append(candidates,refresh);
 if(canPrepare){
  const title=el('h2');title.append(icon('check'),el('span','实践准备'));
  prep.append(title,binding,field('实践问题',selection));
  const checklist=el('fieldset',undefined,'issue-checklist');checklist.append(el('legend','准备检查清单'));
  for(const text of ['已阅读问题描述与讨论','已定位关联源码与现有测试','已形成复现思路或复盘结论']){
   const check=input('checkbox'),label=el('label',undefined,'option');
   checks.push(check);check.onchange=updatePreparation;label.append(check,el('span',text));checklist.append(label);
  }
  const formActions=el('div',undefined,'issue-form-actions');formActions.append(skip,finish);
  prep.append(checklist,field('准备记录（至少10字）',note),formActions);
  selection.onchange=syncSelection;
  note.oninput=updatePreparation;body.append(prep);
  syncSelection();
 }else body.append(button('返回源码研读',sourceRouteView));
}
function renderReply(text){const block=el('div',undefined,'assistant-reply');for(const part of text.split(/(```[a-zA-Z]*\n[\s\S]*?```)/g)){if(part.startsWith('```'))block.append(el('pre',part.replace(/^```[a-zA-Z]*\n/,'').replace(/```$/,'')));else part.split('\n\n').filter(Boolean).forEach(t=>block.append(el('p',t)));}return block;}

function highlightedPython(code,rows){
 const tokens=/(?<comment>#[^\n]*)|(?<string>"{3}[\s\S]*?(?:"{3}|$)|'{3}[\s\S]*?(?:'{3}|$)|"(?:\\[^\n]|[^"\\\n])*"|'(?:\\[^\n]|[^'\\\n])*')|(?<keyword>\b(?:False|None|True|and|as|assert|async|await|break|class|continue|def|del|elif|else|except|finally|for|from|global|if|import|in|is|lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b)|(?<number>\b\d[\d_]*(?:\.\d[\d_]*)?\b)/g;
 let line=0,cursor=0;
 function append(part,kind){
  for(const [i,text] of part.split('\n').entries()){
   if(i)line++;
   if(text)rows[line].append(kind?el('span',text,'reading-token-'+kind):text);
  }
 }
 for(const match of code.matchAll(tokens)){
  append(code.slice(cursor,match.index));
  append(match[0],Object.keys(match.groups).find(key=>match.groups[key]!==undefined));
  cursor=match.index+match[0].length;
 }
 append(code.slice(cursor));
}
function numberedSource(view){
 const block=el('div',undefined,'numbered-source');
 block.setAttribute('aria-label','带行号的源码');block.tabIndex=0;
 const rows=view.code.split('\n').map((_,i)=>{
  const n=view.span.start_line+i,row=el('div',undefined,'code-line');
  row.dataset.line=String(n);
  const content=el('code');
  row.append(el('span',String(n),'line-number'),content);block.append(row);
  return content;
 });
 highlightedPython(view.code,rows);
 for(const row of rows)if(!row.hasChildNodes())row.textContent=' ';
 return block;
}

function profileCheck(row){const q=row.review_question,box=el('details');box.append(el('summary','复核该主题'),el('pre',q.code));const select=el('select');select.setAttribute('aria-label',row.title+'画像复核答案');select.append(new Option('请选择运行结果',''));q.choices.forEach((t,i)=>select.append(new Option(t,String(i))));box.append(select,button('保存主题复核',async()=>{if(select.value==='')throw Error('请选择运行结果');await request('learning-check',{user_id:profile.user_id,route_id:q.route_id,unit_id:q.unit_id,concept:q.concept,answer:Number(select.value)});await sourceProfile();notice('主题复核已保存，将用于后续规划');}));return box;}
