[English](./README.md) | 中文

# dotfiles

## 概览

使用 [chezmoi](https://www.chezmoi.io/) 管理，一条命令即可完成新 Mac 的配置。

## 新设备初始化

在新的 Apple Silicon Mac 上打开 Terminal.app，运行：

```sh
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply imzyf
```

运行前需插入 YubiKey，GPG 私钥 `19084855608DB9D5` 存放在卡上，否则加密文件无法解密。首次运行会提示输入 private GitLab 的 name、email 和 host。

## 致谢

特别感谢 [liby/dotfiles](https://github.com/liby/dotfiles)，这里很多代码都直接来自它，帮我解决了太多难题。
