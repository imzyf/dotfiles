#!/bin/zsh
set -euo pipefail

command -v codex &>/dev/null && exit 0

echo "Installing Codex..."
curl -fsSL https://chatgpt.com/codex/install.sh | sh
