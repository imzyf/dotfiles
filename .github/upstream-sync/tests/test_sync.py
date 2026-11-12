import datetime
import os
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

from upstream_sync import sync  # noqa: E402
from upstream_sync.github import IN_PROGRESS, PullRequest  # noqa: E402
from upstream_sync.gitcmd import git, rev  # noqa: E402

# 不读用户自己的 Git 配置，比如签名和 hook。
ISOLATED_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Local User",
    "GIT_AUTHOR_EMAIL": "local@example.com",
    "GIT_COMMITTER_NAME": "Local User",
    "GIT_COMMITTER_EMAIL": "local@example.com",
}


def setUpModule():
    global _saved_env
    _saved_env = {k: os.environ.get(k) for k in ISOLATED_ENV}
    os.environ.update(ISOLATED_ENV)


def tearDownModule():
    for key, value in _saved_env.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def write(root, path, content, executable=False):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as handle:
        handle.write(content)
    if executable:
        os.chmod(full, os.stat(full).st_mode | stat.S_IXUSR)


def read(root, path):
    with open(os.path.join(root, path)) as handle:
        return handle.read()


def commit(root, message):
    git("add", "-A", cwd=root)
    git("commit", "--quiet", "--allow-empty", "-m", message, cwd=root)
    return rev("HEAD", root)


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = self.tmp.name
        self.up = os.path.join(root, "upstream")
        self.repo = os.path.join(root, "local")
        os.makedirs(self.up)
        os.makedirs(self.repo)
        git("init", "--quiet", "-b", "main", cwd=self.up)
        git("init", "--quiet", "-b", "main", cwd=self.repo)

        write(self.up, ".chezmoiscripts/run_a.sh", "echo a\n", executable=True)
        write(self.up, "dot_zshrc", "zshrc v1\n")
        write(self.up, "Brewfile", "brew 'a'\n")
        write(self.up, "docs/notes.md", "notes v1\n")
        os.environ["GIT_AUTHOR_NAME"] = "Upstream Author"
        self.base = commit(self.up, "base")
        os.environ["GIT_AUTHOR_NAME"] = ISOLATED_ENV["GIT_AUTHOR_NAME"]

        write(self.repo, ".chezmoiscripts/run_a.sh", "echo a\n", executable=True)
        write(self.repo, ".chezmoitemplates/zsh/upstream.dot_zshrc", "zshrc v1\n")
        write(self.repo, "Brewfile", "brew 'mine'\n")
        write(
            self.repo,
            sync.RULES_PATH,
            f"base {self.base}\n"
            "follow .chezmoiscripts/**\n"
            "follow dot_zshrc > .chezmoitemplates/zsh/upstream.dot_zshrc\n"
            "own Brewfile\n"
            "watch docs/**\n",
        )
        commit(self.repo, "local main")

        self.cfg = sync.Config(
            repo=self.repo,
            worktree=os.path.join(root, "worktree"),
            url=self.up,
            state_dir=os.path.join(root, "state"),
        )

    def tearDown(self):
        self.tmp.cleanup()

    def upstream_commit(self, message, files, author="Upstream Author"):
        """files 把路径映射到新内容，值为 None 表示删除。"""
        for path, content in files.items():
            if content is None:
                os.remove(os.path.join(self.up, path))
            else:
                write(self.up, path, content)
        os.environ["GIT_AUTHOR_NAME"] = author
        try:
            return commit(self.up, message)
        finally:
            os.environ["GIT_AUTHOR_NAME"] = ISOLATED_ENV["GIT_AUTHOR_NAME"]

    def ticket_messages(self):
        out = git("log", "--reverse", "--format=%B%x00", f"main..{self.cfg.ticket}", cwd=self.repo)
        return [m.strip() for m in out.split("\0") if m.strip()]


class MirrorTest(Fixture):
    def test_creates_and_fast_forwards(self):
        self.assertIn("(new)", sync.update_mirror(self.cfg, "2026-11-11"))
        self.assertEqual(rev("upstream", self.repo), self.base)
        new = self.upstream_commit("next", {"docs/notes.md": "notes v2\n"})
        sync.update_mirror(self.cfg, "2026-11-11")
        self.assertEqual(rev("upstream", self.repo), new)
        self.assertIn("up to date", sync.update_mirror(self.cfg, "2026-11-11"))

    def test_rewritten_history_keeps_archive_and_stops(self):
        self.upstream_commit("next", {"docs/notes.md": "notes v2\n"})
        sync.update_mirror(self.cfg, "2026-11-11")
        old = rev("upstream", self.repo)
        git("reset", "--quiet", "--hard", self.base, cwd=self.up)
        self.upstream_commit("rewritten", {"docs/notes.md": "other\n"})
        with self.assertRaises(sync.SyncError):
            sync.update_mirror(self.cfg, "2026-11-11")
        self.assertEqual(rev("upstream", self.repo), old)
        self.assertEqual(rev("upstream-archive/2026-11-11", self.repo), old)


class PrepareTest(Fixture):
    def prepare(self):
        sync.update_mirror(self.cfg, "2026-11-11")
        return sync.prepare(self.cfg)[0]

    def test_prepares_one_commit_per_upstream_commit(self):
        c1 = self.upstream_commit(
            "feat: add b\n\nUpstream body.",
            {
                ".chezmoiscripts/run_a.sh": "echo a2\n",
                ".chezmoiscripts/run_b.sh": "echo b\n",
                "Brewfile": "brew 'b'\n",
                "docs/notes.md": "notes v2\n",
            },
        )
        self.upstream_commit("fix: zshrc", {"dot_zshrc": "zshrc v2\n"})
        self.upstream_commit("docs: only notes", {"docs/notes.md": "notes v3\n"})
        self.upstream_commit("chore: drop b", {".chezmoiscripts/run_b.sh": None})

        results = self.prepare()
        self.assertEqual([p.subject for p in results], ["feat: add b", "fix: zshrc", "docs: only notes", "chore: drop b"])
        wt = self.cfg.worktree

        first = self.ticket_messages()[0]
        self.assertTrue(first.startswith("feat: add b\n\nUpstream body.\n\nApplied:\n"))
        self.assertIn("Applied:\n  .chezmoiscripts/run_a.sh\n  .chezmoiscripts/run_b.sh (added)\n", first)
        self.assertIn("Not applied:\n  Brewfile (own)\n  docs/notes.md (watch)\n", first)
        self.assertIn("New upstream files:\n  .chezmoiscripts/run_b.sh\n", first)
        self.assertTrue(first.endswith(f"Upstream-Commit: {c1}\nUpstream-Author: Upstream Author\nUpstream-Decision: pending"))

        second = self.ticket_messages()[1]
        self.assertIn("  dot_zshrc -> .chezmoitemplates/zsh/upstream.dot_zshrc\n", second)
        self.assertEqual(read(wt, ".chezmoitemplates/zsh/upstream.dot_zshrc"), "zshrc v2\n")

        self.assertIn("Applied:\n  none\n", self.ticket_messages()[2])
        self.assertIn("Applied:\n  .chezmoiscripts/run_b.sh (deleted)\n", self.ticket_messages()[3])
        self.assertEqual(git("diff", "--stat", f"{self.cfg.ticket}~2", f"{self.cfg.ticket}~1", cwd=self.repo), "")

        self.assertFalse(os.path.exists(os.path.join(wt, ".chezmoiscripts/run_b.sh")))
        self.assertEqual(read(wt, ".chezmoiscripts/run_a.sh"), "echo a2\n")
        self.assertEqual(read(wt, "Brewfile"), "brew 'mine'\n")
        self.assertEqual(git("status", "--porcelain", cwd=wt), "")
        self.assertEqual(read(self.repo, "Brewfile"), "brew 'mine'\n")
        self.assertEqual(git("symbolic-ref", "HEAD", cwd=self.repo).strip(), "refs/heads/main")

    def test_rename_to_unclassified_path_is_labelled(self):
        os.makedirs(os.path.join(self.up, "bin"))
        git("mv", ".chezmoiscripts/run_a.sh", "bin/run_a.sh", cwd=self.up)
        self.upstream_commit("refactor: move run_a", {})
        self.prepare()
        message = self.ticket_messages()[0]
        self.assertIn("Applied:\n  .chezmoiscripts/run_a.sh (deleted, renamed to bin/run_a.sh)\n", message)
        self.assertIn("Not applied:\n  bin/run_a.sh (unclassified, added, renamed from .chezmoiscripts/run_a.sh)\n", message)
        self.assertFalse(os.path.exists(os.path.join(self.cfg.worktree, ".chezmoiscripts/run_a.sh")))

    def test_upstream_file_on_local_path_is_not_applied(self):
        write(self.repo, ".chezmoiscripts/lib/mine.sh", "mine\n")
        with open(os.path.join(self.repo, sync.RULES_PATH), "a") as handle:
            handle.write("local .chezmoiscripts/lib/**\n")
        commit(self.repo, "register local files")
        self.upstream_commit("feat: add lib", {".chezmoiscripts/lib/mine.sh": "theirs\n"})
        self.prepare()
        _rules, report = sync.load_rules(self.cfg, self.repo)
        self.assertEqual([p for p, _r in report.conflicts], [".chezmoiscripts/lib/mine.sh"])
        message = self.ticket_messages()[0]
        self.assertIn("Not applied:\n  .chezmoiscripts/lib/mine.sh (local, added)\n", message)
        self.assertEqual(read(self.cfg.worktree, ".chezmoiscripts/lib/mine.sh"), "mine\n")

    def test_keeps_file_mode(self):
        self.upstream_commit("feat: exec", {"docs/notes.md": "x\n"})
        self.prepare()
        mode = git("ls-tree", self.cfg.ticket, ".chezmoiscripts/run_a.sh", cwd=self.repo).split()[0]
        self.assertEqual(mode, "100755")

    def test_rerun_prepares_only_new_commits(self):
        self.upstream_commit("one", {"dot_zshrc": "zshrc v2\n"})
        self.assertEqual(len(self.prepare()), 1)
        self.assertEqual(self.prepare(), [])
        self.upstream_commit("two", {"dot_zshrc": "zshrc v3\n"})
        self.assertEqual([p.subject for p in self.prepare()], ["two"])

    def test_commits_recorded_in_main_are_not_pending(self):
        c1 = self.upstream_commit("one", {"dot_zshrc": "zshrc v2\n"})
        self.upstream_commit("two", {"docs/notes.md": "x\n"})
        write(self.repo, ".chezmoitemplates/zsh/upstream.dot_zshrc", "zshrc v2\n")
        git("add", "-A", cwd=self.repo)
        git("commit", "--quiet", "-m", f"one\n\nUpstream-Commit: {c1}\nUpstream-Decision: accepted", cwd=self.repo)
        sync.update_mirror(self.cfg, "2026-11-11")
        self.assertEqual([p.subject for p in sync.pending(self.cfg, self.base)], ["two"])
        self.assertEqual([p.subject for p in sync.prepare(self.cfg)[0]], ["two"])

    def test_local_drift_becomes_failed_empty_commit(self):
        write(self.repo, ".chezmoitemplates/zsh/upstream.dot_zshrc", "edited locally\n")
        commit(self.repo, "local edit")
        self.upstream_commit("fix: zshrc", {"dot_zshrc": "zshrc v2\n"})
        results = self.prepare()
        self.assertTrue(results[0].failed)
        message = self.ticket_messages()[0]
        self.assertIn("Failed to apply:\n  .chezmoitemplates/zsh/upstream.dot_zshrc: differs from upstream before this commit\n", message)
        self.assertIn("Applied:\n  none\n", message)
        self.assertIn("Not applied:\n  dot_zshrc -> .chezmoitemplates/zsh/upstream.dot_zshrc (follow)\n", message)
        self.assertEqual(git("diff", "--stat", "main", self.cfg.ticket, cwd=self.repo), "")

    def test_skips_upstream_merge_commits(self):
        git("checkout", "--quiet", "-b", "side", cwd=self.up)
        self.upstream_commit("side change", {"docs/notes.md": "side\n"})
        git("checkout", "--quiet", "main", cwd=self.up)
        self.upstream_commit("main change", {"dot_zshrc": "zshrc v2\n"})
        git("merge", "--quiet", "--no-ff", "-m", "Merge side", "side", cwd=self.up)
        self.assertEqual(sorted(p.subject for p in self.prepare()), ["main change", "side change"])

    def test_rules_errors_stop_preparation(self):
        write(self.repo, sync.RULES_PATH, f"base {self.base}\nfolow x\n")
        commit(self.repo, "broken rules")
        sync.update_mirror(self.cfg, "2026-11-11")
        with self.assertRaisesRegex(sync.SyncError, "unknown keyword"):
            sync.prepare(self.cfg)

    def test_dirty_worktree_stops_preparation(self):
        sync.update_mirror(self.cfg, "2026-11-11")
        sync.prepare(self.cfg)
        write(self.cfg.worktree, "Brewfile", "dirty\n")
        with self.assertRaisesRegex(sync.SyncError, "uncommitted changes"):
            sync.prepare(self.cfg)

    def test_prepared_commits_are_unsigned_and_authored_by_user(self):
        self.upstream_commit("one", {"dot_zshrc": "zshrc v2\n"}, author="Someone Else")
        self.prepare()
        author, signature = git("log", "-1", "--format=%an%x00%G?", self.cfg.ticket, cwd=self.repo).strip().split("\0")
        self.assertEqual(author, "Local User")
        self.assertEqual(signature, "N")
        self.assertIn("Upstream-Author: Someone Else", self.ticket_messages()[0])


NOW = datetime.datetime(2026, 11, 11, 12, 0, tzinfo=datetime.timezone.utc)


class FakeGitHub:
    def __init__(self):
        self.pr = None
        self.label_time = None
        self.calls = []

    def find_pr(self, head):
        return self.pr

    def label_added_at(self, number, label):
        return self.label_time

    def create_pr(self, base, head, title, body):
        self.calls.append(("create", base, head, title, body))
        self.pr = PullRequest(1, "https://github.com/me/dotfiles/pull/1")
        return self.pr.url

    def edit_pr(self, number, title, body):
        self.calls.append(("edit", number, title, body))


class TaskTest(Fixture):
    def setUp(self):
        super().setUp()
        self.origin = os.path.join(self.tmp.name, "origin.git")
        git("init", "--quiet", "--bare", self.origin, cwd=self.tmp.name)
        git("remote", "add", "origin", self.origin, cwd=self.repo)
        git("push", "--quiet", "origin", "main", cwd=self.repo)
        self.gh = FakeGitHub()

    def remote_ref(self, branch):
        return rev(f"refs/heads/{branch}", self.origin)

    def test_first_run_pushes_and_creates_pr(self):
        self.upstream_commit("fix: zshrc", {"dot_zshrc": "zshrc v2\n"})
        result = sync.run_task(self.cfg, self.gh, NOW)
        self.assertEqual(result.pr_url, "https://github.com/me/dotfiles/pull/1")
        self.assertEqual(self.remote_ref("upstream"), rev("upstream", self.repo))
        self.assertEqual(self.remote_ref(self.cfg.ticket), rev(self.cfg.ticket, self.repo))
        kind, base, head, title, body = self.gh.calls[0]
        self.assertEqual((kind, base, head), ("create", "main", "upstream-sync"))
        self.assertTrue(title.startswith("Upstream sync: 1 pending since "))
        self.assertIn("fix: zshrc", body)

    def test_later_run_edits_pr(self):
        self.upstream_commit("one", {"dot_zshrc": "zshrc v2\n"})
        sync.run_task(self.cfg, self.gh, NOW)
        self.upstream_commit("two", {"dot_zshrc": "zshrc v3\n"})
        sync.run_task(self.cfg, self.gh, NOW)
        kind, number, title, body = self.gh.calls[1]
        self.assertEqual((kind, number), ("edit", 1))
        self.assertIn("2 pending", title)
        self.assertEqual(self.remote_ref(self.cfg.ticket), rev(self.cfg.ticket, self.repo))

    def test_in_progress_label_only_updates_mirror(self):
        self.gh.pr = PullRequest(1, "url", [IN_PROGRESS])
        self.gh.label_time = "2026-11-11T08:00:00Z"
        new = self.upstream_commit("one", {"dot_zshrc": "zshrc v2\n"})
        result = sync.run_task(self.cfg, self.gh, NOW)
        self.assertEqual(self.remote_ref("upstream"), new)
        self.assertIsNone(rev(f"refs/heads/{self.cfg.ticket}", self.repo))
        self.assertEqual(result.prepared, [])
        self.assertFalse(any("warning" in m for m in result.messages))

    def test_stale_label_warns(self):
        self.gh.pr = PullRequest(1, "url", [IN_PROGRESS])
        self.gh.label_time = "2026-11-09T08:00:00Z"
        result = sync.run_task(self.cfg, self.gh, NOW)
        self.assertTrue(any("more than a day ago" in m for m in result.messages))

    def test_local_run_does_not_push(self):
        self.upstream_commit("one", {"dot_zshrc": "zshrc v2\n"})
        sync.run_task(self.cfg, None, NOW)
        self.assertIsNone(self.remote_ref("upstream"))
        self.assertIsNone(self.remote_ref(self.cfg.ticket))

    def test_no_pending_commits_creates_no_pr(self):
        sync.run_task(self.cfg, self.gh, NOW)
        self.assertEqual(self.gh.calls, [])
        self.assertIsNone(self.remote_ref(self.cfg.ticket))


class LockTest(unittest.TestCase):
    def test_second_holder_is_rejected(self):
        with tempfile.TemporaryDirectory() as state:
            with sync.lock(state):
                with self.assertRaisesRegex(sync.SyncError, "in progress"):
                    with sync.lock(state):
                        pass
            with sync.lock(state):
                pass


if __name__ == "__main__":
    unittest.main()
