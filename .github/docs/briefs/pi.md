# Pi

## 是什么，解决什么问题

[Pi](https://github.com/earendil-works/pi) 是一个在终端里运行的开源 coding agent，和 Claude Code、Codex 属于同一类工具。它的特点是不绑定某一家模型厂商：内置一份模型目录，也可以在 `models.json` 里自己声明 provider 和模型，再按模型设置推理强度（thinking level）。功能可以用 TypeScript 扩展和 npm、Git 包来加，命令、编辑器、footer 这类界面部分也能替换。

上游用 Pi 来跑 Claude Code 和 Codex 以外的模型，比如通过一个 model gateway 访问的各家模型，也用它在 Rex pane 里做跨厂商的 review。

## 上游怎么用

- 安装：`claude` 和 `pi` 都由一个 `run_once` 脚本用官方安装器装成 managed install，不用 Homebrew 或 npm，因为只有 managed install 会固定它的传递依赖。Pi 不会自己更新，后台的 unattended-upgrades job 定期运行 `pi update`。
- 配置分两种管理方式：
  - `~/.pi/agent/models.json` 整份由模板渲染：声明 gateway provider、每个模型的上下文预算、输出上限和 `thinkingLevelMap`。密钥不写进文件，用凭据命令在运行时读取。
  - `~/.pi/agent/settings.json` 由 modifier 部分管理：设置片段里声明的顶层 key 每次 apply 都覆盖，没声明的 key 保留，这样 Pi 在 UI 里写入的其他状态不受影响。
- 全局指令：`~/.pi/agent/AGENTS.md` 引入和 Claude Code、Codex 相同的共享指令。不用 `APPEND_SYSTEM.md`，因为项目里的同名文件会整个替换全局的那份，而 `AGENTS.md` 是全局和项目两份一起加载。
- 扩展：命令 sandbox、guard 适配器、编辑器和 footer 来自单独的 pi-extensions 包，由脚本从 Git 安装；压缩后提醒的扩展因为要渲染共享的提示文本，留在仓库里。
- 设置片段里几个影响日常使用的选择：`shellPath` 让命令在 Homebrew bash 里运行，因为模型写的是 bash；`enabledModels` 只开放 gateway 和指定的 Anthropic 模型，不开放整个内置目录；`tuiMode = "regular"` 把选中和复制交给终端，在 Mac 上看远程的 Pi session 也能直接复制。

## 要点和坑

- 改了设置后，`/reload` 只重新读文件，模型的 thinking 默认值要再用 `/model` 选一次模型才生效；改了 `enabledModels` 要开新 session（`/new` 或新的 `pi` 进程）。resume 的 session 可能恢复它当时记录的模型和推理强度。
- modifier 保留没声明的 key，所以从设置片段里删掉一个 key，部署出的 `settings.json` 里还会留着旧值，要手动删。
- 模板里删掉一个整份管理的文件时，chezmoi 不会删除已经部署的文件，例如曾经的 `~/.pi/agent/keybindings.json`。
- `~/.pi/agent` 里还有凭据、session、已安装的包和信任记录，都归 Pi 自己管理，这个目录不能整个纳入 chezmoi。
- `defaultProjectTrust = "always"` 让每个目录的项目级设置、包和扩展都直接加载，不再询问。这是有意的选择，打开不信任的仓库时要记得这一点。
- 推理强度映射要按 gateway 实际支持的值来写：请求成功不代表要求的强度真的生效了，gateway 可能把它映射成别的值。

## 延伸阅读

- [Pi 的设置文档](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md)：`enabledModels`、`modelThinkingLevels`、`tuiMode` 等设置项。
- [模型配置文档](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models-configuration.md)：自定义 provider 和 `thinkingLevelMap`。
- [压缩文档](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/compaction.md)：上下文预算和 `compaction.reserveTokens` 的关系。
- 本仓库 [CONCEPTS 的 Pi 配置一节](../../CONCEPTS.md#pi-配置)：本地的具体约定。

## 核对依据

按上游 commit `81d3b86df`、本机 Pi 1.6.0 核对。
