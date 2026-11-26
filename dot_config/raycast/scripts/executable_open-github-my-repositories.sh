#!/bin/bash

# @raycast.schemaVersion 1
# @raycast.title My GitHub Repositories
# @raycast.mode silent
# @raycast.icon https://github.githubassets.com/favicons/favicon.png
# @raycast.iconDark https://github.githubassets.com/favicons/favicon-dark.png

exec "$(dirname "$0")/open-or-focus-chrome-url.applescript" \
  "https://github.com/imzyf?tab=repositories&type=source"
