#!/usr/bin/env bash

if test ! $(which brew); then
  echo "Installing homebrew..."
  /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
fi

# https://mirror.tuna.tsinghua.edu.cn/help/homebrew/
git -C "$(brew --repo)" remote set-url origin https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/brew.git

git -C "$(brew --repo homebrew/core)" remote set-url origin https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-core.git

git -C "$(brew --repo homebrew/cask)" remote set-url origin https://mirrors.tuna.tsinghua.edu.cn/git/homebrew/homebrew-cask.git

echo -e "\nUpgrade homebrew packages..."
brew update
brew upgrade

echo -e "\nInstalling homebrew packages..."
echo "=============================="

# fx https://github.com/antonmedv/fx
# bat https://github.com/sharkdp/bat
# fd https://github.com/chinanf-boy/fd-zh
# clojure-lsp https://github.com/snoe/clojure-lsp
formulas=(
  fish
  ripgrep
  fzf
  tmux
  git
  tree
  wget
  neovim
  thefuck
  cmake
  fx
  bat
  fd
  clojure-lsp
  borkdude/brew/clj-kondo
)

for formula in "${formulas[@]}"; do
  if brew list "$formula" >/dev/null 2>&1; then
    echo "$formula already installed... skipping."
  else
    brew install $formula
  fi
done