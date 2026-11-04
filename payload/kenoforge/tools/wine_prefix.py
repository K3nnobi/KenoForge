"""Wine prefix maintenance: read-only diagnosis and journaled, isolated repair.

No Steam prefix repair, global wineserver kill, driver change, or prefix deletion.
All filesystem writes to prefix trees use no-follow directory descriptors.
"""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import stat
import struct
import subprocess
import sys
import time
import uuid

from maintenance_state import _write_json, utc_now, upsert_task, resolve_task
from runtime_files import private_directory, read_private_file, safe_text

TOOLS = Path(__file__).resolve().parent
SESSION_PARTS = ("Installer-Backups", "Wine-Prefix-Repair")
WATCH_PARTS = ("Config", "Maintenance")
MAX_ENTRIES = 500000
ESSENTIAL_NAMES = ("kernel32.dll", "ntdll.dll")
MIMES = ("application/x-ms-dos-executable", "application/x-msdownload")
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK


def walk_error(error):
    raise error


def normal_user():
    if os.geteuid() == 0:
        raise ValueError("Run as your normal user, without sudo. Wine is never run as root.")


def prefix_path(value=None):
    value = str(value or os.environ.get("WINEPREFIX") or Path.home() / ".wine")
    if any(ord(c) < 32 for c in value):
        raise ValueError("Control characters in the prefix path are refused.")
    path = Path(os.path.abspath(os.path.expanduser(value)))
    if path == Path.home() or path == Path("/"):
        raise ValueError("Home or the filesystem root cannot be a prefix.")
    return path


@contextmanager
def directory(path):
    """Open every ancestor without following symlinks, retaining the leaf fd."""
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("An absolute normalized path is required.")
    fd = os.open("/", DIRECTORY_FLAGS)
    try:
        for name in path.parts[1:]:
            child = os.open(name, DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        yield fd
    finally:
        os.close(fd)


@contextmanager
def relative_parent(fd, relative):
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in (".", "..", "") for p in parts):
        raise ValueError("Unsafe relative prefix path.")
    parent = os.dup(fd)
    try:
        for part in parts[:-1]:
            child = os.open(part, DIRECTORY_FLAGS, dir_fd=parent)
            os.close(parent)
            parent = child
        yield parent, parts[-1]
    finally:
        os.close(parent)


def regular_bytes(rootfd, name, limit=16384, complete=False):
    with relative_parent(rootfd, name) as (parent, leaf):
        fd = os.open(leaf, FILE_FLAGS, dir_fd=parent)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Not a regular file: " + str(name))
            if complete and info.st_size > limit:
                raise ValueError("File is too large for a complete safety inspection: " + str(name))
            data = bytearray()
            while len(data) < limit:
                chunk = os.read(fd, min(1024 * 1024, limit - len(data)))
                if not chunk:
                    break
                data.extend(chunk)
            return bytes(data)
        finally:
            os.close(fd)


def architecture(rootfd):
    values = set()
    for name in ("system.reg", "user.reg", "userdef.reg"):
        try:
            data = regular_bytes(rootfd, name)
        except (OSError, ValueError):
            continue
        match = re.search(rb"(?m)^#arch=(win32|win64)\s*$", data)
        if match:
            values.add(match.group(1).decode())
    return next(iter(values)) if len(values) == 1 else "unknown/conflicting"


def steam_managed(path):
    lower = str(path).lower()
    return ("compatdata" in (p.lower() for p in path.parts)
            or any(p.lower() in ("default_pfx", "proton-pfx") for p in path.parts)
            or (path.name == "pfx" and (path.parent.name.isdigit()
                or (path.parent / "config_info").exists() or (path.parent / "version").exists()))
            or ("proton" in lower and path.name == "pfx")
            or ((path.parent / "tracked_files").exists() and (path.parent / "config_info").exists()))


def proton_reference(value):
    lower = value.lower()
    return "proton" in lower or "compatibilitytools.d" in lower


def file_state(rootfd, relative):
    try:
        with relative_parent(rootfd, relative) as (parent, name):
            info = os.stat(name, dir_fd=parent, follow_symlinks=False)
            if stat.S_ISLNK(info.st_mode):
                target = os.readlink(name, dir_fd=parent)
                try:
                    followed = os.stat(name, dir_fd=parent)
                    state = "valid-link" if stat.S_ISREG(followed.st_mode) else "non-file-link"
                except FileNotFoundError:
                    state = "broken-link"
                except OSError:
                    state = "unreadable-link"
                return {"state": state, "target": target}
            return {"state": "regular" if stat.S_ISREG(info.st_mode) else "non-file"}
    except FileNotFoundError:
        return {"state": "missing"}
    except (OSError, ValueError) as exc:
        return {"state": "unsafe/unreadable", "detail": str(exc)}


def essentials(rootfd, arch):
    paths = ["drive_c/windows/system32/" + n for n in ESSENTIAL_NAMES]
    if arch == "win64":
        paths += ["drive_c/windows/syswow64/" + n for n in ESSENTIAL_NAMES]
    return {path: file_state(rootfd, path) for path in paths}


def query(command, timeout=15):
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                timeout=timeout, env={**os.environ, "LC_ALL": "C"}, check=False)
        return {"code": result.returncode, "text": safe_text(result.stdout + result.stderr)[:16000]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"code": None, "text": str(exc)}


def log_findings(text):
    lower = text.lower()
    return {
        "loader_failure": any(x in lower for x in ("could not load kernel32.dll", "could not load ntdll.dll", "c0000135")),
        "graphics_warnings": any(x in lower for x in ("vulkan", "mesa-egl", "dri2", "physical_devices")),
        "fixme_messages": "fixme:" in lower,
    }


def diagnose(value=None, system=True):
    path = prefix_path(value)
    report = {"prefix": str(path), "managed_by_steam": steam_managed(path), "errors": [],
              "broken_links": [], "proton_references": [], "entries": 0, "complete": True}
    try:
        with directory(path) as fd:
            report["architecture"] = architecture(fd)
            report["essentials"] = essentials(fd, report["architecture"])
            report["registry"] = {name: file_state(fd, name) for name in ("system.reg", "user.reg", "userdef.reg")}
            for root, dirs, files, current in os.fwalk(".", dir_fd=fd, follow_symlinks=False, onerror=walk_error):
                for name in dirs + files:
                    report["entries"] += 1
                    if report["entries"] > MAX_ENTRIES:
                        raise ValueError("Scan limit reached; use a smaller dedicated prefix.")
                    info = os.stat(name, dir_fd=current, follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        relative = str(Path(root) / name)
                        target = os.readlink(name, dir_fd=current)
                        try:
                            os.stat(name, dir_fd=current)
                            broken = False
                        except FileNotFoundError:
                            broken = True
                        except OSError as exc:
                            report["errors"].append(f"Cannot inspect {relative}: {exc}")
                            report["complete"] = False
                            continue
                        item = {"path": relative, "target": target,
                                "windows": relative.startswith("drive_c/windows/"), "broken": broken}
                        if broken:
                            report["broken_links"].append(item)
                        if proton_reference(target):
                            report["proton_references"].append(item)
    except (OSError, ValueError) as exc:
        report["errors"].append(str(exc))
        report["complete"] = False
    core = report.get("essentials", {})
    missing = [p for p, state in core.items() if state["state"] not in ("regular", "valid-link")]
    report["essential_problems"] = missing
    report["repair_scenario"] = bool(report["complete"] and not report["managed_by_steam"]
        and report.get("architecture") in ("win32", "win64")
        and all(report.get("registry", {}).get(name, {}).get("state") == "regular" for name in ("system.reg", "user.reg"))
        and any(x["windows"] for x in report["broken_links"])
        and all(core[p]["state"] == "broken-link" for p in missing))
    if system:
        wine = shutil.which("wine", path="/usr/bin:/bin")
        report["wine"] = query([wine, "--version"]) if wine and os.geteuid() != 0 else {
            "code": None, "text": "Wine unavailable, or diagnosis running as root (Wine not executed)."}
        report["packages"] = query(["pacman", "-Q", "wine", "wine-staging", "mesa", "nvidia-utils",
                                     "vulkan-icd-loader"]) if shutil.which("pacman") else {"text": "Pacman unavailable"}
        report["mime"] = {mime: query(["gio", "mime", mime]) for mime in MIMES}
        report["graphics"] = "Package inventory only. No driver changes or GPU health claim. Review graphics logs separately."
        report["sandbox"] = bool(shutil.which("bwrap", path="/usr/bin:/bin"))
        try:
            report["processes"] = active_processes([path])
        except ValueError as exc:
            report["processes"] = {"unavailable": str(exc)}
    return report


def check_prefix(path):
    path = prefix_path(path)
    # Repairs are restricted to user-owned prefixes below Home, as in Wine Compatibility Pack.
    if not path.is_relative_to(Path.home().resolve()):
        raise ValueError("Repair is restricted to prefixes inside Home; external paths can be diagnosed.")
    if steam_managed(path):
        raise ValueError("Steam/Proton-managed prefixes are diagnostic-only. This module does not repair them.")
    with directory(path) as fd:
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise ValueError("Prefix must be owned by this user and not group/other writable.")
        for name in ("system.reg", "user.reg"):
            regular_bytes(fd, name)
        with relative_parent(fd, "drive_c/windows/.check"):
            pass
    return path


def identity(path):
    with directory(path) as fd:
        st = os.fstat(fd)
        return [st.st_dev, st.st_ino]


def copy_metadata(source, target, info):
    for name in os.listxattr(source):
        os.setxattr(target, name, os.getxattr(source, name))
    os.fchmod(target, stat.S_IMODE(info.st_mode))
    os.utime(target, ns=(info.st_atime_ns, info.st_mtime_ns))


def copy_tree(source, destination):
    """Copy data/metadata and literal links, never traverse a linked directory."""
    with directory(source) as sourcefd, directory(destination.parent) as parentfd:
        os.mkdir(destination.name, 0o700, dir_fd=parentfd)
        targetfd = os.open(destination.name, DIRECTORY_FLAGS, dir_fd=parentfd)
        try:
            def visit(src, dst):
                parent_info = os.fstat(src)
                if parent_info.st_uid != os.getuid():
                    raise ValueError("Prefix contains another user's directory.")
                for name in sorted(os.listdir(src)):
                    st = os.stat(name, dir_fd=src, follow_symlinks=False)
                    if st.st_uid != os.getuid():
                        raise ValueError("Prefix contains another user's file: " + name)
                    if stat.S_ISLNK(st.st_mode):
                        os.symlink(os.readlink(name, dir_fd=src), name, dir_fd=dst)
                        os.utime(name, ns=(st.st_atime_ns, st.st_mtime_ns), dir_fd=dst, follow_symlinks=False)
                    elif stat.S_ISDIR(st.st_mode):
                        a = os.open(name, DIRECTORY_FLAGS, dir_fd=src)
                        try:
                            os.mkdir(name, 0o700, dir_fd=dst)
                            b = os.open(name, DIRECTORY_FLAGS, dir_fd=dst)
                            try:
                                visit(a, b)
                            finally:
                                os.close(b)
                        finally:
                            os.close(a)
                    elif stat.S_ISREG(st.st_mode):
                        a = os.open(name, FILE_FLAGS, dir_fd=src)
                        try:
                            start = os.fstat(a)
                            if not stat.S_ISREG(start.st_mode) or (st.st_dev, st.st_ino) != (start.st_dev, start.st_ino):
                                raise ValueError("Source changed during backup.")
                            b = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dst)
                            try:
                                while chunk := os.read(a, 1024 * 1024):
                                    view = memoryview(chunk)
                                    while view:
                                        view = view[os.write(b, view):]
                                copy_metadata(a, b, start)
                                os.fsync(b)
                            finally:
                                os.close(b)
                            end = os.fstat(a)
                            if (start.st_size, start.st_mtime_ns, start.st_ctime_ns) != (end.st_size, end.st_mtime_ns, end.st_ctime_ns):
                                raise ValueError("A prefix file changed during backup.")
                        finally:
                            os.close(a)
                    else:
                        raise ValueError("Special file refused in prefix: " + name)
                copy_metadata(src, dst, parent_info)
                os.fsync(dst)
            visit(sourcefd, targetfd)
        finally:
            os.close(targetfd)


def tree_hash(path):
    """Fingerprint data, permissions, names and link targets; no link traversal."""
    digest = hashlib.sha256()
    size = 0
    count = 0
    with directory(path) as fd:
        for root, dirs, files, current in os.fwalk(".", dir_fd=fd, follow_symlinks=False, onerror=walk_error):
            dirs.sort()
            for name in sorted(dirs + files):
                count += 1
                if count > MAX_ENTRIES:
                    raise ValueError("Prefix exceeds the safe inventory limit.")
                st = os.stat(name, dir_fd=current, follow_symlinks=False)
                entry = [str(Path(root) / name), st.st_mode]
                if st.st_uid != os.getuid():
                    raise ValueError("Prefix contains files not owned by this user.")
                if stat.S_ISLNK(st.st_mode):
                    entry += ["link", os.readlink(name, dir_fd=current)]
                elif stat.S_ISREG(st.st_mode):
                    item = os.open(name, FILE_FLAGS, dir_fd=current)
                    try:
                        if not stat.S_ISREG(os.fstat(item).st_mode):
                            raise ValueError("File changed type during inventory.")
                        content = hashlib.sha256()
                        while chunk := os.read(item, 1024 * 1024):
                            size += len(chunk)
                            content.update(chunk)
                        entry += ["file", content.hexdigest()]
                    finally:
                        os.close(item)
                elif not stat.S_ISDIR(st.st_mode):
                    raise ValueError("Special files cannot be snapshotted.")
                digest.update(json.dumps(entry, ensure_ascii=True, separators=(",", ":")).encode() + b"\0")
    return digest.hexdigest(), size


def content_inventory(path):
    """Per-path audit around wineboot; records existing data and literal links."""
    result = {}
    with directory(path) as fd:
        for root, dirs, files, current in os.fwalk(".", dir_fd=fd, follow_symlinks=False, onerror=walk_error):
            for name in dirs + files:
                relative = str(Path(root) / name)
                info = os.stat(name, dir_fd=current, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    result[relative] = ["link", os.readlink(name, dir_fd=current)]
                elif stat.S_ISREG(info.st_mode):
                    item = os.open(name, FILE_FLAGS, dir_fd=current)
                    try:
                        digest = hashlib.sha256()
                        while chunk := os.read(item, 1024 * 1024):
                            digest.update(chunk)
                        result[relative] = ["file", digest.hexdigest(), stat.S_IMODE(info.st_mode)]
                    finally:
                        os.close(item)
                elif stat.S_ISDIR(info.st_mode):
                    result[relative] = ["directory", stat.S_IMODE(info.st_mode)]
                else:
                    result[relative] = ["special"]
    return result


def active_processes(paths, proc=Path("/proc")):
    """Unknown Wine processes block mutations too; do not kill user processes."""
    selected = {str(prefix_path(p)) for p in paths}
    active = []
    for item in proc.iterdir():
        if not item.name.isdigit() or int(item.name) == os.getpid():
            continue
        try:
            if item.stat().st_uid != os.getuid():
                continue
            comm = (item / "comm").read_text().strip().lower()
            wine_process = "wine" in comm or comm.endswith((".exe", ".com"))
            try:
                executable = os.readlink(item / "exe").lower()
                wine_process = wine_process or "wine" in Path(executable).name or executable.endswith((".exe", ".com"))
            except (FileNotFoundError, PermissionError):
                pass
            try:
                raw = (item / "environ").read_bytes()
            except PermissionError:
                if wine_process:
                    active.append({"pid": int(item.name), "reason": "Wine process with unreadable environment"})
                continue
            env = dict(x.split(b"=", 1) for x in raw.split(b"\0") if b"=" in x)
            prefix = env.get(b"WINEPREFIX")
            if wine_process and prefix and str(prefix_path(os.fsdecode(prefix))) in selected:
                active.append({"pid": int(item.name), "reason": "Process uses the selected prefix"})
            elif wine_process and not prefix and str(Path.home() / ".wine") in selected:
                active.append({"pid": int(item.name), "reason": "Possible Wine process using the default prefix"})
        except (FileNotFoundError, ProcessLookupError):
            continue
        except (OSError, ValueError) as exc:
            raise ValueError("Process inspection incomplete; close Wine and retry: " + str(exc)) from exc
    return active


def require_idle(*paths):
    active = active_processes(paths)
    if active:
        raise ValueError("Close applications and Wine processes for this prefix, then retry. PIDs: "
                         + ", ".join(str(x["pid"]) for x in active))


def read_state(name, parts, default=None):
    try:
        _, fd = private_directory(parts, create=False)
    except FileNotFoundError:
        return default
    try:
        try:
            return json.loads(read_private_file(fd, name, limit=32 * 1024 * 1024))
        except FileNotFoundError:
            return default
    finally:
        os.close(fd)


@contextmanager
def prefix_lock(path):
    _, fd = private_directory(("State", "Wine-Prefix-Repair"), create=True)
    key = hashlib.sha256(str(path).encode()).hexdigest() + ".lock"
    lock = os.open(key, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    os.close(fd)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError:
        raise ValueError("Another KenoForge operation is using this prefix.") from None
    finally:
        os.close(lock)


def journal(session, event, **detail):
    session.setdefault("events", []).append({"at": utc_now(), "event": event, **detail})
    session["updated_at"] = utc_now()
    _write_json("session.json", session, (*SESSION_PARTS, session["id"]))
    _write_json(session["id"] + ".json", session, ("Logs", "Wine-Prefix-Repair"))


def session_paths(session):
    sid = session["id"]
    if not re.fullmatch(r"[a-f0-9]{32}", sid):
        raise ValueError("Invalid repair session ID.")
    source = prefix_path(session["source"])
    if not source.is_relative_to(Path.home().resolve()) or steam_managed(source):
        raise ValueError("Unsafe session prefix.")
    stage = source.parent / ("." + source.name + ".kenoforge-repair-" + sid)
    return {"source": source, "stage": stage, "backup": stage / "backup", "work": stage / "work",
            "clean": stage / "clean", "home": stage / "runtime-home",
            "original": source.parent / (source.name + ".kenoforge-original-" + sid)}


def load_session(sid):
    if not re.fullmatch(r"[a-f0-9]{32}", sid):
        raise ValueError("Invalid session ID.")
    session = read_state("session.json", (*SESSION_PARTS, sid))
    if not session or session.get("format") != 1 or session.get("id") != sid:
        raise ValueError("Repair session not found or invalid.")
    paths = session_paths(session)
    with directory(paths["stage"]) as fd:
        st = os.fstat(fd)
        if st.st_uid != os.getuid() or st.st_mode & 0o077:
            raise ValueError("The repair stage must remain private to this user.")
    return session


def sessions():
    try:
        root, fd = private_directory(SESSION_PARTS, create=False)
    except FileNotFoundError:
        return []
    os.close(fd)
    return [load_session(p.name) for p in sorted(root.iterdir())
            if re.fullmatch(r"[a-f0-9]{32}", p.name)]


def sandbox_command(session, target, command):
    """Root filesystem and original prefix stay read-only, including linked folders."""
    paths = session_paths(session)
    bwrap = shutil.which("bwrap", path="/usr/bin:/bin")
    if not bwrap:
        raise ValueError("Isolated Wine execution requires bubblewrap (Arch package: bubblewrap).")
    for path in (target, paths["home"]):
        with directory(path):
            pass
    args = [bwrap, "--die-with-parent", "--unshare-pid", "--unshare-net", "--unshare-ipc", "--new-session",
            "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
            "--bind", str(target), str(target), "--bind", str(paths["home"]), str(paths["home"])]
    if Path("/tmp/.X11-unix").is_dir():
        args += ["--ro-bind", "/tmp/.X11-unix", "/tmp/.X11-unix"]
    runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/" + str(os.getuid())))
    if runtime.is_dir():
        args += ["--tmpfs", str(runtime)]
    if Path("/run/dbus").is_dir():
        args += ["--tmpfs", "/run/dbus"]
    env = {"PATH": "/usr/bin:/bin", "HOME": str(paths["home"]), "WINEPREFIX": str(target),
           "KENOFORGE_WINE_SANDBOX": "1",
           "WINEARCH": session["architecture"], "WINEDEBUG": "+timestamp,err+all,warn+all,fixme+all",
           "XDG_RUNTIME_DIR": str(paths["home"] / "runtime"),
           "XDG_CONFIG_HOME": str(paths["home"] / "config"), "XDG_CACHE_HOME": str(paths["home"] / "cache"),
           "LC_ALL": "C"}
    if target == paths["clean"]:
        env["WINEDLLOVERRIDES"] = "mscoree,mshtml="
    for name in ("DISPLAY", "XAUTHORITY", "LANG", "USER", "LOGNAME"):
        if os.environ.get(name):
            env[name] = os.environ[name]
    wayland = os.environ.get("WAYLAND_DISPLAY")
    if wayland:
        socket = Path(wayland) if wayland.startswith("/") else runtime / wayland
        if socket.exists():
            destination = paths["home"] / "runtime" / "wayland-0"
            args += ["--ro-bind", str(socket), str(destination)]
            env["WAYLAND_DISPLAY"] = str(destination)
    authority = os.environ.get("XAUTHORITY")
    if authority and Path(authority).is_file():
        destination = paths["home"] / ".Xauthority"
        args += ["--ro-bind", authority, str(destination)]
        env["XAUTHORITY"] = str(destination)
    # A private IPC/network namespace avoids Wine services reaching host daemons.
    # No D-Bus, Steam variables, LD_PRELOAD or custom Wine loader environment is inherited.
    args += ["--chdir", str(target), "--", sys.executable, "-B", str(TOOLS / "wine_sandbox_run.py"),
             *command]
    return args, env


def classify_output(text, code):
    findings = log_findings(text)
    findings["fatal"] = code != 0 or findings["loader_failure"]
    return findings


def startup_registry(rootfd):
    """Conservative comparison with a fresh prefix, without loading a Wine hive."""
    result = {}
    for hive in ("system.reg", "user.reg", "userdef.reg"):
        raw = regular_bytes(rootfd, hive, 64 * 1024 * 1024, complete=True).decode(errors="replace")
        section = ""
        for line in raw.splitlines():
            if line.startswith("[") and "]" in line:
                section = line[1:line.index("]")].replace("\\\\", "\\").lower()
            elif line.startswith(('"', '@=')):
                dangerous = (any(part in section for part in (
                    "\\currentversion\\run", "\\services\\", "\\winlogon", "\\image file execution options",
                    "\\currentversion\\windows", "\\command processor"))
                    or "startup" in line.lower())
                if dangerous:
                    result.setdefault(hive + ":" + section, set()).add(line.strip())
    return result


def execution_hazards(work, clean):
    """Do not boot a copied prefix with unknown Run/Startup/service commands."""
    with directory(work) as fd, directory(clean) as baselinefd:
        source = startup_registry(fd)
        baseline = startup_registry(baselinefd)
        findings = [key for key, values in source.items() if values - baseline.get(key, set())]
        for root, dirs, files, current in os.fwalk(".", dir_fd=fd, follow_symlinks=False, onerror=walk_error):
            relative = str(Path(root)).lower()
            if relative.endswith("/startup") and (files or dirs):
                findings.append("Non-empty Startup folder: " + str(root))
            # Never let a user-configured external Startup folder escape this check.
            for name in dirs + files:
                if name.lower() == "startup":
                    info = os.stat(name, dir_fd=current, follow_symlinks=False)
                    if stat.S_ISLNK(info.st_mode):
                        findings.append("Linked Startup folder: " + str(Path(root) / name))
        try:
            winini = regular_bytes(fd, "drive_c/windows/win.ini", 1024 * 1024, complete=True).decode(errors="replace")
        except FileNotFoundError:
            winini = ""
        if re.search(r"(?mi)^\s*(?:run|load)\s*=\s*\S", winini):
            findings.append("win.ini has a Run/Load command")
    return findings


def refuse_autostart(work, clean):
    hazards = execution_hazards(work, clean)
    if hazards:
        raise ValueError("Unknown autostart/service entries differ from fresh Wine; no Wine action is allowed on this copy. Review manually: " + "; ".join(hazards[:20]))


def run_wine(session, target, command, label, timeout=180):
    normal_user()
    paths = session_paths(session)
    if target != paths["clean"]:
        refuse_autostart(target, paths["clean"])
    args, env = sandbox_command(session, target, command)
    logdir, fd = private_directory(("Logs", "Wine-Prefix-Repair"), create=True)
    name = session["id"] + "-" + label + "-" + uuid.uuid4().hex[:8] + ".log"
    logfd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    os.close(fd)
    code = None
    output = bytearray()
    truncated = False
    process = None
    try:
        process = subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        limit = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while selector.get_map():
                if time.monotonic() > limit:
                    raise TimeoutError("Wine action timed out; the original prefix is unchanged.")
                for key, _ in selector.select(.2):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        capacity = 8 * 1024 * 1024 - len(output)
                        if len(chunk) > capacity:
                            truncated = True
                        if capacity:
                            chunk = chunk[:capacity]
                            os.write(logfd, chunk)
                            output.extend(chunk)
        code = process.wait(timeout=5)
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        os.close(logfd)
    findings = classify_output(output.decode(errors="replace"), code)
    findings["log_truncated"] = truncated
    findings["fatal"] = findings["fatal"] or truncated
    journal(session, label, command=command, code=code, log=str(logdir / name), findings=findings)
    if findings["fatal"]:
        raise ValueError(f"{label} failed (status {code}). Review {logdir / name}. Driver warnings alone do not prove a prefix failure.")
    return findings


def wine_tools():
    result = {}
    for name in ("wine", "wineboot", "winecfg", "wineserver"):
        found = shutil.which(name, path="/usr/bin:/bin")
        if not found or proton_reference(str(Path(found).resolve())):
            raise ValueError("System Wine tools are required; missing or Proton-linked: " + name)
        result[name] = found
    bwrap = shutil.which("bwrap", path="/usr/bin:/bin")
    if not bwrap:
        raise ValueError("bubblewrap is required for isolated Wine execution; no unsandboxed fallback is allowed.")
    try:
        probe = subprocess.run([bwrap, "--die-with-parent", "--unshare-pid", "--unshare-net", "--unshare-ipc",
                                "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--", "/bin/true"],
                               env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"}, capture_output=True,
                               text=True, timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Bubblewrap isolation could not be verified: " + str(exc)) from exc
    if probe.returncode:
        raise ValueError("Bubblewrap namespaces are blocked; no Wine is run and no prefix copy is prepared. " + safe_text(probe.stderr).strip())
    return result


def tools_signature(tools):
    result = {}
    for name, value in tools.items():
        path = Path(value).resolve(strict=True)
        info = path.stat()
        result[name] = [str(path), info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]
    return result


def unchanged_wine(session):
    tools = wine_tools()
    if tools != session["wine_tools"] or tools_signature(tools) != session["wine_signature"]:
        raise ValueError("The installed Wine changed since preparation; create a new repair session.")


def pe_machine(fd):
    if os.pread(fd, 2, 0) != b"MZ":
        return None
    raw = os.pread(fd, 4, 0x3c)
    if len(raw) != 4:
        return None
    offset = struct.unpack("<I", raw)[0]
    if offset > 16 * 1024 * 1024:
        return None
    header = os.pread(fd, 6, offset)
    return struct.unpack("<H", header[4:])[0] if len(header) == 6 and header[:4] == b"PE\0\0" else None


def replace_broken(work, clean, items, arch, on_change):
    changed, skipped = [], []
    with directory(work) as wfd, directory(clean) as cfd:
        if architecture(cfd) != arch:
            raise ValueError("Fresh prefix architecture does not match the original; no replacements performed.")
        for item in items:
            relative = item["path"]
            if not relative.startswith("drive_c/windows/"):
                continue
            try:
                with relative_parent(wfd, relative) as (dst, leaf), relative_parent(cfd, relative) as (src, donor):
                    current = os.stat(leaf, dir_fd=dst, follow_symlinks=False)
                    if not stat.S_ISLNK(current.st_mode) or os.readlink(leaf, dir_fd=dst) != item["target"]:
                        raise ValueError("The candidate is no longer the diagnosed link.")
                    try:
                        os.stat(leaf, dir_fd=dst)
                    except FileNotFoundError:
                        pass
                    else:
                        raise ValueError("The candidate is no longer broken.")
                    donorfd = os.open(donor, FILE_FLAGS, dir_fd=src)
                    temporary = ".kenoforge-repair-" + uuid.uuid4().hex
                    try:
                        info = os.fstat(donorfd)
                        if not stat.S_ISREG(info.st_mode):
                            raise ValueError("No regular donor file at the same relative path.")
                        if Path(relative).suffix.lower() in (".dll", ".exe", ".sys"):
                            expected = 0x14c if arch == "win32" or "/syswow64/" in relative.lower() else 0x8664
                            if pe_machine(donorfd) != expected:
                                raise ValueError("Donor PE architecture is unknown or mismatched.")
                        out = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dst)
                        try:
                            while chunk := os.read(donorfd, 1024 * 1024):
                                view = memoryview(chunk)
                                while view:
                                    view = view[os.write(out, view):]
                            copy_metadata(donorfd, out, info)
                            os.fsync(out)
                        finally:
                            os.close(out)
                        # Recheck the symlink immediately before replacing the link itself.
                        now = os.stat(leaf, dir_fd=dst, follow_symlinks=False)
                        if (now.st_dev, now.st_ino, now.st_mtime_ns) != (current.st_dev, current.st_ino, current.st_mtime_ns):
                            raise ValueError("Link changed during repair.")
                        on_change("replace-intent", path=relative, old_target=item["target"])
                        os.replace(temporary, leaf, src_dir_fd=dst, dst_dir_fd=dst)
                        os.fsync(dst)
                        changed.append(relative)
                        on_change("replaced-link", path=relative)
                    finally:
                        os.close(donorfd)
                        try:
                            os.unlink(temporary, dir_fd=dst)
                        except FileNotFoundError:
                            pass
            except (OSError, ValueError) as exc:
                skipped.append({"path": relative, "reason": str(exc)})
    return changed, skipped


def prepare(value):
    normal_user()
    source = check_prefix(value)
    with prefix_lock(source):
        report = diagnose(source, system=False)
        if not report["repair_scenario"]:
            raise ValueError("Diagnosis did not confirm the supported broken-Windows-link scenario. No repair started.")
        require_idle(source)
        tools = wine_tools()
        fingerprint, size = tree_hash(source)
        required = 3 * size + 512 * 1024 * 1024
        if shutil.disk_usage(source.parent).free < required:
            raise ValueError(f"Insufficient free space: reserve at least {required} bytes for backup, work and fresh prefix.")
        session = {"format": 1, "id": uuid.uuid4().hex, "source": str(source), "phase": "creating",
                   "architecture": report["architecture"], "source_hash": fingerprint,
                   "original_identity": identity(source), "wine_tools": tools,
                   "wine_signature": tools_signature(tools), "created_at": utc_now()}
        paths = session_paths(session)
        with directory(source.parent) as fd:
            os.mkdir(paths["stage"].name, 0o700, dir_fd=fd)
        journal(session, "created", bytes=size, required_free=required, diagnosis=report)
        try:
            print("Creating verified prefix backup...", flush=True)
            copy_tree(source, paths["backup"])
            if tree_hash(paths["backup"])[0] != fingerprint or tree_hash(source)[0] != fingerprint:
                raise ValueError("Prefix changed during backup; partial copies were retained, never activated.")
            require_idle(source)
            journal(session, "backup-verified", path=str(paths["backup"]))
            print("Creating isolated working copy...", flush=True)
            copy_tree(paths["backup"], paths["work"])
            paths["clean"].mkdir(mode=0o700)
            paths["home"].mkdir(mode=0o700)
            for name in ("runtime", "config", "cache"):
                (paths["home"] / name).mkdir(mode=0o700)
            session["work_identity"] = identity(paths["work"])
            journal(session, "copies-ready")
            print("Creating a clean prefix with the installed Wine (sandboxed)...", flush=True)
            run_wine(session, paths["clean"], [tools["wineboot"], "-i"], "fresh-prefix")
            changes, skipped = replace_broken(paths["work"], paths["clean"], report["broken_links"],
                                              session["architecture"], lambda event, **data: journal(session, event, **data))
            session["changes"], session["skipped"] = changes, skipped
            if not changes:
                raise ValueError("No safe regular equivalents were found. Original and backups were preserved.")
            before_update = content_inventory(paths["work"])
            refuse_autostart(paths["work"], paths["clean"])
            run_wine(session, paths["work"], [tools["wineboot"], "-u"], "update-work")
            after_update = content_inventory(paths["work"])
            delta = [name for name in sorted(set(before_update) | set(after_update))
                     if before_update.get(name) != after_update.get(name)]
            journal(session, "wineboot-file-changes", paths=delta)
            allowed = {"system.reg", "user.reg", "userdef.reg", ".update-timestamp"}
            protected = [name for name in delta if name in before_update and name not in allowed]
            if protected:
                session["protected_changes"] = protected
                raise ValueError("wineboot changed pre-existing files or valid links beyond registry/update metadata. Activation blocked; inspect the retained working copy and journal.")
            result = diagnose(paths["work"], system=False)
            session["validation"] = result
            if result["essential_problems"] or not result["complete"]:
                raise ValueError("Essential components are still unhealthy after repair; activation is blocked.")
            session["phase"] = "prepared"
            journal(session, "prepared", remaining_links=result["broken_links"])
        except BaseException as exc:
            session["phase"] = "failed"
            journal(session, "failed", detail=str(exc))
            raise
        return session


def validate_session(session, executable=None):
    normal_user()
    paths = session_paths(session)
    if session["phase"] not in ("prepared", "tested"):
        raise ValueError("Only a prepared working copy can be tested.")
    with prefix_lock(paths["source"]):
        require_idle(paths["source"], paths["work"])
        check_prefix(paths["work"])
        unchanged_wine(session)
        refuse_autostart(paths["work"], paths["clean"])
        result = diagnose(paths["work"], system=False)
        if result["essential_problems"] or not result["complete"]:
            raise ValueError("Working prefix essentials are not healthy.")
        session["phase"] = "prepared"
        journal(session, "validation-intent", executable=executable)
        if executable:
            app = Path(os.path.abspath(os.path.expanduser(executable)))
            with directory(app.parent) as fd:
                raw = regular_bytes(fd, app.name, 2)
            if raw != b"MZ":
                raise ValueError("The selected file is not a Windows executable (MZ signature missing).")
            run_wine(session, paths["work"], [session["wine_tools"]["wine"], str(app)], "selected-app", timeout=900)
        else:
            run_wine(session, paths["work"], [session["wine_tools"]["winecfg"]], "winecfg", timeout=900)
            session["winecfg_completed"] = True
        result = diagnose(paths["work"], system=False)
        session["validation"] = result
        if result["essential_problems"] or not result["complete"]:
            journal(session, "validation-failed", detail="Essential components failed after the test.")
            raise ValueError("The working copy failed its post-test integrity check.")
        session["phase"] = "tested"
        journal(session, "validation-completed", executable=str(executable) if executable else "winecfg")


def rename_noreplace(source, destination):
    """Linux atomic no-clobber rename, including recovery paths."""
    libc = ctypes.CDLL(None, use_errno=True)
    operation = getattr(libc, "renameat2", None)
    if operation is None:
        raise ValueError("Atomic no-clobber rename is unavailable on this platform.")
    operation.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    operation.restype = ctypes.c_int
    with directory(source.parent) as srcfd, directory(destination.parent) as dstfd:
        info = os.stat(source.name, dir_fd=srcfd, follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("Only real prefix directories can be renamed.")
        if operation(srcfd, os.fsencode(source.name), dstfd, os.fsencode(destination.name), 1):
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code), str(destination))
        os.fsync(srcfd)
        os.fsync(dstfd)


def activate(session, confirmed=False):
    normal_user()
    if not confirmed:
        raise ValueError("Explicit activation confirmation is required.")
    paths = session_paths(session)
    with prefix_lock(paths["source"]):
        if session["phase"] != "tested" or not session.get("winecfg_completed"):
            raise ValueError("Run winecfg and confirm the working copy before activation.")
        unchanged_wine(session)
        for key in ("source", "work"):
            check_prefix(paths[key])
        require_idle(paths["source"], paths["work"])
        if identity(paths["source"]) != session["original_identity"] or identity(paths["work"]) != session["work_identity"]:
            raise ValueError("Prefix directory identity changed; activation refused.")
        if tree_hash(paths["source"])[0] != session["source_hash"] or tree_hash(paths["backup"])[0] != session["source_hash"]:
            raise ValueError("Original or backup changed since repair. Create a new repair session.")
        report = diagnose(paths["work"], system=False)
        if report["essential_problems"] or not report["complete"]:
            raise ValueError("Working prefix failed final integrity checks.")
        require_idle(paths["source"], paths["work"])
        if identity(paths["source"])[0] != identity(paths["work"])[0]:
            raise ValueError("Activation requires the same filesystem. No cross-device copying is attempted.")
        session["phase"] = "activating"
        journal(session, "activation-intent", original_backup=str(paths["original"]))
        moved = False
        try:
            rename_noreplace(paths["source"], paths["original"])
            moved = True
            rename_noreplace(paths["work"], paths["source"])
            if identity(paths["source"]) != session["work_identity"]:
                raise ValueError("Activation directory verification failed.")
            session["phase"] = "active"
            journal(session, "activated")
        except BaseException:
            # Never overwrite a path that may have appeared concurrently.
            if moved and not os.path.lexists(paths["source"]):
                try:
                    rename_noreplace(paths["original"], paths["source"])
                    session["phase"] = "tested"
                    journal(session, "activation-recovered")
                except BaseException:
                    pass  # Intent receipt plus retained directories enable explicit recovery.
            raise
    return session


def rollback(session, confirmed=False):
    normal_user()
    if not confirmed:
        raise ValueError("Explicit rollback confirmation is required.")
    paths = session_paths(session)
    with prefix_lock(paths["source"]):
        if session["phase"] not in ("active", "activating", "rolling-back"):
            raise ValueError("This session has no active prefix to roll back.")
        require_idle(paths["source"], paths["original"])
        if (not os.path.lexists(paths["original"]) and os.path.lexists(paths["source"])
                and identity(paths["source"]) == session["original_identity"]):
            session["phase"] = "rolled-back"
            journal(session, "previous-recovery-confirmed")
            return session
        if identity(paths["original"]) != session["original_identity"]:
            raise ValueError("The preserved original does not match the activation receipt.")
        if tree_hash(paths["original"])[0] != session["source_hash"]:
            raise ValueError("The preserved original was modified; review it before rollback.")
        # Recovery after interruption between the two activation renames.
        if not os.path.lexists(paths["source"]):
            rename_noreplace(paths["original"], paths["source"])
            session["phase"] = "rolled-back"
            journal(session, "interrupted-activation-recovered")
            return session
        if identity(paths["source"]) != session["work_identity"]:
            raise ValueError("The active directory changed identity; no automatic replacement is allowed.")
        check_prefix(paths["source"])
        saved = paths["source"].parent / (paths["source"].name + ".kenoforge-repaired-" + uuid.uuid4().hex)
        session["phase"] = "rolling-back"
        session["retained_repaired"] = str(saved)
        journal(session, "rollback-intent")
        rename_noreplace(paths["source"], saved)
        try:
            rename_noreplace(paths["original"], paths["source"])
        except BaseException:
            if not os.path.lexists(paths["source"]):
                try:
                    rename_noreplace(saved, paths["source"])
                    session["phase"] = "active"
                    journal(session, "rollback-recovered")
                except BaseException:
                    pass
            raise
        session["phase"] = "rolled-back"
        journal(session, "rolled-back", retained_repaired=str(saved))
    return session


def watch_prefix(value, enabled):
    normal_user()
    prefix = check_prefix(value)
    state = watched_state()
    entries = [x for x in state["prefixes"] if x["prefix"] != str(prefix)]
    if enabled:
        if len(entries) >= 16:
            raise ValueError("At most 16 prefixes can be watched.")
        with directory(prefix) as fd:
            arch = architecture(fd)
            signature = essentials(fd, arch)
        entries.append({"prefix": str(prefix), "architecture": arch, "signature": signature})
    _write_json("wine-prefix-watch.json", {"format": 1, "prefixes": entries}, WATCH_PARTS)


def guard_watched(changed):
    """Only a few essential lstat/stat checks, never Wine execution or full scans."""
    state = watched_state()
    relevant = any(re.match(r"^(wine|proton|steam)(-|$)", name) for name in changed)
    created = []
    for entry in state["prefixes"][:16]:
        prefix = prefix_path(entry["prefix"])
        task = "wine-prefix-" + hashlib.sha256(str(prefix).encode()).hexdigest()[:16]
        try:
            with directory(prefix) as fd:
                current = essentials(fd, architecture(fd))
            bad = [name for name, value in current.items() if value["state"] not in ("regular", "valid-link")]
            if bad:
                trigger = "Wine/Proton/Steam package change" if relevant else "Lightweight integrity check"
                upsert_task(task, "Review Wine prefix integrity", f"{trigger}: {prefix}: unhealthy essentials: {', '.join(bad)}. Open Wine Prefix Repair; no repair was run.", "warning", "Wine Prefix Watch")
                created.append(task)
            elif not bad:
                resolve_task(task)
        except (OSError, ValueError) as exc:
            upsert_task(task, "Inspect unavailable Wine prefix", f"{prefix}: {exc}. No repair was run.", "warning", "Wine Prefix Watch")
            created.append(task)
    return created


def watched_state():
    state = read_state("wine-prefix-watch.json", WATCH_PARTS, {"format": 1, "prefixes": []})
    if not isinstance(state, dict) or state.get("format") != 1 or not isinstance(state.get("prefixes"), list):
        raise ValueError("Invalid opt-in Wine watch configuration.")
    for item in state["prefixes"]:
        if (not isinstance(item, dict) or not isinstance(item.get("prefix"), str)
                or not isinstance(item.get("signature"), dict)):
            raise ValueError("Invalid prefix in Wine watch configuration.")
    return state


def mime_default(mime):
    result = query(["gio", "mime", mime])
    match = re.search(r"(?m)^Default application for .+?:\s*([^\s]+\.desktop)\s*$", result["text"])
    return match.group(1) if result["code"] == 0 and match else None


def set_wine_mime(confirmed=False):
    normal_user()
    if not confirmed:
        raise ValueError("Explicit MIME confirmation is required.")
    if not shutil.which("gio"):
        raise ValueError("gio is unavailable (Arch package: glib2).")
    applications = [Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "applications"]
    applications += [Path(part) / "applications" for part in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if part]
    if not any((root / "wine.desktop").is_file() for root in applications):
        raise ValueError("wine.desktop is not installed. No launcher will be created or overwritten.")
    previous = {mime: mime_default(mime) for mime in MIMES}
    if any(not value for value in previous.values()):
        raise ValueError("Previous MIME defaults could not be determined. Automatic change refused to keep rollback reliable.")
    sid = uuid.uuid4().hex
    receipt = {"id": sid, "previous": previous, "applied": "wine.desktop", "phase": "applying", "at": utc_now()}
    _write_json(sid + ".json", receipt, ("Installer-Backups", "Wine-MIME"))
    for mime in MIMES:
        result = query(["gio", "mime", mime, "wine.desktop"])
        if result["code"] != 0 or mime_default(mime) != "wine.desktop":
            raise ValueError("MIME update incomplete. Retained receipt: " + sid + "; use MIME rollback.")
    receipt["phase"] = "applied"
    _write_json(sid + ".json", receipt, ("Installer-Backups", "Wine-MIME"))
    return sid


def rollback_mime(sid, confirmed=False):
    normal_user()
    if not confirmed or not re.fullmatch(r"[a-f0-9]{32}", sid):
        raise ValueError("Valid MIME receipt ID and explicit confirmation required.")
    receipt = read_state(sid + ".json", ("Installer-Backups", "Wine-MIME"))
    if not receipt or receipt.get("phase") not in ("applying", "applied"):
        raise ValueError("MIME receipt unavailable or already restored.")
    for mime in MIMES:
        old = receipt["previous"].get(mime)
        if not isinstance(old, str) or not re.fullmatch(r"[\w.\-]+\.desktop", old):
            raise ValueError("Invalid previous desktop ID in MIME receipt.")
        current = mime_default(mime)
        if current not in ("wine.desktop", old):
            raise ValueError("MIME default changed after this patch; refusing to overwrite a newer preference.")
    for mime in MIMES:
        old = receipt["previous"][mime]
        if query(["gio", "mime", mime, old])["code"] != 0 or mime_default(mime) != old:
            raise ValueError("MIME restore incomplete; the receipt is retained for retry.")
    receipt["phase"] = "restored"
    _write_json(sid + ".json", receipt, ("Installer-Backups", "Wine-MIME"))
