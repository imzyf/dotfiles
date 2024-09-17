# dotfiles

⚙️ My vim/neovim, nix, git, and tmux configuration files.

## Install

```sh
sh <(curl -L https://nixos.org/nix/install)
nix-build https://github.com/LnL7/nix-darwin/archive/master.tar.gz -A installer
./result/bin/darwin-installer
git clone https://github.com/imzyf/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
./setup.sh
```

## References

- [ahonn/dotfiles](https://github.com/ahonn/dotfiles)
- <https://github.com/LnL7/nix-darwin>
- <https://nix.dev/>
