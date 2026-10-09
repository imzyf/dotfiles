---
name: envchain
description: 通过 envchain 为 CLI 子进程注入 token、API key、密码等敏感环境变量。用于 glab/GitLab、Slack、Jira 等 CLI 需要 envchain 中的凭据时，以及为其他 skill 的认证命令添加 envchain 包装、定位缺失的凭据命名空间或变量时。已有客户端认证且不依赖 envchain 的调用不使用此 skill。
---

# 用 envchain 调用需要凭据的 CLI

让消费凭据的客户端获取环境变量，agent 只查看命名空间和变量名，不读取秘密值。agent 只能使用已有凭据，不得自行创建命名空间、添加 key、设置或覆盖值，也不得删除已有凭据；不能通过其他 CLI、API 或脚本绕过这条限制。此 skill 负责凭据注入；具体服务的 skill 仍负责命令语法、目标、输出和操作授权。拥有 token 不构成发送消息、写入远端或付费的授权。

## 确认凭据与消费者

1. 确认实际 CLI、目标服务和主机。先读对应 skill、非敏感配置或客户端文档，查明它接受的环境变量；不读取 `.env`、凭据文件、Keychain 内容或加密 seed。Slack、Jira 的同名 CLI 可能有不同认证方式，不能凭服务名猜变量。
2. 仅列出名称：

   ```sh
   envchain --list
   envchain --list <namespace>
   ```

   正确选项是 `--list`，不是 `envchain list`。按实际枚举结果和消费者约定选择命名空间；它不一定与可执行文件同名，例如 `glab` 可使用 `gitlab`。有多个账户或主机时，结合任务目标确认，不能随意试用 token。
3. 确认命名空间存在，且列出的键包含客户端需要的变量。envchain 在命名空间不存在时可能警告后仍执行命令，因此不能把执行成功当作注入成功。多个命名空间逐个检查，只组合该消费者确实需要的集合。

## 包装其他 skill 的命令

把已确认的认证调用 `command arg ...` 改为 `envchain <namespace> command arg ...`。保留原来的参数、工作目录、输入文件、标准输入和版本绑定；未授权的写操作仍停在原来的授权边界。纯本地、不需要凭据的命令不包装。

以下命名空间仅为示例，执行前必须按上面的步骤确认：

```sh
envchain gitlab glab mr list -R group/project -F json
```

`glab` 支持 `GITLAB_TOKEN`；按 [GitLab CLI 的认证约定](https://docs.gitlab.com/cli/)核对目标主机与所需配置。其他客户端同样确认其文档后使用 `envchain <namespace> <实际CLI> ...`，不编造 Slack、Jira 的子命令。

- 原命令已有正确的 envchain 包装时沿用，例如 Context7 skill 的 `envchain context7 ...`；不要重复包装或换掉它的命名空间。
- 管道只包住需要认证的一侧：`envchain <namespace> glab ... | jq ...`。管道另一侧不会获得注入的环境变量；若两侧都是认证客户端，各自包装。
- 多个命名空间用逗号组合：`envchain <namespace-a>,<namespace-b> <command> ...`。若它们有同名变量，先解决选择冲突，不依赖覆盖顺序。
- 不用 shell 字符串拼接或 `eval` 封装参数。需要在子进程中做变量名映射时，先确认已有变量与客户端所需变量的对应关系，使用单引号包住固定的 `sh -c` 程序，通过 `"$@"` 转发参数；映射只留在子进程环境中，不写入凭据库。

不要在父 shell 中展开秘密变量，也不要把值放入 `--token`、HTTP header、URL 或其他命令参数。若客户端仅接受明文参数或写入凭据文件，停止该认证步骤，说明缺少安全的消费方式，不能用泄露值的包装勉强完成。

## 缺失与验证

envchain、命名空间或必需变量缺失时，停止依赖它的调用，继续不依赖认证的工作。告知缺少的工具、命名空间或变量；添加 key 和设置值只能由用户在自己的终端完成，不要求用户把值发进聊天。下面的命令仅供展示给用户，agent 不得执行 `envchain --set` 或 `envchain --unset`：

```sh
envchain --set --noecho <namespace> <VARIABLE> [<VARIABLE> ...]
```

认证失败时核对主机、变量名和客户端错误，不打印 token，不自动 login、覆盖或删除凭据。用户更新后重新列出键名，再用任务所需的最小只读请求验证；成功的业务响应才能证明该调用认证可用，键名存在不能证明值有效。写操作返回不确定结果时，先查询远端状态再决定是否重试。

不要运行 `--show-value`、客户端的 token 输出命令、环境变量转储、打印秘密的 shell 命令或带认证调试的 trace；不要把凭据缓存进文件、日志、笔记或 skill。验证包装语法时使用隔离环境和合成变量，不把真实凭据交给新写的测试脚本。
