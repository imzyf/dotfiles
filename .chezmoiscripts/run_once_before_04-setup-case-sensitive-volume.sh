#!/bin/zsh
set -euo pipefail

[[ "$OSTYPE" == darwin* ]] || exit 0

container_id=$(diskutil list | grep "APFS Container Scheme" | head -1 | awk '{print $NF}')
if [[ -z "$container_id" ]]; then
  echo "Error: No APFS container found"
  exit 1
fi

mkdir -p "$HOME/Code"
