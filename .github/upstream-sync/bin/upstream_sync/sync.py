"""准备任务的机械步骤：更新镜像分支、算出待处理列表、把上游 commit 准备到工单分支上。

设计见 .github/upstream-sync/design.md 第 2、4、5 节。
"""

from __future__ import annotations

import datetime
import fcntl
import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

from . import rules as rules_mod
from . import ticket as ticket_mod
from .github import IN_PROGRESS
from .gitcmd import GitError, entry, git, rev, succeeds

RULES_PATH = ".github/upstream-sync/rules"
ZERO_OID = "0" * 40


class SyncError(Exception):
    pass


@dataclass
class Config:
    repo: str  # chezmoi 的源目录，始终停在 main 上
    worktree: str  # 工单分支检出的位置
    url: str = "https://github.com/liby/dotfiles.git"
    upstream_ref: str = "main"
    mirror: str = "upstream"
    ticket: str = "upstream-sync"
    main: str = "main"
    remote: str = "origin"
    github_repo: str = "imzyf/dotfiles"
    state_dir: str = os.path.expanduser("~/.local/state/upstream-sync")


@contextmanager
def lock(state_dir: str) -> Iterator[None]:
    """防止两次准备任务同时运行。进程退出时锁自动释放。"""
    os.makedirs(state_dir, exist_ok=True)
    handle = open(os.path.join(state_dir, "prepare.lock"), "w")
    try:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SyncError("another preparation run is in progress") from None
        yield
    finally:
        handle.close()


def update_mirror(cfg: Config, today: str) -> str:
    """把上游快进到镜像分支。上游改写了历史时保留旧镜像并停下来，不覆盖。"""
    git("fetch", "--no-tags", "--quiet", cfg.url, cfg.upstream_ref, cwd=cfg.repo)
    new = rev("FETCH_HEAD", cfg.repo)
    old = rev(f"refs/heads/{cfg.mirror}", cfg.repo)
    if new is None:
        raise SyncError("fetch did not produce FETCH_HEAD")
    if old == new:
        return f"mirror {cfg.mirror} is up to date at {new[:9]}"
    if old and not succeeds("merge-base", "--is-ancestor", old, new, cwd=cfg.repo):
        tag = f"upstream-archive/{today}"
        if rev(f"refs/tags/{tag}", cfg.repo) is None:
            git("tag", tag, old, cwd=cfg.repo)
        raise SyncError(
            f"upstream history was rewritten: {old[:9]} is not an ancestor of {new[:9]}. "
            f"Kept the old mirror as tag {tag} and stopped without updating {cfg.mirror}."
        )
    git("update-ref", f"refs/heads/{cfg.mirror}", new, old or ZERO_OID, cwd=cfg.repo)
    return f"mirror {cfg.mirror} moved {old[:9] if old else '(new)'} -> {new[:9]}"


def recorded(cfg: Config, rev_range: str) -> set[str]:
    """rev_range 里所有 Upstream-Commit trailer 的值。"""
    out = git("log", "--format=%(trailers:key=Upstream-Commit,valueonly)", rev_range, cwd=cfg.repo)
    return {line.strip() for line in out.splitlines() if line.strip()}


def upstream_commits(cfg: Config, base: str) -> list[str]:
    """起点之后的上游 commit，按上游顺序，跳过 merge commit。"""
    out = git("rev-list", "--reverse", "--no-merges", f"{base}..refs/heads/{cfg.mirror}", cwd=cfg.repo)
    return out.split()


@dataclass
class Pending:
    commit: str
    subject: str
    prepared: bool


def pending(cfg: Config, base: str) -> list[Pending]:
    done = recorded(cfg, cfg.main)
    prepared: set[str] = set()
    if rev(f"refs/heads/{cfg.ticket}", cfg.repo):
        prepared = recorded(cfg, f"{cfg.main}..{cfg.ticket}")
    result = []
    for commit in upstream_commits(cfg, base):
        if commit in done:
            continue
        subject = git("log", "-1", "--format=%s", commit, cwd=cfg.repo).strip()
        result.append(Pending(commit, subject, commit in prepared))
    return result


def ensure_worktree(cfg: Config) -> None:
    """工单分支只在 worktree 里检出，源目录始终停在 main 上（设计 4.1）。"""
    if rev(f"refs/heads/{cfg.ticket}", cfg.repo) is None:
        git("branch", "--no-track", cfg.ticket, cfg.main, cwd=cfg.repo)
    if not os.path.isdir(cfg.worktree):
        git("worktree", "prune", cwd=cfg.repo)  # 目录被手动删掉时，先清掉 Git 里的旧登记
        git("worktree", "add", "--quiet", cfg.worktree, cfg.ticket, cwd=cfg.repo)
    head = git("symbolic-ref", "--quiet", "HEAD", cwd=cfg.worktree).strip()
    if head != f"refs/heads/{cfg.ticket}":
        raise SyncError(f"{cfg.worktree} is on {head or 'a detached HEAD'}, expected {cfg.ticket}")
    if git("status", "--porcelain", cwd=cfg.worktree).strip():
        raise SyncError(f"{cfg.worktree} has uncommitted changes")


def load_rules(cfg: Config, tree: str) -> tuple[rules_mod.Rules, rules_mod.Report]:
    path = os.path.join(tree, RULES_PATH)
    try:
        with open(path) as handle:
            text = handle.read()
    except FileNotFoundError:
        raise SyncError(f"rules file not found: {path}") from None
    files = git("ls-tree", "-r", "--name-only", f"refs/heads/{cfg.mirror}", cwd=cfg.repo).splitlines()
    return rules_mod.validate(
        text,
        files,
        base_exists=lambda base: succeeds(
            "merge-base", "--is-ancestor", base, f"refs/heads/{cfg.mirror}", cwd=cfg.repo
        ),
        local_exists=lambda p: os.path.lexists(os.path.join(tree, p)),
    )


@dataclass
class Change:
    status: str  # A、M、D 或 T
    path: str
    old: tuple[str, str] | None
    new: tuple[str, str] | None
    renamed: str | None = None  # 改名时另一边的路径

    def notes(self) -> list[str]:
        if self.status == "A":
            return ["added"] + ([f"renamed from {self.renamed}"] if self.renamed else [])
        if self.status == "D":
            return ["deleted"] + ([f"renamed to {self.renamed}"] if self.renamed else [])
        return []


def changes(cfg: Config, commit: str) -> list[Change]:
    """改名拆成旧路径的删除和新路径的新增，两边各自按规则处理，并互相记下对方的路径。"""
    out = git("diff-tree", "-r", "-z", "-M", "--no-commit-id", f"{commit}^", commit, cwd=cfg.repo)
    fields = out.split("\0")
    result = []
    i = 0
    while i + 1 < len(fields):
        old_mode, new_mode, old_oid, new_oid, status = fields[i].lstrip(":").split()
        old, new = (old_mode, old_oid), (new_mode, new_oid)
        if status[0] == "R":
            src, dst = fields[i + 1], fields[i + 2]
            result.append(Change("D", src, old, None, renamed=dst))
            result.append(Change("A", dst, None, new, renamed=src))
            i += 3
            continue
        path = fields[i + 1]
        result.append(Change(status[0], path, None if status == "A" else old, None if status == "D" else new))
        i += 2
    return result


def _label(text: str, notes: list[str]) -> str:
    return f"{text} ({', '.join(notes)})" if notes else text


@dataclass
class Prepared:
    commit: str
    subject: str
    applied: list[str] = field(default_factory=list)
    not_applied: list[str] = field(default_factory=list)
    new_files: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)


def plan(cfg: Config, rules: rules_mod.Rules, commit: str, tree_commit: str) -> tuple[Prepared, list[tuple[str, tuple[str, str] | None]]]:
    """算出一个上游 commit 在本地要做的改动。tree_commit 是要在其上应用的本地 commit。"""
    subject = git("log", "-1", "--format=%s", commit, cwd=cfg.repo).strip()
    result = Prepared(commit, subject)
    ops: list[tuple[str, tuple[str, str] | None]] = []
    follow_lines: list[str] = []
    for change in changes(cfg, commit):
        c = rules_mod.classify(rules, change.path)
        if c.kind != "follow" or c.local is None:
            result.not_applied.append(_label(change.path, [c.kind or "unclassified"] + change.notes()))
            continue
        target = change.path if c.local == change.path else f"{change.path} -> {c.local}"
        shown = _label(target, change.notes())
        follow_lines.append(_label(target, ["follow"] + change.notes()))
        current = entry(tree_commit, c.local, cfg.repo)
        if current == change.new:
            continue  # 本地已经是上游这个 commit 之后的内容
        if change.status == "A":
            if current is not None:
                result.failed.append(f"{c.local}: already exists locally with different content")
                continue
            result.new_files.append(c.local)
        elif current is None:
            result.failed.append(f"{c.local}: missing locally")
            continue
        elif current != change.old:
            result.failed.append(f"{c.local}: differs from upstream before this commit")
            continue
        ops.append((c.local, change.new))
        result.applied.append(shown)
    if result.failed:
        result.not_applied = follow_lines + result.not_applied
        result.applied, result.new_files, ops = [], [], []
    return result, ops


def message(cfg: Config, p: Prepared) -> str:
    original = git("log", "-1", "--format=%B", p.commit, cwd=cfg.repo).rstrip()
    author = git("log", "-1", "--format=%an", p.commit, cwd=cfg.repo).strip()

    def section(title: str, items: list[str]) -> str:
        return title + ":\n" + "\n".join(f"  {item}" for item in (items or ["none"]))

    parts = [original, ""]
    if p.failed:
        parts += [section("Failed to apply", p.failed)]
    parts += [
        section("Applied", p.applied),
        section("Not applied", p.not_applied),
        section("New upstream files", p.new_files),
        "",
        f"Upstream-Commit: {p.commit}",
        f"Upstream-Author: {author}",
        "Upstream-Decision: pending",
    ]
    return "\n".join(parts) + "\n"


def commit_prepared(cfg: Config, p: Prepared, ops: list[tuple[str, tuple[str, str] | None]]) -> None:
    wt = cfg.worktree
    for path, new in ops:
        if new is None:
            git("update-index", "--force-remove", "--", path, cwd=wt)
        else:
            git("update-index", "--add", "--cacheinfo", f"{new[0]},{new[1]},{path}", cwd=wt)
    git(
        "-c", "commit.gpgsign=false",
        "commit", "--quiet", "--allow-empty", "--no-verify", "-F", "-",
        cwd=wt,
        input=message(cfg, p),
    )
    # 提交只更新了 index，再把工作目录同步到新的 HEAD。
    for path, new in ops:
        full = os.path.join(wt, path)
        if new is None:
            if os.path.lexists(full):
                os.remove(full)
                _remove_empty_parents(os.path.dirname(full), wt)
        else:
            git("checkout", "--", path, cwd=wt)


def _remove_empty_parents(directory: str, stop: str) -> None:
    while directory != stop and os.path.isdir(directory) and not os.listdir(directory):
        os.rmdir(directory)
        directory = os.path.dirname(directory)


def prepare(cfg: Config) -> tuple[list[Prepared], rules_mod.Report]:
    """把还没准备的上游 commit 逐个准备到工单分支上（设计 5.2 第 4 步）。"""
    ensure_worktree(cfg)
    rules, report = load_rules(cfg, cfg.worktree)
    if report.errors:
        raise SyncError("rules file has errors:\n" + "\n".join(f"  {e}" for e in report.errors))
    assert rules.base is not None
    done = recorded(cfg, cfg.main) | recorded(cfg, f"{cfg.main}..{cfg.ticket}")
    results = []
    for commit in upstream_commits(cfg, rules.base):
        if commit in done:
            continue
        head = rev("HEAD", cfg.worktree)
        assert head is not None
        p, ops = plan(cfg, rules, commit, head)
        try:
            commit_prepared(cfg, p, ops)
        except GitError as error:
            raise SyncError(f"failed to commit {commit[:9]}: {error}") from error
        results.append(p)
    return results, report


def push_mirror(cfg: Config) -> None:
    """镜像分支只会快进，所以普通 push 就够了。"""
    git("push", "--quiet", cfg.remote, f"refs/heads/{cfg.mirror}:refs/heads/{cfg.mirror}", cwd=cfg.repo)


def push_ticket(cfg: Config) -> None:
    """工单分支会被 rebase，用 --force-with-lease：远端在别处被改过时不覆盖。"""
    ref = f"refs/heads/{cfg.ticket}"
    git("push", "--quiet", f"--force-with-lease={ref}", cfg.remote, f"{ref}:{ref}", cwd=cfg.repo)


@dataclass
class TaskResult:
    messages: list[str] = field(default_factory=list)
    prepared: list[Prepared] = field(default_factory=list)
    report: rules_mod.Report | None = None
    pr_url: str | None = None


def _parse_time(value: str) -> datetime.datetime:
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def run_task(cfg: Config, gh, now: datetime.datetime, update_mirror_first: bool = True) -> TaskResult:
    """准备任务的完整步骤（设计 5.2）。gh 为 None 时只在本地运行，不 push，也不读写 PR。"""
    result = TaskResult()
    with lock(cfg.state_dir):
        if update_mirror_first:
            result.messages.append(update_mirror(cfg, now.date().isoformat()))
            if gh:
                push_mirror(cfg)
        pr = gh.find_pr(cfg.ticket) if gh else None
        if pr and IN_PROGRESS in pr.labels:
            result.pr_url = pr.url
            result.messages.append(f"{pr.url} is labelled {IN_PROGRESS}; only the mirror was updated")
            added = gh.label_added_at(pr.number, IN_PROGRESS)
            if added and now - _parse_time(added) > datetime.timedelta(days=1):
                result.messages.append(
                    f"warning: the {IN_PROGRESS} label was added at {added}, more than a day ago. "
                    "If no session is running, finish or abandon it and remove the label."
                )
            return result
        result.prepared, result.report = prepare(cfg)
        if gh:
            entries = ticket_mod.items(cfg.repo, cfg.main, cfg.ticket)
            if entries:
                push_ticket(cfg)
                title = ticket_mod.title(entries)
                body = ticket_mod.body(entries, cfg.github_repo, cfg.mirror)
                if pr:
                    gh.edit_pr(pr.number, title, body)
                    result.pr_url = pr.url
                else:
                    result.pr_url = gh.create_pr(cfg.main, cfg.ticket, title, body)
    return result
