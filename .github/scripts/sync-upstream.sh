#!/bin/zsh
#
# 把 sync-upstream.paths 里列出的路径从上游 dotfiles 仓库复制到本仓库。
# 以 '!' 开头的行表示排除这个路径。'上游路径 > 本地路径' 形式的行把上游文件
# 复制到另一个本地路径，上游路径对应的本地文件不动，这样本地已经改过的文件
# 可以和上游版本并存。本地文件会被无条件覆盖，所以先 commit 或 stash，
# 之后用 git diff 检查结果。

set -euo pipefail

# 下面裁剪行首行尾空白用到 '[[:space:]]#'（零个或多个）这种写法，需要开启。
setopt extended_glob

upstream_repo="${UPSTREAM_REPO:-https://github.com/liby/dotfiles.git}"
upstream_ref="${UPSTREAM_REF:-main}"

# clone 存在这里，在 TTL 之内重复使用。设 SYNC_CACHE_TTL_MIN=0 强制重新 clone。
cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/dotfiles-sync"
cache_ttl_minutes="${SYNC_CACHE_TTL_MIN:-60}"

script_dir="${0:A:h}"
repo_root="$(git -C "$script_dir" rev-parse --show-toplevel)"

# includes 和 destinations 一一对应：destinations[i] 是 includes[i] 复制到的本地
# 路径，除非这一行写了映射，否则两者相同。
typeset -a includes destinations excludes preserved_sources
for line in ${(f)"$(grep -v -e '^[[:space:]]*#' -e '^[[:space:]]*$' "$script_dir/sync-upstream.paths" || true)"}; do
  line="${${line##[[:space:]]#}%%[[:space:]]#}"
  if [[ "$line" == '!'* ]]; then
    excludes+=("${${line#!}%%/}")
  elif [[ "$line" == *'>'* ]]; then
    src="${${${line%%>*}%%[[:space:]]#}%%/}"
    dest="${${${line#*>}##[[:space:]]#}%%/}"
    if [[ -z "$src" || -z "$dest" ]]; then
      print -r -- "invalid mapping: $line" >&2
      exit 1
    fi
    includes+=("$src")
    destinations+=("$dest")
    # src 上的本地文件保留自己的内容，整个父目录被同步时也一样。
    preserved_sources+=("$src")
  else
    includes+=("${line%%/}")
    destinations+=("${line%%/}")
  fi
done

# 逐级匹配路径，避免普通 glob 跨越 '/'。单独的 '**' 路径部分可以匹配零级
# 或多级目录。
matches_exclusion() {
  local rel="$1" pattern="$2" component="${2%%/*}"
  if [[ "$component" == '**' ]]; then
    [[ "$pattern" != */* ]] && return 0
    matches_exclusion "$rel" "${pattern#*/}" && return 0
    if [[ "$rel" == */* ]]; then
      matches_exclusion "${rel#*/}" "$pattern" && return 0
    fi
  elif [[ "${rel%%/*}" == ${~component} ]]; then
    # 匹配到目录时，也排除该目录下的所有内容。
    [[ "$pattern" != */* ]] && return 0
    if [[ "$rel" == */* ]]; then
      matches_exclusion "${rel#*/}" "${pattern#*/}" && return 0
    fi
  fi
  return 1
}

# 本地路径本身被列出，或者位于被排除的目录之下，就算排除。用目的路径来匹配，
# 因为 '!' 的含义是这个路径保留本地版本。
is_excluded() {
  local rel="$1" pattern
  # 即使映射源路径包含 glob 字符，也仍然按字面路径处理。
  for pattern in "${excludes[@]}" "${preserved_sources[@]}"; do
    [[ "$rel" == "$pattern" || "$rel" == "$pattern"/* ]] && return 0
  done
  for pattern in "${excludes[@]}"; do
    matches_exclusion "$rel" "$pattern" && return 0
  done
  return 1
}

copy_file() {
  local rel="$1" dest="$2"
  if is_excluded "$dest"; then
    print -r -- "skipped  $dest"
    return
  fi
  mkdir -p "$repo_root/${dest:h}"
  cp -f "$clone_dir/$rel" "$repo_root/$dest"
  if [[ "$rel" == "$dest" ]]; then
    print -r -- "copied   $rel"
  else
    print -r -- "copied   $rel > $dest"
  fi
}

clone_dir="$cache_root/${upstream_repo//[^A-Za-z0-9._-]/-}@${upstream_ref//\//-}"

# 只有目录的修改时间超过 TTL，find 才会打印它，所以输出为空说明缓存的 clone 还
# 在有效期内。TTL 为 0 的情况单独判断，因为 'find -mmin +0' 按整分钟截断，会把
# 几秒前建的 clone 也当成有效。
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

for ((i = 1; i <= $#includes; i++)); do
  entry="$includes[i]"
  dest="$destinations[i]"
  src="$clone_dir/$entry"

  if [[ ! -e "$src" ]]; then
    print -r -- "missing upstream: $entry" >&2
  elif [[ -d "$src" ]]; then
    # 目录按文件逐个复制，被排除的子路径就能保留本地版本。
    for child in ${(f)"$(cd "$src" && find . \( -type f -o -type l \) | sed 's|^\./||')"}; do
      copy_file "$entry/$child" "$dest/$child"
    done
  else
    copy_file "$entry" "$dest"
  fi
done

print -r -- "Review with: git -C $repo_root diff"
