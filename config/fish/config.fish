set -gx DOTFILES $HOME/.dotfiles

set -gx LANG en_US.UTF-8
set -gx TERM 'screen-256color'

set -gx EDITOR 'nvim'
set -gx GIT_EDITOR 'nvim'

set -gx FZF_DEFAULT_COMMAND 'rg --files --no-ignore --hidden --follow -g "!{.git,node_modules}/*" 2> /dev/null'

# disable greeting
function fish_greeting
end

source $DOTFILES/config/fish/aliases.fish
source $DOTFILES/config/fish/path.fish