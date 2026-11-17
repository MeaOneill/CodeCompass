                                                                                    
let disposeSourceMap=null;
function mapSvg(tag,attrs={},text){const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;}
function mapIcon(name){
 const paths={search:'M10 17a7 7 0 1 1 0-14 7 7 0 0 1 0 14z M15 15l6 6',
  zoomIn:'M10 17a7 7 0 1 1 0-14 7 7 0 0 1 0 14z M15 15l6 6 M7 10h6 M10 7v6',
  zoomOut:'M10 17a7 7 0 1 1 0-14 7 7 0 0 1 0 14z M15 15l6 6 M7 10h6',
  branch:'M6 6v12 M18 6v3a5 5 0 0 1-5 5H6 M6 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M18 6a2 2 0 1 0 0-4 2 2 0 0 0 0 4z M6 22a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  layers:'M12 3l9 5-9 5-9-5 9-5z M3 12l9 5 9-5 M3 16l9 5 9-5'};
 const svg=icon(name);
 if(paths[name])svg.firstElementChild.setAttribute('d',paths[name]);
 return svg;
}
function mapMetric(label,value,detail,symbol){
 const card=metricCard(label,value,detail),heading=el('div',undefined,'map-metric-heading');
 const badge=el('span',undefined,'map-metric-icon');badge.append(mapIcon(symbol));
 heading.append(card.firstElementChild,badge);card.prepend(heading);
 return card;
}
function mapButton(text,action,symbol,primary=false){
 const control=button(text,action,primary);control.firstElementChild.replaceWith(mapIcon(symbol));return control;
}
async function sourceMapView(){
 const r=sourceRoute;page='home';clear('整体规划图');document.body.classList.add('planning-overview');notice('');
 const map=await request('source-map?user='+encodeURIComponent(profile.user_id)+'&id='+encodeURIComponent(r.id));
 const view=$('view'),overview=el('section',undefined,'map-overview');
 const ready=r.state.result.status==='FEASIBLE'&&!r.state.planning_error&&map.steps.length>0;
 const meta=el('div',undefined,'map-overview-meta');
 meta.append(el('span',$('crumb').textContent));
 if(ready){
  const status=el('span',undefined,'map-plan-status');
  status.append(icon('check'),el('span','规划已生成'));meta.append(status);
 }
 const headline=el('div',undefined,'map-headline'),titles=el('div');
 const heading=view.querySelector('h1');heading.id='planning-heading';
 titles.append(heading,el('p',r.state.goal,'map-goal'));headline.append(titles);
 if(map.repository){
  const repository=el('div',undefined,'map-repository'),identity=el('div');
  identity.append(el('strong',map.repository));
  if(map.commit){
   const revision=el('code','固定版本 '+map.commit.slice(0,8));
   revision.title=map.commit;identity.append(revision);
  }
  repository.append(mapIcon('branch'),identity);
  headline.append(repository);
 }
 const stages=routeStages('planning');stages.querySelector('.current').setAttribute('aria-current','step');
 overview.setAttribute('aria-labelledby',heading.id);
 overview.append(meta,headline,stages);view.append(overview);
 const stats=el('div',undefined,'metrics map-metrics');
 const order=r.state.result.reading_order?.metrics;
 stats.append(mapMetric('选入路线',map.steps.length+' 步',r.insights.route.files+' 个源码文件','route'));
 if(order && Number.isInteger(order.dependency_violations)){
  const verified=new Set(map.edges.filter(e=>e.kind==='verified_call'&&e.sites.some(site=>site.used_for_order))
                         .map(e=>e.source+'→'+e.target)).size;
                                                                       
  stats.append(mapMetric('已核实调用先后',verified+' 条','顺序冲突 '+order.dependency_violations+' 条','branch'));
 }
 if(order && Number.isInteger(order.satisfied_supply_topic_count)){
  stats.append(mapMetric('已安排的前置知识',order.satisfied_supply_topic_count+' 项',
      '起点需补充 '+order.root_exposure_topic_count+' 项','book'));
 }
 if(order && Number.isInteger(order.MCS_support))stats.append(mapMetric('单步补学峰值',order.MCS_support+' 项','每步最多新接触的待补学主题','layers'));
 overview.append(stats);
 const top=el('div',undefined,'map-heading');
 if(ready&&r.insights.learning_phase!=='review')top.append(el('p','可按推荐顺序阅读源码，或先查看下方的仓库关系。'));
 const action=mapButton(r.insights.learning_phase==='review'?'返回学习报告':(r.state.learning_started||r.state.completed.length)?'继续源码研读':'开始源码研读',()=>startMapLearning(),'code',true);
 action.append(icon('arrow'));top.append(action);overview.append(top);
 const workspace=el('section',undefined,'map-workspace');
 workspace.setAttribute('aria-labelledby','map-workspace-heading');
 const toolbar=el('div',undefined,'map-toolbar'),search=input('search');search.placeholder='查找文件、函数或类';search.setAttribute('aria-label','查找源码节点');
 const mode=el('select');mode.setAttribute('aria-label','关系图显示范围');mode.append(new Option('全部源码','all'),new Option('仅主路径','route'));
 const calls=input('checkbox');calls.checked=true;calls.setAttribute('role','switch');const callLabel=el('label',undefined,'map-toggle');callLabel.append(calls,el('span',undefined,'map-switch-track'),el('span','显示调用关系'));
 const graph=el('div',undefined,'map-canvas');graph.setAttribute('aria-label','仓库源码关系图');graph.tabIndex=0;
 const panel=el('div',undefined,'map-inspector');panel.setAttribute('aria-live','polite');
 let manualZoom=null,scale=1,drawing=null,selected=null;const expanded=new Set();let positions=new Map();
 const searchField=el('div',undefined,'map-search');searchField.append(mapIcon('search'),search);
 const controls=el('div',undefined,'map-controls');
 const filters=el('div',undefined,'map-filters');filters.append(searchField,mode);
 const zoom=el('div',undefined,'map-zoom');zoom.append(mapButton('放大',()=>zoomBy(.15),'zoomIn'),mapButton('缩小',()=>zoomBy(-.15),'zoomOut'));
 const count=el('span',undefined,'map-count');count.setAttribute('role','status');
 const reset=mapButton('重置视图',()=>{manualZoom=null;search.value='';mode.value='all';expanded.clear();selected=null;layout.classList.remove('inspecting');draw();graph.scrollTo(0,0);},'refresh');
 controls.append(callLabel,zoom,reset);toolbar.append(filters,controls);
 const workspaceHeader=el('div',undefined,'map-workspace-header'),workspaceIntro=el('div');
 const workspaceTitle=el('h2','仓库关系图');workspaceTitle.id='map-workspace-heading';
 workspaceIntro.append(workspaceTitle,el('p','查看源码文件、函数调用和学习顺序之间的关系。'));
 workspaceHeader.append(workspaceIntro,count);workspace.append(workspaceHeader,toolbar);view.append(workspace);
 const legend=el('div',undefined,'map-legend');legend.setAttribute('aria-label','图谱图例');
 for(const [group,entries] of [
  ['结构关系',[['contains','文件 / 实现包含关系'],['imports','本地导入声明'],['inheritance','已核实继承（子类 → 基类）']]],
  ['调用关系',[['verified','已核实调用（调用者 → 被调用者）'],['candidate','候选调用线索']]],
  ['学习关系',[['study','规划学习顺序（先读 → 后读）'],['target','学习目标']]],
 ]){
  const items=el('div',undefined,'map-legend-group');items.append(el('strong',group));
  for(const [kind,label] of entries)items.append(el('span',label,'legend-'+kind));
  legend.append(items);
 }
 workspace.append(legend);
 const layout=el('div',undefined,'map-layout');layout.append(graph,panel);workspace.append(layout);
 let containerWidth=graph.getBoundingClientRect().width;
 const observer=new ResizeObserver(()=>{
  const width=graph.getBoundingClientRect().width;
  if(width!==containerWidth){containerWidth=width;manualZoom=null;}
  if(manualZoom===null)sizeGraph();
 });
 observer.observe(graph);
 disposeSourceMap=()=>observer.disconnect();
 function sizeGraph(){
  if(!drawing||!graph.clientWidth)return;
                                                                                    
  scale=manualZoom??Math.min(1,Math.max(.72,graph.clientWidth/drawing.width));
  drawing.svg.setAttribute('width',Math.floor(drawing.width*scale));
  drawing.svg.setAttribute('height',Math.floor(drawing.height*scale));
 }
 function zoomBy(delta){
  manualZoom=Math.min(1.5,Math.max(.45,scale+delta));
  sizeGraph();
 }
 const index=new Map(map.nodes.map(n=>[n.id,n]));
 function inspect(n){layout.classList.add('inspecting');selected=n.id;panel.replaceChildren(el('span',n.kind==='file'?'源码文件':n.target?'学习目标':'源码实现','badge'),el('h3',n.label),el('p',n.path,'source-title'));if(n.kind==='file'){const children=map.nodes.filter(x=>x.kind==='symbol'&&x.path===n.path);panel.append(el('p',`包含 ${children.length} 个函数或类，选中 ${children.filter(x=>x.selected).length} 项。`),button(expanded.has(n.path)?'收起文件实现':'展开文件实现',()=>{expanded.has(n.path)?expanded.delete(n.path):expanded.add(n.path);draw();inspect(n);}));}else{panel.append(el('p',`第 ${n.span.start_line}–${n.span.end_line} 行`));const step=map.steps.find(s=>s.node_id===n.id);if(step)panel.append(el('h3','选择依据'),el('p',step.reason),el('p',`主路径第 ${n.steps.join('、')} 步`),button('进入所选步骤',()=>startMapLearning(step.unit_id),true));else panel.append(el('p','当前路线未选择此实现，可在调整学习目标时加入。'));}for(const step of map.steps.filter(s=>s.node_id===n.id)){const why=orderReason(map.remaining_order_explanations?.[step.unit_id] ?? step.order_reason);if(why)panel.append(why);}const path=n.path.split('/').map(encodeURIComponent).join('/');panel.append(external('在 GitHub 中查看','https://github.com/'+map.repository+'/blob/'+map.commit+'/'+path+(n.span?'#L'+n.span.start_line+'-L'+n.span.end_line:'')));const incoming=map.edges.filter(e=>e.target===n.id&&e.kind!=='contains'),outgoing=map.edges.filter(e=>e.source===n.id&&e.kind!=='contains');if(incoming.length||outgoing.length){panel.append(el('h3','相关关系'));for(const e of [...incoming,...outgoing].slice(0,10)){const other=index.get(e.source===n.id?e.target:e.source);panel.append(el('p',mapRelationLabel(e,n,other)));}}draw();}
 function draw(){
  const query=search.value.trim().toLowerCase();const files=map.nodes.filter(n=>n.kind==='file'&&(mode.value!=='route'||n.selected)&&(!query||n.path.toLowerCase().includes(query)||map.nodes.some(s=>s.kind==='symbol'&&s.path===n.path&&s.label.toLowerCase().includes(query)))).sort((a,b)=>(a.selected?0:1)-(b.selected?0:1)||(Math.min(...a.steps,99999)-Math.min(...b.steps,99999))||a.path.localeCompare(b.path));
  const arrangement=sourceMapPositions(map,files,expanded,mode.value);positions=arrangement.positions;const y=arrangement.height;
  const height=Math.max(y+20,400);
  count.replaceChildren("显示 ",el("strong",`${files.length} / ${map.counts.files}`)," 个文件");const svg=mapSvg('svg',{viewBox:`0 0 900 ${height}`,role:'group','aria-label':'源码结构与规划主路径'});const defs=mapSvg('defs');for(const [id,color] of [['study','#087f5b'],['imports','#5b83ad'],['candidate','#a181bb'],['verified','#a2470b'],['verified_inheritance','#267477']]){const marker=mapSvg('marker',{id:'arrow-'+id,markerWidth:7,markerHeight:7,refX:6,refY:3,orient:'auto'});marker.append(mapSvg('path',{d:'M0 0L6 3L0 6Z',fill:color}));defs.append(marker);}svg.append(defs);
  const line=(a,b,kind)=>{const colors={contains:'#d5dfd8',imports:'#5b83ad',candidate:'#a181bb',verified:'#a2470b',verified_inheritance:'#267477',study:'#087f5b'};let startX=a.x+a.w,startY=a.y+a.h/2,endX=b.x,endY=b.y+b.h/2;if(kind==='study'){svg.append(mapSvg('path',{d:sourceMapStudyArrow(a,b),fill:'none',stroke:colors.study,'stroke-width':3,'class':'map-edge edge-study','marker-end':'url(#arrow-study)'}));return;}if(kind==='candidate'||kind==='verified'||kind==='verified_inheritance')endX=b.x+b.w;const bend=kind==='contains'?(startX+endX)/2:Math.max(startX,endX)+35;svg.append(mapSvg('path',{d:`M${startX},${startY} C${bend},${startY} ${bend},${endY} ${endX},${endY}`,fill:'none',stroke:colors[kind],'class':'map-edge edge-'+kind,'stroke-width':kind==='study'?3:kind==='contains'?1.5:kind==='verified'?2.4:1.2,'stroke-dasharray':kind==='candidate'?'5 5':kind==='verified_inheritance'?'10 3 2 3':'none',...(kind!=='contains'?{'marker-end':'url(#arrow-'+kind+')'}:{})}));};
  const root={x:12,y:20,w:205,h:58};for(const f of files)line(root,positions.get(f.id),'contains');for(const e of map.edges){if(e.source==='repository')continue;const a=positions.get(e.source),b=positions.get(e.target);if(a&&b&&(!['call_candidate','verified_call'].includes(e.kind)||calls.checked))line(a,b,e.kind==='call_candidate'?'candidate':e.kind==='verified_call'?'verified':e.kind);}
  for(const e of map.study_edges){const a=positions.get(e.source),b=positions.get(e.target);if(a&&b)line(a,b,'study');}
  const rootGroup=mapSvg('g',{'class':'map-root'});rootGroup.append(mapSvg('rect',{x:root.x,y:root.y,width:root.w,height:root.h,rx:12,fill:'#173c2e'}),mapSvg('text',{x:27,y:44,fill:'#fff','font-size':16,'font-weight':600},map.repository.length>22?map.repository.slice(0,20)+'…':map.repository),mapSvg('text',{x:27,y:64,fill:'#c9e0d4','font-size':12},'固定版本 '+map.commit.slice(0,8)));svg.append(rootGroup);
  for(const p of positions.values()){const n=p.n,g=mapSvg('g',{role:'button',tabindex:0,'aria-label':(n.kind==='file'?'文件 ':'实现 ')+n.label+(n.selected?' · 主路径第'+n.steps.join('、')+'步':''),'class':`map-node map-node-${n.kind}${n.selected?' is-on-route':''}${n.id===selected?' is-selected':''}${n.target?' is-target':''}`});g.append(mapSvg('title',{},n.label),mapSvg('rect',{x:p.x,y:p.y,width:p.w,height:p.h,rx:10,fill:n.selected?'#e6f5ec':n.test?'#f5f5f3':'#fff',stroke:n.id===selected?'#17211b':n.target?'#d28b24':n.selected?'#087f5b':'#d8e1da','stroke-width':n.id===selected||n.target?2.5:1.3}));const label=n.kind==='file'?n.path:n.label;
   g.append(mapSvg('line',{x1:p.x+5,x2:p.x+5,y1:p.y+13,y2:p.y+p.h-13,'class':'map-node-accent','aria-hidden':'true'}));
   g.append(mapSvg('text',{x:p.x+12,y:p.y+23,'class':'map-node-label','font-size':15,'font-weight':n.selected?600:400,fill:'#20382b'},label.length>30?label.slice(0,28)+'…':label));g.append(mapSvg('text',{x:p.x+12,y:p.y+43,'font-size':12,fill:'#65766c'},n.selected?(n.kind==='file'?'主路径涉及 '+n.steps.length+' 步':'第 '+n.steps.join('、')+' 步'):n.kind==='file'?(n.test?'测试文件 · ':'')+map.nodes.filter(x=>x.kind==='symbol'&&x.path===n.path).length+' 个实现 · 点击查看':n.span.start_line+'–'+n.span.end_line+' 行'));g.onclick=()=>inspect(n);g.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();inspect(n);}};svg.append(g);}
  graph.replaceChildren(svg);if(!files.length)graph.append(el('p','没有匹配的源码节点。'));
  const box=svg.getBBox();
  const width=Math.max(520,Math.ceil(box.x+box.width+24));
  drawing={svg,width,height};svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
  sizeGraph();
 }
 function refit(){manualZoom=null;draw();graph.scrollTo(0,0);}
 search.oninput=refit;mode.onchange=refit;calls.onchange=refit;
 panel.append(el('h3','查看规划依据'),el('p','绿色节点为主路径，金色边框为学习目标。点击文件或实现查看位置与关系。'));
 const path=el('article',undefined,'map-path');
 const pathHeader=el('div',undefined,'map-path-header'),pathIntro=el('div');
 pathIntro.append(el('h2','规划主路径'),el('p','按推荐顺序阅读关键源码与基础示例。'));
 pathHeader.append(pathIntro,el('span',map.steps.length+' 个步骤','map-path-count'));
 const chain=el('ol',undefined,'map-path-chain');
 for(const step of map.steps){
  const item=el('li'),control=button(step.title,()=>inspect(index.get(step.node_id)));
  const prefix='基础研读 · ';
  const title=el('span',undefined,'map-path-title');
  if(step.title.startsWith(prefix))title.append(el('span','基础研读','map-path-kind'));
  title.append(el('code',step.title.startsWith(prefix)?step.title.slice(prefix.length):step.title));
  control.replaceChildren(el('span',String(step.number).padStart(2,'0'),'map-step-number'),title);
  control.setAttribute('aria-label',`${step.number}. ${step.title}`);
  control.classList.add(step.completed?'path-completed':'path-pending');
  item.append(control);chain.append(item);
 }
 const adjust=mapButton('调整学习目标',()=>sourceRepository(r.repository_id),'settings');
 adjust.append(icon('arrow'));path.append(pathHeader,chain,adjust);
 $('view').append(path);draw();
}
async function startMapLearning(unit){if(!sourceRoute.state.learning_started&&!sourceRoute.state.completed.length)sourceRoute=await request('route-feedback',{user_id:profile.user_id,route_id:sourceRoute.id,revision:sourceRoute.revision,request_id:crypto.randomUUID(),action:'begin_learning'});activeReadingUnit=unit||null;await sourceRouteView();}

                                                                                     
function sourceMapPositions(map,files,expanded,mode){
 const positions=new Map(),visible=new Set(files.map(f=>f.path));
 const selected=map.nodes.filter(n=>n.kind==='symbol'&&n.selected&&visible.has(n.path)).sort((a,b)=>Math.min(...a.steps)-Math.min(...b.steps));
 let y=110;
 for(const n of selected){positions.set(n.id,{x:570,y,w:290,h:56,n});y+=84;}
 for(const f of files){
  const children=selected.filter(n=>n.path===f.path);
  const others=mode==='all'&&expanded.has(f.path)?map.nodes.filter(n=>n.kind==='symbol'&&n.path===f.path&&!n.selected).sort((a,b)=>a.span.start_line-b.span.start_line):[];
  if(children.length){positions.set(f.id,{x:230,y:positions.get(children[0].id).y,w:260,h:58,n:f});for(const n of others){positions.set(n.id,{x:570,y,w:290,h:56,n});y+=70;}if(others.length)y+=28;}
  else{const height=Math.max(76,others.length*70);positions.set(f.id,{x:230,y:y+height/2-29,w:260,h:58,n:f});others.forEach((n,i)=>positions.set(n.id,{x:570,y:y+i*70,w:290,h:56,n}));y+=height+28;}
 }
 return {positions,height:y};
}
function sourceMapStudyArrow(a,b){return `M${a.x+a.w/2},${a.y+a.h} L${b.x+b.w/2},${b.y}`;}

function mapRelationLabel(edge,node,other){
 if(edge.kind==='call_candidate'&&edge.basis==='known_subclass_override')return '候选调用线索：'+other.label+' · 快照中存在子类重写，调用目标待确认';
 if(edge.kind==='call_candidate'&&edge.basis==='ambiguous_method_dispatch')return '候选调用线索：'+other.label+' · 方法分派存在歧义，调用目标待确认';
 if(edge.kind==='verified_inheritance')return '已核实继承 · '+(edge.source===node.id?'基类 ':'子类 ')+other.label+' · '+edge.path+':'+edge.line;
 if(edge.kind==='verified_call'){
  const direction=edge.source===node.id?'调用 ':'被调用，调用者为 ';
  const lines=edge.sites.map(site=>site.path+':'+site.line).join('、');
  return (node.path===other.path?'已核实调用':'已核实跨文件调用')+' · '+direction+other.label+' · '+lines+(edge.sites.some(site=>site.used_for_order)?' · 用于本路线排序':'');
 }
 return (edge.kind==='imports'?'导入声明：':'候选调用线索：')+(other?.label||'')+(edge.line?' · 第'+edge.line+'行':'');
}
