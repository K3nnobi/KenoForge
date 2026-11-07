#!/usr/bin/env python3
"""Focused isolated tests for the optional Caps Lock No Delay patch."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "payload/kenoforge/tools/configure-capslock-nodelay.sh"


class CapsLockNoDelayTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="kenoforge-capslock-")
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.data = self.home / ".kenoforge"
        self.config = self.root / "etc/keyd/default.conf"
        self.fake_bin = self.root / "bin"
        self.home.mkdir()
        self.fake_bin.mkdir()
        for name, body in {
            "pacman": "#!/bin/sh\nexit 0\n",
            "systemctl": "#!/bin/sh\nexit 0\n",
            "keyd": "#!/bin/sh\nexit 0\n",
        }.items():
            path = self.fake_bin / name
            path.write_text(body, encoding="utf-8")
            path.chmod(0o755)

        self.env = os.environ.copy()
        self.env.update(
            {
                "HOME": str(self.home),
                "KENOFORGE_DATA_HOME": str(self.data),
                "KENOFORGE_KEYD_CONFIG": str(self.config),
                "KENOFORGE_TEST_SIMULATE": "1",
                "PATH": f"{self.fake_bin}:{self.env['PATH']}",
            }
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_helper(self, *arguments: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["bash", str(HELPER), *arguments],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout)
        return result

    def test_new_configuration_is_idempotent_and_removable(self) -> None:
        self.run_helper("--apply", "--yes")
        content = self.config.read_text(encoding="utf-8")
        self.assertEqual(content.count("KENOFORGE_CAPSLOCK_NODELAY"), 1)
        self.assertEqual(content.count("capslock = macro(capslock)"), 1)
        self.assertEqual(content.count("macro_timeout = 600000"), 1)

        self.run_helper("--apply", "--yes")
        self.assertEqual(self.config.read_text(encoding="utf-8"), content)

        self.run_helper("--remove", "--yes")
        self.assertFalse(self.config.exists())

    def test_existing_configuration_is_restored(self) -> None:
        original = "[ids]\n*\n\n[main]\nesc = capslock\n"
        self.config.parent.mkdir(parents=True)
        self.config.write_text(original, encoding="utf-8")

        self.run_helper("--apply", "--yes")
        changed = self.config.read_text(encoding="utf-8")
        self.assertIn("capslock = macro(capslock)", changed)
        self.assertIn("esc = capslock", changed)

        self.run_helper("--remove", "--yes")
        self.assertEqual(self.config.read_text(encoding="utf-8"), original)

    def test_conflicting_mapping_is_refused_without_changes(self) -> None:
        original = "[ids]\n*\n\n[main]\ncapslock = esc\n"
        self.config.parent.mkdir(parents=True)
        self.config.write_text(original, encoding="utf-8")

        result = self.run_helper("--apply", "--yes", expected=2)
        self.assertIn("existing Caps Lock remapping", result.stdout)
        self.assertEqual(self.config.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
