let reviewMaterial=null;
// Shared, public learning guidance. No final answers or method-specific hints.
const GUIDE={
 task_002:{title:'给一个真实函数加上输入检查',goal:'你要修复一个小问题：一个函数用 size 表示窗口大小，但它还没有严格拒绝不合适的 size。你只修改输入检查，保留原来的正常功能。',example:'先理解“滑动窗口”：从 [1, 2, 3, 4] 每次取相邻的两个数，得到 (1, 2)、(2, 3)、(3, 4)。size=2 就表示每个窗口放两个数。',outcome:'最后交付修改后的代码、你自己的验证记录和一段修改说明。刚开始不用上传文件；先按路线理解它。',standard:['size 必须是内置正整数；True、False 不算。','类型不合适时报告 TypeError；整数为零或负数时报告 ValueError。','原来正确的输入仍得到原结果；默认填充值、空输入等已有行为也要保留。'],units:{
  u_iterable:['认识“逐个取数据”','窗口函数会一步一步取输入，而不是必须一次拿到全部数据。先认识这个接口，有助于理解后面的窗口处理。','找出这里检查对象能否被逐个读取的地方。把不懂的 iter、next 或 yield 记下来，可以用下方提问卡问AI。','你能用自己的话说出“逐个取数据”和“已经存好的列表”有什么不同即可。'],
  u_windowed_iter:['找到要修改的窗口函数','这是任务要改的函数。先看清输入和处理顺序，才知道输入检查应放在哪里。','找到 size 从哪里进入、何时被使用；再观察正常窗口怎样产生。此时先别急着改代码。','你知道目标函数在哪里，能指出 size 的使用位置，并知道哪些正常行为需要保留。'],
  u_positive_int:['对照项目里已有的参数检查','同一个项目中的检查写法可以作为阅读参考，但不一定满足本任务全部要求。','观察这里怎样检查数值并报告错误。将它与任务要求逐项比较，不要直接照抄。','你能列出需要拒绝的输入类别，并区分“类型不对”和“数值不对”。']
 }},
 B07_more_chunked:{title:'换一个仓库，看看同一知识怎样使用',goal:'这一轮练习阅读，不要求修改代码或上传文件。你要在另一个真实仓库里找到：数据怎样被逐个取出、怎样组成一组、何时结束。',example:'“分组”和“滑动窗口”不同：把 [1, 2, 3, 4] 每两个分成一组，得到 [1, 2] 和 [3, 4]，中间不会重叠。',outcome:'完成一次新短测，并用自己的话记录一个发现或仍不懂的问题。这个功能案例不作为正式任务评分。',standard:['找到 chunked 的入口和它调用的 take。','说出一个你在两个仓库中都看到的概念；不懂也可以如实记录。'],units:{B07_more_chunked:['在新仓库识别熟悉的概念','前一轮的阅读经验可能帮助你认识这里的代码；系统仍会安排一道不同的小题检查理解。','先找函数的输入，再顺着 take 看一组数据怎样产生。遇到 partial 或 iter 的特殊写法，可用提问卡逐个解释。','你能指出一组数据从哪里产生；不会的术语已标出来，接着做独立短测。']}}
};
function guideFor(s){return GUIDE[s?.task?.task_id]||GUIDE[$('task').value]||GUIDE.task_002;}
function addText(parent,tag,value,cls){const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;parent.append(e);return e;}
function unitName(id){for(const g of Object.values(GUIDE))if(g.units[id])return g.units[id][0];return '阅读相关源码（'+id+'）';}
function brief(){if(!session)document.querySelectorAll('[data-stage]').forEach(e=>e.classList.toggle('current',e.dataset.stage===(!participant?'1':'2')));const g=GUIDE[$('task').value]||GUIDE.task_002;text('briefTitle',g.title);text('briefGoal',g.goal);text('briefExample',g.example);text('briefOutcome',g.outcome);$('briefStandards').replaceChildren();g.standard.forEach(v=>addText($('briefStandards'),'li',v));}
function guideSession(){if(!session)return;const s=session,g=guideFor(s),done=terminal(s),quiz=s.phase==='quiz',work=!s.route.length&&s.quiz_done&&!done;const progress=done?6:quiz?4:work?5:3;
 document.querySelectorAll('[data-stage]').forEach(e=>{e.classList.toggle('current',Number(e.dataset.stage)===progress);e.setAttribute('aria-current',Number(e.dataset.stage)===progress?'step':'false');});
 text('currentGoal',g.goal);text('currentOutcome',g.outcome);text('currentStep',done?'本轮已结束':s.status==='PAUSED'?'已暂停：恢复后继续当前步骤':quiz?'第4步 · 用一道小题检查理解':work?'第5步 · 动手完成任务':`第3步 · 跟着路线阅读（已读 ${s.completed.length} 份，剩余 ${s.route.length} 份）`);
 text('nextAction',done?'查看学习记录，或开始第二个仓库的练习。':quiz?'先自己作答；这一题只帮助调整后续路线，不代表整个任务完成。':work?'现在再打开工作区。按下面的清单修改、验证，准备好后才提交。':'先看本步目标，再读这一小段源码。遇到不懂的地方，用提问卡整理问题；读完后进入下一步。');
 $('readingArea').hidden=done||quiz||work||s.status==='PAUSED';$('submitPanel').hidden=!work;$('completion').hidden=!done;
 const unitId=reviewMaterial?.unit_id||s.route[0];const spec=g.units[unitId]||['阅读当前源码','这份材料来自当前任务的规划路线。','围绕任务目标，找输入、输出以及关键处理步骤。','能指出当前材料与任务的关系；不懂的问题可以先记下。'];
 text('unitTitle',(reviewMaterial?'回看已读内容 · ':'')+spec[0]);$('backToCurrent').hidden=!reviewMaterial;$('complete').hidden=!!reviewMaterial;text('unitWhy',spec[1]);text('unitDo',spec[2]);text('unitDone',spec[3]);
 text('complete',s.quiz_done?'这份材料已读完，继续下一步':'这份材料已读完，做一道小题');
 $('route').querySelectorAll('li').forEach((li,i)=>{const ids=[...s.completed,...s.route];li.textContent=(i<s.completed.length?'✓ 已读 · ':i===s.completed.length?'正在读 · ':'稍后读 · ')+unitName(ids[i]);if(i<s.completed.length&&!done&&!quiz&&!work){const b=document.createElement('button');b.className='quiet';b.textContent='回看';b.onclick=()=>guarded(async()=>{reviewMaterial=await request('/api/material?id='+encodeURIComponent(s.session_id)+'&unit='+encodeURIComponent(ids[i]));sourceRows('materials',reviewMaterial.materials);guideSession();$('unitTitle').scrollIntoView({block:'start'});});li.append(b);}});
 const canAsk=!done&&!quiz&&!work&&s.status==='ACTIVE';$('askHelp').hidden=!canAsk;
 if(reviewMaterial)sourceRows('materials',reviewMaterial.materials);const sources=(reviewMaterial?.materials||s.materials||[]).map(m=>`${m.source_span.path}:${m.source_span.start_line}-${m.source_span.end_line}\n${m.text}`).join('\n\n');
 text('aiQuestion',`我有基础Python知识，正在学习一个开源项目。请帮助我理解，不要直接写最终任务补丁。\n任务：${g.goal}\n当前学习步骤：${spec[0]}\n我现在需要做：${spec[2]}\n固定版本：${s.task.repo_commit}\n源码：\n${sources}\n\n请先用通俗语言说明这段代码在做什么，再解释必要术语，用一个不同于任务的小例子说明。最后问我一个理解问题。我的疑问：`);
 $('patchSubmission').hidden=!s.patch_task;$('responseSubmission').hidden=s.patch_task||s.task.task_id==='B07_more_chunked';
 text('workTitle',s.patch_task?'第5步 · 在本地完成修改，再提交作品':'第5步 · 记录这次阅读的发现');
 text('workIntro',s.patch_task?'先下载未修改的起始代码包。解压后按 START_HERE.md 的顺序操作；不会的地方可以回看源码。只有作品准备好才选择文件提交。':'无需上传代码、无需填写JSON。写下一点发现或一个仍不懂的问题，再保存阅读记录。');
 text('submit',s.patch_task?'作品准备好了，提交检查':'保存我的阅读记录');
 $('starterDownload').hidden=!s.patch_task;$('starterDownload').href='/api/starter?task=task_002';
 text('explanationLabel',s.patch_task?'还有什么需要说明？（可选）':'你发现了什么，或仍然不懂什么？');
 text('completionText',s.status==='SUBMITTED'?'提交已保存。短测结果与最终作品评分分开；作品尚未独立评分。':s.status==='WITHDRAWN'?'本轮已保存为未完成。它不会被当作成功，也不会丢掉之前的阅读记录。':'本轮已停止，原记录保留。查看提示后再决定下一步。');
}
function showWorkChecklist(){text('submissionHint','请选择起始包中的5个交付文件。下面会检查文件是否齐全；文件齐全不代表答案正确。');}
async function copyQuestion(){try{await navigator.clipboard.writeText($('aiQuestion').value);text('copyStatus','已复制。可粘贴到你正在使用的AI对话中；这不会自动发起模型调用。');}catch{ $('aiQuestion').focus();$('aiQuestion').select();text('copyStatus','请按 Ctrl+C 复制，再粘贴到AI对话中。');}}

document.addEventListener('DOMContentLoaded',()=>{$('backToCurrent').onclick=()=>{reviewMaterial=null;renderSession();$('unitTitle').scrollIntoView({block:'start'});};});
