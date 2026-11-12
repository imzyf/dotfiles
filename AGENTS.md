# 仓库指令

本仓库使用 [chezmoi](https://www.chezmoi.io/) 将 `~/.local/share/chezmoi` 中的配置部署到 `$HOME`。[chezmoi 参考文档](https://www.chezmoi.io/reference/) 说明通用的源文件命名和模板机制；以下规则说明本仓库与上游的关系。

## 上游同步与本地改造

本项目以 [liby/dotfiles](https://github.com/liby/dotfiles) 为基础。[`.github/upstream-sync/rules`](.github/upstream-sync/rules) 按上游路径规定每个文件的处理方式，同一文件匹配多条规则时后面的生效。修改上游也有的文件前，先找到它的规则：

- `follow`：本地只整份接受上游改动，不得手改，包括 `>` 映射出的 `upstream.*` 副本。本地定制写在另行维护的本地文件里；格式允许时，本地文件引入副本，只叠加必要改动，上游结构变化使改动落空时用 `fail` 报错。各文件的覆盖方式不同，编辑前核对实际映射和消费者。要定制一个还没有副本的跟随文件，先把规则改为映射到 `upstream.*` 副本，再另建本地文件。
- `own`：本地文件由本仓库维护，可以直接修改。
- `watch`、`skip`：上游的这份文件不进入本仓库。要在同一路径维护本地版本，先把规则改为 `own`。
- 上游没有的路径由本仓库自有，不受规则约束。

改规则单独一个 commit，原因写进 commit message；改完运行 `.github/upstream-sync/bin/upstream-sync check`。上游改动只经由 `upstream-sync` 工单引入，不要从 `upstream` 分支或上游仓库手动复制文件。

[`.github/CONCEPTS.md`](.github/CONCEPTS.md) 说明本仓库跨文件的设计决定和与上游的差异。上游的 `AGENTS.md` 和 `.github/CONCEPTS.md` 用 `git show upstream:<路径>` 查看；应用其中的做法前，先用本仓库的规则、本地覆盖和实际消费者核对其适用性。
