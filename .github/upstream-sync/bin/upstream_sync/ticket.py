"""从工单分支上的 commit 整理出 PR 的标题和描述（设计 4.3）。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .gitcmd import git

GROUPS = (
    ("failed", "Failed to apply"),
    ("new", "New upstream files to confirm"),
    ("other", "Other local changes"),
    ("watch", "Watched files only"),
    ("no-change", "No local change"),
    ("processed", "Processed, waiting to merge"),
)


@dataclass
class Item:
    upstream: list[str]
    subject: str
    date: str
    decision: str
    failed: bool = False
    new_files: bool = False
    applied: bool = True
    watched: bool = False

    @property
    def group(self) -> str:
        if self.decision != "pending":
            return "processed"
        if self.failed:
            return "failed"
        if self.new_files:
            return "new"
        if self.applied:
            return "other"
        return "watch" if self.watched else "no-change"


def _section_first_item(message: str, title: str) -> str | None:
    match = re.search(rf"^{re.escape(title)}:\n  (.*)$", message, re.MULTILINE)
    return match.group(1) if match else None


def parse_item(message: str, upstream_date: str) -> Item | None:
    """解析一个准备好的 commit 的 message。没有 Upstream-Commit trailer 的 commit 不是工单项。"""
    upstream = re.findall(r"^Upstream-Commit: (\S+)$", message, re.MULTILINE)
    if not upstream:
        return None
    decision = re.search(r"^Upstream-Decision: (\S+)$", message, re.MULTILINE)
    return Item(
        upstream=upstream,
        subject=message.split("\n", 1)[0],
        date=upstream_date,
        decision=decision.group(1) if decision else "pending",
        failed=re.search(r"^Failed to apply:$", message, re.MULTILINE) is not None,
        new_files=_section_first_item(message, "New upstream files") not in (None, "none"),
        applied=_section_first_item(message, "Applied") != "none",
        watched=re.search(r"^Not applied:\n(?:  .*\n)*?  \S.* \(watch[,)]", message, re.MULTILINE) is not None,
    )


def items(repo: str, main: str, ticket: str) -> list[Item]:
    out = git("log", "--reverse", "--format=%B%x1e", f"{main}..{ticket}", cwd=repo)
    result = []
    for message in out.split("\x1e"):
        message = message.strip("\n")
        if not message:
            continue
        first = re.search(r"^Upstream-Commit: (\S+)$", message, re.MULTILINE)
        date = git("log", "-1", "--format=%as", first.group(1), cwd=repo).strip() if first else ""
        item = parse_item(message, date)
        if item:
            result.append(item)
    return result


def title(entries: list[Item]) -> str:
    pending = [e for e in entries if e.decision == "pending"]
    if not pending:
        return "Upstream sync: nothing pending"
    return f"Upstream sync: {len(pending)} pending since {min(e.date for e in pending)}"


def body(entries: list[Item], github_repo: str, mirror: str) -> str:
    pending = [e for e in entries if e.decision == "pending"]
    base = f"https://github.com/{github_repo}"
    lines = []
    if pending:
        dates = sorted(e.date for e in pending)
        lines.append(f"{len(pending)} upstream commits are waiting, from {dates[0]} to {dates[-1]}.")
    else:
        lines.append("No upstream commits are waiting.")
    lines.append(f"Full upstream commits are on the [`{mirror}`]({base}/commits/{mirror}) branch.")
    for key, heading in GROUPS:
        group = [e for e in entries if e.group == key]
        if not group:
            continue
        lines += ["", f"### {heading} ({len(group)})", ""]
        for e in group:
            links = ", ".join(f"[`{sha[:9]}`]({base}/commit/{sha})" for sha in e.upstream)
            lines.append(f"- {links} {e.subject} · {e.date}")
    return "\n".join(lines) + "\n"
