"""对 git 命令的简单封装。"""

from __future__ import annotations

import subprocess


class GitError(Exception):
    pass


def git(*args: str, cwd: str, input: str | None = None, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        input=input,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise GitError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def succeeds(*args: str, cwd: str) -> bool:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True).returncode == 0


def rev(ref: str, cwd: str) -> str | None:
    """解析成完整的 object id，不存在时返回 None。"""
    out = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref], cwd=cwd, capture_output=True, text=True
    )
    return out.stdout.strip() or None


def entry(commit: str, path: str, cwd: str) -> tuple[str, str] | None:
    """返回 commit 里某个路径的 (mode, blob id)，路径不存在时返回 None。"""
    out = git("ls-tree", "-z", commit, "--", path, cwd=cwd)
    for record in out.split("\0"):
        if not record:
            continue
        meta, name = record.split("\t", 1)
        if name == path:
            mode, _type, oid = meta.split()
            return mode, oid
    return None
