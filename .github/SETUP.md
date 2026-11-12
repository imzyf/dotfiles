# 安装

这套配置面向 Apple Silicon Mac。部分设置依赖我的账号、GPG 密钥和私有 GitLab。

## 配置新 Mac

在新 Mac 上打开 Terminal.app，先安装 Apple 的 [Command Line Tools](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools/)，再克隆本仓库：

```sh
xcode-select --install
```

等安装窗口结束，确认 `xcode-select -p` 和 `git --version` 都有输出。

继续之前：

- 登录 App Store，`Brewfile` 才能按 [mas 对账号的要求](https://github.com/mas-cli/mas#app-store-apple-account-requirements)安装 App Store 里的 App。
- 为和其他 Mac 相同的 Apple 账号打开 iCloud 钥匙串，让 [Maskey 里的凭据](CONCEPTS.md#凭据)在初始化读取之前同步到这台 Mac。
- 插上 YubiKey。GPG 私钥 `19084855608DB9D5` 存在卡上，没有它加密文件无法解密。

用 [chezmoi 的一键安装命令](https://www.chezmoi.io/user-guide/daily-operations/#install-chezmoi-and-your-dotfiles-on-a-new-machine-with-a-single-command)完成配置：

```sh
sh -c "$(curl -fsLS https://get.chezmoi.io)" -- -b "$(mktemp -d)" init --apply imzyf
```

`-b` 把这次下载的 chezmoi 放进临时目录，之后使用和升级的 chezmoi 由 `Brewfile` 安装。

运行期间保持 Terminal.app 打开：

- 首次运行会提示输入 OpenAI 兼容 API 的 base URL（以 `/v1` 结尾）和私有 GitLab 的 host。
- 安装系统级配置时要输入 `sudo` 密码。
- 解密文件时要用 YubiKey 输入 PIN。
- glab 会在浏览器里打开私有 GitLab 的登录页，登录完成后才继续。

如果中途失败，按报错处理后重新运行同一条命令，chezmoi 会按[脚本生命周期](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/)接着执行。

已经装好 chezmoi 时，运行：

```sh
chezmoi init --apply imzyf
```

完成后运行 `gh auth login`。Git 通过 HTTPS push 到 GitHub、拉取私有仓库时都用这个登录，后台升级任务也只有登录后才会升级 gh 扩展。

[Rex](https://www.superlogical.com/rex) 需要手动安装并打开。`chezmoi apply` 写入的 Rex 设置在重新打开 app 后生效。

## 日常操作

按 [chezmoi 的日常流程](https://www.chezmoi.io/user-guide/daily-operations/)编辑和应用文件。排查初始化问题时运行 `chezmoi apply -v`，可以看到每个脚本步骤的完整输出。

[编辑加密文件](https://www.chezmoi.io/reference/commands/edit-encrypted/)需要 YubiKey，不要交给 agent。

上游 [liby/dotfiles](https://github.com/liby/dotfiles) 的改动由 [`upstream-sync`](upstream-sync/) 整理成工单，逐个处理后合并进 `main`，不要手动从上游复制文件。

## 更新已有的 Mac

更新已有的 Mac 时，查看这台机器上次 apply 之后的 commit，找出废弃的路径和字段。删除前先看它们的当前内容，保留仍然需要的本地改动。应用新的源文件[不会清理所有废弃配置](CONCEPTS.md#配置归属)，`chezmoi status` 为空也一样。

`.chezmoi.toml.tmpl` 有变化时，先运行 [`chezmoi init`](https://www.chezmoi.io/reference/commands/init/) 重新生成本机配置，再 apply。
