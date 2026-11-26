#!/bin/bash

# @raycast.schemaVersion 1
# @raycast.title Gmail
# @raycast.mode silent
# @raycast.icon https://www.gstatic.com/images/branding/product/2x/gmail_2020q4_48dp.png

# Without a fragment, any tab of this account matches, and a new tab opens the inbox.
exec "$(dirname "$0")/open-or-focus-chrome-url.applescript" \
  "https://mail.google.com/mail/u/0/"
