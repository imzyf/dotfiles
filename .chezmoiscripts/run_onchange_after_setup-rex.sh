#!/bin/zsh
set -euo pipefail

source "$CHEZMOI_SOURCE_DIR/.chezmoiscripts/.lib/step.zsh"

# Only settings chosen on this machine; state the app records itself stays out.
# The app reads these at launch; apply leaves relaunching it to the user.
domain=com.superlogical.rex
defaults write $domain Workspace.appearance -string system
defaults write $domain Workspace.darkThemeID -string merino-dark
defaults write $domain Workspace.lightThemeID -string merino-light
defaults write $domain Workspace.inactivePaneFadeMode -string both
defaults write $domain Workspace.interfaceStyle -string useTheme
defaults write $domain Workspace.tabIconTintMode -string off
defaults write $domain Workspace.terminalFontPointSize -float 16.5
defaults write $domain Workspace.usesStandardInactiveWindowPaneStyles -bool true
# Matches `--feature-session-naming=false` in the agents' Rex hooks. A skill stub that
# setup already installed keeps naming on until `rex skill setup --session-naming=false`
# runs again, or the Integrations switch is turned off once.
defaults write $domain rex.agents.names-sessions -bool false
# Rex is not installed through Homebrew, so the app updates itself: download in the
# background and relaunch while hidden, with the server's sessions still running.
# The setting lives in Developer Mode's Experimental section.
defaults write $domain RexAppUpdateAutomation -string install
defaults write $domain rex.developer-mode-enabled -bool true

if [[ -n $(lsappinfo find bundleid=$domain) ]]; then
  print -u2 -r -- "$step_yellow!$step_reset Reopen the Rex app to apply its settings; leave Rex Server running"
fi
