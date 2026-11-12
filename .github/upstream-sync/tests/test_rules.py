import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

from upstream_sync import rules  # noqa: E402

TEXT = """\
# comment
base       abc123

follow     .chezmoiscripts/**
own        .chezmoiscripts/run_setup.sh
follow     dot_zshrc                         > .chezmoitemplates/zsh/upstream.dot_zshrc
follow     templates/claude                  > local/claude
skip       **/encrypted_*
skip       **/*.test.*
local      templates/claude/mine.json
local      .chezmoiscripts/lib/**
"""


class ParseTest(unittest.TestCase):
    def test_valid_file(self):
        parsed, errors = rules.parse(TEXT)
        self.assertEqual(errors, [])
        self.assertEqual(parsed.base, "abc123")
        self.assertEqual([r.kind for r in parsed.handling], ["follow", "own", "follow", "follow", "skip", "skip"])
        self.assertEqual(parsed.handling[2].dest, ".chezmoitemplates/zsh/upstream.dot_zshrc")
        self.assertEqual([(r.kind, r.pattern) for r in parsed.local], [("local", "templates/claude/mine.json"), ("local", ".chezmoiscripts/lib/**")])

    def errors(self, text):
        return rules.parse("base abc\n" + text)[1]

    def test_unknown_keyword(self):
        self.assertIn("unknown keyword 'folow'", self.errors("folow a\n")[0])

    def test_wrong_field_count_mentions_spaces(self):
        self.assertIn("cannot contain spaces", self.errors("follow my file\n")[0])

    def test_arrow_only_on_follow(self):
        self.assertIn("only allowed on follow", self.errors("own a > b\n")[0])

    def test_local_takes_one_pattern(self):
        self.assertIn("expected 'local PATTERN'", self.errors("local a > b\n")[0])
        self.assertIn("expected 'local PATTERN'", self.errors("local a b\n")[0])
        self.assertIn("unknown keyword 'overlay'", self.errors("overlay a\n")[0])

    def test_arrow_needs_literal_path(self):
        self.assertIn("literal path", self.errors("follow a/** > b\n")[0])

    def test_base_must_appear_once(self):
        self.assertIn("found 0", rules.parse("follow a\n")[1][0])
        self.assertIn("found 2", rules.parse("base a\nbase b\n")[1][0])


class MatchTest(unittest.TestCase):
    def test_single_star_stays_in_one_level(self):
        self.assertTrue(rules.matches("a/*.sh", "a/x.sh"))
        self.assertFalse(rules.matches("a/*.sh", "a/b/x.sh"))

    def test_double_star_matches_zero_or_more_levels(self):
        self.assertTrue(rules.matches("**/x.test.ts", "x.test.ts"))
        self.assertTrue(rules.matches("**/*.test.*", "a/b/x.test.zsh"))
        self.assertTrue(rules.matches("a/**", "a/.hidden/x"))
        self.assertFalse(rules.matches("a/**", "a"))

    def test_directory_pattern_covers_contents(self):
        self.assertTrue(rules.matches("dot_config/git", "dot_config/git/config.tmpl"))
        self.assertFalse(rules.matches("dot_config/git", "dot_config/gitx"))


class ClassifyTest(unittest.TestCase):
    def setUp(self):
        self.rules, _ = rules.parse(TEXT)

    def test_last_matching_rule_wins(self):
        self.assertEqual(rules.classify(self.rules, ".chezmoiscripts/run_other.sh").kind, "follow")
        self.assertEqual(rules.classify(self.rules, ".chezmoiscripts/run_setup.sh").kind, "own")

    def test_follow_maps_local_path(self):
        c = rules.classify(self.rules, "dot_zshrc")
        self.assertEqual(c.local, ".chezmoitemplates/zsh/upstream.dot_zshrc")
        self.assertEqual(rules.classify(self.rules, "templates/claude/a.json").local, "local/claude/a.json")
        self.assertEqual(rules.classify(self.rules, ".chezmoiscripts/x").local, ".chezmoiscripts/x")

    def test_only_follow_has_local_path(self):
        self.assertIsNone(rules.classify(self.rules, ".chezmoiscripts/run_setup.sh").local)

    def test_unclassified(self):
        c = rules.classify(self.rules, "Brewfile")
        self.assertIsNone(c.kind)
        self.assertIsNone(c.rule)

    def test_local_path_beats_follow_in_any_order(self):
        c = rules.classify(self.rules, ".chezmoiscripts/lib/x.sh")
        self.assertEqual(c.kind, "local")
        self.assertIsNone(c.local)
        self.assertEqual(c.rule.pattern, ".chezmoiscripts/lib/**")

    def test_local_matches_mapped_path(self):
        self.assertEqual(rules.classify(self.rules, "templates/claude/mine.json").kind, "follow")
        parsed, _ = rules.parse("base a\nfollow templates/claude > local/claude\nlocal local/claude/mine.json\n")
        self.assertEqual(rules.classify(parsed, "templates/claude/mine.json").kind, "local")

    def test_mapped_follow_implies_local_template(self):
        parsed, _ = rules.parse("base a\nfollow **\nfollow dot_zshrc > copy\n")
        c = rules.classify(parsed, "dot_zshrc.tmpl")
        self.assertEqual((c.kind, c.rule.line, c.rule.pattern), ("local", 3, "dot_zshrc.tmpl"))


class ValidateTest(unittest.TestCase):
    def validate(self, text, files, base_ok=True, local=(), local_files=()):
        return rules.validate(text, files, lambda _b: base_ok, lambda p: p in local, local_files)[1]

    def test_base_not_on_mirror(self):
        report = self.validate("base abc\n", [], base_ok=False)
        self.assertIn("base abc is not on the mirror branch", report.errors)

    def test_missing_local_path(self):
        report = self.validate("base a\nfollow x > y\n", ["x"])
        self.assertIn("local path y does not exist", report.errors[0])
        self.assertEqual(self.validate("base a\nfollow x > y\n", ["x"], local={"y"}).errors, [])

    def test_unmatched_shadowed_and_unclassified(self):
        text = "base a\nfollow d/**\nskip d/x\nskip d/**\nskip gone/**\n"
        report = self.validate(text, ["d/x", "d/y", "other"])
        self.assertEqual([r.pattern for r in report.unmatched], ["gone/**"])
        self.assertEqual([r.pattern for r in report.shadowed], ["d/**", "d/x"])
        self.assertEqual(report.unclassified, ["other"])

    def test_local_registration(self):
        text = "base a\nfollow d/**\nfollow up > copy\nfollow up2 > copy2\nlocal d/mine/**\nlocal gone\n"
        report = self.validate(
            text,
            ["d/x", "d/mine/clash", "up", "up.tmpl", "up2"],
            local={"copy", "copy2"},
            local_files=["d/x", "copy", "copy2", "d/mine/a", "d/mine/clash", "up.tmpl", "up2.tmpl", "extra"],
        )
        self.assertEqual(
            [(p, r.kind, r.line) for p, r in report.conflicts], [("d/mine/clash", "local", 5), ("up.tmpl", "local", 3)]
        )
        self.assertEqual([r.pattern for r in report.unmatched], ["gone"])
        self.assertEqual(report.unregistered, ["extra"])


if __name__ == "__main__":
    unittest.main()
