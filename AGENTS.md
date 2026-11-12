# 仓库指令

本仓库使用 [chezmoi](https://www.chezmoi.io/) 将 `~/.local/share/chezmoi` 中的配置部署到 `$HOME`。[chezmoi 参考文档](https://www.chezmoi.io/reference/) 说明通用的源文件命名和模板机制；以下规则说明本仓库与上游的关系和本仓库的工作流程。

## 上游同步与本地改造

本项目以 [liby/dotfiles](https://github.com/liby/dotfiles) 为基础。[`.github/upstream-sync/rules`](.github/upstream-sync/rules) 按上游路径规定每个文件的处理方式，同一文件匹配多条规则时后面的生效。修改上游也有的文件前，先找到它的规则：

- `follow`：本地只整份接受上游改动，不得手改，包括 `>` 映射出的 `upstream.*` 副本。本地定制写在另行维护的本地文件里；格式允许时，本地文件引入副本，只叠加必要改动，上游结构变化使改动落空时用 `fail` 报错。各文件的覆盖方式不同，编辑前核对实际映射和消费者。要定制一个还没有副本的跟随文件，先把规则改为映射到 `upstream.*` 副本，再另建本地文件。
- `own`：本地文件由本仓库维护，可以直接修改。
- `watch`、`skip`：上游的这份文件不进入本仓库。要在同一路径维护本地版本，先把规则改为 `own`。
- `local`：上游没有这个路径的本地文件，按本地路径登记。`follow X > 副本` 的本地模板是 `X.tmpl` 时，这条规则已经隐含登记了它，不用另写。其他这类文件新增时加一条登记，`check` 列出的 `unregistered` 就是还没登记的文件。上游以后在登记的路径上加文件，准备任务不应用，`check` 报冲突。

改完规则运行 `.github/upstream-sync/bin/upstream-sync check`。上游改动只经由 `upstream-sync` 工单引入，不要从 `upstream` 分支或上游仓库手动复制文件。

[`.github/CONCEPTS.md`](.github/CONCEPTS.md) 说明本仓库跨文件的设计决定和与上游的差异。上游的 `AGENTS.md` 和 `.github/CONCEPTS.md` 用 `git show upstream:<路径>` 查看；应用其中的做法前，先用本仓库的规则、本地覆盖和实际消费者核对其适用性。

## 工作流程

- 提交前，对范围内每个改动过的非加密托管目标运行 `chezmoi status --exclude=encrypted <目标路径>` 和 `chezmoi diff --recursive --exclude=encrypted <目标路径>`。`diff` 和 `status` 不同，默认不递归，对目录目标什么也不输出。不要运行不带路径的 `chezmoi status` 或 `chezmoi diff`，它们可能生成解密后的目标内容。全仓库范围的状态检查只在用户要求做 drift 审计时运行，审计中无权访问的目标作为缺口报告，不为此扩大权限。`-` 是只在部署出的文件里有的内容，`+` 是只在渲染结果里有的内容。部署出的文件里多出的改动属于本次修改时才 re-add；无关的改动只报告，不修改。两边都改过时，展示限定范围的 diff。
- 停用或替换一个托管路径时，先核对确切的非加密部署路径，再在同一个改动里删除废弃的源文件和已部署的文件。不要加 `remove_` 条目、兼容旧数据的读取代码或其他迁移标记；之后的残留通过专门的审计处理。这类 commit 的 message 写出受影响的非加密目标路径或字段，说明删除原因，并注明需要保留的本地内容。
- 加密源文件可以和相关的非加密改动放在同一个 commit 里。commit message 只笼统地描述它，例如 `update encrypted zshenv`，依据元数据和用户对改动的归类来写，不推测明文改了什么。
- Claude Code、Codex 和 Pi 的根模板只引入 [`.chezmoitemplates/agents/local.md`](.chezmoitemplates/agents/local.md)。它的每个章节和上游根模板引入的一个片段同名，顺序也相同，不加没有对应片段的章节。写或改写 `local.md` 的规则前，先读同名的上游片段，再在 `.chezmoitemplates/agents/` 里找管同一件事的句子，因为相关约束可能写在别的片段里。找到了，就以上游的写法、条件和例外为基础来写，再结合本地的情况调整；找不到，才自己写。提交 `local.md` 的规则改动时，commit message 写明参考了哪个上游片段的哪句话；没有找到对应句子的，写明没有找到，以及这条规则是由什么问题引出的。
