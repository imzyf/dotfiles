be() {
  local backend_dir="$HOME/Projects/saas/backend"

  if (( $# == 0 )); then
    builtin cd -- "$backend_dir" || return
    be help
  elif (( $# == 1 )) && [[ $1 == up ]]; then
    (builtin cd -- "$backend_dir" && command make up)
  elif (( $# == 1 )) && [[ $1 == down ]]; then
    (builtin cd -- "$backend_dir" && command make down)
  elif (( $# == 1 )) && [[ $1 == reset-env ]]; then
    (builtin cd -- "$backend_dir" && ./bin/artisan retail hook:deploy --reset-environment)
  elif (( $# == 1 )) && [[ $1 == model-sync ]]; then
    (builtin cd -- "$backend_dir" && ./bin/artisan retail model:sync)
  elif (( $# == 1 )) && [[ $1 == test ]]; then
    (builtin cd -- "$backend_dir" && ./bin/test retail)
  elif (( $# == 1 )) && [[ $1 == phpstan ]]; then
    (builtin cd -- "$backend_dir" && ./bin/phpstan retail)
  elif (( $# == 1 )) && [[ $1 == fmt ]]; then
    (builtin cd -- "$backend_dir" && ./bin/format retail)
  elif (( $# == 1 )) && [[ $1 == h || $1 == -h || $1 == help ]]; then
    print -rl -- \
      'Usage: be [up|down|reset-env|model-sync|test|phpstan|fmt|h|-h|help]' \
      '  be               Go to ~/Projects/saas/backend and show this command list' \
      '  be up            Run make up in that directory' \
      '  be down          Run make down in that directory' \
      '  be reset-env     Run bin/artisan retail hook:deploy --reset-environment' \
      '  be model-sync    Run bin/artisan retail model:sync' \
      '  be test          Run bin/test retail' \
      '  be phpstan       Run bin/phpstan retail' \
      '  be fmt           Run bin/format retail' \
      '  be h|-h|help     Show this command list'
  else
    print -u2 'Usage: be [up|down|reset-env|model-sync|test|phpstan|fmt|h|-h|help]'
    return 2
  fi
}

_be() {
  local -a commands=(
    'up:Run make up in the backend directory'
    'down:Run make down in the backend directory'
    'reset-env:Run the backend environment reset'
    'model-sync:Run backend model synchronization'
    'test:Run backend tests'
    'phpstan:Run backend PHPStan checks'
    'fmt:Format backend code'
    'h:Show the command list'
    '-h:Show the command list'
    'help:Show the command list'
  )

  _describe -t commands 'be command' commands
}

compdef _be be
