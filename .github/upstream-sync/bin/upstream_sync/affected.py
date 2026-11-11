"""比较两个版本的源目录渲染出的目标，找出受影响的部署目标和脚本（设计 6.2）。

两个版本各导出到临时目录，用 `chezmoi archive` 渲染成 tar 包再逐项比较。这样 `.chezmoitemplates/`
里的副本被哪些目标引用，不用另外去查。加密文件不渲染，因为渲染它们需要解密。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass

from .gitcmd import git

CONFIG_TEMPLATE = ".chezmoi.toml.tmpl"


class AffectedError(Exception):
    pass


@dataclass(frozen=True)
class Target:
    path: str  # 相对 $HOME 的目标路径
    change: str  # added、removed 或 changed

    @property
    def is_script(self) -> bool:
        return self.path.startswith(".chezmoiscripts/")


def _render(repo: str, commit: str, workdir: str, chezmoi_args: list[str]) -> dict[str, tuple[int, bytes]]:
    # 两个版本先后导出到同一个目录，否则引用 .chezmoi.sourceDir 的模板会因为路径不同而被误报。
    tree = os.path.join(workdir, "source")
    if os.path.exists(tree):
        shutil.rmtree(tree)
    os.makedirs(tree)
    archive = subprocess.run(["git", "archive", commit], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", tree], input=archive, check=True)
    output = os.path.join(workdir, f"{commit}.tar")
    result = subprocess.run(
        ["chezmoi", *chezmoi_args, "--source", tree, "archive", "--format=tar", "--exclude=encrypted", "--output", output],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AffectedError(f"chezmoi archive failed for {commit[:9]}: {result.stderr.strip()}")
    entries: dict[str, tuple[int, bytes]] = {}
    with tarfile.open(output) as tar:
        for member in tar.getmembers():
            if member.isdir():
                continue
            if member.issym():
                content = member.linkname.encode()
            else:
                handle = tar.extractfile(member)
                content = handle.read() if handle else b""
            name = member.name[2:] if member.name.startswith("./") else member.name
            entries[name] = (member.mode, content)
    return entries


def affected(repo: str, old: str, new: str, chezmoi_args: list[str] | None = None) -> tuple[list[Target], bool]:
    """返回受影响的目标，以及 chezmoi 配置模板是否改变（改变时要重新运行 chezmoi init）。"""
    old_id = git("rev-parse", "--verify", old, cwd=repo).strip()
    new_id = git("rev-parse", "--verify", new, cwd=repo).strip()
    with tempfile.TemporaryDirectory() as workdir:
        before = _render(repo, old_id, workdir, chezmoi_args or [])
        after = _render(repo, new_id, workdir, chezmoi_args or [])
    targets = []
    for path in sorted(before.keys() | after.keys()):
        if path not in before:
            targets.append(Target(path, "added"))
        elif path not in after:
            targets.append(Target(path, "removed"))
        elif before[path] != after[path]:
            targets.append(Target(path, "changed"))
    config_changed = bool(git("diff", "--name-only", old_id, new_id, "--", CONFIG_TEMPLATE, cwd=repo).strip())
    return targets, config_changed
