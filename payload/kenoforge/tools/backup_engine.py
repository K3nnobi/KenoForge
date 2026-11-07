#!/usr/bin/env python3
"""Shared backup format, safe extraction, copying and portable recovery data.

No Wine executable, package manager or system service is executed here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import uuid
from contextlib import contextmanager

FORMAT = 3
META = {'inventory.json', 'checksums.sha256'}
LAUNCHERS = ('kenoforge', 'kenoforge-console', 'kenoforge-monitor', 'kenoforge-music')
FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def file_hash(stream):
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(block)
    return digest.hexdigest()


def name(value):
    if not value or value.startswith('/') or '\\' in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Unsafe backup path: ' + repr(value))
    parts = PurePosixPath(value).parts
    if '..' in parts:
        raise ValueError('Parent traversal refused: ' + value)
    return str(PurePosixPath(value))


@contextmanager
def directory(path, create=False):
    """Open every ancestor without following symlinks, including outside Home."""
    path = Path(os.path.abspath(path))
    fd = os.open('/', FLAGS)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            nxt = os.open(part, FLAGS, dir_fd=fd)
            os.close(fd)
            fd = nxt
        yield fd
    finally:
        os.close(fd)


def read_json(path):
    with directory(Path(path).parent) as fd:
        stream = os.open(Path(path).name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
        with os.fdopen(stream, 'r', encoding='utf-8') as f:
            if not stat.S_ISREG(os.fstat(f.fileno()).st_mode) or os.fstat(f.fileno()).st_size > 64 * 1024 * 1024:
                raise ValueError('Invalid metadata: ' + str(path))
            return json.load(f)


def write_json(path, data):
    atomic_bytes(path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode())


def atomic_bytes(path, data, mode=0o600):
    path = Path(path)
    with directory(path.parent, True) as fd:
        tmp = '.backup-' + uuid.uuid4().hex
        out = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode, dir_fd=fd)
        try:
            with os.fdopen(out, 'wb') as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path.name, src_dir_fd=fd, dst_dir_fd=fd)
            os.fsync(fd)
        finally:
            try:
                os.unlink(tmp, dir_fd=fd)
            except FileNotFoundError:
                pass


def _copy(srcfd, srcname, dstfd, dstname):
    st = os.stat(srcname, dir_fd=srcfd, follow_symlinks=False)
    try:
        old = os.stat(dstname, dir_fd=dstfd, follow_symlinks=False)
    except FileNotFoundError:
        old = None
    # An identical literal link needs no write; conflicting redirects are refused.
    if old and stat.S_ISLNK(old.st_mode) and stat.S_ISLNK(st.st_mode) and os.readlink(srcname, dir_fd=srcfd) == os.readlink(dstname, dir_fd=dstfd):
        return
    if old and (stat.S_ISLNK(old.st_mode) or stat.S_ISDIR(old.st_mode) != stat.S_ISDIR(st.st_mode)):
        raise ValueError('Unsafe/conflicting restore destination: ' + dstname)
    if stat.S_ISDIR(st.st_mode):
        if old is None:
            os.mkdir(dstname, 0o700, dir_fd=dstfd)
        a = os.open(srcname, FLAGS, dir_fd=srcfd)
        b = os.open(dstname, FLAGS, dir_fd=dstfd)
        try:
            for child in sorted(os.listdir(a)):
                _copy(a, child, b, child)
            # Do not change an existing directory's permissions during a merge.
            if old is None:
                os.fchmod(b, stat.S_IMODE(st.st_mode) & 0o777)
                os.utime(b, ns=(st.st_atime_ns, st.st_mtime_ns))
        finally:
            os.close(a)
            os.close(b)
    elif stat.S_ISLNK(st.st_mode):
        os.symlink(os.readlink(srcname, dir_fd=srcfd), dstname, dir_fd=dstfd)
    elif stat.S_ISREG(st.st_mode):
        inp = os.open(srcname, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=srcfd)
        tmp = '.backup-' + uuid.uuid4().hex
        out = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=dstfd)
        try:
            with os.fdopen(inp, 'rb') as i, os.fdopen(out, 'wb') as o:
                shutil.copyfileobj(i, o)
                os.fchmod(o.fileno(), stat.S_IMODE(st.st_mode) & 0o777)
                os.utime(o.fileno(), ns=(st.st_atime_ns, st.st_mtime_ns))
                o.flush()
                os.fsync(o.fileno())
            os.replace(tmp, dstname, src_dir_fd=dstfd, dst_dir_fd=dstfd)
        finally:
            try:
                os.unlink(tmp, dir_fd=dstfd)
            except FileNotFoundError:
                pass
    elif not stat.S_ISSOCK(st.st_mode):
        raise ValueError('Unsupported special file: ' + srcname)


def copy(src, dst, home_only=False):
    src, dst = Path(src), Path(os.path.abspath(dst))
    if home_only:
        dst.relative_to(Path(os.path.abspath(Path.home())))
    with directory(src.parent) as a, directory(dst.parent, True) as b:
        _copy(a, src.name, b, dst.name)


def entries(root):
    result = {}
    def visit(base, rel=''):
        for item in sorted(base.iterdir()):
            key = name((PurePosixPath(rel) / item.name).as_posix())
            st = item.lstat()
            mode = stat.S_IMODE(st.st_mode)
            if item.is_symlink():
                result[key] = {'type': 'link', 'target': os.readlink(item), 'mode': mode}
            elif stat.S_ISDIR(st.st_mode):
                result[key] = {'type': 'directory', 'mode': mode}
                visit(item, key)
            elif stat.S_ISREG(st.st_mode):
                with item.open('rb') as f:
                    digest = file_hash(f)
                result[key] = {'type': 'file', 'size': st.st_size, 'sha256': digest, 'mode': mode}
            else:
                raise ValueError('Unsupported backup object: ' + key)
    with directory(root):
        visit(Path(root))
    return result


def manifest(root):
    root = Path(root)
    if (root / 'manifest.json').exists():
        data = read_json(root / 'manifest.json')
        if not isinstance(data, dict):
            raise ValueError('Invalid manifest')
        return data
    path = root / 'manifest.txt'
    if path.is_symlink() or not path.is_file():
        raise ValueError('Missing manifest')
    data = {}
    for line in path.read_text().splitlines():
        sep = '=' if '=' in line else ':'
        if sep in line:
            k, v = line.split(sep, 1)
            data[k.strip()] = v.strip()
    return data


def seal(root):
    root = Path(root)
    data = manifest(root)
    data.update(format='kenoforge', format_version=FORMAT, source_home=str(Path.home()),
                source_data=str(Path.home() / '.kenoforge'))
    build = Path(__file__).parent.parent / 'BUILD-ID'
    data['build_id'] = build.read_text().strip() if build.is_file() else 'unknown'
    data['scope'] = {
        'included': [x for x in ('configs', 'gnome', 'packages', 'project', 'toolkit', 'maintenance', 'recovery') if (root / x).is_dir()],
        'excluded': ['active Wine/Steam prefixes', 'personal music/audio/video files', 'regenerable cover caches', 'full operating system image'],
        'wine_recovery': 'Managed recovery snapshots only; original receipts are offline evidence, never imported as active rollback identities.'}
    write_json(root / 'manifest.json', data)
    listing = {k: v for k, v in entries(root).items() if k not in META}
    write_json(root / 'inventory.json', {'format': FORMAT, 'entries': listing})
    # Keep a complete regular-file catalog for older inspection tools.
    listing = entries(root)
    atomic_bytes(root / 'checksums.sha256', ''.join(v['sha256'] + '  ' + k + '\n' for k, v in listing.items() if v['type'] == 'file' and k != 'checksums.sha256').encode())


def verify(root):
    root = Path(root)
    data = manifest(root)
    actual = entries(root)
    for key in ('configs/.zshrc', 'configs/kenoforge-config/Zsh/aliases.zsh', 'configs/kenoforge-config/Zsh/p10k.zsh'):
        if key in actual and actual[key]['type'] != 'file':
            raise ValueError('Executable shell configuration must be a regular file: ' + key)
    for component in ('configs', 'gnome', 'packages', 'project', 'toolkit', 'maintenance', 'recovery'):
        if component in actual and actual[component]['type'] != 'directory':
            raise ValueError('Invalid component: ' + component)
    if data.get('format_version') == FORMAT:
        catalog = read_json(root / 'inventory.json')
        expected = catalog.get('entries') if isinstance(catalog, dict) and catalog.get('format') == FORMAT else None
        if expected != {k: v for k, v in actual.items() if k not in META}:
            raise ValueError('Backup inventory mismatch (content, links, permissions or coverage).')
    elif data.get('format_version') is not None:
        raise ValueError('Unsupported backup format version')
    checksum = root / 'checksums.sha256'
    if checksum.is_symlink() or not checksum.is_file():
        raise ValueError('Missing checksums')
    covered = set()
    for line in checksum.read_text().splitlines():
        match = re.fullmatch(r'([a-fA-F0-9]{64}) [ *](.+)', line)
        if not match:
            raise ValueError('Invalid checksum entry')
        key = name(match[2])
        if key in covered or key not in actual or actual[key]['type'] != 'file' or actual[key]['sha256'].lower() != match[1].lower():
            raise ValueError('Checksum mismatch: ' + key)
        covered.add(key)
    regular = {k for k, v in actual.items() if v['type'] == 'file' and k != 'checksums.sha256'}
    if covered != regular:
        raise ValueError('Incomplete checksum coverage')
    if data.get('format_version') != FORMAT:
        print('Legacy backup: link targets were not recorded; runtime code will be recovered separately.', file=sys.stderr)
    return data


def free_space(destination, size):
    with directory(destination):
        if shutil.disk_usage(destination).free < size + max(16 * 1024 * 1024, size // 20):
            raise ValueError('Insufficient free space for backup/recovery')


def pack(root, destination):
    seal(root)
    verify(root)
    destination = Path(destination)
    with directory(destination.parent, True):
        free_space(destination.parent, sum(x.get('size', 0) for x in entries(root).values()))
        fd, tmp = tempfile.mkstemp(prefix='.kenoforge-', dir=destination.parent)
        os.close(fd)
        published = False
        try:
            with tarfile.open(tmp, 'w:gz', dereference=False) as archive:
                archive.add(root, arcname='.', recursive=True)
            # Validate the completed bytes before exposing the definitive filename.
            with tempfile.TemporaryDirectory(prefix='kenoforge-check-') as check:
                extract(tmp, check, check_sidecar=False)
                verify(check)
            with open(tmp, 'rb') as f:
                digest = file_hash(f)
                os.fsync(f.fileno())
            sidecar = Path(str(destination) + '.sha256')
            if sidecar.exists() or sidecar.is_symlink():
                raise FileExistsError(str(sidecar))
            os.link(tmp, destination)  # atomic no-clobber publication, even under concurrency
            published = True
            # Exclusive sidecar avoids replacing an older backup's metadata.
            with sidecar.open('x') as f:
                f.write(digest + '  ' + destination.name + '\n')
                f.flush()
                os.fsync(f.fileno())
            with directory(destination.parent) as d:
                os.fsync(d)
        except Exception:
            # If publication succeeded, retain a valid archive even if its sidecar failed.
            if published:
                print('Archive retained at ' + str(destination), file=sys.stderr)
            raise
        finally:
            os.unlink(tmp)


def extract(source, destination, check_sidecar=True):
    destination = Path(destination)
    with directory(destination):
        if any(destination.iterdir()):
            raise ValueError('Extraction requires an empty private directory')
        if check_sidecar:
            side = Path(str(source) + '.sha256')
            if side.exists() or side.is_symlink():
                if side.is_symlink() or not side.is_file():
                    raise ValueError('Unsafe outer checksum')
                expected = side.read_text().split()[0]
                with open(source, 'rb') as f:
                    if file_hash(f) != expected:
                        raise ValueError('Outer archive checksum mismatch')
        with tarfile.open(source, 'r:*') as archive:
            members = {}
            for member in archive.getmembers():
                key = name(member.name)
                if key == '.':
                    if not member.isdir():
                        raise ValueError('Invalid archive root')
                    continue
                if key in members or not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                    raise ValueError('Duplicate/unsupported member: ' + key)
                members[key] = member
            for key, member in members.items():
                for parent in PurePosixPath(key).parents:
                    ancestor = members.get(str(parent))
                    if ancestor and not ancestor.isdir():
                        raise ValueError('Archive member below a link/file: ' + key)
                if member.islnk():
                    target = members.get(name(member.linkname))
                    if target is None or not target.isfile():
                        raise ValueError('Unsafe hardlink: ' + key)
            free_space(destination, sum(m.size for m in members.values()))
            # Files first, then inert symbolic links. Never use tar.extractall.
            for key, member in sorted(members.items(), key=lambda x: (len(PurePosixPath(x[0]).parts), x[0])):
                target = destination / key
                with directory(target.parent, True):
                    if member.isdir():
                        target.mkdir(exist_ok=True, mode=0o700)
                    elif member.issym():
                        os.symlink(member.linkname, target)
                    else:
                        origin = members[name(member.linkname)] if member.islnk() else member
                        with archive.extractfile(origin) as inp, target.open('xb') as out:
                            shutil.copyfileobj(inp, out)
                        target.chmod(member.mode & 0o777)
                        os.utime(target, (member.mtime, member.mtime))
            for key, member in sorted(members.items(), key=lambda x: -len(PurePosixPath(x[0]).parts)):
                if member.isdir():
                    (destination / key).chmod(member.mode & 0o777)


def capture_extra(root):
    root, home = Path(root), Path.home()
    data = home / '.kenoforge'
    mappings = [('State/Maintenance', 'maintenance/state'), ('Logs', 'maintenance/logs'),
                ('Backups/Safety/firefox-chatgpt-emoji', 'recovery/receipts/firefox-chatgpt-emoji')]
    receipts = data / 'Installer-Backups'
    if receipts.exists():
        with directory(receipts):
            for item in receipts.iterdir():
                if (item.is_file() and not item.is_symlink()) or item.name in {'Wine-Prefix-Repair', 'Wine-MIME', 'Wine', 'Plymouth', 'NVIDIA-Vibrance', 'GNOME-Drag-Hover', 'Caps-Lock-No-Delay', 'firefox-chatgpt-emoji'}:
                    mappings.append(('Installer-Backups/' + item.name, 'recovery/receipts/' + item.name))
    for src, dst in mappings:
        path = data / src
        if path.exists() or path.is_symlink():
            if path.is_symlink():
                raise ValueError('Linked managed recovery/state directory refused: ' + str(path))
            size = sum(x.get('size', 0) for x in entries(path).values()) if path.is_dir() else path.stat().st_size
            free_space(root, size)
            copy(path, root / dst)
    # Locks are process-local and must never be imported as maintenance state.
    state = root / 'maintenance/state'
    if state.is_dir() and not state.is_symlink():
        for lock in state.glob('*.lock'):
            lock.unlink()
    units = root / 'configs/.config/systemd/user'
    if units.is_dir() and not units.is_symlink():
        for relative in ('kenoforge-patch-persistence.service', 'kenoforge-patch-persistence.timer', 'timers.target.wants/kenoforge-patch-persistence.timer'):
            unit = units / relative
            with directory(unit.parent, True):
                if os.path.lexists(unit):
                    unit.unlink()
    snapshots = []
    sessions = receipts / 'Wine-Prefix-Repair'
    if sessions.exists():
        with directory(sessions):
            # Session receipts live in <sid>/session.json.
            for receipt in sorted(sessions.glob('*/session.json')):
                session = read_json(receipt)
                sid = session.get('id', session.get('session_id', receipt.stem))
                source = session.get('source', '')
                if not isinstance(sid, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', sid):
                    raise ValueError('Unsafe Wine session id')
                prefix = Path(os.path.abspath(source))
                if str(prefix) != source:
                    raise ValueError("Noncanonical Wine receipt path")
                if not prefix.is_absolute():
                    raise ValueError('Invalid Wine receipt source')
                prefix.relative_to(home)
                from wine_prefix import steam_managed
                if steam_managed(prefix):
                    raise ValueError('Steam-managed recovery requires a specific export flow')
                stage = prefix.parent / ('.' + prefix.name + '.kenoforge-repair-' + sid)
                candidates = [stage / 'backup', stage / 'work', prefix.parent / (prefix.name + '.kenoforge-original-' + sid)]
                retained = session.get('retained_repaired')
                if retained:
                    candidate = Path(os.path.abspath(retained))
                    candidate.relative_to(home)
                    if not candidate.name.startswith(prefix.name + '.kenoforge-'):
                        raise ValueError('Unexpected retained Wine path')
                    candidates.append(candidate)
                for n, candidate in enumerate(candidates):
                    if not candidate.exists() and not candidate.is_symlink():
                        continue
                    with directory(candidate):
                        # Imported lazily; this check never launches Wine.
                        from wine_prefix import require_idle
                        require_idle(candidate)
                        before = entries(candidate)
                        size = sum(x.get('size', 0) for x in before.values())
                        free_space(root, size)
                        relative = 'recovery/prefixes/' + sid + '/' + str(n)
                        copy(candidate, root / relative)
                        require_idle(candidate)
                        if before != entries(candidate) or before != entries(root / relative):
                            raise ValueError('Wine recovery data changed during capture; close Wine and retry')
                        snapshots.append({'session': sid, 'source': str(candidate), 'snapshot': relative, 'inventory': before})
    write_json(root / 'recovery/index.json', {'format': 1, 'snapshots': snapshots,
        'note': 'Offline copies. Old device/inode activation receipts are not valid after migration.'})


def rebase(value, old, new):
    if isinstance(value, dict):
        return {k: rebase(v, old, new) for k, v in value.items()}
    if isinstance(value, list):
        return [rebase(v, old, new) for v in value]
    if isinstance(value, str) and old and (value == old or value.startswith(old + '/')):
        return new + value[len(old):]
    return value


def restore_extra(root):
    root, home = Path(root), Path.home()
    data = home / '.kenoforge'
    if (root / 'maintenance/state').is_dir():
        copy(root / 'maintenance/state', data / 'State/Maintenance', True)
    # Logs/receipts remain evidence; no stale inode receipt becomes an active rollback.
    for component in ('recovery', 'maintenance/logs'):
        if (root / component).is_dir():
            dst = data / 'Recovered-Data' / ('backup-' + uuid.uuid4().hex) / component
            copy(root / component, dst, True)
            print('Recovered offline data: ' + str(dst))
    metadata = manifest(root)
    old = metadata.get('source_home')
    # Format 3 existed before the hidden data directory. Earlier manifests
    # lacked source_data and therefore refer to the previous visible root.
    old_home = Path(old) if isinstance(old, str) and Path(old).is_absolute() else home
    old = str(old_home)
    old_data = metadata.get('source_data')
    candidates = [old_home / 'KenoForge', old_home / '.kenoforge']
    source_data = next((p for p in candidates if str(p) == old_data), candidates[0])
    xdg = Path(os.environ.get('XDG_CONFIG_HOME') or home / '.config')
    if source_data != data:
        from data_root_migration import changes, write_item
        for path, kind, _, updated, mode in changes(home, xdg, source_data):
            write_item(path, kind, updated, mode)
    if old and old != str(home):
        for relative in ('Config/MediaDeck/music.json', 'Config/Maintenance/wine-prefix-watch.json'):
            target = data / relative
            if target.exists():
                write_json(target, rebase(read_json(target), old, str(home)))
    # Recreate only launchers whose installed targets exist. Never copy old absolute links.
    for launcher in LAUNCHERS:
        target = data / 'System/Toolkit/bin' / launcher
        if not target.is_file():
            continue
        link = home / '.local/bin' / launcher
        with directory(link.parent, True) as fd:
            if link.exists() and not link.is_symlink():
                print('Custom launcher retained: ' + str(link))
                continue
            tmp = '.backup-' + uuid.uuid4().hex
            os.symlink(str(target), tmp, dir_fd=fd)
            os.replace(tmp, link.name, src_dir_fd=fd, dst_dir_fd=fd)
    unit = xdg / 'systemd/user/kenoforge-patch-persistence.service'
    if unit.exists() or (data / 'State/Maintenance/patch-persistence.json').exists():
        with directory(unit.parent, True):
            if unit.is_symlink():
                raise ValueError('Linked maintenance unit refused')
        import importlib.util
        spec = importlib.util.spec_from_file_location('backup_patch_persistence', Path(__file__).with_name('patch-persistence.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.DATA = data
        module.install_timer(enable=False, helper=data / 'System/Core/tools/patch-persistence.py')
        print('Maintenance units regenerated. Review patch selection before enabling the timer.')
    # Do not carry a timers.target.wants link that could start automatic repairs at next login.
    enabled = unit.parent / 'timers.target.wants/kenoforge-patch-persistence.timer'
    with directory(enabled.parent, True) as fd:
        try:
            st = os.stat(enabled.name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISLNK(st.st_mode):
                os.unlink(enabled.name, dir_fd=fd)
        except FileNotFoundError:
            pass


def recover_project(root, current):
    root, current = Path(root), Path(current)
    data = Path.home() / '.kenoforge'
    # Code is never automatically executed/replaced by a data restore. Use the installer
    # for code activation, preserving both Core and Toolkit as a coherent release.
    recovered = data / 'Recovered-Projects' / ('snapshot-' + uuid.uuid4().hex)
    for src, dst in [('project', 'Core'), ('toolkit', 'Toolkit')]:
        if (root / src).is_dir():
            copy(root / src, recovered / dst, True)
    if recovered.exists():
        write_json(recovered / 'recovery.json', manifest(root))
        print('Runtime snapshot recovered separately: ' + str(recovered))
        print('Current Core and Toolkit preserved. Activate code using the matching KenoForge installer.')


def recover_wine(snapshot, destination):
    snapshot, destination = Path(os.path.abspath(snapshot)), Path(os.path.abspath(destination))
    snapshot.relative_to(Path.home() / '.kenoforge/Recovered-Data')
    destination.relative_to(Path.home())
    if os.path.lexists(destination):
        raise ValueError('Choose a new, nonexistent Wine prefix path')
    recovery = next((p for p in snapshot.parents if p.name == 'recovery' and (p / 'index.json').is_file()), None)
    if recovery is None:
        raise ValueError('Recovery catalog missing')
    catalog = read_json(recovery / 'index.json')
    record = next((x for x in catalog.get('snapshots', []) if x.get('snapshot') == 'recovery/' + snapshot.relative_to(recovery).as_posix()), None)
    if record is None or record.get('inventory') != entries(snapshot):
        raise ValueError('Recovery snapshot integrity mismatch')
    from wine_prefix import steam_managed, rename_noreplace
    if steam_managed(destination):
        raise ValueError('Steam-managed prefix destination refused')
    if not (snapshot / 'drive_c').is_dir() or (snapshot / 'drive_c').is_symlink():
        raise ValueError('Snapshot is not a Wine prefix')
    with directory(destination.parent, True):
        stage = Path(tempfile.mkdtemp(prefix='.kenoforge-prefix-import-', dir=destination.parent))
        work = stage / 'prefix'
        copy(snapshot, work, True)
        if entries(snapshot) != entries(work):
            raise ValueError('Imported prefix verification failed; retained: ' + str(stage))
        rename_noreplace(work, destination)
        stage.rmdir()
    print('Prefix copied without execution: ' + str(destination))
    print('Diagnose this copy in Wine Prefix Repair before testing it. Original receipts remain offline.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['seal', 'verify', 'pack', 'extract', 'copy', 'capture-extra', 'restore-extra', 'recover-project', 'manifest', 'check-path', 'mkdir', 'recover-wine'])
    parser.add_argument('path')
    parser.add_argument('target', nargs='?')
    args = parser.parse_args()
    if args.action == 'seal': seal(args.path)
    elif args.action == 'verify': verify(args.path)
    elif args.action == 'pack': pack(args.path, args.target)
    elif args.action == 'extract': extract(args.path, args.target)
    elif args.action == 'copy': copy(args.path, args.target, True)
    elif args.action == 'capture-extra': capture_extra(args.path)
    elif args.action == 'restore-extra': restore_extra(args.path)
    elif args.action == 'recover-project': recover_project(args.path, args.target)
    elif args.action == 'manifest': print(manifest(args.path).get(args.target, ''))
    elif args.action == 'mkdir':
        with directory(args.path, True):
            pass
    elif args.action == 'recover-wine': recover_wine(args.path, args.target)
    elif args.action == 'check-path':
        p = Path(args.path)
        p.relative_to(Path.home())
        with directory(p.parent, True):
            if p.is_symlink(): raise ValueError('Symlink destination refused: ' + str(p))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, tarfile.TarError) as exc:
        print('KenoForge backup: ' + str(exc), file=sys.stderr)
        raise SystemExit(1)
