import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

from upstream_sync import ticket  # noqa: E402


def message(
    subject, applied="  a", not_applied="  none", new="  none", risk="none", decision="pending", failed=False, upstream=("a" * 40,)
):
    parts = [subject, ""]
    if failed:
        parts.append("Failed to apply:\n  x: differs from upstream before this commit")
    parts += [f"Applied:\n{applied}", f"Not applied:\n{not_applied}", f"New upstream files:\n{new}", f"Risk: {risk}", ""]
    parts += [f"Upstream-Commit: {sha}" for sha in upstream]
    parts += ["Upstream-Author: Someone", f"Upstream-Decision: {decision}"]
    return "\n".join(parts)


class ParseTest(unittest.TestCase):
    def test_reads_fields(self):
        item = ticket.parse_item(message("feat: x", risk="daily-tool, machine-state"), "2026-11-03")
        self.assertEqual(item.subject, "feat: x")
        self.assertEqual(item.risks, ["daily-tool", "machine-state"])
        self.assertEqual(item.decision, "pending")
        self.assertTrue(item.applied)

    def test_ignores_commits_without_trailer(self):
        self.assertIsNone(ticket.parse_item("local fix\n\nbody", "2026-11-03"))

    def test_combined_commit_keeps_every_upstream_commit(self):
        item = ticket.parse_item(message("x", upstream=("a" * 40, "b" * 40)), "d")
        self.assertEqual(item.upstream, ["a" * 40, "b" * 40])


class GroupTest(unittest.TestCase):
    def group(self, **kwargs):
        return ticket.parse_item(message("s", **kwargs), "d").group

    def test_priority(self):
        self.assertEqual(self.group(failed=True, new="  f", risk="silent"), "failed")
        self.assertEqual(self.group(new="  f", risk="silent"), "new")
        self.assertEqual(self.group(risk="daily-tool, silent"), "silent")
        self.assertEqual(self.group(risk="daily-tool, machine-state"), "machine-state")
        self.assertEqual(self.group(), "other")
        self.assertEqual(self.group(applied="  none"), "no-change")
        self.assertEqual(self.group(applied="  none", not_applied="  b (skip)\n  dot_config/rex/init.lua (watch)"), "watch")
        self.assertEqual(self.group(applied="  none", not_applied="  x (watch, deleted)"), "watch")
        self.assertEqual(self.group(not_applied="  x (watch)"), "other")
        self.assertEqual(self.group(decision="accepted", risk="silent"), "processed")


class RenderTest(unittest.TestCase):
    def test_title_and_body(self):
        entries = [
            ticket.parse_item(message("feat: risky", risk="silent", upstream=("1" * 40,)), "2026-11-04"),
            ticket.parse_item(message("docs: nothing", applied="  none", upstream=("2" * 40,)), "2026-11-02"),
            ticket.parse_item(message("done", decision="accepted", upstream=("3" * 40,)), "2026-11-01"),
        ]
        self.assertEqual(ticket.title(entries), "Upstream sync: 2 pending since 2026-11-02")
        body = ticket.body(entries, "me/dotfiles", "upstream")
        self.assertTrue(body.startswith("2 upstream commits are waiting, from 2026-11-02 to 2026-11-04.\n"))
        self.assertIn("[`upstream`](https://github.com/me/dotfiles/commits/upstream)", body)
        self.assertIn(
            "### Risk: silent (1)\n\n- [`111111111`](https://github.com/me/dotfiles/commit/" + "1" * 40 + ") feat: risky · 2026-11-04 · silent\n",
            body,
        )
        self.assertIn("### No local change (1)\n\n- [`222222222`]", body)
        self.assertIn("### Processed, waiting to merge (1)", body)
        self.assertLess(body.index("Risk: silent"), body.index("No local change"))

    def test_nothing_pending(self):
        self.assertEqual(ticket.title([]), "Upstream sync: nothing pending")


if __name__ == "__main__":
    unittest.main()
