#!/usr/bin/env python3
"""Maintain only KenoForge's Nautilus thumbnail CSS; preserve other rules."""
import argparse
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile

BEGIN = "/* KenoForge: Nautilus transparent thumbnails */"
END = "/* End KenoForge: Nautilus transparent thumbnails */"
# Nautilus src/resources/style.css uses .nautilus-image.file-thumbnail.
# Older releases use .thumbnail. These selectors do not change generic GTK images.
BLOCK = BEGIN + "\n" + """.nautilus-image.file-thumbnail,
.nautilus-window .thumbnail {
    background: none;
    background-color: transparent;
    background-image: none;
    box-shadow: none;
}
""" + END + "\n"


def reject_redirects(path):
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f"Refused symbolic link: {part}")


def strip_managed(text):
    """Refuse incomplete/nested ownership markers before touching the file."""
    lines = []
    opened = False
    count = 0
    for line in text.splitlines(keepends=True):
        if line.strip() == BEGIN:
            if opened:
                raise ValueError("Nested KenoForge CSS markers; no file changed.")
            opened = True
            count += 1
        elif line.strip() == END:
            if not opened:
                raise ValueError("Unmatched KenoForge CSS end marker; no file changed.")
            opened = False
        elif not opened:
            lines.append(line)
    if opened:
        raise ValueError("Incomplete KenoForge CSS block; no file changed.")
    return "".join(lines), count


def css_target():
    root = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    if not root.is_absolute():
        raise ValueError("XDG_CONFIG_HOME must be absolute.")
    return root / "gtk-4.0/gtk.css"


def update(target, backup_dir, remove=False):
    reject_redirects(target)
    if target.exists() and not target.is_file():
        raise ValueError(f"Not a regular CSS file: {target}")
    original = target.read_bytes() if target.exists() else b""
    unmanaged, count = strip_managed(original.decode("utf-8"))
    if remove:
        result = unmanaged
    else:
        separator = "\n" if unmanaged and not unmanaged.endswith("\n") else ""
        result = unmanaged + separator + BLOCK
    encoded = result.encode("utf-8")
    if original == encoded:
        print("[OK] Nautilus thumbnail CSS is already current." if not remove else "[OK] No managed CSS to remove.")
        return False
    reject_redirects(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    if target.exists():
        fd, name = tempfile.mkstemp(prefix="gtk.css-before-nautilus-", dir=backup_dir)
        os.close(fd)
        shutil.copy2(target, name)
        print("[INFO] CSS backup:", name)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix=".gtk.css-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print("[OK] Managed Nautilus transparency rules removed." if remove else
          "[OK] Thumbnail CSS updated for current and older Nautilus releases.")
    print("[INFO] The new CSS takes effect after Nautilus exits and starts again.")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true")
    group.add_argument("--remove", action="store_true")
    group.add_argument("--status", action="store_true")
    args = parser.parse_args()
    target = css_target()
    if not (args.apply or args.remove):
        reject_redirects(target)
        original = target.read_text(encoding="utf-8") if target.is_file() else ""
        unmanaged, count = strip_managed(original)
        print("CSS:", target)
        current = count == 1 and BLOCK in original
        print("Managed transparency:", "current" if current else "missing or outdated")
        return int(not current)
    if os.geteuid() == 0:
        raise ValueError("Run as your normal user, without sudo.")
    backup_dir = Path.home() / ".kenoforge/Installer-Backups"
    update(target, backup_dir, args.remove)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, UnicodeError) as exc:
        print("[ERROR]", exc, file=sys.stderr)
        raise SystemExit(1)
