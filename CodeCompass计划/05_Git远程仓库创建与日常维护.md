# Git远程仓库创建与日常维护

更新日期：2026年10月16日。适用方式：两位成员、两台Windows电脑，各自使用GitHub账号和本地项目副本。教程以GitHub为例；使用其他托管平台时需核对对应认证和协作入口。

## 1 现有安排与当前状态

旧计划D01和双机规范已经提到仓库权限、commit和push，但没有把操作细化到首次创建、首次上传、第二台电脑加入、每轮维护与检查。现将这些列为明确任务，并嵌入16天日程与两份成员手册。

2026年10月16日只读检查：本机命令行Git可用，位置为D:/Git/cmd/git.exe；当前D:/AIC算法主题赛没有.git目录。本次更新的是文档与模板，尚未初始化本地Git、创建远程仓库、登录GitHub或上传文件。实际远程地址尚未知。

今天若仍未完成D01，先补仓库启动步骤，再衔接D02；不修改已实际完成的任务状态，不把计划日期当完成日期。正式截止仍为10月30日20:00。

## 2 先理解五个词

| 词 | 在本项目中的意思 |
|---|---|
| 本地仓库 | 你电脑中的项目和版本记录；另一台电脑有自己的副本 |
| 远程仓库 origin | GitHub上的同一份共享仓库；origin只是本地保存的远程名称 |
| commit 提交 | 在本机保存一个版本；仅commit，另一台电脑还拿不到 |
| push 推送 | 把本机提交上传到远程；成功后另一台电脑才能拉取 |
| pull 拉取 | 取回远程更新并更新当前分支；必须核对分支和本地未提交修改 |
| main与任务分支 | main放已验收版本；task分支放本轮开发或中断检查点 |

日常顺序：开始前同步正确版本 → 在任务分支开发 → 验证并更新日志 → commit → push → 核对远程SHA → 交接。任务验收通过后再按负责人流程合入main。

## 3 第一步 两位成员准备账号与Git

两位成员分别准备自己的GitHub账号，不共用密码。两台电脑各打开PowerShell，执行：
```powershell
git --version
```
能返回版本号即可。本机已有Git，不需要重复安装。另一台若提示无法识别git，从[Git for Windows官方入口](https://git-scm.com/downloads/win)安装，保留凭据管理器，安装后重新打开PowerShell再检查。

GitHub HTTPS认证推荐使用Git Credential Manager或GitHub CLI。第一次需要权限的push/clone可能打开浏览器，让各自在自己电脑上登录并授权；不要把GitHub网页密码填到Git的密码提示，也不要把token放进URL、代码、文档或发给Agent。[官方凭据说明](https://docs.github.com/en/get-started/git-basics/caching-your-github-credentials-in-git?platform=windows)

若浏览器授权没有出现，先记录报错并检查凭据工具；也可在已安装GitHub CLI时使用gh auth login，选择GitHub.com、HTTPS和浏览器登录。不要求为了本教程额外安装CLI。

## 4 第二步 由队长在网页创建一个空的私有仓库

1. 在浏览器登录GitHub，打开[新建仓库页面](https://github.com/new)。
2. Owner选择队长账号；Repository name建议填CodeCompass；描述可填“面向开源代码学习的能力与依赖联合路径规划”。
3. 开发阶段建议选Private，先与队友协作；参赛前按开放计划与许可检查再决定公开范围。仓库创建与公开是两件不同的事。
4. 因为电脑已有项目文件，本教程采用“网页空仓库＋本地首次上传”：不要预先添加README、.gitignore或LICENSE，也不要启动自动生成代码。这些文件可以在本地准备后再提交。
5. 点击Create repository。复制Quick setup里的HTTPS地址，形如https://github.com/你的账号/CodeCompass.git。示例中的“你的账号”不能照抄成真实地址。

已有代码上传时不预填文件，可以避免额外的初始历史冲突。[官方创建说明](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)

若已经创建了带README的非空远程，不要强推覆盖，也不要套用下面空仓库流程；先克隆到新目录，再把现有项目文件审查后复制进去提交。

## 5 第三步 邀请另一位成员

进入仓库Settings → Collaborators（部分界面可能显示为Collaborators and teams）→ Add people，输入队友账号并发送邀请；队友接受后才能访问私有仓库。两台电脑若由同一位成员本人操作，可使用其自己的登录；两人协作应各自登录。[官方邀请说明](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/repository-access-and-collaboration/inviting-collaborators-to-a-personal-repository)

随后确认：队友能用自己的账号打开仓库，且有项目所需写入权限。只给了网址但未接受邀请，不算双机接力配置完成。

## 6 第四步 第一台电脑建立本地仓库

先确认你正在D:/AIC算法主题赛，并且不存在已有.git。以下命令逐块执行；任一步报错先停下看原因，不能把后续命令盲目运行下去。
```powershell
Set-Location -LiteralPath 'D:\AIC算法主题赛'
Test-Path -LiteralPath '.git'
```
只有上面返回False、且确定这是要纳入版本管理的项目目录，才执行：
```powershell
git init -b main
$taskGitName = Read-Host '输入本人的提交署名'
$taskGitEmail = Read-Host '输入本人的GitHub提交邮箱或GitHub提供的noreply邮箱'
git config --local user.name "$taskGitName"
git config --local user.email "$taskGitEmail"
git config --local pull.ff only
```
署名与邮箱是提交记录，不是登录凭据；两位成员分别用自己的信息。这里设置只影响本项目，不改其他项目。

复制本包的忽略规则模板到根目录。仅在没有.gitignore时执行，不覆盖已有规则：
```powershell
if (-not (Test-Path -LiteralPath '.gitignore')) {
    Copy-Item -LiteralPath 'CodeCompass计划\templates\gitignore.txt' -Destination '.gitignore'
}
git status --short
```
模板排除虚拟环境、密钥、个人数据库、原始大数据、临时目录和Word锁文件。首次只提交本团队准备的计划与Word文档；赛事原始PDF和临时转换文件不顺手打包上传。以后代码/配置/去标识化小型结果按需要显式加入。

## 7 第五步 首次提交并上传

在根目录执行：
```powershell
git add -- .gitignore 'CodeCompass计划' 'Word文档'
git diff --cached --stat
git status --short
```
检查暂存文件名和敏感信息，确认只有准备共享的材料后再继续：
```powershell
git commit -m 'docs: initialize CodeCompass project plans'
$taskRepoUrl = Read-Host '粘贴你刚创建的空仓库HTTPS地址'
git remote add origin "$taskRepoUrl"
git push -u origin main
```
正常情况下origin只添加一次。如果提示origin已存在，先在本机检查已有远程地址是否正确，不要直接替换或把带凭据的URL贴进聊天。首次push可能需要浏览器登录。

上传后执行：
```powershell
git rev-parse HEAD
git ls-remote origin refs/heads/main
git status -sb
```
HEAD与远程main的SHA相同，且没有本次任务遗漏的修改，才可记首次同步成功。网页应能看到CodeCompass计划和Word文档。push失败只算本地已提交，不能交接为已同步。

## 8 第六步 第二台电脑克隆并配置

在第二台电脑选择要放项目的父目录。无需与第一台电脑使用相同盘符，也不要先另建第二个空GitHub仓库。例如目标文件夹为D:/CodeCompass且尚不存在：
```powershell
$taskRepoUrl = Read-Host '粘贴同一个CodeCompass仓库的HTTPS地址'
git clone "$taskRepoUrl" 'D:\CodeCompass'
Set-Location -LiteralPath 'D:\CodeCompass'
$taskGitName = Read-Host '输入本人的提交署名'
$taskGitEmail = Read-Host '输入本人的GitHub提交邮箱或noreply邮箱'
git config --local user.name "$taskGitName"
git config --local user.email "$taskGitEmail"
git config --local pull.ff only
git status -sb
git rev-parse HEAD
```
目标文件夹已存在时改用新的空目录；不要覆盖已有副本。克隆不自动安装Python依赖、下载被忽略的数据或配置API密钥；依照README另行准备。大数据需按来源/共享地址获取，并检查hash。

本次启动的双机验收：第一台能push；第二台能clone并看到同一SHA；第二台在自己的task/setup-b-sync分支增加一份无敏感内容的个人环境检查记录、commit和push；第一台fetch后能看到该分支。该测试也按下面任务分支流程执行，不能只以“网页能打开”作为接力成功。

## 9 每轮开始 必须先同步

先查看本地状态与分支：
```powershell
git status -sb
git branch --show-current
git fetch origin
```
若有未提交修改，先确认归属并保存自己的检查点，不直接pull覆盖。任务有两种情形：

新任务，且所需前置已合入main：
```powershell
git switch main
git pull --ff-only origin main
git switch -c task/A-D02-graph
```
上面的分支名是A-D02示例，其他任务使用自己的实际ID，新分支只创建一次。若前置任务还在分支上，不要假装main已包含它：先复核合入，或明确登记依赖哪个分支/提交后再工作。

接力一个未完成任务：不要另开重复任务，接管同一个分支。首次没有本地分支时执行：
```powershell
git switch --track origin/task/A-D02-graph
git pull --ff-only
```
本机已经有该分支时用git switch task/A-D02-graph，再git pull --ff-only。记录当前HEAD、输入数据hash和Owner，原Owner确认停止写入。同一任务分支同一时刻只有一个写入者。

## 10 每轮结束 必须保存并推送

1. 运行本轮必要验证，保留失败和未完成项。
2. 更新本人的状态、开发日志、贡献、交接、实验记录和图表索引。写明哪些完成、验证命令、下一步第一个动作。
3. 检查差异，显式加入本轮文件。例如A的图模块任务可执行：
```powershell
git status --short
git diff --check
git diff --stat
git add -- src/codecompass/graph docs/A report_materials/A
git diff --cached --stat
```
路径必须真实存在且属于本轮；首次建包或其他任务按实际文件清单调整，不能原样套用不存在路径。还需检查暂存内容无凭据/身份信息，本轮小型图表/配置/日志不能漏交。原始大文件用共享存储地址和hash交接。

4. 提交并推送当前任务分支。例如：
```powershell
git commit -m 'feat(A-D02): extract source graph with provenance'
git push -u origin HEAD
git rev-parse HEAD
git branch --show-current
```
首次设置upstream后同一分支也可git push。没有实际文件变化就记录“无新提交”及当前SHA，不创建空提交假装完成任务。

5. 核对远程分支包含刚才的HEAD。把上一条返回的实际分支名填入：
```powershell
$taskBranch = git branch --show-current
git ls-remote origin "refs/heads/$taskBranch"
git status -sb
```
仅push命令显示成功还应检查正确仓库/分支与SHA。若还有修改，区分本轮遗漏和他人工作；本轮关键文件没同步不能说交接完成。

## 11 已完成与未完成分别怎样处理

未完成/断额：在原任务分支写明PAUSED或BLOCKED，用wip(A-D02): ...描述保存真实工作并push；不合入main，不删除任务分支。下一台电脑按同分支接管，保留正在运行实验的信息。

完成：状态先为READY_FOR_REVIEW。队友读取diff、验收日志并做必要复核；在GitHub创建本团队仓库内部Pull Request，base选main、compare选实际任务分支。正文写问题、改动、验证和限制。确认通过后，由当次指定集成负责人Merge pull request，保存PR链接及合并后main SHA；不强制配置付费保护功能，也不假装已有人独立审核。无法独立审核时如实写自审及理由。

合并后两台电脑分别git fetch origin、git switch main、git pull --ff-only origin main，再开下一个任务分支。两人并行时不要同时编辑Word二进制文件，文档主责者汇总修改；代码不同目录也可能因接口或共享索引产生冲突，需要复核。

本计划的例行团队仓库维护包括按已确认origin提交/推送任务分支与指定负责人的集成；不能把它当作对任意第三方仓库发Issue/PR、公开私有仓库或提交比赛材料的授权。本次只编写流程，没有执行任何远程写入。

## 12 每天的维护清单

| 时点 | Agent必须做什么 | 验收依据 |
|---|---|---|
| 开始 | 核对工作区/分支/Owner，fetch并同步正确前置 | base SHA及前一棒交接 |
| 中途 | 每45—60分钟保存小检查点，记录当前进度 | 本地提交或明确可恢复现场 |
| 收尾 | 验证，更新日志/图表索引，检查暂存后commit | 命令结果、提交SHA、文件列表 |
| 交接 | push任务分支，核对远程SHA，移交Owner | remote SHA与本机一致 |
| 完成 | 复核后合入main，记录PR/合并SHA | 复核结论与main版本 |
| 未完成 | 任务分支保留，状态PAUSED/BLOCKED | wip记录与下一步动作 |

交接单无法包含“它自己最终提交的SHA”并同时让该SHA不变化。可在单内记录base SHA、分支、父提交、验证和下一步；push后在任务回复/交接通知中给出最终HEAD SHA。后续新记录可以引用上一提交SHA，不要反复为了自填SHA无限提交。

## 13 关键日期的额外维护

- D01（未做则10月16日补做）：创建私有空远程、邀请、首次上传；记录真实地址和权限。D01-B/补做：第二台clone及反向push演练。
- D02—D05：每轮代码/接口/配置/图表有提交，不提交本机依赖、API密钥或来源未明大文件。
- D06 10月20日：双方确认评测协议、数据与配置冻结后，给main上实际冻结提交创建v0.1-protocol-freeze标签，明确其不是最终作品。
- D07—D11：每次实验登记实际代码commit与数据/config hash；大原始记录用可访问路径+hash，不以Git提交替代数据备份。
- D12—D13：Markdown报告内容、图表清单与来源入库；Word/报告由主责者更新，视频大文件存共享位置并记录hash。
- D14 10月28日：候选版验收后创建v0.9-submission-rc1；修复后新建rc2，不覆盖旧标签。
- D15：第二台基于候选标签在新目录复现，保证验证对象正是提交候选版。
- D16：实际提交后，为对应代码创建v1.0-aic-submitted，另记报告/视频/平台回执SHA256；代码标签不自动包含未入库的大文件。

创建标签示例，仅在对应里程碑实际通过、main已同步时执行：
```powershell
git switch main
git pull --ff-only origin main
git tag -a v0.1-protocol-freeze -m 'Freeze evaluation protocol and configuration'
git push origin v0.1-protocol-freeze
```
不要今天预先创建这些里程碑标签；不要强推标签或用后续代码悄悄替换已提交版本。

## 14 常见问题

“commit了但另一台看不到”：检查是否push，以及对方是否fetch/pull了正确分支。

“push被拒绝 non-fast-forward”：通常远程有新提交。先fetch查看变化、保存本地工作，再按实际分支合并；不要用force绕过。冲突文件逐段核对，Word二进制冲突由文档主责汇总，不能两份任选一份覆盖。

“pull --ff-only失败”：说明不能简单快进；这是保留双方工作的提示。先保留当前提交和分支，再请Agent解释分叉/冲突并解决，不能reset --hard清理。

“文件被.gitignore忽略”：gitignore主要影响未追踪文件，不能让已提交秘密自动消失。若秘密误提交，先撤销/轮换凭据，再审查历史处理；仅删当前文件不代表历史已清除。

“上传太大”：不要把数据集、模型、视频当普通Git文件反复提交。优先放团队可访问的存储，Git记录来源/版本/hash和取得方法；确认需要版本管理的大文件后再评估Git LFS。

“退出了Agent，实验还在运行”：不要在另一台重复同一run。交接PID/机器/命令/日志位置，等待完成或明确标中断；跨机重跑新建run_id。

## 15 可直接发给首次配置Agent的话

> 请帮我配置本项目的Git协作。我会先在GitHub网页创建空的私有CodeCompass仓库、邀请队友并完成浏览器登录，再把真实HTTPS仓库地址给你。先检查当前目录是否已是Git仓库、是否有未提交工作及已有origin，禁止覆盖或重建已有历史。按本教程准备.gitignore，审查后只提交本团队计划/文档与明确允许的项目文件，设置本仓库个人署名。真实地址和浏览器认证就绪后完成首次push并核对远程SHA，记录实际URL、分支、版本、权限与结果。不要提交密钥/个人数据/临时目录/未经授权第三方内容；未完成认证或push失败如实写明。另一台电脑用clone接入并做任务分支反向推送演练；不得创建两个互不相干的项目仓库。

## 16 可直接发给每天执行Agent的话

> 每轮任务开始先读上一棒交接并检查git status、当前分支、Owner与HEAD，fetch后同步正确前置版本。新任务按main或明确登记的依赖分支开始；接力原任务继续同一分支。完成必要验证、状态/日志/贡献/交接与图表索引后，审查diff并显式暂存本轮文件，commit并push到已确认的团队任务分支，核对远程SHA。未完成任务保存wip并记PAUSED/BLOCKED，不合入main；完成任务记READY_FOR_REVIEW，经实际复核由指定集成负责人合入main。最终回复给出仓库、分支、base/HEAD/remote SHA、验证和未完成项；没有推送就不能写双机同步已完成。不得强推、覆盖他人工作、泄露凭据或把维护操作扩展为第三方社区提交。
