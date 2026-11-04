#!/usr/bin/env python3
"""Regression coverage for old-to-new Nautilus CSS updates in disposable paths."""
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("nautilus_css", ROOT / "payload/kenoforge/tools/nautilus-thumbnail-css.py")
css = importlib.util.module_from_spec(spec)
spec.loader.exec_module(css)


class ThumbnailCss(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = self.root / "config/gtk-4.0/gtk.css"
        self.backups = self.root / "backups"

    def tearDown(self):
        self.tmp.cleanup()

    def seed(self, text):
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_text(text)

    def old_block(self):
        return css.BEGIN + "\n.nautilus-window.view .thumbnail {\n    background: none;\n}\n" + css.END + "\n"

    def test_upgrade_replaces_old_block_preserves_custom_rules_and_backup(self):
        personal = "/* personal */\nwindow { color: red; }\n"
        original = personal + self.old_block() + "label { color: blue; }\n"
        self.seed(original)
        self.target.chmod(0o640)
        css.update(self.target, self.backups)
        updated = self.target.read_text()
        self.assertTrue(updated.startswith(personal))
        self.assertIn("label { color: blue; }\n", updated)
        self.assertIn(".nautilus-image.file-thumbnail,", updated)
        self.assertNotIn(".nautilus-window.view .thumbnail", updated)
        self.assertEqual(next(self.backups.iterdir()).read_text(), original)
        self.assertEqual(stat.S_IMODE(self.target.stat().st_mode), 0o640)

    def test_reapply_is_noop_without_another_backup(self):
        self.seed("/* custom */\n")
        css.update(self.target, self.backups)
        before = self.target.read_bytes()
        count = len(list(self.backups.iterdir()))
        self.assertFalse(css.update(self.target, self.backups))
        self.assertEqual(self.target.read_bytes(), before)
        self.assertEqual(len(list(self.backups.iterdir())), count)

    def test_incomplete_block_refuses_changes(self):
        self.seed("/* keep */\n" + css.BEGIN + "\npartial")
        before = self.target.read_bytes()
        with self.assertRaises(ValueError):
            css.update(self.target, self.backups)
        self.assertEqual(self.target.read_bytes(), before)
        self.assertFalse(self.backups.exists())

    def test_duplicate_managed_blocks_collapse_to_one(self):
        self.seed(self.old_block() + "/* keep */\n" + self.old_block())
        css.update(self.target, self.backups)
        text = self.target.read_text()
        self.assertEqual(text.count(css.BEGIN), 1)
        self.assertIn("/* keep */\n", text)

    def test_rollback_removes_only_managed_block(self):
        personal = "window { color: red; }\n"
        self.seed(personal)
        css.update(self.target, self.backups)
        css.update(self.target, self.backups, remove=True)
        self.assertEqual(self.target.read_text(), personal)

    def test_symlink_target_and_parent_are_refused(self):
        outside = self.root / "outside"
        outside.write_text("unchanged")
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(outside)
        with self.assertRaises(ValueError):
            css.update(self.target, self.backups)
        self.assertEqual(outside.read_text(), "unchanged")
        linked_dir = self.root / "redirect"
        linked_dir.symlink_to(self.target.parent, target_is_directory=True)
        with self.assertRaises(ValueError):
            css.update(linked_dir / "another.css", self.backups)

    def test_custom_xdg_configuration_path(self):
        custom = self.root / "settings with spaces"
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(custom)}):
            self.assertEqual(css.css_target(), custom / "gtk-4.0/gtk.css")
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "relative"}):
            with self.assertRaises(ValueError):
                css.css_target()


if __name__ == "__main__":
    unittest.main()
