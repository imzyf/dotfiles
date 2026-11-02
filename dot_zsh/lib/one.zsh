one() {
  local one_dir="$HOME/Projects/saas/one"

  if (( $# == 0 )); then
    builtin cd -- "$one_dir" || return
    one help
  elif (( $# == 1 )) && [[ $1 == up ]]; then
    (builtin cd -- "$one_dir" && command make up)
  elif (( $# == 1 )) && [[ $1 == down ]]; then
    (builtin cd -- "$one_dir" && command make down)
  elif (( $# == 1 )) && [[ $1 == reset-env ]]; then
    (builtin cd -- "$one_dir" && ./bin/artisan retail-api hook:deploy --reset-environment)
  elif (( $# == 1 )) && [[ $1 == model-sync ]]; then
    (builtin cd -- "$one_dir" && ./bin/artisan retail-api model:sync)
  elif (( $# == 1 )) && [[ $1 == test ]]; then
    (builtin cd -- "$one_dir" && ./bin/test retail-api)
  elif (( $# == 1 )) && [[ $1 == phpstan ]]; then
    (builtin cd -- "$one_dir" && ./bin/phpstan retail-api)
  elif (( $# == 1 )) && [[ $1 == fmt ]]; then
    (builtin cd -- "$one_dir" && ./bin/format retail-api)
  elif (( $# == 1 )) && [[ $1 == h || $1 == -h || $1 == help ]]; then
    print -rl -- \
      'Usage: one [up|down|reset-env|model-sync|test|phpstan|fmt|h|-h|help]' \
      '  one               Go to ~/Projects/saas/one and show this command list' \
      '  one up            Run make up in that directory' \
      '  one down          Run make down in that directory' \
      '  one reset-env     Run bin/artisan retail-api hook:deploy --reset-environment' \
      '  one model-sync    Run bin/artisan retail-api model:sync' \
      '  one test          Run bin/test retail-api' \
      '  one phpstan       Run bin/phpstan retail-api' \
      '  one fmt           Run bin/format retail-api' \
      '  one h|-h|help     Show this command list'
  else
    print -u2 'Usage: one [up|down|reset-env|model-sync|test|phpstan|fmt|h|-h|help]'
    return 2
  fi
}

_one() {
  local -a commands=(
    'up:Run make up in the one directory'
    'down:Run make down in the one directory'
    'reset-env:Run the retail-api environment reset'
    'model-sync:Run retail-api model synchronization'
    'test:Run retail-api tests'
    'phpstan:Run retail-api PHPStan checks'
    'fmt:Format retail-api code'
    'h:Show the command list'
    '-h:Show the command list'
    'help:Show the command list'
  )

  _describe -t commands 'one command' commands
}

compdef _one one
