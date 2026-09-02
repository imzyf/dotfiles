<h4 align="right"><strong>中文</strong> | <a href="./README.en.md">English</a></h4>

# dotfiles

我的个人 dotfiles，使用 [chezmoi](https://www.chezmoi.io/) 管理，一条命令即可完成新 Mac 的配置。

## 新设备初始化

在新的 Apple Silicon Mac 上打开 Terminal.app，运行：

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply imzyf
```

运行前需插入 YubiKey，GPG 私钥 `19084855608DB9D5` 存放在卡上，否则加密文件无法解密。首次运行会提示输入 private GitLab 的 name、email 和 host。

## 致谢

特别感谢 [liby/dotfiles](https://github.com/liby/dotfiles)，帮我解决了太多难题。这里大部分文件直接沿用它的版本，由 [`sync-upstream.sh`](scripts/sync-upstream.sh) 同步。

有几个文件我改成了自己的习惯，不能再让上游整份覆盖。它们的上游版本单独存一份在 `.chezmoitemplates/`，本地文件用 `includeTemplate` 引入这份副本，再叠上自己的改动，需要维护的只有差异。这样既站在了巨人的肩膀上，又能改成自己顺手的样子，上游后来的新功能和优化照样跟得上。
