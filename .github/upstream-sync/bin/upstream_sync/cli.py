"""命令行入口。"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys

from . import sync
from .affected import AffectedError, affected
from .github import GitHub, GitHubError
from .gitcmd import GitError, git
from .rules import Report

DEFAULT_WORKTREE = os.path.expanduser("~/Code/worktrees/chezmoi-upstream-sync")


def config() -> sync.Config:
    here = os.path.dirname(os.path.realpath(__file__))
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=here).strip()
    cfg = sync.Config(
        repo=os.path.dirname(common),
        worktree=os.environ.get("UPSTREAM_SYNC_WORKTREE", DEFAULT_WORKTREE),
    )
    cfg.url = os.environ.get("UPSTREAM_SYNC_URL", cfg.url)
    cfg.state_dir = os.environ.get("UPSTREAM_SYNC_STATE_DIR", cfg.state_dir)
    origin = git("remote", "get-url", cfg.remote, cwd=cfg.repo).strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", origin)
    if match:
        cfg.github_repo = match.group(1)
    return cfg


def print_report(report: Report) -> None:
    for error in report.errors:
        print(f"error: {error}")
    for rule in report.unmatched:
        print(f"warning: line {rule.line}: '{rule.kind} {rule.pattern}' matches no upstream file")
    for rule in report.shadowed:
        print(f"warning: line {rule.line}: '{rule.kind} {rule.pattern}' is overridden by later rules for every file it matches")
    for path in report.unclassified:
        print(f"unclassified: {path}")


def cmd_check(cfg: sync.Config, args: argparse.Namespace) -> int:
    tree = git("rev-parse", "--show-toplevel", cwd=os.getcwd()).strip()
    _rules, report = sync.load_rules(cfg, tree)
    print_report(report)
    return 1 if report.errors else 0


def cmd_mirror(cfg: sync.Config, args: argparse.Namespace) -> int:
    print(sync.update_mirror(cfg, datetime.date.today().isoformat()))
    return 0


def cmd_pending(cfg: sync.Config, args: argparse.Namespace) -> int:
    rules, report = sync.load_rules(cfg, cfg.worktree if os.path.isdir(cfg.worktree) else cfg.repo)
    if report.errors or rules.base is None:
        print_report(report)
        return 1
    items = sync.pending(cfg, rules.base)
    for item in items:
        state = "prepared" if item.prepared else "new"
        print(f"{item.commit[:9]}  {state:<8}  {item.subject}")
    print(f"{len(items)} pending")
    return 0


def cmd_affected(cfg: sync.Config, args: argparse.Namespace) -> int:
    targets, config_changed = affected(cfg.repo, args.old, args.new)
    home = os.path.expanduser("~")
    for t in targets:
        kind = "script" if t.is_script else "file"
        print(f"{t.change:<8} {kind:<6} {os.path.join(home, t.path)}")
    print(f"{len(targets)} targets affected")
    if config_changed:
        print("warning: .chezmoi.toml.tmpl changed; run chezmoi init to regenerate the config")
    return 0


def cmd_prepare(cfg: sync.Config, args: argparse.Namespace) -> int:
    gh = None if args.local else GitHub(cfg.github_repo)
    now = datetime.datetime.now(datetime.timezone.utc)
    result = sync.run_task(cfg, gh, now, update_mirror_first=not args.no_mirror)
    if result.report:
        print_report(result.report)
    for line in result.messages:
        print(line)
    for p in result.prepared:
        flag = "FAILED" if p.failed else f"{len(p.applied)} applied"
        risk = f"  [{', '.join(p.risks)}]" if p.risks else ""
        print(f"{p.commit[:9]}  {flag:<10}  {p.subject}{risk}")
    print(f"prepared {len(result.prepared)} commits on {cfg.ticket} in {cfg.worktree}")
    if result.pr_url:
        print(f"ticket: {result.pr_url}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="upstream-sync", description="Prepare upstream liby/dotfiles changes for review.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="validate the rules file in the current checkout")
    sub.add_parser("mirror", help="fast-forward the local mirror branch from upstream")
    sub.add_parser("pending", help="list upstream commits that are not in main yet")
    affected_cmd = sub.add_parser("affected", help="list targets whose rendered content differs between two commits")
    affected_cmd.add_argument("old")
    affected_cmd.add_argument("new")
    prepare = sub.add_parser("prepare", help="prepare pending upstream commits on the ticket branch")
    prepare.add_argument("--no-mirror", action="store_true", help="skip updating the mirror branch")
    prepare.add_argument("--local", action="store_true", help="do not push or touch the pull request")
    args = parser.parse_args(argv)
    handlers = {"affected": cmd_affected, "check": cmd_check, "mirror": cmd_mirror, "pending": cmd_pending, "prepare": cmd_prepare}
    try:
        return handlers[args.command](config(), args)
    except (sync.SyncError, GitHubError, GitError, AffectedError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
