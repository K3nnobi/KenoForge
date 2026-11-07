#!/usr/bin/env python3
"""Reversibly remove this user's runtime; keep configuration and all backups."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def safe_path(path):
    # Inspect parents too: never write through redirected integration directories.
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"Refused symbolic link: {part}")


def desktop_exec(path):
    # Match install.sh's Desktop Entry Exec escaping, including percent signs.
    value = str(path).replace('\x5c', '\x5c\x5c')
    for character in '"$`':
        value = value.replace(character, '\x5c' + character)
    value = value.replace('\x5c', '\x5c\x5c').replace('%', '%%')
    return f'Exec="{value}" %f'.encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Perform reversible removal')
    parser.add_argument('--yes', action='store_true', help='Confirm removal with --apply')
    args = parser.parse_args()
    home = Path.home()
    root = home / '.kenoforge'
    system = root / 'System'
    safe_path(system)
    if not system.exists():
        print('KenoForge runtime is not installed. Nothing changed.')
        return
    if not (system / 'Core/console/main.zsh').is_file():
        raise ValueError('The runtime does not match a KenoForge installation.')
    links = {home / '.local/bin' / name: system / 'Toolkit/bin' / name
             for name in ('kenoforge', 'kenoforge-console', 'kenoforge-monitor', 'kenoforge-music')}
    config_home = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    data_home = Path(os.environ.get('XDG_DATA_HOME') or home / '.local/share')
    if not config_home.is_absolute() or not data_home.is_absolute():
        raise ValueError('XDG paths must be absolute.')
    links[home / '.local/bin/kenoforge'] = system / 'Toolkit/bin/kenoforge-console'
    links[config_home / 'kenoforge'] = system / 'Core'
    links[data_home / 'kenoforge-toolkit'] = system / 'Toolkit'
    owned = {}
    for path, target in links.items():
        safe_path(path.parent)
        if path.is_symlink() and path.readlink() == target:
            owned[path] = str(target)
        elif path.exists() or path.is_symlink():
            print(f'Preserving unrecognized integration: {path}')
    desktop = data_home / 'applications/kenoforge-execute-terminal.desktop'
    zshrc = home / '.zshrc'
    changes = {}
    for path in (desktop, zshrc):
        safe_path(path)
        if path.exists() and not path.is_file():
            raise ValueError(f'Not a regular file: {path}')
    if desktop.exists():
        content = desktop.read_bytes()
        if desktop_exec(system / 'Core/tools/execute-in-terminal.sh') in content.splitlines():
            changes[desktop] = (content, None)
        else:
            print(f'Preserving unrecognized desktop entry: {desktop}')
    if zshrc.exists():
        original = zshrc.read_bytes()
        pattern = rb'(?m)^# KENOFORGE-SHELL-BEGIN\n.*?^# KENOFORGE-SHELL-END\n?'
        updated = re.sub(pattern, b'', original, flags=re.S)
        if updated != original:
            changes[zshrc] = (original, updated)
    print(f'Runtime to archive: {system}')
    print(f'Owned links to remove: {len(owned)}; integration files to update: {len(changes)}')
    print('Configurations, personal backups and installed system packages will be preserved.')
    if not args.apply:
        print('Preview only. Run again with --apply to proceed.')
        return
    if os.geteuid() == 0:
        raise ValueError('Run as your normal user, not as root.')
    if not args.yes and input('Type REMOVE to confirm: ') != 'REMOVE':
        print('Cancelled. Nothing changed.')
        return
    units = config_home / 'systemd/user'
    timer = units / 'kenoforge-patch-persistence.timer'
    service = units / 'kenoforge-patch-persistence.service'
    if service.is_file() and not service.is_symlink() and str(system / 'Core/tools/patch-persistence.py') in service.read_text():
        result = subprocess.run(['systemctl', '--user', 'disable', '--now', timer.name], check=False)
        if result.returncode:
            raise ValueError('Could not disable patch persistence; disable its timer before uninstalling.')
        service.unlink()
        if timer.is_file() and not timer.is_symlink() and 'Periodically restore KenoForge patches' in timer.read_text():
            timer.unlink()
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=False)
    backup_root = root / 'Installer-Backups'
    safe_path(backup_root)
    backup_root.mkdir(parents=True, exist_ok=True)
    archive = Path(tempfile.mkdtemp(prefix='uninstalled-', dir=backup_root))
    saved_files = {}
    for index, (path, (original, _)) in enumerate(changes.items()):
        saved = archive / f'integration-{index}'
        shutil.copy2(path, saved)
        saved_files[str(path)] = saved.name
    (archive / 'RESTORE.json').write_text(json.dumps({
        'runtime_target': str(system), 'links': {str(p): v for p, v in owned.items()},
        'integration_files': saved_files}, indent=2) + '\n')
    moved = False
    try:
        system.rename(archive / 'System')
        moved = True
        for path in owned:
            path.unlink()
        for path, (_, updated) in changes.items():
            if updated is None:
                path.unlink()
            else:
                path.write_bytes(updated)
    except BaseException:
        if moved:
            (archive / 'System').rename(system)
        for path, target in owned.items():
            if not path.is_symlink() and not path.exists():
                path.symlink_to(target)
        for path in changes:
            shutil.copy2(archive / saved_files[str(path)], path)
        raise
    print(f'Runtime removed. Reinstall with install.sh to reactivate. Safety archive: {archive}')
    print('Open a new shell to refresh command lookup and aliases.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, EOFError) as exc:
        raise SystemExit(f'KenoForge uninstall: {exc}')
