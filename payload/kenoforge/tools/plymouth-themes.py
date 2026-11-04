#!/usr/bin/env python3
"""Choose an installed Plymouth theme and rebuild initramfs with rollback."""
import os
from pathlib import Path
import re
import subprocess
import sys
from maintenance_state import private_directory


def run(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True).stdout.strip()


def apply(theme):
    if not re.fullmatch(r'[A-Za-z0-9_.+-]+', theme):
        raise ValueError('Invalid theme')
    previous = run('plymouth-set-default-theme')
    directory, fd = private_directory(('Config', 'Patches', 'Plymouth'), create=True)
    try:
        if (directory / 'theme').is_symlink():
            raise ValueError('Unsafe saved theme')
        try:
            run('sudo', 'plymouth-set-default-theme', theme)
            run('sudo', 'mkinitcpio', '-P')
        except subprocess.CalledProcessError:
            run('sudo', 'plymouth-set-default-theme', previous)
            run('sudo', 'mkinitcpio', '-P')
            raise
        temp = '.theme-' + str(os.getpid())
        out = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
        with os.fdopen(out, 'w') as stream:
            stream.write(theme + '\n')
        os.replace(temp, 'theme', src_dir_fd=fd, dst_dir_fd=fd)
    finally:
        os.close(fd)
    print('Theme applied. Reboot to see it.')


def main():
    if os.geteuid() == 0:
        raise ValueError('Run as your normal user, without sudo.')
    while True:
        themes = [x.strip() for x in run('plymouth-set-default-theme', '-l').splitlines() if re.fullmatch(r'[A-Za-z0-9_.+-]+', x.strip())]
        active = run('plymouth-set-default-theme')
        print('\nPlymouth Themes — Active: ' + active)
        for i, theme in enumerate(themes, 1):
            print(f'{i}) {theme}' + (' [active]' if theme == active else ''))
        print('0) Back')
        value = input('> ').strip()
        if value == '0':
            return 0
        if value.isdigit() and 1 <= int(value) <= len(themes):
            apply(themes[int(value)-1])


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Plymouth Themes: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
