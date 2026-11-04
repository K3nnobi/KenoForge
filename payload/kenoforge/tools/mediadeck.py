#!/usr/bin/env python3
"""Launch and diagnose the optional MediaDeck music integration."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys

CORE = Path(__file__).resolve().parents[1]
APP = CORE / "apps" / "mediadeck" / "main.py"
MODULES = {"PySide6.QtCore": "pyside6", "PySide6.QtQml": "pyside6",
           "PySide6.QtMultimedia": "pyside6", "mutagen": "python-mutagen", "numpy": "python-numpy"}
# The existing desktop/audio stack is reused; no session, boot, or autostart changes.
PACKAGES = ["pyside6", "python-mutagen", "python-numpy", "qt6-multimedia",
            "qt6-multimedia-ffmpeg", "ffmpeg", "libpulse", "xcb-util-cursor"]


def data_root():
    return Path(os.environ.get("KENOFORGE_DATA_HOME", str(Path.home() / "KenoForge"))).expanduser()


def missing_modules():
    missing = []
    for module, package in MODULES.items():
        try:
            if importlib.util.find_spec(module) is None:
                missing.append(package)
        except (ImportError, ValueError, ModuleNotFoundError):
            missing.append(package)
    return sorted(set(missing))


def graphics_available():
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def status():
    missing = missing_modules()
    print("KenoForge Music / MediaDeck 0.6.5.0")
    print("Application:", "available" if APP.is_file() else "missing")
    print("Python dependencies:", ", ".join(missing) if missing else "available")
    print("Graphical session:", "available" if graphics_available() else "not detected (TTY)")
    print("Spectrum capture:", "available" if shutil.which("parec") else "unavailable; music still works")
    print("Configuration:", data_root() / "Config/MediaDeck")
    print("Cover cache:", data_root() / "Cache/MediaDeck/covers")
    print("Player log:", data_root() / "Logs/MediaDeck/player.log")
    print("Music source: local folders; streaming services are not included.")
    print("Arch dependencies:", "sudo pacman -S --needed " + " ".join(PACKAGES))
    return int(bool(missing) or not APP.is_file())


def install_dependencies():
    if os.geteuid() == 0:
        print("Run this command as your normal user; sudo is used only for Pacman.")
        return 1
    if not shutil.which("pacman") or not shutil.which("sudo"):
        print("Automatic dependency installation requires Arch Linux, Pacman, and sudo.")
        return 1
    print("Optional Music Center dependencies:", " ".join(PACKAGES))
    print("The package manager will show its transaction for review.")
    if input("Continue? [y/N] ").strip().lower() not in ("y", "yes"):
        print("Cancelled.")
        return 0
    return subprocess.run(["sudo", "pacman", "-S", "--needed", *PACKAGES], check=False).returncode


def launch(detach=False):
    if not APP.is_file():
        print("Music application missing. Reinstall the current KenoForge package.")
        return 1
    missing = missing_modules()
    if missing:
        print("Missing music dependencies:", ", ".join(missing))
        print("Open Music Center -> Install Music Dependencies, or run kenoforge-music --install-deps.")
        return 1
    if not graphics_available():
        print("Music Center needs a graphical session (GNOME, KDE, etc.). Open it from a desktop terminal.")
        return 1
    command = [sys.executable, "-B", str(APP)]
    if not detach:
        os.execv(sys.executable, command)
    log = data_root() / "Logs/MediaDeck/player.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as output:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                   start_new_session=True)
    try:
        code = process.wait(timeout=0.8)
    except subprocess.TimeoutExpired:
        print("Music window launch requested. You can continue using KenoForge.")
        print("If the window does not appear, check:", log)
        return 0
    print("Player exited with status", code, "— details:", log)
    return code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--status", action="store_true")
    group.add_argument("--install-deps", action="store_true")
    group.add_argument("--detach", action="store_true", help="Open the window and release the console")
    args = parser.parse_args(argv)
    if args.status:
        return status()
    if args.install_deps:
        return install_dependencies()
    return launch(args.detach)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, EOFError) as exc:
        print("Music Center:", exc, file=sys.stderr)
        raise SystemExit(1)
