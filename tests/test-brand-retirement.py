#!/usr/bin/env python3
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('migration', ROOT / 'payload/kenoforge/tools/migrate-brand.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class BrandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'HOME': str(self.home), 'XDG_CONFIG_HOME': str(self.home / '.config'), 'XDG_DATA_HOME': str(self.home / '.local/share')})
        self.env.start()
        self.backup = self.home / '.kenoforge/Installer-Backups/retirement'
        self.shell = self.home / '.zshrc'
        self.original = 'alias personal="true"\nexport ARCHMIND_HOME="$HOME/ArchMind/System/Core"\nsource "$ARCHMIND_HOME/core/loader.zsh"\n'
        self.shell.write_text(self.original)
        self.old = self.home / 'ArchMind'
        (self.old / 'Backups').mkdir(parents=True)
        (self.old / 'Backups/keep.txt').write_text('original')
        (self.home / '.local/bin').mkdir(parents=True)
        self.launcher = self.home / '.local/bin/archmind'
        self.launcher.symlink_to(self.old / 'System/Toolkit/bin/archmind')

    def tearDown(self):
        self.env.stop(); self.temp.cleanup()

    def test_retire_restore_and_repeated_migration(self):
        migration.apply(self.home, self.backup)
        self.assertNotIn('archmind', self.shell.read_text().lower())
        self.assertIn('alias personal="true"', self.shell.read_text())
        self.assertIn('$HOME/.kenoforge/System/Core', self.shell.read_text())
        self.assertFalse(self.old.exists())
        self.assertFalse(self.launcher.is_symlink())
        self.assertEqual((self.backup / 'previous-installation/Backups/keep.txt').read_text(), 'original')
        edits, moves, links = migration.plan(self.home)
        self.assertEqual((edits, moves, links), ([], [], []))
        migration.rollback(self.backup, self.home)
        self.assertEqual(self.shell.read_text(), self.original)
        self.assertEqual((self.old / 'Backups/keep.txt').read_text(), 'original')
        self.assertTrue(self.launcher.is_symlink())

    def test_symlink_shell_is_rejected_before_mutation(self):
        self.shell.unlink()
        target = self.home / 'untouched'
        target.write_text(self.original)
        self.shell.symlink_to(target)
        with self.assertRaises(ValueError):
            migration.apply(self.home, self.backup)
        self.assertEqual(target.read_text(), self.original)
        self.assertTrue(self.old.exists())
        self.assertFalse(self.backup.exists())

    def test_previous_alias_symlink_is_imported_and_reversible(self):
        alias = self.old / 'Config/Zsh/aliases.zsh'
        alias.parent.mkdir(parents=True)
        alias.write_text('alias archmind-status="archmind status"\n')
        link = self.home / '.zsh_aliases'
        link.symlink_to(alias)
        migration.apply(self.home, self.backup)
        self.assertTrue(link.resolve().is_file())
        self.assertNotIn('archmind', link.read_text())
        self.assertIn('kenoforge-status', link.read_text())
        migration.rollback(self.backup, self.home)
        self.assertEqual(link.resolve(), alias)
        self.assertEqual(alias.read_text(), 'alias archmind-status="archmind status"\n')

    def test_unknown_launcher_is_preserved(self):
        self.launcher.unlink(); self.launcher.write_text('#!/bin/sh\necho personal\n')
        with self.assertRaises(ValueError):
            migration.apply(self.home, self.backup)
        self.assertEqual(self.shell.read_text(), self.original)
        self.assertTrue(self.old.exists())


if __name__ == '__main__':
    unittest.main()
