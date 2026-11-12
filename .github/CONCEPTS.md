# 仓库概念

## 与上游的关系

本仓库以 [liby/dotfiles](https://github.com/liby/dotfiles) 为基础。[`upstream-sync/rules`](upstream-sync/rules) 按上游路径给每个文件定一种处理方式：`follow` 的文件整份接受上游改动，`own` 的文件由本仓库维护，`watch` 的文件不进入本仓库、上游改动只用来学习，`skip` 的文件本仓库不需要。上游没有这个路径的本地文件用 `local` 按本地路径登记；引入 `upstream.*` 副本再修改的本地模板只比上游文件多一个 `.tmpl` 后缀时，由 `follow` 的 `>` 映射隐含登记。上游以后用到这些路径时，改动不会写进来。上游改动由 [`upstream-sync`](upstream-sync/) 整理成工单，逐个 commit 决定后才合并进 `main`，所以跟随的文件停在最后一次处理到的上游 commit。本仓库不运行 Renovate，`.github/dev-tools` 里的版本和 `.chezmoiexternal.toml` 里固定的 commit 也随工单从上游进来。

跟随的文件需要本地改动时用覆盖层：上游文件复制成 `.chezmoitemplates/` 下的 `upstream.*` 副本，本地模板用 `includeTemplate` 引入副本，只叠加差异。叠加的改动依赖副本里的某段内容，例如一行 `zoxide init` 或结尾的一组 include；上游改掉这段内容时，本地模板用 `fail` 让渲染报错，不让改动静默失效。哪些上游文件有 `upstream.*` 副本，以 [rules](upstream-sync/rules) 里带 `>` 的规则为准；本地文件不一定引入副本。

## 初始化

初始化保持交互式，因为它涉及账号相关的输入、系统级安装和存放在硬件上的 GPG 私钥。脚本负责文件同步表达不了的工具安装和机器状态。

[`.chezmoiscripts`](../.chezmoiscripts/) 里的脚本使用 [chezmoi 的脚本生命周期](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/)，本仓库没有自己的执行器。文件名不带排序前缀，所以一个脚本依赖同一阶段的另一个脚本时，先检查对方的结果再写入。`run_once` 和 `run_onchange` 的安装不做健康检查：工具被删掉，或者换了一张密钥不同的卡，都要显式重新调度脚本才会修复。

重新调度单个 `run_onchange` 脚本，用 [`chezmoi state delete`](https://www.chezmoi.io/reference/commands/state/#delete) 删除 `entryState` bucket 里 key 为 `$HOME/.chezmoiscripts/<目标名>` 的记录，目标名去掉 `run_onchange_before_` 或 `run_onchange_after_` 前缀和 `.tmpl` 后缀。例如只重新调度 `run_onchange_after_setup-gitconfig.sh.tmpl`，再检查并 apply 这个脚本：

```sh
chezmoi state delete --bucket=entryState --key="$HOME/.chezmoiscripts/setup-gitconfig.sh"
chezmoi status --exclude=encrypted "$HOME/.chezmoiscripts/setup-gitconfig.sh"
chezmoi diff --recursive --exclude=encrypted "$HOME/.chezmoiscripts/setup-gitconfig.sh"
chezmoi apply "$HOME/.chezmoiscripts/setup-gitconfig.sh"
```

这个 key 不能重新调度 `run_once` 脚本。只有确实要重跑一整类脚本时，才用 [chezmoi 重置整个 bucket 的方法](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/#clear-the-state-of-all-run_onchange_-and-run_once_-scripts)：删除 `scriptState` 会重新调度所有 `run_once` 脚本，删除 `entryState` 会重新调度所有 `run_onchange` 脚本，包括需要 YubiKey 的 GPG 设置。完整 apply 之前，先准备好这些脚本需要的交互条件。

安装脚本里的注释也是运行输入：改注释可能[让脚本重跑](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/#understand-how-scripts-work)，改 `Brewfile` 会改变安装脚本里嵌入的 hash。只有重跑在计划内时才改它们。

脚本运行的大多数工具会打印进度或无事可做的提示，这些输出只在失败时有用。这类外部命令通过 [`.chezmoiscripts/.lib/step.zsh`](../.chezmoiscripts/.lib/step.zsh) 里的 `step` 运行，脚本从 `$CHEZMOI_SOURCE_DIR` source 这个库：`step` 用一行状态代替命令输出，只在命令失败时回放输出，`chezmoi apply -v` 则直接显示输出。没事可做时什么都不打印的命令不需要包装。被包装的命令从 `/dev/null` 读输入，运行时只显示状态行，所以需要用户参与的命令不包装，例如厂商安装程序、`brew bundle`、sudo、浏览器登录、启动 GUI 和 YubiKey 操作。修改这个库不改变任何脚本的内容，不会触发重跑，各脚本下次运行时生效。脚本改用它会改变脚本内容，所以重跑需要用户参与的脚本，只在本来就要改它时顺便改用。

这些依赖决定了顺序：

- Homebrew 和 [`Brewfile`](../Brewfile) 里的包提供后续脚本用到的工具。
- proto 从 `~/.proto/.prototools` 解析所有工具版本，这个文件由 chezmoi 在同步文件时从 [`dot_proto/dot_prototools`](../dot_proto/dot_prototools) 写入。dev-tools 脚本在 `after` 阶段运行，这样 proto 在安装运行时、协调 npm、uv 和 mbx 工具之前能读到这份声明。`before` 阶段这个文件还不存在，proto 会拒绝安装 Node.js 版本要求未配置的工具。
- `claude` 和 `pi` 由 `run_once_after_install-agent-clis.sh` 用厂商安装程序安装，`codex` 来自 `Brewfile` 声明的 `codex` cask。这个脚本在 `after` 阶段运行，因为 Pi 需要 `~/.proto/.prototools` 声明的 Node。
- gpg-agent 和 keyboxd 由 launchd LaunchAgent 管理，`~/.gnupg/common.conf` 里的 `no-autostart` 阻止任何客户端隐式启动它们：从 sandbox 里的 agent shell 启动的 daemon 会一直留在那个 sandbox 里，访问不到 YubiKey。GPG 脚本在 `before` 阶段、Homebrew 安装之后写入并 bootstrap 这些 job，因为 chezmoi 同步加密文件时需要私钥。它是以 daemon 链接的 Homebrew keg 为触发条件的 `run_onchange`，所以 gnupg 或它的某个库升级后，daemon 会用磁盘上的新文件重启。dirmngr 故意不管理，keyserver 操作会明确失败，而不是自动启动它；脚本通过 HTTPS 从卡上存储的 URL 导入卡的公钥，不用卡的 `fetch` 命令。

上游还会创建一个区分大小写的 `Code` APFS 卷，本仓库跳过了这个脚本，`~/Code` 是 home 所在卷上的普通目录。

## 软件包和工具的归属

一个工具在哪里声明，取决于它能容忍多久的更新延迟：

- Coding agent 不能容忍延迟。`claude` 和 `pi` 由 `after` 阶段的一个 `run_once` 脚本用厂商安装程序安装，不固定版本；`claude` 自己更新，`pi` 只在运行 `pi update` 时更新，所以由 unattended-upgrades job 调用。Pi 用它的托管安装，不用 Homebrew formula 或 npm 包，因为只有托管安装固定了传递依赖。`codex` 来自 `homebrew/cask` 官方的 CLI cask，它的更新也交给同一个 job，它报告的更新命令是 `brew upgrade --cask codex`。
- 和 agent 相关的 CLI（`ctx7`、`oracle`）也在 `Brewfile` 里；`oracle` 来自 `steipete/tap`，因为它没有自更新。`brew bundle` 没有 gh extension 的条目类型，所以 [`run_onchange_after_install-gh-extensions.sh`](../.chezmoiscripts/run_onchange_after_install-gh-extensions.sh) 在 apply 时安装 `gh stack` 和 `gh actions-lock`，不需要 gh 登录。Claude Code 的 sandbox 写不了 gh 的 extension 目录，agent 无法在第一次使用时自己安装。
- 后台开发工具（`typescript`、`typescript-language-server`、Pyright、mbx）的版本固定在 `.github/dev-tools`。
- 运行时（通过 proto 管理的 `node`、`bun`、`pnpm`、`go`，以及通过 rustup 管理的 Rust）由各自的管理器解析，不固定版本，也没有等待期。`oracle` 和 `ctx7` 的 formula 会拉入 Homebrew 的 `node`（`oracle` 还有 `pnpm`），本仓库的 `Brewfile` 还装了 Homebrew 的 `go`。它们在 `PATH` 上排在 proto 的 shim 后面，不是运行时渠道，所以这些 CLI 用的是本仓库不固定版本的 Node。
- GUI 和日常 app 是 `Brewfile` 里的 cask，只在 App Store 上架的 app 是 `mas` 条目。

`Brewfile` 由本仓库维护。它保留上游的命令行工具、agent 相关工具和 `entwining/tap` 里的工具，去掉本机不用的 app 和服务 CLI，例如 Snowflake 和 Resend 的 CLI，再加上自己的 app 和 PHP、Composer 等开发工具。

Brewfile 安装脚本用 [`brew bundle --no-upgrade`](https://docs.brew.sh/Manpage#bundle-subcommand) 把安装和升级分开。formula 和 cask 的升级归 unattended-upgrades job，App Store 的更新偏好留在本机。

托管的 [LaunchAgent](../private_Library/private_LaunchAgents/com.liby.unattended-upgrades.plist.tmpl) 声明后台升级的时间表，并有意在登录或重新加载时立即运行一次。它的 [helper](../private_Library/private_Application%20Support/com.liby.unattended-upgrades/executable_unattended-upgrades) 有自己的可执行路径，这样登录项能用文件名称呼这个 job。[注册脚本](../.chezmoiscripts/run_onchange_after_setup-unattended-upgrades.sh.tmpl) 嵌入了这两个文件的 hash，任一文件变化都会在文件同步后重新加载 job；改 `Brewfile` 不会重新加载它。

helper 把 Homebrew 升级和 Pi、gh extension、Rust 的更新、定期清理包缓存以及升级后的维护放在一起。它和 Brewfile 安装脚本都会清除 Codex cask 可执行文件的 quarantine 属性，因为只批准 CLI 本身覆盖不到它的辅助程序和替换后的文件。helper 还会重启缺失或过期的 GnuPG daemon；只升级了库时 GnuPG 报告的版本不变，要等下一次 `chezmoi apply`。这些职责需要 Homebrew 包升级之外的一个 job，helper 自己负责命令顺序和 PATH。

有自己更新器的 app 不归这个 job 升级：[`dot_homebrew/brew.env`](../dot_homebrew/brew.env) 设置 Homebrew 的 [`HOMEBREW_NO_UPGRADE_AUTO_UPDATES_CASKS`](https://docs.brew.sh/Manpage#environment)，用 cask 自己的 `auto_updates` 声明，不另外维护一份列表。不带 `auto_updates` 的 cask，例如 `codex`，仍由 job 升级。后台 job 不加 `--greedy`，以保持这条边界。终端和后台 job 读的是同一个 `~/.homebrew/brew.env`，所以在终端里运行的 `brew upgrade` 也跳过这些 cask。

npm 全局工具的精确版本在 [`.github/dev-tools/package.json`](dev-tools/package.json)，Pyright 在 [`.github/dev-tools/requirements.txt`](dev-tools/requirements.txt)，mbx 固定在[它的 release 安装脚本](dev-tools/install-mbx.sh)里，脚本用 release 的 `SHA256SUMS` 校验官方 release 包，再装到 `~/.local/bin`。一个共享的 `run_onchange` 安装脚本先安装 proto 声明的工具，再逐个协调这些声明，不删除机器上无关的工具；不要拆分这个安装脚本。`typescript`、`typescript-language-server` 和 Pyright 支撑 Claude Code 的 LSP 插件；workspace 自己的 `typescript` 提供不了 tsserver 时，`typescript-language-server` 回退到全局的 `typescript`。

这些声明都有发布时间等待期，被攻破的上游版本在固定到这里之前，有时间被发现并撤回。npm 和 PyPI 的等待期由安装脚本执行，它拒绝解析比等待期更新的包。[`dot_config/uv/uv.toml`](../dot_config/uv/uv.toml) 用 uv 的 `exclude-newer` 设置 PyPI 的等待期，安装脚本把同一个值写进自己的 `uv tool install` 命令，不依赖 uv 找到部署的文件。npm 的等待期由安装脚本用 `npm config set` 写进 `~/.npmrc`；写在 `.zshenv` 的环境变量会漏掉不继承这个环境的 npm 进程。`~/.npmrc` 还存放 registry token，所以源文件用命令声明这个设置，不管理整个文件。所有等待期是同一个值，一个值就够，因为这些声明只包含没人等着用的后台工具。

`Brewfile` 拥有 `proto` 可执行文件，只通过 Homebrew 升级。proto 的[自升级命令](https://moonrepo.dev/docs/proto/commands/upgrade)会在 `$PROTO_HOME/bin` 装一份副本，在本仓库的工具链 PATH 里遮住 Homebrew 的版本。[`dot_proto/dot_prototools`](../dot_proto/dot_prototools) 有意使用[版本别名](https://moonrepo.dev/docs/proto/commands/install#installing-one-tool)，包括 [Node 的 LTS](https://moonrepo.dev/docs/proto/commands/pin)，并开启 proto 的[自动安装和清理](https://moonrepo.dev/docs/proto/config#settings)；这个设置接受运行时版本随时变化，没有等待期。proto 的独立安装程序不是后备路径。

mbx 是本机的 Cargo 构建缓存。`~/.zshenv` 把它的 Cargo shim 放在 `~/.cargo/bin` 前面，项目和 agent 不需要另外的 mbx 步骤。rustup 默认保持 stable，需要 nightly 的项目固定一个带日期的 nightly：后台 job 每天都会推进不带日期的 nightly，让那个工具链的缓存失效。dev-tools 安装脚本把缓存放在 `~/Code/.mbx`，和代码 checkout 在同一个卷上，移动和 clone 都很便宜。保持 Cargo 默认的 target 位置，让构建输出进入 [mbx 管理的 target 生命周期](https://mr-boxington.jdx.dev/managed-targets)。

在已有机器上改 mbx 的[缓存目录](https://mr-boxington.jdx.dev/configuration)，要显式迁移旧缓存；只改设置会让旧数据留在回收范围之外。怀疑构建输出有问题时，在新的 target 目录里用 `MBX_VERIFY=1` 运行 [mbx 校验](https://mr-boxington.jdx.dev/troubleshooting)，让 Cargo 真的编译要检查的单元。

上游的 `.chezmoiexternal.toml` 把 zsh 插件、TypeSafe 的 skill 和 rime-ice 的压缩包固定在指定 commit。上游用 Squirrel 运行 rime-ice，本机用微信输入法，所以 Rime 的配置和部署脚本按 `skip` 处理。`.chezmoiexternal.toml` 映射到 [`upstream.chezmoiexternal.toml`](../.chezmoitemplates/chezmoi/upstream.chezmoiexternal.toml) 副本，本地 [`.chezmoiexternal.toml.tmpl`](../.chezmoiexternal.toml.tmpl) 解析副本，删掉 `Library/Rime` 条目后输出其余的 external，副本里没有这个条目时用 `fail` 报错。

## 仓库校验

本仓库不运行 CI，也不带测试，上游的测试和 workflow 都不进入本仓库。本地改动在提交前用限定目标的 `chezmoi diff` 检查渲染结果。上游改动在工单里由 `upstream-sync affected` 渲染新旧两个版本，列出部署结果有变化的文件和脚本，任一版本渲染失败就报错。

## 配置归属

大部分源文件和模板渲染到 `$HOME` 下的路径，源文件命名和模板机制沿用 chezmoi 的规则。

不是每份配置都整份替换。Codex、Claude Code 等应用会写入运行时状态，所以 [`modify_` 源文件](https://www.chezmoi.io/reference/target-types/#modify-file)只管理选定的字段，保留应用自己的值。

源文件完全拥有的子树整个替换，这样删掉的字段会从目标里消失。共享的子树用覆盖或替换时的显式例外保留应用自己的字段。归属看应用里谁写这些字段，不看配置的形状。覆盖会保留没声明的字段，所以删掉源文件里的声明，不会清除目标里已有的值。

本仓库要求显式清理不再使用的路径，不用 [chezmoi 的删除列表](https://www.chezmoi.io/reference/special-files/chezmoiremove/)，这样源文件只描述当前配置，不积累历史删除。更新已有机器时，要检查废弃的文件和共享配置里废弃的字段；`chezmoi status` 为空不等于检查过。

JSON 和 TOML modifier 在解析后的值已经一致时原样输出输入，所以应用自己的格式和片段里的 key 顺序都不算漂移。嵌在脚本里的片段，例如 [`codex/requirements.toml`](../.chezmoitemplates/codex/requirements.toml)，也会影响脚本的触发 hash，改顺序可能让使用它的脚本重跑。

chezmoi 源文件管理可移植、长期的偏好，包括已经形成的操作习惯，前提是它们应在多台机器间保持一致。和默认值相同的便利设置不写出来，除非显式值用来守住仓库边界，或者抵消观察到的回写漂移。生成的运行时状态、机器特定的路径和在别处同步的设置，仍由原来的系统管理。

[macOS 设置脚本](../.chezmoiscripts/run_onchange_after_setup-macos-defaults.sh)由本仓库维护，管理 Apple 自带的偏好，每个 key 的含义写在旁边的注释里。首选语言用整个数组写入，手动添加的语言在重跑后不会保留；语言、区域和外观在下次登录时生效，不在当前会话生效。上游另有脚本管理第三方 app 偏好、登录项和通知等设置，本仓库都不部署。

### Shell 启动

agent 和 chezmoi 脚本需要的环境变量、必须排在 Homebrew 前面的工具链目录，放在 [`~/.zshenv`](../dot_zshenv)，这样不依赖交互式启动或 agent 的 shell 快照。这个划分要符合 [zsh 启动文件的约定](https://zsh.sourceforge.io/Doc/Release/Files.html#Startup_002fShutdown-Files)。Homebrew 和 OrbStack 的环境放在 [`~/.zprofile`](../dot_zprofile)，它在 macOS 的 `path_helper` 之后恢复工具链的优先级。[`~/.zshrc`](../dot_zshrc.tmpl) 放交互式配置：补全、历史、alias、插件、proto 激活和提示符。Pi 的 `bash -c` 和 launchd helper 不读这些 zsh 文件，它们需要继承或显式设置的 PATH。

`~/.zshenv` 原样跟随上游，不设置 XDG 目录变量。Homebrew 在设置了 `XDG_CONFIG_HOME` 时从 `~/.config/homebrew` 读 `brew.env` 和 `trust.json`，没设置时从 `~/.homebrew` 读；launchd job 不读 zsh 文件，所以在 `~/.zshenv` 设置它，会让终端和后台 job 各用一份配置和信任名单。按 XDG 规范处理的工具在变量没设置时本来就用 `~/.config`、`~/.local/share`、`~/.local/state` 和 `~/.cache`。`~/.zshrc` 是覆盖层，它让 zoxide 用 `cd` 代替上游默认的 `z`，在上游内容之后定义本地 alias，覆盖或删除同名的上游 alias。最后它 source `~/.zsh/lib/*.zsh`，这些本地函数、alias 和补全只在本仓库里。

### Codex 配置

[`.chezmoitemplates/codex/config.toml`](../.chezmoitemplates/codex/config.toml) 声明 [Codex 用户配置](https://developers.openai.com/codex/config-reference/)里由源文件拥有的部分。[modifier](../dot_codex/modify_private_config.toml) 整个替换 `plugins`、`permissions.development` 和源文件声明的每个 `mcp_servers` 表，这些表里只保留目标已有的 `node_repl.env` 和 `node_repl.env_vars`。其他声明的配置做深度覆盖。替换 server 表可以去掉过时的传输字段，这些字段会让 Codex 拒绝整份配置。从源文件删掉整个 server 时，仍要显式清理目标。设置了 `default_permissions` 时，每次 apply 还会删除 `sandbox_mode` 和 `sandbox_workspace_write`，因为这两个旧选项可能覆盖 profile。

`model`、`model_reasoning_effort` 和各 app 的授权不写进源文件（`apps.*` 表只声明每个 app 的 `enabled`），这样在 Desktop、TUI 或直接改文件做的修改在 apply 后仍然保留。

Desktop 会生成 `node_repl` 的环境字段，之后还可能替换它的运行时表，apply 挡不住应用之后的回写。不要在源文件里声明旧的独立 `mcp_servers.computer-use`：源文件的声明可能覆盖同名插件的注册，和 [Desktop 拥有的运行时状态](https://github.com/openai/codex/issues/24387#issuecomment-4531286877)冲突。

内置的 `computer-use` 和 `unified-computer-use` 插件保持启用，`unified-computer-use` 提供 Desktop 的 `cua_repl` 浏览器和电脑操作运行时。内置的 `code-review` 插件保持禁用，因为它在 `gh` 和 `review` skill 之外又加了一条在 GitHub 上评论和合并 PR 的路径。

Desktop 把已注册的偏好存在 `[desktop]` 下，迁移后删除它们在 global state 或 persisted atom 里的旧副本。已注册的偏好在 [`.chezmoitemplates/codex/config.toml`](../.chezmoitemplates/codex/config.toml) 里管理。

本仓库不管理 `~/.codex/.codex-global-state.json`，整份文件归 Desktop。上游用 modifier 把一个片段里的 persisted atom 覆盖到这个文件上。Desktop 26.1106.51428 把其中 6 个移到了按账号区分的 `electron-owner-atoms:<hash>` 下，每次 apply 都会把它们写回旧位置，`chezmoi diff` 一直显示这个文件有差异（[liby/dotfiles#67](https://github.com/liby/dotfiles/issues/67)）。key 名里的 hash 由账号 ID 算出，模板拿不到。剩下的 2 个 atom 不值得为一个 1 MB 的文件维护 modifier。

`approval_policy = "on-request"`、`approvals_reviewer = "auto_review"` 和唯一的自定义 profile `default_permissions = "development"` 要一起保留。[`.chezmoitemplates/codex/requirements.toml`](../.chezmoitemplates/codex/requirements.toml) 约束这组值，因为 Desktop 用保存的 agent 模式而不是 `config.toml` 生成新任务的审批策略和审核者（[#33552](https://github.com/openai/codex/issues/33552)）：不加约束时，保存的 `auto` 模式得到 `on-request` / `user`，`full-access` 得到 `never` / `user`。这个约束有意去掉内置模式，包括 Full Access。修改这个文件后重启 Desktop，目前没有复现显示 Desktop 会热加载修改后的 `requirements.toml`。

同一个 requirements 文件注册 `~/.codex/managed-hooks` 里的托管 hook：[`guard-bash`](../dot_codex/managed-hooks/executable_guard-bash) 是唯一的 `PreToolUse` Bash hook，把每个事件交给 agent-guard；[`contextual-markdown-links`](../dot_codex/managed-hooks/executable_contextual-markdown-links) 在 `UserPromptSubmit` 时给每个 prompt 加上 Markdown 链接位置的指令。

[Codex requirements 脚本](../.chezmoiscripts/run_onchange_after_setup-codex-requirements.sh.tmpl)把渲染后的 requirements 装成 root 所有的 `/etc/codex/requirements.toml`，需要 sudo，所以在交互式终端里 apply。

`development` 文件系统 profile 独立存在：`:root = write`；`~/.ssh` 整体拒绝，只放行 ssh 和 Git 签名验证用到的 `config`、`allowed_signers` 和 `known_hosts`；每个 workspace 根目录下的 `.env` 和 `.env.local` 只读；不复制各工具的缓存列表，也不放行宽泛的命令。程序可以通过正常接口使用凭据和环境文件，但修改或删除它们仍需要用户明确要求。文件系统权限不等于允许远程 Git 操作或涉及密钥的 chezmoi 操作。

[Browser modifier](../dot_codex/browser/modify_config.toml) 把[它的模板](../.chezmoitemplates/codex/browser/config.toml)覆盖到 Desktop 写入的 full-CDP 和上传允许列表上；模板有意为 Browser 工具放宽限制，给予无需确认的 full-CDP 控制，让 agent 的运行不用等人在键盘前确认。

[openai/codex#40254](https://github.com/openai/codex/issues/40254) 记录了当前 macOS 上的复现：没有显式的 Browser 缓存读规则时，Chrome 无法通过可信 RPC 的路径校验。保留 `~/.codex/plugins/cache/openai-bundled/browser` 作为唯一额外的只读路径，让可信 worker 能加载 Desktop 运行时拥有的 Browser 服务；chezmoi 的 `private_`、`readonly_` 源文件和 `chmod` 都不能建立可信的权限根。只有在删除源文件规则、apply 渲染后的配置、完全重启 Desktop、确认实际权限表里没有这条规则，并且在新任务里第一次初始化 Chrome 就成功（之前没有 Browser 尝试或重试）之后，才删除这个例外。

`features.network_proxy = true` 对 sandbox 里的命令执行 `development` profile 的域名和 Unix socket 规则。Claude Code 和 Codex 从 [`sandbox/allowed-domains.json`](../.chezmoitemplates/sandbox/allowed-domains.json) 和 [`sandbox/allowed-unix-sockets.json`](../.chezmoitemplates/sandbox/allowed-unix-sockets.json) 渲染共享的域名和 socket 路径。共享域名列表包含由 `npmHost` 渲染出的 `npm.invalid` 和由 `tailnetDomain` 渲染出的 `*.invalid`；`invalid` 是保留的顶级域名，永远解析不到。`allow_local_binding` 让命令能监听本地端口、直接访问 loopback，开发服务器和浏览器 SSO 回调需要这一点。它也关掉了代理的私有地址检查：解析到私有地址的允许列表内主机名会被放行，云 metadata 端点这类不在列表里的私有或链路本地地址只因不在允许列表而被拒绝；Codex 把私有网段放进 `NO_PROXY`，所以直接连局域网地址会在 OS sandbox 里表现为连接错误，而不是策略拒绝。socket 条目允许访问 GnuPG、OrbStack 的 Docker daemon、Rex、Maskey 的 Keychain 服务等本地服务，以及 Codex 设为命令 `TMPDIR` 的 `~/.cache/codex-tmp` 目录，工具会在那里绑定自己的 socket。Web search、MCP、Browser 和 Computer Use 有各自的网络控制。修改代理功能后重启 Desktop，命令才会使用新策略。

代理在命令第一次被拒绝的请求时结束整个命令，并报告 `Network access to "<host>" was blocked: <reason>`；Claude Code 的 sandbox 只在 `<sandbox_violations>` 里列出拒绝，命令继续运行。所以 Claude Code 在命令正常工作之外报告的主机，在 Codex 下也会让这个命令失败。工具自己发出这类请求时，例如遥测、更新检查或平台探测，用工具的开关在 [`dot_zshenv`](../dot_zshenv) 里关掉，所有 zsh 都会读这个文件，包括终端和两个 agent 的命令。只有 zsh 启动时设不了开关的请求，才考虑加进共享允许列表；一个主机因为别的请求被允许后，它的开关仍然保持设置。

`cli_auth_credentials_store` 和 `mcp_oauth_credentials_store` 都明确设为 `keyring`，`auto` 可能退回到明文文件。在另一台机器上启用前，先用不泄露凭据的状态检查确认目标存储里已有登录。agent 不迁移、不改写、不删除真实的凭据存储。

`features.daemon_auto_start = false` 让 Codex 不启动共享的 app-server daemon，每个 TUI 运行自己内嵌的 app server。共享 daemon 用第一个启动它的终端的环境，运行所有连接上的 session 的 hook 和工具命令，所以 Rex hook 会报告错误的 pane 或者不报告，工具命令里的 `REX_*` 指向 agent 不在的 pane（[openai/codex#48500](https://github.com/openai/codex/issues/48500)）。已经在运行的 daemon，例如设置生效前启动的，TUI 仍会连上它；停掉它会让连着的 TUI 离线，而不是切到内嵌 server。要停掉它，等它的 session 都不在工作，退出每个连着的 TUI 并记下它打印的 `codex resume <id>`，运行 `codex app-server daemon stop`，再在原来的 pane 里 resume 每个 session。`codex queue` 不需要 daemon，仍能发到忙碌的内嵌 session。

### GitLab CLI 配置

glab 从 `~/.config/glab-cli` 读配置，由 `~/.zshenv` 用 `GLAB_CONFIG_DIR` 指定，不用 macOS 默认的 `~/Library/Application Support`，因为 Claude Code 的 sandbox 能写 `~/.config`，不能写 `~/Library`。上游用 modifier 管理 `config.yml` 的顶层偏好，本仓库只观察它，不部署，这个文件完全由 glab 自己写。[glab 设置脚本](../.chezmoiscripts/run_onchange_after_setup-glab.sh.tmpl)用 `glab config set` 从 Maskey 复制私有 GitLab 的 OAuth application ID，只在 glab 从没登录过那个 host 时运行网页登录。ID 改变后，要重新调度这个脚本才会写进 glab。

网页登录把 token 明文存进 `config.yml`，不用 glab 默认的 Keychain。glab 每次刷新都要保存新 token，保存不了就拒绝刷新，而 Codex 在 Keychain 可写的环境里运行不了 glab：它的 sandbox 拒绝 Keychain 写入需要的共享内存写，profile 拒绝 `~/.ssh` 时，提权也不能让命令离开这个 sandbox。所以用 Keychain 要放弃 `~/.ssh` 的保护，而 Keychain 本来也挡不住 agent，agent 在 sandbox 里通过 glab 就能用 token；明文放弃的只是文件副本（例如备份）的保护。每次刷新都会让旧 token 失效，所以副本只在下次刷新前有用，除非偷到副本的人先刷新并保住 session，这时 glab 的下次刷新会报 `invalid_grant`。重新登录用设置脚本里的登录命令；`glab auth status` 提示的 `glab auth login` 会把 token 放回 Keychain。

### Claude Code 配置

上游把 Claude Code 设置、sandbox 和集成的决定写在 `.claude/rules/claude-code-settings.md`，本仓库只观察这个文件，不部署。

`~/.claude/settings.json` 由 [modifier](../dot_claude/modify_private_settings.json) 合并[设置片段](../.chezmoitemplates/claude/settings.json)，片段是覆盖层，对上游只做一处修改：只保留 `rexume` 的 hook 和压缩前后的两个 hook（`pre-compact-instructions.sh` 和 `post-compact-reminder.sh`），去掉上游注册的其他 hook。被去掉的 hook 脚本仍随 `dot_claude/**` 部署，只是没有注册。片段保留 `hooks` 这个 key，这样 apply 会替换机器上已有的 hook；上游不再注册其中任何一个保留的 hook 时，渲染报错。

`disableDeepLinkRegistration`、`DISABLE_TELEMETRY` 和 `DISABLE_ERROR_REPORTING` 放在 managed settings 里，由 [sudo 脚本](../.chezmoiscripts/run_onchange_after_setup-claude-managed-settings.sh.tmpl)装成 root 所有的 `/Library/Application Support/ClaudeCode/managed-settings.json`。用 `--setting-sources` 跳过用户设置的 session 也会读这个文件。任何 managed settings 文件都会让 Claude Code 把内置的 `cc-plugin-sec-default` 插件放在最外层，所以片段把 `prependPlugins` 设为空列表。

`~/.claude.json` 存放账号状态，[modifier](../modify_private_dot_claude.json) 只管理选定的字段，并按 0600 部署。`~/.claude/CLAUDE.md` 是本仓库自己的全文，不引入上游的共享指令。

### Pi 配置

`~/.pi/agent/models.json` 和 `~/.pi/agent/keybindings.json` 整份管理，`~/.pi/agent/settings.json` 只管理一部分。[设置 modifier](../private_dot_pi/private_agent/modify_private_settings.json) 替换[设置片段](../.chezmoitemplates/pi/settings.json)声明的每个顶层 key，包括整个 `modelThinkingLevels`，保留没声明的 key。apply 有意覆盖在 UI 里保存的启动默认值和各模型默认值，让多台设备共用源文件的配置。

临时的 `/model` 和 `/thinking` 选择仍然可用。apply 设置后，先 `/reload`，再用 `/model` 重新选模型，thinking 默认值才生效；resume 一个 session 可能恢复它记录的模型和 thinking 级别。`defaultProjectTrust = "always"` 有意让每个目录都加载项目本地的设置、资源、包和扩展，不弹信任提示。

本仓库把 Pi 的 [`enabledModels`](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/settings.md#model-and-thinking) 限制在 `rc-gateway/**` 和 `modelOverrides` 里的 `anthropic` 模型，不开放整个内置目录。[共享的模型覆盖](../.chezmoitemplates/pi/model-overrides.json)同时提供 Anthropic 的 `modelOverrides` 和 `enabledModels` 里的 `anthropic/` 条目。改了范围后要开新 session（`/new` 或新的 `pi` 进程），只 `/reload` 不会生效。gateway 的模式要保留 `**`，因为它的模型 ID 里有 `vendor/model` 形式的斜杠。

设置开启了 Pi 内置的 codemode，用于分类器工作。TypeSafe provider 条目只覆盖认证，保留 Pi 内置的分类器目录和 System One 协议适配器。

`rc-gateway` 的 [`thinkingLevelMap`](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models-configuration.md) 从 [models.dev 目录](https://models.dev/api.json)里 `vercel` 下同 ID 的条目推出。这条路由前面是 Vercel AI Gateway，它的[推理映射](https://vercel.com/docs/ai-gateway/models-and-providers/reasoning#how-reasoning-is-mapped)意味着请求成功不能证明要求的 effort 被执行了。每个列出的 `effort` 映射到同名的 Pi 级别，`none` 映射到 `off`；不支持的级别按 Pi 对这个映射的定义编码。不要给级别起别名，偏好的默认值放在 `settings.json`。

[`private_models.json.tmpl`](../private_dot_pi/private_agent/private_models.json.tmpl) 里的 `contextWindow` 是本仓库的工作预算，不超过路由接受的上限。默认 400000，让 session 在长上下文质量下降之前压缩。改某个模型的预算时，按 [Pi 的压缩规则](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/compaction.md)重新检查预留：工作窗口要远大于 `compaction.reserveTokens`，或者给这个模型加一条 `compaction.modelOverrides["provider/modelId"]`。

`maxTokens` 取工作窗口、厂商文档写明的输出上限和路由实际执行的上限三者中最小的一个。目录里宣称的上限本身不足以证明路由会执行它。厂商没有写输出上限时，用工作窗口。用 `pi --list-models rc-gateway` 检查渲染出的窗口和输出上限，推理映射另外验证。

[Pi 扩展包](https://github.com/Entwining/pi-extensions)负责编辑器、footer、guard 适配器和推理问题的绕过，包括它们的测试和发布。压缩提示扩展留在本仓库，因为它渲染共享的提示文本。[`run_onchange_after_install-pi-extensions.sh`](../.chezmoiscripts/run_onchange_after_install-pi-extensions.sh) 在 CLI 安装之后安装这个 Git 包，包的注册交给 Pi，保留其他已安装的包和它们的资源过滤。

Pi 的 `npmCommand` 对整个 `@earendil-works/*` scope 使用 npm 的[发布时间豁免](https://docs.npmjs.com/cli/v11/using-npm/config/#min-release-age-exclude)，因为 Pi 固定同一次发布里的兄弟包。豁免保持在 scope 级别，这些依赖可以一起更新，第三方包仍受本机的等待期约束。扩展包用同样的等待期和豁免检查自己的开发依赖，因为安装 Git 包时也会解析它们。

`~/.pi/agent` 下的凭据、session、已安装的包和记录的信任决定都归运行时，所以这个目录绝不能整个纳入管理。两个托管的源目录保持 `private_`，以保留 0700 权限。gateway 的 base URL 来自 `.private.rcGatewayBaseUrl`；渲染出的模型文件用凭据命令读取 Maskey 条目，不包含密钥本身。

### Oracle 配置

上游用 modifier 管理 `~/.oracle/config.json` 的部分 key，本仓库只观察这些文件，`~/.oracle/config.json` 由本机自己维护。`oracle` skill 跟随上游。

## Rex 集成

[偏好脚本](../.chezmoiscripts/run_onchange_after_setup-rex.sh)由本仓库维护，只写本机选定的 Rex 设置。其中 `Workspace.experiments.*` 是实验功能，需要开启开发者模式。app 启动时读取这些设置，所以改完要重新打开 app，Rex Server 和它运行的程序保持不动。app 自己记录的状态、主题文件和 session 状态不写进源文件。

上游的 `setup-rex`、Lua 配置和重新加载配置的脚本，本仓库只观察，不部署。所以本机没有 `Cmd+W` 的前台进程确认，新机器上要手动运行 `rex skill setup --session-naming=false` 安装 Rex 的 skill，手动运行 `rexume install` 安装 Rexume。

编排 skill 是 Rexume 自带的 `rexume` skill：`rexume install` 写入一个 stub，它用 `rexume skill show` 输出已安装版本的指南，所以和[其他工具自带的 skill](#skill-管理)一样不放进源文件。上游把这套环境对被启动 agent 的约束写进[共享 agent 指令](#共享-agent-指令)：`claude` launcher 选择模式的参数、直接接受被启动 agent 的 folder trust 提示、Codex 的 managed permission profile 做不到只读。本仓库没有部署共享指令的根文件，所以这些约束在本机不生效。上游在 apply 时用 `rexume skill status` 报告的 Rex 版本和指南 hash 检查 Rex 的指南，本仓库跳过了这个检查。

Rexume 在 Claude Code 里的 `SessionStart`、`UserPromptSubmit`、`Stop` 和 `StopFailure` hook 写在设置片段里，Codex 的整个 [hooks 文件](../dot_codex/hooks.json)跟随上游，同时包含 Rex 和 Rexume 的条目。命令要保持原样，`rex skill setup` 和 `rexume install` 才能认出它们并保持不变。新机器上要在 Codex 里通过 `/hooks` 信任这些 hook；Rexume 的条目要排在 Rex 的后面，插在已信任的条目前面会让 Codex 再问一次。

apply 会整个替换 `enabledPlugins` 和 `extraKnownMarketplaces`，所以源文件也声明了 `rexume install` 注册的 `rexume@rexume` 插件和 `rexume` 目录 marketplace；两者都在时，安装程序跳过注册，目录里的插件文件仍归它自己。Pi 扩展和 LaunchAgent 归 Rexume 的安装程序，不写进源文件。

Rex 的 Integrations 设置管理它安装的 skill，但其中的开关也会修改 hook，下一次 apply 会把 hook 恢复。**Let agents name sessions** 保持关闭：它的请求会发给 session 里启动的每个 agent，包括其他 agent 在里面启动的辅助 agent，每个 agent 都会给整个共享的 session 改名。Rexume 的 skill 改为让协调这个 session 工作的 agent 直接命名 session，不等请求。偏好脚本和 Codex 的 Rex hook 条目都写着这个选择，要打开它就要一起改。

hook 报告的是运行它的进程继承的 `REX_*`，而 `rex whoami` 接受任何还存在的 pane，所以这些变量必须来自 agent 自己的 pane。因此 Codex 的 TUI 不用共享的 app-server daemon。从 Rex pane 启动的 app 同样会保留 pane 的 `REX_*`，并传给它启动的终端和 agent，所以 [`~/.local/bin/open`](../dot_local/bin/executable_open) 用从 Dock 启动时的环境启动 app。

## Agent guard

[`Brewfile`](../Brewfile) 从 `entwining/tap` 安装 [agent-guard](https://github.com/Entwining/agent-guard)，提供 `/opt/homebrew/bin/agent-guard`。[Codex requirements](../.chezmoitemplates/codex/requirements.toml) 把 hook 放在 `managed_dir` 下，[`guard-bash`](../dot_codex/managed-hooks/executable_guard-bash) 检查 Homebrew 的二进制存在后，用 `--runtime codex` exec 它。[Pi 扩展包](https://github.com/Entwining/pi-extensions#extensions)里的 guard 适配器把 Pi 的工具调用映射成 guard 事件，调用同一个可执行文件。上游的 Claude Code 设置也为 Bash 和文件工具注册了它，本仓库的设置片段去掉了这些 hook，所以 Claude Code 不经过 agent-guard。

guard 把自己的失败，包括超过内部时限，报告为 exit 2，各运行时都把它当成阻止。guard 启动不了或 hook 超时，由运行时决定：Pi 扩展对干净通过以外的任何结果都阻止。Codex 在这些情况下会执行调用，而且没有对应的设置，所以 `guard-bash` 自己阻止缺失的二进制，它的 hook 超时必须大于 guard 的时限。

guard 的规则、解析器和测试归 agent-guard 包。本仓库拥有 [`dot_ignore`](../dot_ignore)，其中的 `/Library/` 条目让在它上层的大范围搜索不去遍历那棵目录树。

## 共享 agent 指令

Claude Code、Codex 和 Pi 共用的全局行为，在上游写成 [`.chezmoitemplates/agents/`](../.chezmoitemplates/agents/) 下按顺序排列的片段，每个运行时的根文件按同样的顺序引入。本仓库没有部署任何根文件：Claude 的 `CLAUDE.md` 是自己写的全文，Codex 和 Pi 的 `AGENTS.md` 只有上游副本。

压缩提示仍然部署。运行时适配器在压缩后把[压缩提示](../.chezmoitemplates/agents/compaction-reminder.md)交给执行者。Codex 把托管的 [`compaction-reminder`](../dot_codex/managed-hooks/executable_compaction-reminder.tmpl) 作为 `compact` 来源的 `SessionStart` hook 运行，[requirements 脚本](../.chezmoiscripts/run_onchange_after_setup-codex-requirements.sh.tmpl)运行后才会生效。Codex 在压缩和下一轮之间退出时，[可能丢掉排队的提示](https://github.com/openai/codex/issues/56316)，托管 hook 在 resume 时补不回这段上下文。[Pi 的上下文扩展](../private_dot_pi/private_agent/extensions/compaction-reminder.ts.tmpl)把提示放在保留的压缩前消息之后、新消息之前。Claude Code 的设置片段保留上游注册的 `post-compact-reminder.sh`，作为 `compact` 来源的 `SessionStart` hook 运行。

## Skill 管理

[`dot_agents/skills/<name>/SKILL.md`](../dot_agents/skills/) 是 chezmoi 管理的 skill 的源文件位置，部署到 `~/.agents/skills`；Claude Code 通过托管的 `~/.claude/skills` symlink 读取它，所以不要直接在 `~/.claude/skills` 下加 skill。用 `chezmoi source-path` 找到已安装 skill 的源文件，改源文件，不改部署后的副本。批量维护时排除不由本仓库管理的已安装 skill，只在用户点名时改它们；`~/.agents/.skill-lock.json` 是运行时的安装状态，不要动。`references`、`scripts` 和 `assets` 放在所属 skill 里面，没有索引、清单或分类目录。

源文件只放本仓库自己写文字的 skill，本仓库的 skill 都跟随上游。上游 skill 文字的副本落后时没有任何提示，所以当本仓库需要给一个 CLI 写自己的规则时，它的 skill 在自己没覆盖的地方指向已安装版本的上游指南：`gh` 和 `oracle` 读取与已安装版本 tag 对应的上游 skill。这种 skill 不记录上游 tag，CLI 变化让它的文字过时时也没有提示。上游的 `glab` skill 和其他只适合上游的 skill，本仓库跳过。

工具自带、原样使用的 skill 不放进源文件，`~/.agents/skills/<name>` 通过工具文档说明的方式，使用跟随工具版本的那一份。[Homebrew 安装脚本](../.chezmoiscripts/run_onchange_before_install-brew-packages.sh.tmpl)运行 `mk skill install` 和 `sessidx skill install`，分别链接到 Maskey.app 里的 skill 和 Homebrew `share` 目录下的 skill，每次升级都会换成新版本自带的 skill。Rex 和 Rexume 的 skill 是手动运行 `rex skill setup` 和 `rexume install` 时写入的 stub，使用时从 `rex` 和 `rexume` 读取指南。这些命令都只在运行时安装一次，手动删掉的 skill 要等对应命令再次运行才会回来。Surge 只在文档里给出 skill 的路径，所以 [`symlink_surge`](../dot_agents/skills/symlink_surge) 把 `~/.agents/skills/surge` 链接到 Surge.app 里的 skill。TypeSafe 的 skill 说明的是线上 API，没有本地工具，所以 [`.chezmoiexternal.toml`](../.chezmoitemplates/chezmoi/upstream.chezmoiexternal.toml) 像 zsh 插件一样把它固定在上游的某个 commit。

Claude Code 的 `auto` 模式下，skill 的 `allowed-tools` 让这个 skill 那一轮里它负责的具体命令前缀和工具跳过分类器审查。跨轮次或长期的授权在 `~/.claude/settings.json` 里，开放式命令和解释器命令仍走 sandbox 和分类器。Claude 拒绝了一条匹配的 skill 授权时，保持 skill 的约定，加一条有复现支持、范围最小的运行时例外。

## 身份和加密数据

[`.chezmoi.toml.tmpl`](../.chezmoi.toml.tmpl) 由本仓库维护，`init` 时提示输入账号相关的值。`tailnetDomain` 是常量 `invalid`，因为本机没有 Tailscale，而上游的 sandbox 允许列表要渲染 `*.<tailnetDomain>`；以后有 tailnet 时，换回上游的提示。`npmHost` 同理是常量 `npm.invalid`，因为不再使用私有 npm registry，而共享允许列表原样渲染这个主机名；以后需要时，换回上游的提示。

加密文件用 GPG，私钥在 YubiKey 上，`.chezmoi.toml.tmpl` 只写本机的收件人。上游的加密文件本仓库解不开，所以都是 `skip`。

agent 可以读 `~/.ssh` 顶层的客户端配置（`config`、`config.*`）、公钥、`allowed_signers` 和 `known_hosts`，这个目录下的其他文件都不能读。Claude 的 sandbox 按目录执行这份清单，所以部署在那里的私钥不需要命名约定，也不需要逐个规则。Codex 的 sandbox 只重新放行 ssh 和 Git 签名验证需要的具体文件，所以在那个 sandbox 里公钥也读不到。

### Git 身份和签名

两个代码托管平台都验证 YubiKey 签的 commit，但格式不同。GitHub 验证卡上签名密钥的 OpenPGP 签名。GitLab 用注册在 GitLab 账号上的认证密钥验证卡上认证密钥的 SSH 签名，所以工作邮箱不会成为个人 OpenPGP 密钥的 user ID，这把密钥公开时不带任何雇主信息，以后也不用从密钥上撤销。本地 Git 用加密的 `~/.ssh/allowed_signers` 验证这些签名，GitLab 不读这个文件。[`run_onchange_after_setup-gitconfig.sh.tmpl`](../.chezmoiscripts/run_onchange_after_setup-gitconfig.sh.tmpl) 从 `gpg --card-status` 读取密钥 ID，把带这个 ID 的 [`github.config`](../.chezmoitemplates/git/github.config) 和带导出的认证密钥（Git 的 `key::` 形式）的 [`gitlab.config`](../.chezmoitemplates/git/gitlab.config) 装到 `~/.config/git/`，所以签名不读 `~/.ssh` 下的任何文件。脚本每次重跑都自己推导密钥，因为 GPG 脚本在 Homebrew keg 变化时重跑，不在换卡时重跑。换上存有不同密钥的 YubiKey 时，两个脚本都不会自己重跑，所以换卡后要重新调度两个脚本：`setup-gpg-agent.sh` 导入新卡的公钥，`setup-gitconfig.sh` 重写签名密钥。

`~/.config/git/config` 是覆盖层，去掉上游结尾的 include，换成本仓库的规则。全局 `[user]` 是个人身份，另外加了几个本地 alias。remote 指向 GitHub（SSH 或 HTTPS）的仓库引入 `github.config`，remote 指向私有 GitLab host 的仓库引入 `gitlab.config`，`~/Code/` 下的仓库引入 `performance.config`。上游则是所有仓库都引入 `github.config`，`~/Code/GitLab/` 下的仓库引入 `gitlab.config`。`github.config` 也是覆盖层，把上游的 `[user]` 换成本仓库的 GitHub 身份，签名设置照用上游。

[`git-ssh-gpg-agent`](../dot_config/git/executable_git-ssh-gpg-agent) 的存在原因是：gpg-agent 在 `~/.gnupg/S.gpg-agent.ssh` 提供卡上的 SSH 密钥，而 shell 的 `SSH_AUTH_SOCK` 指向 macOS 的 ssh-agent。这个 wrapper 把 `SSH_AUTH_SOCK` 指向 gpg-agent 的 socket，再为 `core.sshCommand --transport` 运行 `ssh`，或作为 `gpg.ssh.program` 运行 `ssh-keygen`，所以 SSH 签名从任何 shell 都能用到 YubiKey，包括不继承 agent 环境的 sandbox 里的 agent shell。Git 走 SSH 也一样，只有 Claude Code 的 macOS sandbox 例外，它不放行任何 SSH 连接：它把 `GIT_SSH_COMMAND` 设成一个无法向代理认证的代理命令，而 `GIT_SSH_COMMAND` 优先于 `core.sshCommand`。所以 Git 配置把两个平台的 `git@` remote 在 fetch 和 push 时都改写成 HTTPS，通过 `gh` 和 `glab` 认证，对应平台的 CLI 没登录时，push 和 fetch 非公开仓库都会失败。这些 CLI 的 token 在 sandbox 里本来就能写两个平台，所以让 push 继续走 SSH 并不能保护什么。

[SSH 配置](../private_dot_ssh/private_config)由本仓库维护。它对所有 host 都用 `IdentityAgent` 指向 gpg-agent 的 socket，不经过 Git 也能用卡上的认证密钥；GitHub 通过 `ssh.github.com` 连接；另外引入 OrbStack 的 SSH 配置和加密的私有 host 配置。上游只对 `github.com` 和 `gitlab.*` 指定 gpg-agent，其他 host 用 macOS 的 agent 和密钥文件。改这个 socket 时，要一起改 SSH 配置、wrapper 和[共享的 sandbox Unix socket 列表](../.chezmoitemplates/sandbox/allowed-unix-sockets.json)。

### 凭据

凭据存放在 [Maskey](https://github.com/Entwining/maskey) 里，Maskey 把它们存进 iCloud Keychain，登录同一个 Apple 账号的每台 Mac 都能拿到，本仓库里没有副本。条目的形式是 `<namespace>/<NAME>`，NAME 就是使用者收到的环境变量名。本仓库的文件用 `mk run` 和 `mk get` 引用条目，用 `rg 'mk (run|get)'` 能找到所有使用者；其他条目不是本仓库的要求。

`mk run` 把选中的条目交给它启动的命令，并在命令输出里遮住每个选中条目的确切值，所以非机密的常量放在使用者里，存一个 `1` 会把输出里所有的 1 都遮住。`mk get` 把一个条目的值返回给读取它的调用者，前提是用户在 Maskey 里给这个条目授予了程序访问权限。之后任何能运行 `mk` 的程序都能读这个条目，所以只给下面用 `mk get` 读取的条目授权。

各 namespace 的使用者：

- `claude-gateway`：[Claude launcher](../dot_local/share/claude-launcher/bin/executable_claude) 只在 gateway 模式下用 `mk get` 读取这些条目，并自己设置 Vertex 开关；其他模式下，不管这些变量和开关是谁设的，launcher 都会取消设置，所以在 gateway session 里启动的 `claude` 按保存的模式运行，除非它自己的参数另有指定。启动 Claude Code 之前，launcher 把自己的 PID 导出为 `REXUME_LAUNCH_PID`，把解析出的 `claude --gateway` 或 `claude --subscription` 命令导出为 `REXUME_LAUNCH`，Rexume 用这条命令按会话原来的模式重新打开它。launcher 自己从不读取这两个变量，所以嵌套启动的 `claude` 仍然自己解析并声明模式。launcher 是 `PATH` 上排在 `~/.local/bin` 原生安装前面的可执行文件，不是 shell 函数，所以 Pi 的 bash、`timeout` 这类 wrapper 或脚本的子进程运行 `claude` 时，保存的模式同样生效。
- `context7`：所有 Context7 的使用都经过 [Context7 skill](../dot_agents/skills/context7/SKILL.md)，它在 `mk run context7` 里运行 `ctx7` CLI，`CONTEXT7_API_KEY` 只到达 CLI 子进程。这个 namespace 还可以有一个可选的 `CONTEXT7_BASE_URL`，默认没有；它指向一个转发官方 `/api/v2` 查询 API 的可信反向代理，结尾不带斜杠，同时要把这个主机加进 Claude Code sandbox 的 `allowedDomains`。全局的 `--base-url` 对查询模式的请求有效，但上游只支持 MCP HTTP 方式的自定义部署，查询模式的私有部署不受支持。改 Context7 的配置后，通过 skill 运行一次 resolve 和 query 来验证。
- `glab`：[glab 设置脚本](../.chezmoiscripts/run_onchange_after_setup-glab.sh.tmpl)在 `mk run` 下的命令里，把私有 GitLab 的 OAuth application ID `GITLAB_CLIENT_ID` 写进 glab 的配置，变量名就是 glab 自己读的名字。
- `pi` 和 `typesafe`：[Pi 模型配置](../private_dot_pi/private_agent/private_models.json.tmpl)用 `mk get` 从 `pi` namespace 读取 `ANTHROPIC_API_KEY` 和 `RC_GATEWAY_API_KEY`，从 `typesafe` namespace 读取 `TYPESAFE_API_KEY`。
