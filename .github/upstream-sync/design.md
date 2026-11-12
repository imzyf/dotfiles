# 上游同步设计

## 1. 总体结构

整个流程都在本机运行，不使用 GitHub Actions。GitHub 只用来存放上游镜像分支和工单。

上游的新 commit 先进入镜像分支；准备任务按规则把它们准备成工单里的 commit，并生成报告；用户在处理会话里逐个决定；处理过的部分合进 `main`，再由 chezmoi 应用到机器上。

| 组成部分 | 作用 | 位置 |
|---|---|---|
| 上游镜像分支 | 原样保存上游的 commit，供查看和引用 | origin 的 `upstream` 分支 |
| 处理方式规则 | 确定每个上游文件的处理方式、本地位置和风险类别 | `.github/upstream-sync/rules` |
| 工单 | 一个 PR，分支上放着待处理的上游改动 | origin 的 `upstream-sync` 分支和对应的 PR |
| 准备任务 | 更新镜像、准备 commit、生成报告 | 脚本，先手动运行，跑顺以后由 launchd 定时运行 |
| 处理会话 | 用户坐下来处理工单 | agent 加载 `upstream-sync` skill |

不使用 GitHub Actions 的原因：报告只能在本机生成（C9），用户也只在电脑前处理同步，线上提前检查上游没有用处。少一个运行环境，脚本只需要在本机测试，也不需要在 GitHub 上配置 Actions 的权限。

机械步骤都写成脚本，有测试（R34）。需要理解和判断的步骤写进 skill，判断标准和报告格式都写在 skill 里。

## 2. 上游镜像分支

- 准备任务用 URL 直接 fetch `https://github.com/liby/dotfiles` 的 `main`，不配置 remote（C5）。
- fetch 到的结果快进到本地的 `upstream` 分支，再 push 到 origin。换一台机器时，`git fetch origin` 就会拿到它（R32）。完整的上游 commit 和 diff 都在这个分支上查看（R10）。
- push 用的是用户现有的 Git 凭据，也就是钥匙串里保存的 HTTPS 凭据。启用 launchd 时，要确认后台运行也能 push 成功。
- 镜像分支原样带着上游 `.github/workflows/` 里的 workflow。GitHub 收到 push 时会运行被 push 的分支自己带的 workflow。上游的 workflow 目前都只在 push 到 `main` 时触发，但上游随时可能修改（C10）。本仓库没有自己的 workflow，所以在仓库设置里关闭 GitHub Actions。
- 如果上游改写了历史，快进会失败（C10）。这时准备任务停下来，把旧的 `upstream` 留成 tag `upstream-archive/<日期>`，然后在报告里提醒用户，不自动覆盖。
- 保存镜像的主要原因是 R36：本地 commit 用上游 commit 的 hash 引用原改动，上游即使改写历史或者删库，这些 hash 在本仓库里也仍然能查到。

## 3. 处理方式规则

### 3.1 格式

规则文件取代现在的 `sync-upstream.paths`。每行一条规则：

```
# 起点：第一个纳入新流程的上游 commit 之前的位置
base       2e8b1f355

# 处理方式  上游路径模式                                   [> 本地路径]
follow     .chezmoiscripts/**
own        .chezmoiscripts/run_onchange_after_setup-macos-defaults.sh.tmpl
follow     dot_zshrc                                      > .chezmoitemplates/zsh/upstream.dot_zshrc
follow     .chezmoitemplates/claude/settings.json         > .chezmoitemplates/claude/upstream.settings.json
own        Brewfile
watch      dot_agents/skills/oracle/**
skip       **/encrypted_*
skip       **/*.test.*

# 风险类别  类别           上游路径模式
risk       silent         dot_config/git/**
risk       machine-state  .chezmoiscripts/**
risk       machine-state  Brewfile
risk       daily-tool     dot_claude/**
```

- `base` 只有一行，记录起点：这个 commit 之后的上游 commit 才进入待处理列表。
- 处理方式有四个关键字：`follow` 跟随、`own` 自己维护、`watch` 观察学习、`skip` 不需要。没有被任何规则匹配的文件属于未分类（R2、R6）。
- 模式语法沿用现在清单的规则：`*` 只匹配一级路径，`**` 匹配零级或多级目录。
- 同一个文件匹配多条处理方式规则时，后面的规则生效，和 `.gitignore` 的习惯一样。
- `> 本地路径` 只用于跟随的文件，表示上游文件复制到这个本地路径，由本地模板继承后再修改，也就是 R4 说的继承后调整。
- 风险规则可以叠加，一个文件可以同时属于几个风险类别（R24）。三个类别对应 R24 的三条标准：`silent` 出了问题也不报错，`machine-state` 直接改变机器状态，`daily-tool` 影响日常离不开的工具。路径规则只是最低保证：AI 写说明时还要按 R24 的三条标准逐个判断，路径没标出来、但符合标准的改动也要标出来。
- 默认带两条 `skip`：上游的加密文件本项目解不开（C4），上游的测试不重复运行。
- 准备任务每次运行先校验规则文件，处理会话改过规则文件以后也要校验，再提交。以下情况是错误，准备任务停下来报错，不猜测用户的意思：
  - 关键字不是 `base`、`follow`、`own`、`watch`、`skip`、`risk` 之一，或者字段数不对；`>` 用在 `follow` 以外的规则上；风险类别不是 `silent`、`machine-state`、`daily-tool` 之一；路径里有空格。
  - `base` 不是正好一行，或者这个 commit 不在镜像分支上。
  - `>` 后面的本地路径不存在。
- 以下情况不算错误，写进报告提醒用户：
  - 某条规则在上游当前版本里一个文件都匹配不到，可能是拼错了，也可能是上游改名或删除了文件（C10）。
  - 某条规则匹配到的文件全被后面的规则改了处理方式，这条规则已经没有作用。
  - 未分类的文件（R2）。

### 3.2 改变处理方式

- 改变处理方式就是改规则文件，单独一个 commit，原因写在 commit message 里（R8）。
- 改成跟随时，脚本直接从镜像分支复制上游当前的版本，不回头处理以前跳过的 commit（R22）。
- 从跟随改成不需要或观察学习时，删除本地对应的文件（R1）。机器上已经部署的那份列进手动步骤，由用户决定删不删。
- 上游在已有规则覆盖的目录里新增文件时，准备任务按 diff 里的新增状态识别出来，在报告里作为新文件单独提醒（R7）。准备好的 commit 照常包含这个文件，并在 message 的 `New upstream files` 里列出；处理会话遇到时必须让用户明确确认。用户不要时，加一条规则把它归入不需要，并从 commit 里去掉。apply 只在处理会话结束时发生，所以确认一定在新文件生效之前。

## 4. 工单

### 4.1 分支上的 commit

工单是一个 PR，分支叫 `upstream-sync`，基于 `main`。分支上分两段：前面是本次会话已经处理过的 commit，后面是准备好、还没处理的 commit。

`upstream-sync` 分支只在 worktree `~/Code/worktrees/chezmoi-upstream-sync` 里检出，准备任务和处理会话都在这里操作。`~/.local/share/chezmoi` 是 chezmoi 的源目录，`chezmoi apply` 部署的是这里检出的版本，所以它始终停在 `main` 上，只用来做收尾时的合并和 apply。这样处理到一半时，任何一次 apply 都不会把没处理的改动部署出去，日常改配置也不用等同步结束。两个目录共用同一个 `.git`，会话做好的 commit 不用 push 就能在源目录里合并。

每个待处理的上游 commit 对应一个准备好的 commit，按上游的顺序排列。列上游 commit 时跳过 merge commit，只处理带实际改动的 commit，这样每个改动只处理一次。

- 内容只包含对应得到本地文件的改动：跟随的文件按规则改写路径后应用，删除和改名也一样应用（R19）。对应不到任何本地文件时，是一个空 commit。
- 作者是用户。合进 `main` 的 commit 只包含上游改动里对应得到本地文件的部分，还带着用户的中文说明和决定，不等于上游的原 commit，所以上游作者只记在 trailer 里，只写名字。
- message 保留上游的原文，后面由脚本补上改了哪些文件、哪些没改和原因、上游新增了哪些文件，最后是三行 trailer：

```
feat(claude): add statusline hook

<上游原来的 message 正文>

Applied:
  .chezmoitemplates/claude/settings.json -> .chezmoitemplates/claude/upstream.settings.json
Not applied:
  dot_config/oracle/config.toml (skip)
New upstream files:
  none
Risk: daily-tool

Upstream-Commit: 4a1c2e7f...
Upstream-Author: Bryan Lee
Upstream-Decision: pending
```

准备任务在后台运行，没法输入 GPG 密码，所以准备好的 commit 不签名。处理会话改写每个 commit 时会重新签名，所以合进 `main` 的 commit 都有签名。

### 4.2 状态和同步点

- 每个处理过的上游 commit，在 `main` 上都有一个带 `Upstream-Commit:` 的 commit，`Upstream-Decision:` 写明处理结果：`accepted`、`adjusted`、`combined` 或 `skipped`（R20）。
- 待处理列表等于镜像分支上起点之后的 commit，减去 `main` 上已经出现在 trailer 里的 commit。所以不按顺序处理也没有问题（R16），不需要另外的状态文件。
- 起点写在规则文件的 `base` 行（3.1）。

### 4.3 PR 的标题、描述和评论

- 标题和描述由准备任务每次重写：待处理的数量、起始日期，按风险和处理方式分组的清单，每项链接到镜像分支上的原 commit。
- 中文报告的公开部分作为评论追加到 PR 上（R37）。本机影响写在本地的报告文件里，不发到 PR 上（R31）。
- 处理会话开始时给 PR 加 `in-progress` 标签，结束时去掉。准备任务看到这个标签，只更新镜像，其余都不做，避免和处理会话同时改分支。标签在 GitHub 上，换一台机器也有效。
- 标签挂了超过一天，准备任务在终端输出里提醒用户，因为处理会话可能中途中断，没来得及去掉标签。
- 准备任务另外用一个本地锁文件，防止两次准备任务同时运行，比如手动运行时 launchd 恰好也触发了一次。

## 5. 准备任务

### 5.1 触发

- 前几次手动运行，确认准备和报告的结果符合预期以后，再启用 launchd。
- 启用后，launchd 每天定时运行一次。电脑睡眠时错过的会在唤醒后补跑；再加上登录时运行一次，覆盖关机的情况（R29，C7）。
- 处理会话开始时检查报告是否对应工单当前的状态，不对应就当场重新生成。
- 启用 launchd 以后也可以随时手动运行。

### 5.2 步骤

1. 取得锁文件，已经有一次准备任务在运行就退出（4.3）。
2. 更新镜像分支（第 2 节）。PR 挂着 `in-progress` 标签时到此结束。
3. 算出待处理列表（4.2）。
4. 把还没准备的上游 commit 逐个准备到 `upstream-sync` 分支上（4.1）。某个 commit 应用失败时，比如它依赖一个被推迟的 commit，就生成一个说明失败原因的空 commit，交给处理会话。
5. 用 `gh` 新建或更新 PR。
6. 生成报告：
   - 脚本为每个 commit 整理出结构化数据：上游 message、diff、每个文件的处理方式和风险类别、对应的上游 PR。
   - 脚本在 worktree 里分别渲染每个 commit 前后受影响的目标，算出每个 commit 对渲染结果的改动。这部分只写进本地报告。
   - `claude -p` 加载 skill，读结构化数据，写每个 commit 的中文说明和总览。它只读上游的公开内容，所以写出的内容可以公开。
   - 跟随或观察学习的文件里出现新工具或新概念时，起草简报，作为一个待处理的 commit 放到分支上（R38）。
   - 这次运行准备了新的 commit 时，脚本把说明和总览作为一条新评论发到 PR 上；没有新 commit 就不发，避免重复的评论。完整报告连同本机影响每次都写到 `~/.local/state/upstream-sync/`。

## 6. 处理会话

### 6.1 逐个决定

用户在 worktree 里启动 agent，agent 加载 skill，按总览的顺序逐个处理：

| 决定 | 分支上的操作 |
|---|---|
| 接受 | 在 message 最前面加中文说明，`Upstream-Decision` 改成 `accepted`，签名 |
| 接受后调整 | 同上，改成 `adjusted`，后面加一个本地修改的 commit，理由写在 message 里 |
| 合并处理 | 几个 commit squash 成一个，附上所有上游原文和多个 `Upstream-Commit`，改成 `combined` |
| 跳过 | 去掉内容，留成空 commit，写上中文说明和理由，改成 `skipped` |
| 推迟 | 移到待处理部分的最后 |
| 提前处理 | 移到待处理部分的最前面（R16） |
| 改变处理方式 | 加一个修改规则文件的 commit，原因写在 message 里（3.2），然后照常处理。确认采用新文件也是这种情况 |

跳过一个改了跟随文件的 commit 会让文件偏离上游，违反 R17。遇到这种情况，skill 要求用户二选一：把这个文件改成自己维护，或者接受后用本地覆盖抵消。

### 6.2 收尾

一次会话结束时，处理过的那一段合进 `main`：

1. 在 `main` 上用 `git merge --no-ff` 合进处理过的那一段，merge commit 写明这次处理了哪些上游 commit。先不 push。
2. 按机器此刻的状态预览影响（R26），列出重点类别的改动（R24）和无法撤销的改动（R25）。预览有问题就撤销这次本地合并，回到分支上继续处理。预览和 apply 的范围相同：
   - 这次合并改动的文件对应的目标。
   - 会运行的脚本。软件包安装、系统设置这些改动由 `.chezmoiscripts/` 里的脚本完成，只 apply 文件不会运行它们。用 `chezmoi diff --include=scripts --exclude=encrypted` 找出会运行的脚本，其中包括内容引用了改动文件的 `run_onchange_` 脚本，比如 `Brewfile` 改了，安装软件包的脚本也会运行。和这次合并无关、但也会运行的脚本单独标出来，由用户决定这次是否运行。脚本的目标路径是 `~/.chezmoiscripts/<名字>`，可以和文件目标一起传给 chezmoi。
   - 不做整体 apply，因为整体 apply 会覆盖和这次同步无关的机器上的改动，比如手动改过、还没收进仓库的配置。所有命令都带 `--exclude=encrypted`：apply 加密文件需要解密，只能由用户来做；上游的加密文件本来就归入不需要（C4），排除它们不会漏掉同步的内容。
3. 对上一步的范围运行 `chezmoi apply --exclude=encrypted`。
4. 验证（R27）：重新生成 chezmoi 配置并渲染，和合并前对比，确认本地差异仍然生效；列出要手动做的事，比如重新运行 `chezmoi init`、重启服务、删除上游已经删掉的文件在机器上的部署结果。
5. push `main`。把工单分支重置到新的 `main`，去掉 PR 的 `in-progress` 标签，再运行准备任务，按当前规则重新准备剩下的待处理 commit。本次 session 可能改过规则，原来准备好的 commit 按旧规则生成，不能直接 rebase。准备任务用 `--force-with-lease` push，远端分支在别处被改过时不会覆盖。剩下的为零时，GitHub 会因为分支已经全部进入 `main` 把 PR 标成已合并；下次准备任务发现新的上游 commit 时再开新 PR。

这样每次会话处理的改动当次就生效（R21），没处理的留在工单里。每个 merge commit 对应一次会话，能看出哪些改动是同一次同步进来的。

## 7. 知识保留

- 合进 `main` 的上游 commit，message 依次是：中文说明、上游原文、改动的文件清单和 trailer（R36）。用 `git log --grep 'Upstream-Commit'` 或者 `git log -- <path>` 就能查到。
- 跳过的 commit 是空 commit，`git log -- <path>` 查不到。要用 `git log --grep '<路径>'`，从 message 的 `Not applied` 清单里找到它。
- 简报放在 `.github/docs/briefs/<工具名>.md`（R46）。

## 8. 文件位置

| 内容 | 位置 |
|---|---|
| 规则文件 | `.github/upstream-sync/rules` |
| 脚本和测试 | `.github/upstream-sync/bin/`、`.github/upstream-sync/tests/` |
| 需求和设计文档 | `.github/upstream-sync/requirements.md`、`.github/upstream-sync/design.md` |
| skill | `.claude/skills/upstream-sync/SKILL.md` |
| launchd 配置 | `private_Library/LaunchAgents/` 下的 plist，由 chezmoi 部署 |
| 本地报告和准备任务的锁文件 | `~/.local/state/upstream-sync/` |
| 工单分支的 worktree | `~/Code/worktrees/chezmoi-upstream-sync` |
| 简报 | `.github/docs/briefs/` |

以 `.` 开头的路径不会被 chezmoi 部署（C1），所以规则、脚本、skill 和简报都不会出现在 `$HOME` 里。

## 9. 迁移

1. 在 GitHub 的仓库设置里关闭 GitHub Actions，放在第一次 push 镜像分支之前。
2. 在 Renovate App 的授权范围里移除本仓库，版本升级全部跟着上游走。本仓库的 Renovate 只改跟随的文件，会让它们偏离上游（R17），之后上游改同一行时，准备 commit 就会应用失败。上游的 `.github/renovate.json` 归入不需要。
3. 把 `sync-upstream.paths` 转成规则文件，起点定为 `2e8b1f355`，也就是最后一次完整同步时上游的位置：
   - 普通路径转成 `follow`。
   - `上游 > 本地` 转成带本地路径的 `follow`。本地路径在 `.github/.upstream/` 下的，原来只是参考副本：本地有对应文件的转成 `own`，比如 `AGENTS.md`；没有的转成 `watch`，比如 `.github/CONCEPTS.md`。
   - `!路径`：本地有这个文件的转成 `own`，没有的转成 `skip`。这些规则排在目录的 `follow` 后面，因为后面的规则生效。
   - 清单里没有的上游文件，逐个归入 `watch` 或 `skip`，拿不准的先归入 `skip`。
4. 核对跟随文件的起点：逐个比较本地的跟随文件和 `2e8b1f355` 时的上游版本。准备 commit 按 diff 应用上游的改动，本地文件和起点不一致，应用就会失败，或者把本地的偏离藏起来。有差异的查明来源：本地修改的，改成 `own` 或者改用继承后调整；上次没做完的同步或本仓库的 Renovate 留下的，恢复成起点的版本，让工单重新带进来。
5. 规则文件和上面的修正提交到 `main`。然后建立镜像分支，生成第一张工单，起点之后的 55 个上游 commit 都在里面。
6. 删除 `.github/.upstream/`。自己维护的文件，上游的版本以后从镜像分支查看。
7. 更新本仓库的 `AGENTS.md`，把同步清单和 `.github/.upstream/` 的说明换成新的规则文件和流程。
8. 第一张工单处理完以后，删除 `sync-upstream.sh`、`sync-upstream.paths`、外部 clone `~/Code/o-liby-dotfiles` 和 `stash@{0}`。

## 10. 已定的实施安排

- **D1** skill 放在 `.claude/skills/upstream-sync/`。agent 在沙箱里不能写这个目录，创建和修改 skill 时临时关闭沙箱。
- **D2** 前几次手动运行准备任务，跑顺以后再启用 launchd，到时候再定每天运行的时间。
- **D3** 第一张工单包含 `2e8b1f355` 之后的全部上游 commit，按积压的方式分几次处理。
