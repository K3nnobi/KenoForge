#!/usr/bin/env python3
"""Internal runner: execute inside bubblewrap, then wait only for its wineserver."""
import os
from pathlib import Path
import subprocess
import sys


def main():
    if os.geteuid() == 0:
        print("Wine as root is refused.", file=sys.stderr)
        return 1
    if len(sys.argv) < 2 or Path(sys.argv[1]).name not in ("wine", "wineboot", "winecfg"):
        return 2
    if os.environ.get("KENOFORGE_WINE_SANDBOX") != "1" or not (os.statvfs("/").f_flag & os.ST_RDONLY):
        print("This internal runner requires KenoForge's read-only Bubblewrap sandbox.", file=sys.stderr)
        return 2
    result = subprocess.run(sys.argv[1:], check=False)
    if result.returncode:
        return result.returncode
    # The PID namespace is destroyed when this runner exits; let registry writes finish first.
    server = Path(sys.argv[1]).parent / "wineserver"
    try:
        return subprocess.run([str(server), "-w"], timeout=60, check=False).returncode
    except subprocess.TimeoutExpired:
        print("The sandboxed Wine server did not finish; close the test application and retry.", file=sys.stderr)
        return 124


if __name__ == "__main__":
    raise SystemExit(main())
