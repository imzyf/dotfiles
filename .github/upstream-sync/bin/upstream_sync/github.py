"""通过 gh 读写工单 PR。测试里用同样接口的假对象代替。"""

from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass, field

IN_PROGRESS = "in-progress"


class GitHubError(Exception):
    pass


@dataclass
class PullRequest:
    number: int
    url: str
    labels: list[str] = field(default_factory=list)


class GitHub:
    def __init__(self, repo: str):
        self.repo = repo

    def _gh(self, *args: str) -> str:
        result = subprocess.run(["gh", *args], capture_output=True, text=True)
        if result.returncode != 0:
            raise GitHubError(f"gh {' '.join(args[:2])} failed: {result.stderr.strip() or result.stdout.strip()}")
        return result.stdout

    def find_pr(self, head: str) -> PullRequest | None:
        out = self._gh(
            "pr", "list", "--repo", self.repo, "--head", head, "--state", "open",
            "--json", "number,url,labels",
        )
        prs = json.loads(out)
        if not prs:
            return None
        pr = prs[0]
        return PullRequest(pr["number"], pr["url"], [label["name"] for label in pr["labels"]])

    def label_added_at(self, number: int, label: str) -> str | None:
        """最近一次加上这个标签的时间（ISO 8601），没有记录时返回 None。"""
        out = self._gh(
            "api", "--paginate", f"repos/{self.repo}/issues/{number}/events",
            "--jq", f'.[] | select(.event == "labeled" and .label.name == "{label}") | .created_at',
        )
        times = out.split()
        return times[-1] if times else None

    def create_pr(self, base: str, head: str, title: str, body: str) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".md") as handle:
            handle.write(body)
            handle.flush()
            out = self._gh(
                "pr", "create", "--repo", self.repo, "--base", base, "--head", head,
                "--title", title, "--body-file", handle.name,
            )
        return out.strip()

    def edit_pr(self, number: int, title: str, body: str) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".md") as handle:
            handle.write(body)
            handle.flush()
            self._gh("pr", "edit", str(number), "--repo", self.repo, "--title", title, "--body-file", handle.name)
