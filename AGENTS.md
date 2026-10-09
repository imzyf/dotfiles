# 仓库指令

本仓库使用 [chezmoi](https://www.chezmoi.io/) 将 `~/.local/share/chezmoi` 中的配置部署到 `$HOME`。[chezmoi 参考文档](https://www.chezmoi.io/reference/) 说明通用的源文件命名和模板机制；以下规则说明本仓库与上游的关系。

## 上游同步与本地改造

本项目以 [liby/dotfiles](https://github.com/liby/dotfiles) 为基础。[`sync-upstream.sh`](.github/scripts/sync-upstream.sh) 按照 [`sync-upstream.paths`](.github/scripts/sync-upstream.paths) 的清单复制上游文件。修改文件前先核对该文件对应的清单规则；同步脚本会覆盖选中的本地目标文件。

- 清单同步的上游文件，无论位于原路径还是映射后的副本路径，本地都不得自行修改。需要定制原路径同步的文件时，先调整同步清单，将上游文件映射为保留的副本，再修改另行维护的本地文件。
- 需要本地定制的文件，用清单映射保存上游副本（通常放在 `.chezmoitemplates/`），另行维护本地文件。格式允许时，本地文件可引入上游副本并只叠加必要改动。编辑前核对实际映射和消费者，不要假定所有文件都使用同一种覆盖方式。
- 清单中的 `!` 表示保留对应的本地路径；`上游路径 > 本地路径` 将上游文件复制到映射目标，并保留上游原路径对应的本地文件，即使其父目录也在同步范围内。

同步前检查清单将写入的目标；若同步的上游文件存在本地差异，先查明来源，不得将其作为本地改造保留。同步后检查 Git 差异；上游副本发生变化时，核对本地覆盖及其最终渲染或应用结果。复制成功本身不能证明配置仍然有效。

保存在 `.github/.upstream/` 的上游 [`AGENTS.md`](.github/.upstream/AGENTS.md) 和 [`CONCEPTS.md`](.github/.upstream/CONCEPTS.md) 可用于了解继承文件的工作流和设计。应用其中的做法前，先用本项目的同步清单、本地覆盖和实际消费者核对其适用性。
