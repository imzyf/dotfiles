# Sandbox Runtime

## 是什么，解决什么问题

[Sandbox Runtime](https://github.com/anthropic-experimental/sandbox-runtime)（npm 包 `@anthropic-ai/sandbox-runtime`，命令 `srt`）是 Anthropic 为 Claude Code 开发的开源 sandbox，不用容器，直接用操作系统自带的机制限制一个进程和它的所有子进程：macOS 上用 `sandbox-exec` 加动态生成的 Seatbelt profile，Linux 上用 bubblewrap。

agent 运行的命令默认拥有桌面用户的全部权限，一条写错的 `pkill`、`rm` 或 `npm install -g` 就能影响整台机器。Sandbox Runtime 同时限制两样东西：

- 文件系统：读默认全部允许，用 `denyRead` 挡掉敏感目录，再用 `allowRead` 放开其中的个别文件；写默认全部拒绝，只有 `allowWrite` 列出的路径能写。
- 网络：默认全部拒绝。进程只能连到宿主机上的代理端口，代理按 `allowedDomains` 放行 HTTP/HTTPS 和其他 TCP 连接；Unix socket 要在 `allowUnixSockets` 里单独放开。

## 上游怎么用

Claude Code 的 `sandbox` 设置和 Pi 的命令 sandbox 读的都是 Sandbox Runtime 的配置格式，所以上游把共用的部分拆成 `.chezmoitemplates/sandbox/` 下的几份 JSON 列表：允许的域名、写入路径、读取规则、Mach lookup 和 Unix socket。Claude Code 的设置片段和 Pi 的策略模板各自引入这些列表，Codex 也引入其中的域名和 socket 列表。

两边的差别放在各自的模板里：

- 通过 Rex、OrbStack Docker 这类服务可以在 sandbox 外面启动任务，它们的 socket 单独成一份列表，只有 Claude Code 和 Codex 加上，Pi 不加。
- Claude Code 另外允许写 `~/.claude`、`~/.config`、`~/.local/bin` 这类 agent 状态路径。Pi 不允许，因为里面有在 sandbox 外运行的配置和可执行文件。

Pi 这一侧由 [pi-extensions](https://github.com/Entwining/pi-extensions) 包里的 `sandbox.ts` 负责：它把 `bash` 工具和 `!` 命令放进 Sandbox Runtime 里运行，把 `write`、`edit` 按同一份写入策略检查，策略文件是 `~/.pi/agent/extensions/sandbox.json`。

## 要点和坑

- 策略文件不存在、内容不合法或 sandbox 起不来时，Pi 会直接拒绝运行命令，不会退回到不受限制的方式。所以策略要先于扩展包的更新部署。
- Seatbelt 不能嵌套。从另一个 agent 的 sandbox shell 里启动的 Pi 会拒绝运行所有命令；这时用 `--no-sandbox` 启动，命令就只受外层 sandbox 限制。
- 关掉 Pi sandbox 的唯一办法是启动时加 `--no-sandbox`，而且要放在其他参数前面：Pi 会把扩展参数后面的下一个词当成它的值。写成 `--no-sandbox=false` 也会关掉 sandbox。
- 策略不允许的工作，例如 apply chezmoi、Homebrew、launchd 服务或操作 Rex，要在用 `--no-sandbox` 启动的 Pi 里做。
- 读和写的优先级相反：`allowRead` 压过 `denyRead`，`denyWrite` 压过 `allowWrite`。
- 命令要写的目录不在写入列表里时，报错是 `EPERM` 或 `Operation not permitted`，不会提到 sandbox。上游就遇到过 `snow` 写不了 `~/.snowflake/logs`、每次启动都失败的情况。
- Pi 扩展会从 `PATH` 启动程序，而这些程序在 sandbox 外运行，所以扩展会禁止写 `PATH` 里的目录。可执行文件放在一个允许写的目录里时，命令仍然可以改它。

## 延伸阅读

- [Sandbox Runtime 的 README](https://github.com/anthropic-experimental/sandbox-runtime#readme)：配置项和各平台的实现方式。
- [Claude Code 的 sandbox 文档](https://docs.claude.com/en/docs/claude-code/sandboxing)。
- [Beyond Permission Prompts](https://www.anthropic.com/engineering/claude-code-sandboxing)：Anthropic 说明为什么要同时隔离文件和网络。
- [pi-extensions 的 OS sandbox 说明](https://github.com/Entwining/pi-extensions/blob/main/docs/usage.md#os-sandbox)：Pi 给每个 session 另外加的允许和拒绝规则。

## 核对依据

按上游 commit `1174ab4ef` 和 `3ecc4e172`、pi-extensions `2ebea64f4`（它固定的 `@anthropic-ai/sandbox-runtime` 是 0.0.83）核对。
