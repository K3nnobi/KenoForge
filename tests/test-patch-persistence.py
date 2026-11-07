#!/usr/bin/env python3
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

TOOLS = Path(__file__).resolve().parents[1] / 'payload/kenoforge/tools'
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location('persistence', TOOLS / 'patch-persistence.py')
persistence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(persistence)
from update_guardian_loader import guardian


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.env = patch.dict(os.environ, {'HOME': str(self.data), 'KENOFORGE_DATA_HOME': str(self.data / '.kenoforge')})
        self.env.start()
        self.root = patch.object(persistence, 'DATA', self.data)
        self.root.start()

    def tearDown(self):
        self.root.stop(); self.env.stop(); self.temp.cleanup()

    def repair(self, enabled, execute):
        with patch.object(persistence, '_read_json', return_value={'enabled': enabled}), patch.object(persistence, 'execute', execute), patch.object(guardian, 'detect_external_package_changes', return_value=set()), patch.object(guardian, 'scan'), patch.object(persistence, 'upsert_task') as task, patch.object(persistence, 'resolve_task'):
            status = persistence.repair(True)
            return status, task

    def test_removed_patch_is_not_reinstalled(self):
        execute = Mock()
        status, _ = self.repair(['plymouth', 'capslock', 'firefox-emoji', 'nvibrant', 'unknown'], execute)
        self.assertEqual(status, 0)
        execute.assert_not_called()

    def test_healthy_patch_does_not_reapply(self):
        state = self.data / 'Config/Patches/Plymouth/state.conf'
        state.parent.mkdir(parents=True); state.write_text('test')
        execute = Mock(return_value=Mock(returncode=0))
        status, task = self.repair(['plymouth'], execute)
        self.assertEqual(status, 0)
        self.assertEqual(execute.call_count, 1)
        task.assert_not_called()

    def test_failure_preserves_pending_task(self):
        execute = Mock(return_value=Mock(returncode=1))
        status, task = self.repair(['gnome-drag-hover'], execute)
        self.assertEqual(status, 1)
        self.assertEqual(execute.call_count, 2)
        self.assertEqual(task.call_args.args[0], 'persistence-gnome-drag-hover')

    def test_old_blur_detection_cannot_clear_rebuild(self):
        with patch.object(guardian, 'package_installed', return_value=True), patch.object(guardian.shutil, 'which', return_value='/usr/bin/dconf'), patch.object(guardian, 'run', return_value=Mock(returncode=0, stdout='true')), patch.object(guardian, 'load_tasks', return_value=[{'id': 'rounded-blur-rebuild', 'resolved': False}]), patch.object(guardian, 'resolve_task') as resolve:
            self.assertIn('pending', guardian.scan_rounded_blur())
            resolve.assert_not_called()

    def test_theme_rebuild_failure_restores_previous_selection(self):
        spec = importlib.util.spec_from_file_location('themes', TOOLS / 'plymouth-themes.py')
        themes = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(themes)
        import subprocess
        failure = subprocess.CalledProcessError(1, ['mkinitcpio', '-P'])
        with patch.object(themes, 'run', side_effect=['spinner', '', failure, '', '']) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                themes.apply('solar')
            self.assertEqual(run.call_args_list[3].args, ('sudo', 'plymouth-set-default-theme', 'spinner'))
            self.assertFalse((self.data / '.kenoforge/Config/Patches/Plymouth/theme').exists())

    def test_selected_theme_is_kept_by_transformer(self):
        spec = importlib.util.spec_from_file_location('transform', TOOLS.parent / 'patches/plymouth/plymouth-transform.py')
        transform = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(transform)
        with patch.dict(os.environ, {'KENOFORGE_PLYMOUTH_THEME': 'solar'}):
            self.assertTrue(transform.audit_kind('theme', '[Daemon]\nTheme=solar\n'))
            self.assertFalse(transform.audit_kind('theme', '[Daemon]\nTheme=spinner\n'))

    def test_unit_path_escapes_systemd_specifiers(self):
        self.assertEqual(persistence.unit_quote('/home/a%/a"b'), '"/home/a%%/a\\"b"')


if __name__ == '__main__':
    unittest.main()
