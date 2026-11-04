#!/usr/bin/env python3
"""User-session patch maintenance; never runs inside a pacman transaction."""
from __future__ import annotations
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import sys
from maintenance_state import _read_json, _write_json, upsert_task, resolve_task

TOOLS = Path(__file__).resolve().parent
DATA = Path(os.environ.get('KENOFORGE_DATA_HOME', str(Path.home() / 'KenoForge')))
# Only existing managed integrations are restored. No AUR build runs unattended.
PATCHES = {
    'plymouth': ('Config/Patches/Plymouth/state.conf', ['bash', str(TOOLS.parent / 'patches/plymouth/plymouth-patch.sh'), '--reapply']),
    'capslock': ('Config/Caps-Lock-No-Delay/state.conf', ['bash', str(TOOLS / 'configure-capslock-nodelay.sh'), '--apply', '--yes']),
    'nvibrant': ('Config/NVIDIA/vibrance.conf', ['bash', str(TOOLS / 'configure-nvibrant.sh'), '--reapply']),
    'firefox-emoji': ('Config/Firefox-ChatGPT-Emoji', [sys.executable, '-B', str(TOOLS / 'configure-firefox-chatgpt-emoji.py'), '--apply']),
    'gnome-drag-hover': (None, [sys.executable, '-B', str(TOOLS / 'configure-gnome-drag-hover.py'), '--reapply', '--yes']),
}


def execute(command, background=False, timeout=600):
    return subprocess.run(command, stdin=subprocess.DEVNULL if background else None,
                          env={**os.environ, 'KENOFORGE_NONINTERACTIVE': '1' if background else '0'},
                          timeout=timeout, check=False)


def repair(background=False):
    # Pacman owns the system while its database lock exists, including AUR installs.
    if Path('/var/lib/pacman/db.lck').exists():
        print('Package transaction active; maintenance deferred.')
        return 0
    from update_guardian_loader import guardian
    changed = guardian.detect_external_package_changes()
    if changed:
        guardian.record_changed_packages(changed)
    enabled = _read_json('patch-persistence.json', {'enabled': []}).get('enabled', [])
    failures = 0
    for name in enabled:
        if name not in PATCHES:
            continue
        marker, command = PATCHES[name]
        if marker:
            path = DATA / marker
            if not path.exists() or path.is_symlink():
                continue  # Removal must not silently reinstall an integration.
            if name == 'firefox-emoji' and not any(path.glob('*.json')):
                continue
        check = {
            'plymouth': ['bash', str(TOOLS.parent / 'patches/plymouth/plymouth-patch.sh'), '--check'],
            'capslock': ['bash', str(TOOLS / 'configure-capslock-nodelay.sh'), '--check'],
            'gnome-drag-hover': [sys.executable, '-B', str(TOOLS / 'configure-gnome-drag-hover.py'), '--check'],
            'firefox-emoji': [sys.executable, '-B', str(TOOLS / 'configure-firefox-chatgpt-emoji.py'), '--check'],
            'nvibrant': ['systemctl', '--user', 'is-active', '--quiet', 'nvibrant.service'],
        }[name]
        try:
            if execute(check, background, timeout=45).returncode == 0 and not (name == 'nvibrant' and changed & {'nvidia-utils', 'nvidia-settings'}):
                resolve_task('persistence-' + name)
                continue
        except (OSError, subprocess.TimeoutExpired):
            pass
        # Helpers refuse unsupported versions and preserve their existing backups.
        try:
            result = execute(command, background)
            success = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            success = False
        task = 'persistence-' + name
        if success:
            resolve_task(task)
        else:
            failures += 1
            upsert_task(task, 'Review patch: ' + name,
                        'Automatic repair failed or needs privileges/session/dependencies. Open Maintenance Center → Patch persistence → Repair now. Review helper output before retrying.',
                        'warning', 'Patch Persistence')
    guardian.scan(changed)
    return int(bool(failures))


def unit_quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('\n', '\\n') + '"'


def install_timer(enable=True, helper=None):
    units = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'systemd/user'
    from backup_engine import atomic_bytes, directory
    with directory(units, create=True):
        pass
    service = '[Unit]\nDescription=KenoForge patch persistence\n\n[Service]\nType=oneshot\n'
    service += 'Environment=' + unit_quote('KENOFORGE_DATA_HOME=' + str(DATA)) + '\n'
    service += 'ExecStart=' + unit_quote(sys.executable) + ' -B ' + unit_quote(helper or Path(__file__).resolve()) + ' --background\nTimeoutStartSec=30min\n'
    for name, content in {
        'kenoforge-patch-persistence.service': service,
        'kenoforge-patch-persistence.timer': '[Unit]\nDescription=Periodically restore KenoForge patches\n\n[Timer]\nOnStartupSec=2min\nOnUnitInactiveSec=10min\n\n[Install]\nWantedBy=timers.target\n',
    }.items():
        target = units / name
        if target.is_symlink():
            raise ValueError('Symlink unit refused: ' + str(target))
        atomic_bytes(target, content.encode(), 0o600)
    if enable:
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
        subprocess.run(['systemctl', '--user', 'enable', '--now', 'kenoforge-patch-persistence.timer'], check=True)


def menu():
    while True:
        enabled = _read_json('patch-persistence.json', {'enabled': []}).get('enabled', [])
        print('\nPatch persistence\nEnabled: ' + ', '.join(enabled))
        print('1) Configure automatic repair\n2) Repair now\n3) Disable timer\n0) Back')
        choice = input('> ').strip()
        if choice == '0':
            return 0
        if choice == '1':
            names = list(PATCHES)
            for i, name in enumerate(names, 1):
                print(f'{i}) {name}')
            print('Select numbers separated by spaces. Only select patches you want kept active.')
            selected = input('> ').split()
            if any(not x.isdigit() or not 1 <= int(x) <= len(names) for x in selected):
                print('Invalid selection.'); continue
            _write_json('patch-persistence.json', {'enabled': list(dict.fromkeys(names[int(x)-1] for x in selected))})
            from update_guardian_loader import guardian
            guardian.detect_external_package_changes()
            install_timer()
        elif choice == '2':
            repair()
        elif choice == '3':
            subprocess.run(['systemctl', '--user', 'disable', '--now', 'kenoforge-patch-persistence.timer'], check=True)
            _write_json('patch-persistence.json', {'enabled': []})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--repair', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0 and os.environ.get('KENOFORGE_TEST_SIMULATE') != '1':
        parser.error('Run as your normal user, without sudo.')
    from maintenance_state import state_directory
    directory, fd = state_directory()
    try:
        lock = os.open('patch-persistence.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    finally:
        os.close(fd)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        return repair(args.background) if args.background or args.repair else menu()
    finally:
        os.close(lock)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Patch persistence: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
