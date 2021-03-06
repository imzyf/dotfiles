#!/usr/bin/env bash

echo -e "\nInstalling nvm..."
echo "=============================="

if [ -e $HOME/.nvm ]; then
  echo "nvm already installed... skipping."
else
  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.35.0/install.sh | bash

  nvm install --lts=Carbon
fi

echo "=============================="
echo -e "\nInstalling nrm..."
echo "=============================="

if nrm -V >/dev/null 2>&1; then
  echo "nrm already installed... skipping."
else
  npm install nrm -g

  nrm ls
  nrm use taobao
fi

echo "=============================="
echo -e "\nInstalling npm packages..."
echo "=============================="

formulas=(
  leetcode-cli
  neovim
  prettier
  babel-eslint
  typescript
  gh-pages
  commitizen
  cz-conventional-changelog
  eslint
  eslint-config-standard
  trash-cli
)

for formula in "${formulas[@]}"; do
  if npm list -g --depth=0 "$formula" >/dev/null 2>&1; then
    echo "$formula already installed... skipping."
  else
    npm install $formula -g
  fi
done