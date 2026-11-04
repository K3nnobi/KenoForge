#!/usr/bin/env python3
"""Retire previous user-shell integrations with a reversible migration journal."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys

OLD_TITLE = 'ArchMind'
OLD_COMMAND = 'archmind'


def safe(path, home, allow_link=False):
    path.relative_to(home)
    current = path.parent
    while current != home:
        if current.is_symlink():
            raise ValueError('Symlink ancestor refused: ' + str(current))
        current = current.parent
    if path.is_symlink() and not allow_link:
        raise ValueError('Symlink file refused: ' + str(path))


def journal_save(backup, journal):
    temp = backup / '.journal.tmp'
    temp.write_text(json.dumps(journal, indent=2) + '\n')
    temp.replace(backup / 'journal.json')


def rollback(backup, home):
    journal_path = backup / 'journal.json'
    if not journal_path.exists():
        return
    journal = json.loads(journal_path.read_text())
    for item in reversed(journal['items']):
        target = Path(item['path'])
        saved = backup / item['saved']
        safe(target, home, allow_link=item['kind'] in ('move', 'new'))
        if item['kind'] == 'new':
            if target.is_symlink() or target.is_file():
                target.unlink()
        elif item['kind'] == 'move':
            if saved.exists() or saved.is_symlink():
                if target.exists() or target.is_symlink():
                    raise ValueError('Restore conflict: ' + str(target))
                target.parent.mkdir(parents=True, exist_ok=True)
                saved.rename(target)
        elif saved.exists():
            shutil.copy2(saved, target)
    print('Previous shell integrations restored.')


def rewritten(text):
    # Restrict substitution to selected shell/integration files, never archives.
    return re.sub(OLD_COMMAND, lambda m: 'KENOFORGE' if m[0].isupper() else ('kenoforge' if m[0].islower() else 'KenoForge'), text, flags=re.I)


def plan(home):
    config = Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config')))
    data = Path(os.environ.get('XDG_DATA_HOME', str(home / '.local/share')))
    for root in (config, data):
        safe(root, home)
    retargets = []
    paths = [home / x for x in ('.zshrc', '.zshenv', '.zprofile', '.zlogin', '.bashrc', '.bash_profile', '.profile', '.zsh_aliases')]
    for folder in (home / '.zsh', config / 'zsh', home / 'KenoForge/Config/Zsh'):
        if folder.exists():
            safe(folder, home)
            for path in folder.rglob('*'):
                if path.is_file() and path.suffix in ('.zsh', '.sh', ''):
                    paths.append(path)
    edits = []
    for path in dict.fromkeys(paths):
        if not path.exists() and not path.is_symlink():
            continue
        # Installer can organize .zsh_aliases using a controlled new symlink.
        if path.is_symlink() and path == home / '.zsh_aliases':
            if OLD_COMMAND in str(path.readlink()).lower():
                continue  # Copied and retargeted below, without changing old data.
            path = path.resolve()
        safe(path, home)
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError('Unsupported shell integration: ' + str(path))
        text = path.read_text()
        updated = rewritten(text)
        if updated != text and path not in [p for p, _ in edits]:
            edits.append((path, updated))
    moves = []
    for name in ('.zsh_aliases', '.p10k.zsh'):
        link = home / name
        if link.is_symlink() and OLD_COMMAND in str(link.readlink()).lower():
            source = link.resolve()
            safe(source, home)
            if not source.is_file() or source.stat().st_size > 2 * 1024 * 1024:
                raise ValueError('Previous shell link has no supported target: ' + str(link))
            destination = home / 'KenoForge/Config/Zsh' / ('migrated-' + name.lstrip('.'))
            safe(destination, home)
            if destination.exists() or destination.is_symlink():
                raise ValueError('Shell import conflict: ' + str(destination))
            retargets.append((link, destination, rewritten(source.read_text())))
            moves.append((link, 'shell-link-' + name.lstrip('.')))
    root = home / OLD_TITLE
    if root.exists() or root.is_symlink():
        safe(root, home)
        if not root.is_dir():
            raise ValueError('Previous project is not a directory')
        moves.append((root, 'previous-installation'))
    for path, label in ((config / OLD_COMMAND, 'previous-config'), (data / (OLD_COMMAND + '-toolkit'), 'previous-toolkit')):
        if path.exists() or path.is_symlink():
            safe(path, home, allow_link=True)
            moves.append((path, label))
    bindir = home / '.local/bin'
    if bindir.exists():
        safe(bindir, home)
        for path in bindir.iterdir():
            if path.name == OLD_COMMAND or path.name.startswith(OLD_COMMAND + '-'):
                safe(path, home, allow_link=True)
                if path.is_dir() and not path.is_symlink():
                    raise ValueError('Launcher is a directory: ' + str(path))
                if not path.is_symlink() and OLD_COMMAND not in path.read_text(errors='replace').lower():
                    raise ValueError('Unrecognized previous launcher: ' + str(path))
                moves.append((path, 'launcher-' + path.name.replace(OLD_COMMAND, 'previous')))
    applications = data / 'applications'
    if applications.exists():
        safe(applications, home)
        for path in applications.glob('*.desktop'):
            safe(path, home)
            text = path.read_text()
            if re.search(r'^Exec=.*' + OLD_COMMAND, text, re.I | re.M):
                # Disable old launchers: new commands are already installed.
                moves.append((path, 'desktop-' + str(len(moves)) + '.desktop'))
    return edits, moves, retargets


def apply(home, backup):
    edits, moves, retargets = plan(home)  # Validate every path before the first mutation.
    safe(backup, home)
    backup.mkdir(parents=True, exist_ok=False, mode=0o700)
    journal = {'format': 1, 'items': []}
    journal_save(backup, journal)
    try:
        for i, (path, updated) in enumerate(edits):
            saved = 'shell-' + str(i)
            shutil.copy2(path, backup / saved)
            journal['items'].append({'kind': 'edit', 'path': str(path), 'saved': saved})
            journal_save(backup, journal)
            path.write_text(updated)
        for path, saved in moves:
            journal['items'].append({'kind': 'move', 'path': str(path), 'saved': saved})
            journal_save(backup, journal)
            path.rename(backup / saved)
        for link, destination, content in retargets:
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            for new in (destination, link):
                journal['items'].append({'kind': 'new', 'path': str(new), 'saved': ''})
                journal_save(backup, journal)
                if new == destination:
                    with destination.open('x') as stream:
                        stream.write(content)
                    destination.chmod(0o600)
                else:
                    link.symlink_to(destination)
    except BaseException:
        rollback(backup, home)
        raise
    print(f'KenoForge migration: {len(edits)} shell files updated; {len(moves)} previous integrations archived.')
    print('Close previous shells and open a new terminal. Personal data and old patch rollback states remain in: ' + str(backup))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backup-dir', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    home = Path.home().resolve()
    if args.rollback:
        safe(args.backup_dir, home)
        rollback(args.backup_dir, home)
    elif args.apply:
        if os.geteuid() == 0 and os.environ.get('KENOFORGE_TEST_SIMULATE') != '1':
            raise ValueError('Run as your normal user.')
        if args.backup_dir is None:
            raise ValueError('A backup directory is required')
        apply(home, args.backup_dir)
    else:
        edits, moves, retargets = plan(home)
        for path, _ in edits:
            print('Update shell: ' + str(path))
        for path, _ in moves:
            print('Archive previous integration: ' + str(path))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, UnicodeError) as error:
        raise SystemExit('KenoForge migration: ' + str(error))
