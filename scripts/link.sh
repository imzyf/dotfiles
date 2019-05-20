#!/usr/bin/env bash

DOTFILES=$HOME/.dotfiles

echo -e "\nCreating dotfile symlinks"
echo "=============================="
linkables=$(find -H "$DOTFILES" -not -path "$DOTFILES/.undodir/*" -maxdepth 3 -name '*.symlink')

