import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

from upstream_sync.affected import AffectedError, affected  # noqa: E402
from upstream_sync.gitcmd import git  # noqa: E402
from test_sync import ISOLATED_ENV, commit, write  # noqa: E402


@unittest.skipUnless(shutil.which("chezmoi"), "chezmoi is not installed")
class AffectedTest(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ISOLATED_ENV}
        os.environ.update(ISOLATED_ENV)
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(self.repo)
        git("init", "--quiet", "-b", "main", cwd=self.repo)
        config = os.path.join(self.tmp.name, "chezmoi.toml")
        write(self.tmp.name, "chezmoi.toml", "")
        # 不读用户自己的 chezmoi 配置和状态。
        self.args = [
            "--config", config,
            "--persistent-state", os.path.join(self.tmp.name, "state.boltdb"),
            "--destination", os.path.join(self.tmp.name, "home"),
        ]
        write(self.repo, "dot_plain", "plain\n")
        write(self.repo, ".chezmoitemplates/shared", "shared v1\n")
        write(self.repo, "dot_uses-template.tmpl", '{{ includeTemplate "shared" . }}')
        write(self.repo, "dot_path.tmpl", "{{ .chezmoi.sourceDir }}\n")
        write(self.repo, ".chezmoiscripts/run_onchange_setup.sh.tmpl", "#!/bin/sh\n# {{ include \"dot_plain\" | sha256sum }}\n")
        self.old = commit(self.repo, "old")

    def tearDown(self):
        self.tmp.cleanup()
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_template_change_reaches_its_consumer(self):
        write(self.repo, ".chezmoitemplates/shared", "shared v2\n")
        new = commit(self.repo, "template")
        targets, config_changed = affected(self.repo, self.old, new, self.args)
        self.assertEqual([(t.path, t.change) for t in targets], [(".uses-template", "changed")])
        self.assertFalse(config_changed)

    def test_script_reruns_when_its_input_changes(self):
        write(self.repo, "dot_plain", "plain v2\n")
        os.makedirs(os.path.join(self.repo, "dot_config"))
        write(self.repo, "dot_config/new", "new\n")
        os.remove(os.path.join(self.repo, "dot_uses-template.tmpl"))
        new = commit(self.repo, "files")
        targets, _ = affected(self.repo, self.old, new, self.args)
        self.assertEqual(
            [(t.path, t.change, t.is_script) for t in targets],
            [
                (".chezmoiscripts/setup.sh", "changed", True),
                (".config/new", "added", False),
                (".plain", "changed", False),
                (".uses-template", "removed", False),
            ],
        )

    def test_config_template_change_is_reported(self):
        write(self.repo, ".chezmoi.toml.tmpl", "[data]\n")
        new = commit(self.repo, "config")
        self.assertTrue(affected(self.repo, self.old, new, self.args)[1])

    def test_render_failure_stops(self):
        write(self.repo, "dot_broken.tmpl", "{{ .missing.key }}\n")
        new = commit(self.repo, "broken")
        with self.assertRaisesRegex(AffectedError, "chezmoi archive failed"):
            affected(self.repo, self.old, new, self.args)


if __name__ == "__main__":
    unittest.main()
