#!/bin/zsh
#
# Copy the paths listed in sync-upstream.paths from the upstream dotfiles repo
# into this repo. A line starting with '!' excludes a path instead. Local files
# are overwritten unconditionally, so commit or stash first, then review the
# result with git diff.

set -euo pipefail

upstream_repo="${UPSTREAM_REPO:-https://github.com/liby/dotfiles.git}"
upstream_ref="${UPSTREAM_REF:-main}"

# Clones live here and are reused until they age past the TTL. Set
# SYNC_CACHE_TTL_MIN=0 to force a fresh clone.
cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles-sync"
cache_ttl_minutes="${SYNC_CACHE_TTL_MIN:-60}"

script_dir="${0:A:h}"
repo_root="$(git -C "$script_dir" rev-parse --show-toplevel)"

typeset -a includes excludes
for line in ${(f)"$(grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$script_dir/sync-upstream.paths" || true)"}; do
  line="${${line##[[:space:]]#}%%/}"
  if [[ "$line" == '!'* ]]; then
    excludes+=("${line#!}")
  else
    includes+=("$line")
  fi
done

# Excluded when the path is listed itself or sits under an excluded directory.
is_excluded() {
  local rel="$1" pattern
  for pattern in ${excludes[@]:-}; do
    [[ "$rel" == "$pattern" || "$rel" == "$pattern"/* ]] && return 0
  done
  return 1
}

copy_file() {
  local rel="$1"
  if is_excluded "$rel"; then
    print -r -- "skipped  $rel"
    return
  fi
  mkdir -p "$repo_root/${rel:h}"
  cp -f "$clone_dir/$rel" "$repo_root/$rel"
  print -r -- "copied   $rel"
}

clone_dir="$cache_root/${upstream_repo//[^A-Za-z0-9._-]/-}@${upstream_ref//\//-}"

# find prints the directory only when it is older than the TTL, so empty output
# means the cached clone is still fresh. TTL 0 is checked separately because
# 'find -mmin +0' truncates to whole minutes and would keep a clone made
# seconds ago.
if ((cache_ttl_minutes > 0)) &&
  [[ -d "$clone_dir/.git" && -z "$(find "$clone_dir" -maxdepth 0 -mmin +$cache_ttl_minutes)" ]]; then
  print -r -- "Reusing clone cached at $clone_dir"
else
  print -r -- "Cloning $upstream_repo@$upstream_ref"
  rm -rf "$clone_dir"
  mkdir -p "${clone_dir:h}"
  git clone --quiet --depth 1 --branch "$upstream_ref" "$upstream_repo" "$clone_dir"
  touch "$clone_dir"
fi

for entry in ${includes[@]:-}; do
  src="$clone_dir/$entry"

  if [[ ! -e "$src" ]]; then
    print -r -- "missing upstream: $entry" >&2
  elif [[ -d "$src" ]]; then
    # Copy a directory file by file so excluded children keep the local version.
    for child in ${(f)"$(cd "$src" && find . \( -type f -o -type l \) | sed 's|^\./||')"}; do
      copy_file "$entry/$child"
    done
  else
    copy_file "$entry"
  fi
done

print -r -- "Review with: git -C $repo_root diff"
