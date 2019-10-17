#!/usr/bin/env bash

DOTFILES=$HOME/.dotfiles

echo -e "\nCreating dotfile symlinks"
echo "=============================="
linkables=$(find -H "$DOTFILES" -not -path "$DOTFILES/.undodir/*" -maxdepth 3 -name '*.symlink')

for file in $linkables; do
  filename=".$(basename $file '.symlink')"
  target="$HOME/$filename"
  if [ -e $target ]; then
    echo "$target already exists... Skipping."
  else
    echo "Creating symlink for $file"
    ln -s $file $target
  fi
done