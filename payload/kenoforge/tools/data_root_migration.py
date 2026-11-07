#!/usr/bin/env python3
"""Move the installed data root and journal edits to its active integrations."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from backup_engine import atomic_bytes, directory, read_json, write_json
from wine_prefix import rename_noreplace

OLD_NAME = 'KenoForge'
NEW_NAME = '.kenoforge'
SHELL_FILES = ('.zshrc', '.zshenv', '.zprofile', '.zlogin', '.zsh_aliases',
               '.p10k.zsh', '.bashrc', '.bash_profile', '.profile')
LIMIT = 16 * 1024 * 1024


def translate(text, old, new):
    """Change an exact absolute root and its common shell spellings."""
    before, after = str(old), str(new)
    pairs = [(before, after)]
    # Systemd specifiers escape literal percent signs; Zsh may escape spaces.
    pairs.extend(((before.replace('%', '%%'), after.replace('%', '%%')),
                  (before.replace(' ', r'\ '), after.replace(' ', r'\ '))))
    if old.name != new.name:
        for prefix in ('$HOME/', '${HOME}/', '~/'):
            pairs.append((prefix + old.name, prefix + new.name))
    for source, target in dict(pairs).items():
        text = re.sub(re.escape(source) + r'''(?=$|[/\s'"\x60:;),\]}])''',
                      lambda _: target, text)
    return text


def checked_directory(path):
    with directory(path) as fd:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError('Unsafe ownership or permissions: ' + str(path))


def exists(path):
    return os.path.lexists(path)


def preflight(home, package):
    old, new = home / OLD_NAME, home / NEW_NAME
    for root in (old, new):
        if exists(root):
            checked_directory(root)
    if exists(old) and exists(new):
        raise ValueError(f'Both {old} and {new} exist. Choose which installation to keep; no files were merged.')
    if exists(old):
        if package.is_relative_to(old):
            raise ValueError('Extract or clone the installer outside the old data directory first.')
        # A coincidentally named source checkout or personal folder is not an installation.
        core = old / 'System/Core'
        config = old / 'Config'
        recognized = False
        for marker in (core / 'console/main.zsh', config / 'settings.zsh',
                       config / 'kenoforge.conf'):
            try:
                with directory(marker.parent) as fd:
                    info = os.stat(marker.name, dir_fd=fd, follow_symlinks=False)
                    recognized |= stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            except FileNotFoundError:
                pass
        if not recognized:
            raise ValueError(f'{old} does not look like a KenoForge installation. Move it aside first.')
        return True
    return False


def config_paths(root, home, xdg):
    """Enumerate active settings only; archives, logs and prefix contents stay untouched."""
    yield from (home / name for name in SHELL_FILES)
    for folder in (root / 'Config', root / 'State/Maintenance', home / '.zsh', xdg / 'zsh'):
        if not exists(folder):
            continue
        try:
            checked_directory(folder)
        except (OSError, ValueError):
            if folder.is_symlink():
                continue
            raise
        for current, dirs, files in os.walk(folder, followlinks=False):
            current = Path(current)
            for name in dirs + files:
                path = current / name
                if path.is_symlink() or (name in files and path.suffix in ('.zsh', '.sh', '.json', '.conf', '.ini')):
                    yield path
    yield xdg / 'systemd/user/kenoforge-patch-persistence.service'
    yield xdg / 'gamemode.ini'


def read_item(path):
    try:
        with directory(path.parent) as fd:
            info = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            if info.st_uid != os.getuid():
                raise ValueError('Integration is not owned by the current user: ' + str(path))
            if stat.S_ISLNK(info.st_mode):
                return 'link', os.fsencode(os.readlink(path.name, dir_fd=fd)), 0
            if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
                return None
            file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            with os.fdopen(file_fd, 'rb') as f:
                if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
                    raise ValueError('Integration changed while being inspected: ' + str(path))
                return 'file', f.read(LIMIT + 1), stat.S_IMODE(info.st_mode)
    except FileNotFoundError:
        return None
    except NotADirectoryError:
        # Do not follow a redirected directory to edit anything beyond it.
        if any(parent.is_symlink() for parent in path.parents):
            return None
        raise


def write_item(path, kind, content, mode):
    if kind == 'file':
        atomic_bytes(path, content, mode)
        return
    with directory(path.parent) as fd:
        temp = '.kenoforge-relocate-' + uuid.uuid4().hex
        os.symlink(os.fsdecode(content), temp, dir_fd=fd)
        try:
            os.replace(temp, path.name, src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(temp, dir_fd=fd)
            except FileNotFoundError:
                pass


def translate_json(value, old, new):
    if isinstance(value, dict):
        return {key: translate_json(item, old, new) for key, item in value.items()}
    if isinstance(value, list):
        return [translate_json(item, old, new) for item in value]
    if isinstance(value, str):
        return translate(value, old, new)
    return value


def changes(home, xdg, old=None, receipts=False):
    old, new = old or home / OLD_NAME, home / NEW_NAME
    paths = list(config_paths(new, home, xdg))
    if receipts:
        sessions = new / 'Installer-Backups/Wine-Prefix-Repair'
        if exists(sessions):
            checked_directory(sessions)
            paths.extend(path / 'session.json' for path in sessions.iterdir()
                         if path.is_dir() and not path.is_symlink())
    for path in dict.fromkeys(paths):
        item = read_item(path)
        if not item:
            continue
        kind, original, mode = item
        try:
            text = original.decode()
        except UnicodeDecodeError:
            continue
        if kind == 'link':
            if text != str(old) and not text.startswith(str(old) + '/'):
                continue
            updated = str(new) + text[len(str(old)):]
        elif path == xdg / 'gamemode.ini':
            updated = re.sub(r'(?ms)^; BEGIN KENOFORGE GAMEMODE BLUR\r?$.*?^; END KENOFORGE GAMEMODE BLUR\r?$',
                             lambda m: translate(m[0], old, new), text)
        elif path.name == 'kenoforge-patch-persistence.service':
            if str(old / 'System/Core/tools/patch-persistence.py') not in text.replace('%%', '%'):
                continue
            updated = translate(text, old, new)
        elif path.suffix == '.json':
            try:
                value = json.loads(text)
            except ValueError:
                continue  # Do not normalize damaged or user-defined data.
            rebased = translate_json(value, old, new)
            updated = text if rebased == value else json.dumps(rebased, ensure_ascii=False, indent=2) + '\n'
        else:
            updated = translate(text, old, new)
        if updated != text:
            yield path, kind, original, updated.encode(), mode


def apply(home, xdg, journal):
    edits = list(changes(home, xdg, receipts=True))
    journal.mkdir(mode=0o700)
    records = []
    for path, kind, original, updated, mode in edits:
        saved = str(len(records))
        atomic_bytes(journal / saved, original)
        records.append({'path': str(path), 'saved': saved, 'kind': kind, 'mode': mode})
        write_json(journal / 'journal.json', records)
        if read_item(path) != (kind, original, mode):
            raise ValueError('Integration changed during migration: ' + str(path))
        write_item(path, kind, updated, mode)
        if path == xdg / 'systemd/user/kenoforge-patch-persistence.service':
            atomic_bytes(journal / 'reload-user-units', b'')
    print(f'Moved data to {home / NEW_NAME}; updated {len(edits)} integration(s).')


def undo(journal):
    index = journal / 'journal.json'
    if not index.exists():
        return
    for record in reversed(read_json(index)):
        item = read_item(journal / record['saved'])
        if item is None or item[0] != 'file':
            raise ValueError('Migration recovery copy missing: ' + record['saved'])
        write_item(Path(record['path']), record['kind'], item[1], record['mode'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('move', 'move-back', 'apply', 'undo'))
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    home = Path.home()
    old, new = home / OLD_NAME, home / NEW_NAME
    if args.action == 'move':
        if not preflight(home, args.path):
            return 3
        rename_noreplace(old, new)
    elif args.action == 'move-back':
        checked_directory(new)
        rename_noreplace(new, old)
    elif args.action == 'apply':
        apply(home, Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config'), args.path)
    else:
        undo(args.path)
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        raise SystemExit('KenoForge data migration: ' + str(exc))
