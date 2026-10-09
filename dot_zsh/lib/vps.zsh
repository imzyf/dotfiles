vps() {
  if (( $# )); then
    if (( $# != 1 )) || [[ -z $1 || $1 == -* ]]; then
      print -u2 'Usage: vps [host-name]'
      return 2
    fi
    command ssh "$1"
    return
  fi

  awk '
    tolower($1) == "host" {
      for (i = 2; i <= NF; i++) {
        if ($i ~ /^#/ || $i == "") break
        if ($i !~ /[*!?]/ && !seen[$i]++) print $i
      }
    }
  ' "$HOME/.ssh/config.vps"
}

_vps() {
  (( CURRENT == 2 )) || return 1

  local -a hosts
  hosts=(${(f)"$(vps 2>/dev/null)"})
  (( $#hosts )) || return 1
  _describe -t hosts 'VPS host' hosts
}

compdef _vps vps
