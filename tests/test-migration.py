#!/usr/bin/env python3
"""Namespace, install/uninstall and TTY checks in a disposable HOME."""
import os
import fcntl
import struct
import termios
from pathlib import Path
import pty
import select
import shutil
import subprocess
import tempfile
import time
import unittest

PACKAGE = Path(__file__).resolve().parents[1]


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='kenoforge-migration-')
        self.root = Path(self.temp.name)
        self.package = self.root / 'KenoForge-1.5.23'
        shutil.copytree(PACKAGE, self.package)
        self.home = self.root / 'tester home'
        self.home.mkdir()
        self.simulated = os.geteuid() == 0
        if self.simulated:
            if os.environ.get('KENOFORGE_TEST_SIMULATE') != '1':
                self.temp.cleanup()
                self.skipTest('Run as a normal user, or use KENOFORGE_TEST_SIMULATE=1 for isolated fixtures')
            # Only the disposable copy bypasses root guards. The deliverable retains them.
            path = self.package / 'install.sh'
            path.write_text(path.read_text().replace(
                'if (( ! dry_run && ! check_only && EUID == 0 )); then', 'if (( 0 )); then'))
            path = self.package / 'payload/kenoforge/tools/uninstall.py'
            path.write_text(path.read_text().replace('if os.geteuid() == 0:', 'if False:'))
            import hashlib
            (self.package / 'PAYLOAD.sha256').write_text(''.join(
                f'{hashlib.sha256(f.read_bytes()).hexdigest()}  {f.relative_to(self.package)}\n'
                for f in sorted((self.package / 'payload').rglob('*')) if f.is_file()))
        self.env = dict(os.environ, HOME=str(self.home), USER='tester', LOGNAME='tester',
                        PATH=f'{self.home}/.local/bin:/usr/bin:/bin', TERM='xterm-256color',
                        PYTHONDONTWRITEBYTECODE='1')
        for name in ('DISPLAY', 'WAYLAND_DISPLAY', 'ZDOTDIR', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME',
                     'DBUS_SESSION_BUS_ADDRESS', 'KENOFORGE_ROOT'):
            self.env.pop(name, None)

    def tearDown(self):
        self.temp.cleanup()

    def args(self, *args):
        return [str(a) for a in args]

    def run_cmd(self, *args, code=0, data=''):
        r = subprocess.run(self.args(*args), cwd=self.home, env=self.env, input=data,
                           text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
        self.assertEqual(r.returncode, code, r.stdout)
        return r.stdout

    def write(self, relative, value):
        path = self.home / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
        return path

    def install(self):
        return self.run_cmd('bash', self.package / 'install.sh', '--no-progress')

    def test_clean_aliases_repeated_install_and_safe_uninstall(self):
        old = self.write('ArchMind/Backups/keep.txt', 'old backup')
        shell = self.write('.zshrc', '# Personal shell\nalias mine="true"\n')
        result = self.install()
        self.assertIn('previous integrations archived', result)
        self.install()
        self.assertEqual(shell.read_text().count('# KENOFORGE-SHELL-BEGIN'), 1)
        self.assertIn('Personal shell', shell.read_text())
        output = self.run_cmd('zsh', '-ic', 'alias pacinstall; alias pacupdate; whence -p install')
        self.assertIn('sudo pacman -Syu', output)
        self.assertIn('/usr/bin/install', output)
        for name in ('kenoforge', 'kenoforge-console'):
            self.assertIn('KenoForge 1.5.23', self.run_cmd(name, '--version'))
        settings = self.write('KenoForge/Config/custom.txt', 'settings')
        backup = self.write('KenoForge/Backups/keep.txt', 'new backup')
        self.run_cmd('bash', self.package / 'uninstall.sh')
        self.assertTrue((self.home / 'KenoForge/System').exists())
        self.run_cmd('bash', self.package / 'uninstall.sh', '--apply', data='NO\n')
        self.assertTrue((self.home / 'KenoForge/System').exists())
        self.run_cmd('bash', self.package / 'uninstall.sh', '--apply', '--yes')
        self.assertFalse((self.home / 'KenoForge/System').exists())
        self.assertFalse((self.home / '.local/bin/kenoforge').is_symlink())
        self.assertFalse((self.home / '.local/bin/kenoforge-music').is_symlink())
        self.assertNotIn('KENOFORGE-SHELL-BEGIN', shell.read_text())
        self.assertEqual(settings.read_text(), 'settings')
        self.assertEqual(backup.read_text(), 'new backup')
        self.assertFalse(old.exists())
        archived = list((self.home / 'KenoForge/Installer-Backups').glob('kenoforge-before-*/previous-brand/previous-installation/Backups/keep.txt'))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_text(), 'old backup')
        self.assertTrue(list((self.home / 'KenoForge/Installer-Backups').glob('uninstalled-*/System')))
        self.install()
        self.assertIn('KenoForge', self.run_cmd('kenoforge', '--version'))

    def test_late_failure_restores_previous_brand(self):
        old = self.write('ArchMind/Backups/preserved.txt', 'keep')
        shell = self.write('.zshrc', 'source "$HOME/ArchMind/System/Core/core/loader.zsh"\n')
        original = shell.read_text()
        launcher = self.home / '.local/bin/archmind'
        launcher.parent.mkdir(parents=True)
        launcher.symlink_to(self.home / 'ArchMind/System/Toolkit/bin/archmind')
        installer = self.package / 'install.sh'
        installer.write_text(installer.read_text().replace('\n    configure_public_aliases\n', '\n    false # injected late failure\n'))
        self.run_cmd('bash', installer, '--no-progress', code=1)
        self.assertEqual(old.read_text(), 'keep')
        self.assertEqual(shell.read_text(), original)
        self.assertTrue(launcher.is_symlink())

    def test_previous_shell_loader_uses_current_console(self):
        self.write('ArchMind/System/Core/core/loader.zsh', 'archmind() { print OLD; }\n')
        shell = self.write('.zshrc', 'export ARCHMIND_HOME="$HOME/ArchMind/System/Core"\nsource "$ARCHMIND_HOME/core/loader.zsh"\n')
        self.install()
        self.assertNotIn('archmind', shell.read_text().lower())
        output = self.run_cmd('zsh', '-ic', 'whence -va kenoforge; kenoforge --version; zsh() { print -r -- "$*"; }; kenoforge')
        self.assertIn('KenoForge 1.5.23 (AFI)', output)
        self.assertIn('KenoForge/System/Core/console/main.zsh', output)
        output = self.run_cmd('zsh', '-ic', 'whence -va archmind || true')
        self.assertNotIn('shell function', output)
        self.assertFalse((self.home / '.local/bin/archmind').exists())

    def test_xdg_and_uninstall_preserve_unknown_links(self):
        self.env['XDG_CONFIG_HOME'] = str(self.home / 'xdg config')
        self.env['XDG_DATA_HOME'] = str(self.home / 'xdg data')
        self.install()
        self.assertTrue((self.home / 'xdg config/kenoforge').is_symlink())
        desktop = self.home / 'xdg data/applications/kenoforge-execute-terminal.desktop'
        self.assertTrue(desktop.exists())
        link = self.home / '.local/bin/kenoforge-monitor'
        link.unlink()
        link.symlink_to('/usr/bin/true')
        self.run_cmd('bash', self.package / 'uninstall.sh', '--apply', '--yes')
        self.assertEqual(str(link.readlink()), '/usr/bin/true')
        self.assertFalse((self.home / 'xdg config/kenoforge').is_symlink())
        self.assertFalse(desktop.exists())

    def test_uninstall_rejects_redirected_shell_file(self):
        self.install()
        target = self.write('untouched.txt', 'keep')
        shell = self.home / '.zshrc'
        shell.unlink()
        shell.symlink_to(target)
        self.run_cmd('bash', self.package / 'uninstall.sh', '--apply', '--yes', code=1)
        self.assertEqual(target.read_text(), 'keep')
        self.assertTrue((self.home / 'KenoForge/System').is_dir())

    def test_public_launchers_without_desktop(self):
        self.install()
        for command in ('kenoforge', 'kenoforge-console'):
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 140, 0, 0))
            proc = subprocess.Popen(self.args(command), env=self.env, cwd=self.home,
                                    stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
            os.close(slave)
            output = bytearray()
            try:
                deadline = time.monotonic() + 8
                while time.monotonic() < deadline:
                    if select.select([master], [], [], .1)[0]:
                        output.extend(os.read(master, 65536))
                        if b'KenoForge' in output or b'KENOFORGE' in output:
                            break
                self.assertTrue(b'KenoForge' in output or b'KENOFORGE' in output, repr(output[-800:]))
                self.assertIsNone(proc.poll())
                os.write(master, b'q')
            finally:
                proc.kill()
                proc.wait(timeout=5)
                os.close(master)


if __name__ == '__main__':
    unittest.main()
