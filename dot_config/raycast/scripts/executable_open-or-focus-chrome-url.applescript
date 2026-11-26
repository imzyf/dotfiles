#!/usr/bin/osascript

# @raycast.schemaVersion 1
# @raycast.title Open or Focus URL in Chrome
# @raycast.mode silent
# @raycast.argument1 { "type": "text", "placeholder": "URL" }

# A tab counts as open when its URL starts with the argument, so a page that
# has since gained a query string or fragment is still reused.
on run argv
	set targetURL to item 1 of argv
	tell application "Google Chrome"
		repeat with w in windows
			set i to 0
			repeat with t in tabs of w
				set i to i + 1
				if URL of t starts with targetURL then
					set active tab index of w to i
					set index of w to 1
					activate
					return
				end if
			end repeat
		end repeat
		open location targetURL
		activate
	end tell
end run
