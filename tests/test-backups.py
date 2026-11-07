#!/usr/bin/env python3
"""Backup regressions: real archive/copy operations in disposable Homes; no Wine execution."""
import concurrent.futures
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import sys

PACKAGE = Path(__file__).resolve().parents[1]
TOOLS = PACKAGE / 'payload/kenoforge/tools'
sys.path.insert(0, str(TOOLS))
import backup_engine as engine


class Backups(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.home = self.tmp / 'source-home'
        self.other = self.tmp / 'destination-home'
        self.home.mkdir(mode=0o700)
        self.other.mkdir(mode=0o700)
        self.data = self.home / '.kenoforge'
        self.core = self.data / 'System/Core'
        shutil.copytree(PACKAGE / 'payload/kenoforge', self.core)
        shutil.copytree(PACKAGE / 'payload/toolkit', self.data / 'System/Toolkit')
        self.env = {**os.environ, 'HOME': str(self.home), 'USER': 'fixture', 'KENOFORGE_DATA_HOME': str(self.data),
                    'KENOFORGE_BACKUP_DIR': str(self.home / 'custom-backups'), 'PYTHONDONTWRITEBYTECODE': '1'}
        self.manager = self.core / 'bin/kenoforge-manager'
        self.write(self.home / '.zshrc', '# fixture\n')
        self.write(self.data / 'Config/Zsh/aliases.zsh', "alias fixture='true'\n")
        self.write(self.data / 'Config/MediaDeck/music.json', json.dumps({'music_folder': str(self.home / 'Music'), 'playlists': {'one': [str(self.home / 'Music/song.mp3')]}}))
        self.write(self.home / '.local/share/applications/wine-custom.desktop', '[Desktop Entry]\nExec=wine %f\n')
        self.write(self.home / '.config/mimeapps.list', '[Default Applications]\napplication/x-msdownload=wine-custom.desktop;\n')
        self.write(self.data / 'State/Maintenance/patch-persistence.json', '{"enabled":["capslock"]}')
        self.write(self.data / 'State/Maintenance/pending-tasks.json', '{"tasks":["fixture"]}')
        self.write(self.data / 'Logs/Wine-Prefix-Repair/test.json', '{}')
        self.sid = 'a' * 32
        self.prefix = self.home / '.wine'
        self.stage = self.home / ('..wine.kenoforge-repair-' + self.sid)
        self.write(self.stage / 'backup/drive_c/windows/system32/kernel32.dll', 'dll bytes')
        (self.stage / 'backup/dosdevices').mkdir()
        (self.stage / 'backup/dosdevices/z:').symlink_to('/')
        self.write(self.data / ('Installer-Backups/Wine-Prefix-Repair/' + self.sid + '/session.json'), json.dumps({'format': 1, 'id': self.sid, 'source': str(self.prefix), 'phase': 'tested'}))
        self.write(self.data / 'Installer-Backups/Wine-MIME/receipt.json', '{"previous":{}}')

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_text(value)
        path.chmod(0o600)

    def bash(self, code, home=None, check=True):
        env = self.env.copy()
        if home:
            env.update(HOME=str(home), KENOFORGE_DATA_HOME=str(home / '.kenoforge'))
        script = 'source "$1"; ' + code
        result = subprocess.run(['bash', '-c', script, 'test', str(self.manager)], env=env, capture_output=True, text=True)
        if check and result.returncode:
            self.fail(result.stdout + result.stderr)
        return result

    def cli(self, action, path, target=None, home=None, check=True):
        env = self.env.copy()
        if home:
            env.update(HOME=str(home), KENOFORGE_DATA_HOME=str(home / '.kenoforge'))
        result = subprocess.run([sys.executable, '-B', str(TOOLS / 'backup_engine.py'), action, str(path), *([str(target)] if target else [])], env=env, capture_output=True, text=True)
        if check and result.returncode:
            self.fail(result.stdout + result.stderr)
        return result

    def backup(self):
        self.bash('require_arch(){ :; }; capture_packages(){ mkdir -p "$1"; printf "wine\\n" > "$1/pacman-native.txt"; }; capture_gnome(){ mkdir -p "$1"; }; create_backup completo')
        archives = list((self.home / 'custom-backups').glob('*.kenoforge'))
        return max(archives, key=lambda p: p.stat().st_mtime_ns)

    def unpack(self, archive):
        destination = self.tmp / ('extract-' + str(len(list(self.tmp.glob('extract-*')))))
        destination.mkdir(mode=0o700)
        self.cli('extract', archive, destination)
        self.cli('verify', destination)
        return destination

    def test_full_roundtrip_new_home_and_runtime_preserved(self):
        archive = self.backup()
        root = self.unpack(archive)
        self.assertTrue((root / 'toolkit/bin/kenoforge-music').exists())
        self.assertTrue((root / 'maintenance/state/patch-persistence.json').exists())
        self.assertTrue((root / 'recovery/receipts/Wine-MIME/receipt.json').exists())
        index = json.loads((root / 'recovery/index.json').read_text())
        self.assertEqual(len(index['snapshots']), 1)
        self.assertTrue((root / index['snapshots'][0]['snapshot'] / 'drive_c/windows/system32/kernel32.dll').is_file())
        self.assertIn('personal music/audio/video files', json.loads((root / 'manifest.json').read_text())['scope']['excluded'])
        shutil.copytree(self.core, self.other / '.kenoforge/System/Core')
        shutil.copytree(self.data / 'System/Toolkit', self.other / '.kenoforge/System/Toolkit')
        self.write(self.other / '.kenoforge/System/Core/new-module', 'keep')
        code = 'ensure_dirs; restore_configs "' + str(root) + '"; restore_project "' + str(root) + '"'
        self.bash(code, home=self.other)
        self.bash(code, home=self.other)  # a repeated restore must preserve current runtime too
        music = json.loads((self.other / '.kenoforge/Config/MediaDeck/music.json').read_text())
        self.assertEqual(music['music_folder'], str(self.other / 'Music'))
        self.assertEqual(music['playlists']['one'], [str(self.other / 'Music/song.mp3')])
        self.assertEqual(json.loads((self.other / '.kenoforge/State/Maintenance/patch-persistence.json').read_text())['enabled'], ['capslock'])
        self.assertTrue((self.other / '.local/share/applications/wine-custom.desktop').exists())
        self.assertEqual(os.readlink(self.other / '.local/bin/kenoforge-music'), str(self.other / '.kenoforge/System/Toolkit/bin/kenoforge-music'))
        unit = (self.other / '.config/systemd/user/kenoforge-patch-persistence.service').read_text()
        self.assertIn(str(self.other / '.kenoforge/System/Core/tools/patch-persistence.py'), unit)
        self.assertNotIn(str(self.home), unit)
        self.assertFalse((self.other / '.config/systemd/user/timers.target.wants/kenoforge-patch-persistence.timer').exists())
        self.assertTrue((self.other / '.kenoforge/System/Core/new-module').is_file())
        self.assertFalse((self.other / '.kenoforge/Installer-Backups/Wine-Prefix-Repair').exists())
        snapshots = list((self.other / '.kenoforge/Recovered-Data').glob('*/recovery/prefixes/*/0'))
        self.assertTrue(snapshots)
        self.cli('recover-wine', snapshots[0], self.other / '.wine-imported', home=self.other)
        self.assertTrue((self.other / '.wine-imported/drive_c/windows/system32/kernel32.dll').exists())
        self.assertNotEqual(self.cli('recover-wine', snapshots[0], self.other / '.wine-imported', home=self.other, check=False).returncode, 0)

    def test_legacy_visible_root_references_restore_to_hidden_home(self):
        root = self.tmp / 'legacy-visible-backup'
        source_data = self.home / 'KenoForge'
        self.write(root / 'manifest.json', json.dumps({'version': '1.5.23', 'source_home': str(self.home)}))
        self.write(root / 'configs/.zshrc', 'source "$HOME/KenoForge/Config/Zsh/aliases.zsh"\n')
        self.write(root / 'configs/kenoforge-config/settings.zsh',
                   f'export KENOFORGE_BACKUP_DIR="{source_data}/Backups"\n')
        self.write(root / 'configs/kenoforge-config/MediaDeck/music.json',
                   json.dumps({'music_folder': str(source_data / 'Music'), 'playlists': {'one': [str(self.home / 'Music/song.mp3')]}}))
        self.bash('ensure_dirs; restore_configs "' + str(root) + '"', home=self.other)
        destination = self.other / '.kenoforge'
        self.assertIn(str(destination / 'Backups'), (destination / 'Config/settings.zsh').read_text())
        self.assertIn('$HOME/.kenoforge/Config/Zsh/aliases.zsh', (self.other / '.zshrc').read_text())
        music = json.loads((destination / 'Config/MediaDeck/music.json').read_text())
        self.assertEqual(music['music_folder'], str(destination / 'Music'))
        self.assertEqual(music['playlists']['one'], [str(self.other / 'Music/song.mp3')])
        self.assertFalse((self.other / 'KenoForge').exists())

    def test_concurrent_names_never_collide(self):
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            results = list(executor.map(lambda _: self.backup(), range(2)))
        archives = list((self.home / 'custom-backups').glob('*.kenoforge'))
        self.assertEqual(len(archives), 2)
        for archive in archives:
            self.unpack(archive)

    def test_failed_publication_preserves_prior_bytes(self):
        archive = self.backup()
        before = archive.read_bytes()
        side = Path(str(archive) + '.sha256').read_bytes()
        root = self.unpack(archive)
        self.assertNotEqual(self.cli('pack', root, archive, check=False).returncode, 0)
        self.assertEqual(archive.read_bytes(), before)
        self.assertEqual(Path(str(archive) + '.sha256').read_bytes(), side)
        with patch('backup_engine.tarfile.open', side_effect=OSError('simulated disk failure')):
            with self.assertRaises(OSError):
                engine.pack(root, archive.parent / 'failure.kenoforge')
        self.assertFalse((archive.parent / 'failure.kenoforge').exists())
        self.assertFalse(list(archive.parent.glob('.kenoforge-*')))

    def test_tampered_link_and_unlisted_file_rejected(self):
        root = self.unpack(self.backup())
        link = root / ('recovery/prefixes/' + self.sid + '/0/dosdevices/z:')
        link.unlink()
        link.symlink_to('/different')
        self.assertNotEqual(self.cli('verify', root, check=False).returncode, 0)
        link.unlink()
        link.symlink_to('/')
        self.write(root / 'configs/unlisted', 'extra')
        self.assertNotEqual(self.cli('verify', root, check=False).returncode, 0)

    def test_outer_checksum_rejected(self):
        archive = self.backup()
        with archive.open('ab') as f: f.write(b'tamper')
        dest = self.tmp / 'outer'; dest.mkdir()
        self.assertNotEqual(self.cli('extract', archive, dest, check=False).returncode, 0)
        self.assertEqual(list(dest.iterdir()), [])

    def test_destination_redirect_and_hardlinked_file(self):
        outside = self.tmp / 'outside'; outside.mkdir()
        self.write(outside / 'sentinel', 'keep')
        (self.other / 'redirect').symlink_to(outside, target_is_directory=True)
        source = self.tmp / 'payload'; self.write(source / 'sentinel', 'replace')
        result = self.cli('copy', source, self.other / 'redirect', home=self.other, check=False)
        self.assertNotEqual(result.returncode, 0)
        result = self.cli('copy', source / 'sentinel', self.other / 'redirect/sentinel', home=self.other, check=False)
        self.assertNotEqual(result.returncode, 0)
        os.link(outside / 'sentinel', self.other / 'hardlink')
        self.cli('copy', source / 'sentinel', self.other / 'hardlink', home=self.other)
        self.assertEqual((outside / 'sentinel').read_text(), 'keep')

    def test_malicious_archives_rejected_before_writing(self):
        for scenario in ('traversal', 'link-parent', 'hardlink', 'duplicate', 'device'):
            with self.subTest(scenario=scenario):
                archive = self.tmp / (scenario + '.tar')
                with tarfile.open(archive, 'w') as t:
                    if scenario == 'traversal':
                        m = tarfile.TarInfo('../escaped'); t.addfile(m)
                    elif scenario == 'link-parent':
                        m = tarfile.TarInfo('configs'); m.type = tarfile.SYMTYPE; m.linkname = '/tmp'; t.addfile(m)
                        t.addfile(tarfile.TarInfo('configs/escaped'))
                    elif scenario == 'hardlink':
                        m = tarfile.TarInfo('escape'); m.type = tarfile.LNKTYPE; m.linkname = '/etc/passwd'; t.addfile(m)
                    elif scenario == 'duplicate':
                        t.addfile(tarfile.TarInfo('same')); t.addfile(tarfile.TarInfo('same'))
                    else:
                        m = tarfile.TarInfo('device'); m.type = tarfile.CHRTYPE; t.addfile(m)
                dest = self.tmp / (scenario + '-out'); dest.mkdir()
                self.assertNotEqual(self.cli('extract', archive, dest, check=False).returncode, 0)
                self.assertEqual(list(dest.iterdir()), [])

    def test_legacy_txt_and_json_and_catalog(self):
        for fmt in ('txt', 'json'):
            root = self.tmp / ('legacy-' + fmt); root.mkdir()
            data = {'version': '1.5.22', 'mode': 'completo', 'created': '2026-01-01', 'hostname': 'fixture', 'user': 'fixture'}
            self.write(root / ('manifest.' + fmt), json.dumps(data) if fmt == 'json' else ''.join(k+'='+v+'\n' for k,v in data.items()))
            self.write(root / 'project/legacy-module', 'old')
            listing = engine.entries(root)
            self.write(root / 'checksums.sha256', ''.join(v['sha256']+'  '+k+'\n' for k,v in listing.items() if v['type']=='file'))
            self.cli('verify', root)
            self.cli('recover-project', root, self.core)
            archive = self.tmp / ('legacy-' + fmt + '.kenoforge')
            with tarfile.open(archive, 'w') as tar: tar.add(root, arcname='.')
            result = subprocess.run([sys.executable, '-B', str(TOOLS / 'backup-catalog.py'), '--help'], capture_output=True, text=True, env=self.env)
            # Inspect through the module's metadata reader (no archive extraction).
            import importlib.util
            spec = importlib.util.spec_from_file_location('backup_catalog_test', TOOLS / 'backup-catalog.py')
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            self.assertEqual(mod.inspect(archive)['version'], '1.5.22')
            self.assertTrue((self.core / 'tools/wine-prefix-repair.py').exists())

    def test_afi_and_toolkit_share_the_manager_and_directory(self):
        mock = self.tmp / 'mock-core/bin/kenoforge-manager'
        self.write(mock, '#!/usr/bin/env bash\nprintf "%s|%s|%s\\n" "$KENOFORGE_BACKUP_DIR" "${1:-menu}" "${2:-}"\n')
        mock.chmod(0o755)
        env = {**self.env, 'MOCK_MANAGER': str(mock), 'KENOFORGE_CORE_DIR': str(mock.parent.parent)}
        code = 'source "$1/payload/kenoforge/services/manager.zsh"; manager_find_script(){ print -r -- "$MOCK_MANAGER"; }; KENOFORGE_BACKUP_DIR="$HOME/not-exported"; manager_run'
        result = subprocess.run(['zsh', '-dfc', code, 'test', str(PACKAGE)], env=env, capture_output=True, text=True, check=True)
        self.assertIn(str(self.home / 'not-exported')+'|menu', result.stdout)
        for file, call, expected in [('backup.sh', 'backup_create configs', '--backup|configuracoes'), ('restore.sh', 'restore_backup complete', '--restore-latest|completo')]:
            result = subprocess.run(['bash', '-c', 'source "$1"; '+call, 'test', str(PACKAGE/'payload/toolkit/modules'/file)], env=env, capture_output=True, text=True, check=True)
            self.assertIn(str(self.home/'custom-backups')+'|'+expected, result.stdout)

    def test_space_and_wine_activity_block_publication(self):
        root = self.unpack(self.backup())
        with patch('backup_engine.shutil.disk_usage', return_value=shutil._ntuple_diskusage(100, 100, 0)):
            with self.assertRaises(ValueError): engine.pack(root, self.home / 'no-space.kenoforge')
        env = {**self.env}
        script = 'import sys; sys.path.insert(0,sys.argv[1]); import backup_engine,wine_prefix; wine_prefix.require_idle=lambda *p: (_ for _ in ()).throw(ValueError("active Wine")); backup_engine.capture_extra(sys.argv[2])'
        dest = self.tmp / 'busy'; dest.mkdir()
        result = subprocess.run([sys.executable, '-B', '-c', script, str(TOOLS), str(dest)], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('active Wine', result.stderr)


if __name__ == '__main__': unittest.main(verbosity=2)
