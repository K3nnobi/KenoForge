#!/usr/bin/env python3
"""Isolated filesystem/state tests. Never execute Wine or change host MIME defaults."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "payload/kenoforge/tools"
sys.path.insert(0, str(TOOLS))
import wine_prefix as w


def pe(machine=0x8664, extra=b""):
    value = bytearray(128)
    value[:2] = b"MZ"
    value[0x3c:0x40] = struct.pack("<I", 64)
    value[64:70] = b"PE\0\0" + struct.pack("<H", machine)
    return bytes(value) + extra


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="kenoforge wine ; ")
        self.home = Path(self.tmp.name)
        self.prefix = self.home / ".wine"
        self.data = self.home / ".kenoforge"
        self.env = patch.dict(os.environ, {"HOME": str(self.home), "KENOFORGE_DATA_HOME": str(self.data)})
        self.env.start()
        self.fake_tools = {}
        for name in ("wine", "wineboot", "winecfg", "wineserver"):
            target = self.home / "bin" / name
            target.parent.mkdir(exist_ok=True)
            target.write_text("fixture only; never executed")
            self.fake_tools[name] = str(target)
        self.seed(self.prefix)
        self.kernel = self.prefix / "drive_c/windows/system32/kernel32.dll"
        self.kernel.unlink()
        self.kernel.symlink_to("/missing/SteamLibrary/steamapps/common/Proton Hotfix/files/lib/wine/x86_64-windows/kernel32.dll")
        self.original_hash = w.tree_hash(self.prefix)[0]
        self.calls = []
        self.patches = [patch.object(w, "normal_user"),
                        patch.object(w, "wine_tools", return_value=self.fake_tools),
                        patch.object(w, "require_idle"),
                        patch.object(w, "run_wine", side_effect=self.fake_wine)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.env.stop()
        self.tmp.cleanup()

    def seed(self, path, arch="win64"):
        path.mkdir(exist_ok=True)
        for name in ("system.reg", "user.reg", "userdef.reg"):
            (path / name).write_text("WINE REGISTRY Version 2\n#arch=" + arch + "\n\n[personal]\\nkey=keep\n")
        for sub, machine in (("system32", 0x8664 if arch == "win64" else 0x14c), ("syswow64", 0x14c)):
            if sub == "syswow64" and arch != "win64":
                continue
            folder = path / "drive_c/windows" / sub
            folder.mkdir(parents=True, exist_ok=True)
            for dll in ("kernel32.dll", "ntdll.dll", "custom.dll"):
                (folder / dll).write_bytes(pe(machine, b"KEEP-REGULAR"))
        app = path / "drive_c/Program Files/Personal"
        app.mkdir(parents=True)
        (app / "data.txt").write_text("installed application data")
        (path / "dosdevices").mkdir()
        (path / "dosdevices/c:").symlink_to("../drive_c")
        (path / "dosdevices/z:").symlink_to("/")

    def fake_wine(self, session, target, command, label, timeout=180):
        self.calls.append((str(target), command, label))
        if label == "fresh-prefix":
            self.seed(target)
        elif label == "update-work":
            with (target / "system.reg").open("a") as out:
                out.write("\n[wine-update]\n")
        return {"fatal": False}

    def prepared(self):
        return w.prepare(self.prefix)

    def ready_session(self):
        session = self.prepared()
        w.validate_session(session)
        return session

    def test_diagnosis_finds_proton_links_without_writes_or_wine(self):
        report = w.diagnose(self.prefix, system=False)
        self.assertTrue(report["repair_scenario"])
        self.assertEqual(report["architecture"], "win64")
        self.assertEqual(report["essentials"]["drive_c/windows/system32/kernel32.dll"]["state"], "broken-link")
        self.assertEqual(len(report["proton_references"]), 1)
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)
        self.assertFalse(self.data.exists())
        self.assertEqual(self.calls, [])

    def test_healthy_prefix_is_not_repaired(self):
        self.kernel.unlink()
        self.kernel.write_bytes(pe())
        before = w.tree_hash(self.prefix)[0]
        self.assertFalse(w.diagnose(self.prefix, system=False)["repair_scenario"])
        with self.assertRaisesRegex(ValueError, "not confirm"):
            self.prepared()
        self.assertEqual(w.tree_hash(self.prefix)[0], before)
        self.assertEqual(self.calls, [])

    def test_missing_regular_dll_does_not_imply_supported_repair(self):
        self.kernel.unlink()
        self.assertFalse(w.diagnose(self.prefix, system=False)["repair_scenario"])

    def test_preparation_preserves_original_registry_apps_permissions_and_links(self):
        app = self.prefix / "drive_c/Program Files/Personal/data.txt"
        app.chmod(0o640)
        before = w.tree_hash(self.prefix)[0]
        session = self.prepared()
        paths = w.session_paths(session)
        self.assertEqual(w.tree_hash(self.prefix)[0], before)
        self.assertEqual(w.tree_hash(paths["backup"])[0], before)
        self.assertTrue(self.kernel.is_symlink())
        self.assertFalse((paths["work"] / "drive_c/windows/system32/kernel32.dll").is_symlink())
        self.assertEqual((paths["work"] / "drive_c/Program Files/Personal/data.txt").stat().st_mode & 0o777, 0o640)
        self.assertEqual(os.readlink(paths["work"] / "dosdevices/z:"), "/")
        self.assertEqual(session["changes"], ["drive_c/windows/system32/kernel32.dll"])
        self.assertTrue(all(target != str(self.prefix) for target, _, _ in self.calls))
        self.assertTrue((self.data / "Logs/Wine-Prefix-Repair" / (session["id"] + ".json")).is_file())

    def test_valid_external_link_and_regular_custom_file_are_preserved(self):
        external = self.home / "outside.dll"
        external.write_bytes(pe(extra=b"CUSTOM"))
        link = self.prefix / "drive_c/windows/system32/valid.dll"
        link.symlink_to(external)
        custom = self.prefix / "drive_c/windows/system32/custom.dll"
        before = custom.read_bytes()
        session = self.prepared()
        work = w.session_paths(session)["work"]
        self.assertEqual(os.readlink(work / link.relative_to(self.prefix)), str(external))
        self.assertEqual((work / custom.relative_to(self.prefix)).read_bytes(), before)
        self.assertEqual(external.read_bytes(), pe(extra=b"CUSTOM"))

    def test_preparation_failure_retains_original_and_backup(self):
        def fail(session, target, command, label, timeout=180):
            if label == "update-work":
                raise ValueError("simulated wineboot failure")
            return self.fake_wine(session, target, command, label, timeout)
        with patch.object(w, "run_wine", side_effect=fail):
            with self.assertRaisesRegex(ValueError, "wineboot failure"):
                self.prepared()
        session = w.sessions()[0]
        self.assertEqual(session["phase"], "failed")
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)
        self.assertEqual(w.tree_hash(w.session_paths(session)["backup"])[0], self.original_hash)

    def test_wineboot_modifying_a_custom_regular_file_blocks_activation(self):
        def touch(session, target, command, label, timeout=180):
            result = self.fake_wine(session, target, command, label, timeout)
            if label == "update-work":
                (target / "drive_c/windows/system32/custom.dll").write_bytes(pe(extra=b"overwritten"))
            return result
        with patch.object(w, "run_wine", side_effect=touch):
            with self.assertRaisesRegex(ValueError, "pre-existing"):
                self.prepared()
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)
        self.assertTrue(w.sessions()[0]["protected_changes"])

    def test_architecture_mismatch_or_symlink_donor_is_not_copied(self):
        def bad_donor(session, target, command, label, timeout=180):
            result = self.fake_wine(session, target, command, label, timeout)
            if label == "fresh-prefix":
                donor = target / "drive_c/windows/system32/kernel32.dll"
                donor.write_bytes(pe(0x14c))
            return result
        with patch.object(w, "run_wine", side_effect=bad_donor):
            with self.assertRaisesRegex(ValueError, "No safe"):
                self.prepared()
        self.assertTrue(self.kernel.is_symlink())
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)

    def test_cross_prefix_architecture_is_refused(self):
        def wrong_arch(session, target, command, label, timeout=180):
            if label == "fresh-prefix":
                self.seed(target, "win32")
            return {"fatal": False}
        with patch.object(w, "run_wine", side_effect=wrong_arch):
            with self.assertRaisesRegex(ValueError, "architecture"):
                self.prepared()
        self.assertTrue(self.kernel.is_symlink())

    def test_symlink_donor_is_refused_even_when_it_points_to_regular_file(self):
        outside = self.home / "donor.dll"
        outside.write_bytes(pe())
        def linked_donor(session, target, command, label, timeout=180):
            result = self.fake_wine(session, target, command, label, timeout)
            if label == "fresh-prefix":
                donor = target / "drive_c/windows/system32/kernel32.dll"
                donor.unlink()
                donor.symlink_to(outside)
            return result
        with patch.object(w, "run_wine", side_effect=linked_donor):
            with self.assertRaisesRegex(ValueError, "No safe"):
                self.prepared()
        self.assertTrue(self.kernel.is_symlink())
        self.assertEqual(outside.read_bytes(), pe())

    def test_unknown_run_key_is_not_executed_by_wineboot(self):
        with (self.prefix / "user.reg").open("a") as out:
            out.write('\n[Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run]\n"Unknown"="C:\\\\unknown.exe"\n')
        before = w.tree_hash(self.prefix)[0]
        with self.assertRaisesRegex(ValueError, "autostart"):
            self.prepared()
        self.assertEqual([label for _, _, label in self.calls], ["fresh-prefix"])
        self.assertEqual(w.tree_hash(self.prefix)[0], before)

    def test_unknown_startup_folder_is_blocked(self):
        folder = self.prefix / "drive_c/users/test/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
        folder.mkdir(parents=True)
        (folder / "unknown.lnk").write_text("unknown shortcut")
        with self.assertRaisesRegex(ValueError, "autostart"):
            self.prepared()
        self.assertEqual([label for _, _, label in self.calls], ["fresh-prefix"])

    def test_failed_winecfg_does_not_leave_copy_eligible_for_activation(self):
        session = self.ready_session()
        with patch.object(w, "run_wine", side_effect=ValueError("test failed")):
            with self.assertRaisesRegex(ValueError, "test failed"):
                w.validate_session(session)
        self.assertEqual(w.load_session(session["id"])["phase"], "prepared")
        with self.assertRaises(ValueError):
            w.activate(w.load_session(session["id"]), True)

    def test_user_confirmation_and_winecfg_are_both_required(self):
        session = self.prepared()
        with self.assertRaisesRegex(ValueError, "confirmation"):
            w.activate(session)
        with self.assertRaisesRegex(ValueError, "winecfg"):
            w.activate(session, True)
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)

    def test_activation_and_rollback_keep_both_versions_and_later_user_data(self):
        session = self.ready_session()
        w.activate(session, True)
        paths = w.session_paths(session)
        self.assertEqual(w.tree_hash(paths["original"])[0], self.original_hash)
        self.assertFalse(self.kernel.is_symlink())
        (self.prefix / "later-user-file.txt").write_text("KEEP LATER")
        w.rollback(w.load_session(session["id"]), True)
        self.assertTrue(self.kernel.is_symlink())
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)
        restored = w.load_session(session["id"])
        self.assertEqual((Path(restored["retained_repaired"]) / "later-user-file.txt").read_text(), "KEEP LATER")
        self.assertEqual(w.tree_hash(paths["backup"])[0], self.original_hash)

    def test_activation_error_between_renames_restores_original(self):
        session = self.ready_session()
        real = w.rename_noreplace
        count = 0
        def fail_second(source, target):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("second rename failed")
            return real(source, target)
        with patch.object(w, "rename_noreplace", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "second rename"):
                w.activate(session, True)
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)
        self.assertTrue(w.session_paths(session)["work"].exists())

    def test_interrupted_activation_with_failed_recovery_can_be_rolled_back(self):
        session = self.ready_session()
        real = w.rename_noreplace
        count = 0
        def fail_after_first(source, target):
            nonlocal count
            count += 1
            if count > 1:
                raise OSError("simulated interruption")
            return real(source, target)
        with patch.object(w, "rename_noreplace", side_effect=fail_after_first):
            with self.assertRaises(OSError):
                w.activate(session, True)
        self.assertFalse(self.prefix.exists())
        receipt = w.load_session(session["id"])
        self.assertEqual(receipt["phase"], "activating")
        w.rollback(receipt, True)
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)

    def test_activation_never_overwrites_existing_backup_name(self):
        session = self.ready_session()
        original = w.session_paths(session)["original"]
        original.mkdir()
        (original / "keep").write_text("collision")
        with self.assertRaises(FileExistsError):
            w.activate(session, True)
        self.assertEqual((original / "keep").read_text(), "collision")
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)

    def test_rollback_failure_restores_active_repaired_copy(self):
        session = self.ready_session()
        w.activate(session, True)
        repaired_hash = w.tree_hash(self.prefix)[0]
        real = w.rename_noreplace
        count = 0
        def fail_second(source, target):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("restore failed")
            return real(source, target)
        with patch.object(w, "rename_noreplace", side_effect=fail_second):
            with self.assertRaises(OSError):
                w.rollback(session, True)
        self.assertEqual(w.tree_hash(self.prefix)[0], repaired_hash)
        self.assertEqual(w.tree_hash(w.session_paths(session)["original"])[0], self.original_hash)

    def test_receipt_write_failure_after_activation_retains_recoverable_prefixes(self):
        session = self.ready_session()
        real = w.journal
        def fail_final(receipt, event, **detail):
            if event == "activated":
                raise OSError("receipt publish failed")
            return real(receipt, event, **detail)
        with patch.object(w, "journal", side_effect=fail_final):
            with self.assertRaises(OSError):
                w.activate(session, True)
        receipt = w.load_session(session["id"])
        self.assertEqual(receipt["phase"], "activating")
        w.rollback(receipt, True)
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)

    def test_source_changed_after_repair_blocks_activation(self):
        session = self.ready_session()
        (self.prefix / "new-user-data").write_text("changed")
        with self.assertRaisesRegex(ValueError, "changed since repair"):
            w.activate(session, True)
        self.assertEqual((self.prefix / "new-user-data").read_text(), "changed")

    def test_installed_wine_changed_blocks_test_and_activation(self):
        session = self.ready_session()
        Path(self.fake_tools["wine"]).write_text("new Wine version")
        with self.assertRaisesRegex(ValueError, "Wine changed"):
            w.activate(session, True)
        with self.assertRaisesRegex(ValueError, "Wine changed"):
            w.validate_session(session)

    def test_steam_managed_prefix_is_diagnosed_but_not_repaired(self):
        steam = self.home / "Steam/steamapps/compatdata/123/pfx"
        steam.parent.mkdir(parents=True)
        self.seed(steam)
        self.assertTrue(w.diagnose(steam, system=False)["managed_by_steam"])
        with self.assertRaisesRegex(ValueError, "Steam/Proton"):
            w.prepare(steam)

    def test_root_or_linked_prefix_and_linked_parent_are_refused(self):
        alias = self.home / "alias"
        alias.symlink_to(self.prefix, target_is_directory=True)
        with self.assertRaises(OSError):
            w.check_prefix(alias)
        folder = self.home / "redirect"
        folder.symlink_to(self.prefix.parent, target_is_directory=True)
        with self.assertRaises(OSError):
            w.check_prefix(folder / self.prefix.name)

    def test_busy_prefix_and_low_disk_space_stop_before_copying(self):
        with patch.object(w, "require_idle", side_effect=ValueError("busy")):
            with self.assertRaisesRegex(ValueError, "busy"):
                self.prepared()
        with patch.object(w.shutil, "disk_usage", return_value=type("Disk", (), {"free": 0})()):
            with self.assertRaisesRegex(ValueError, "Insufficient"):
                self.prepared()
        self.assertEqual(list(self.home.glob(".wine.kenoforge-repair-*")), [])
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)

    def test_symlinked_repair_ancestor_cannot_modify_external_file(self):
        session = self.prepared()
        work = w.session_paths(session)["work"]
        original = work / "drive_c/windows/system32"
        moved = work / "drive_c/windows/saved-system32"
        original.rename(moved)
        outside = self.home / "external"
        outside.mkdir()
        keep = outside / "kernel32.dll"
        keep.symlink_to("/missing/target")
        original.symlink_to(outside)
        changes, skipped = w.replace_broken(work, w.session_paths(session)["clean"],
            [{"path": "drive_c/windows/system32/kernel32.dll", "target": "/missing/target"}], "win64", lambda *a, **k: None)
        self.assertEqual(changes, [])
        self.assertTrue(skipped)
        self.assertEqual(os.readlink(keep), "/missing/target")

    def test_watch_is_opt_in_read_only_and_creates_only_maintenance_warning(self):
        self.assertEqual(w.guard_watched({"wine"}), [])
        self.assertFalse(self.data.exists())
        w.watch_prefix(self.prefix, True)
        created = w.guard_watched({"wine"})
        self.assertEqual(len(created), 1)
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)
        self.assertEqual(self.calls, [])
        w.watch_prefix(self.prefix, False)
        self.assertEqual(w.guard_watched({"proton-ge"}), [])

    def test_update_guardian_records_prefix_warning_after_wine_update(self):
        w.watch_prefix(self.prefix, True)
        spec = importlib.util.spec_from_file_location("guardian_wine_test", TOOLS / "update-guardian.py")
        guardian = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guardian)
        tasks = guardian.record_changed_packages({"wine"})
        self.assertEqual(len(tasks), 1)
        self.assertTrue(tasks[0].startswith("wine-prefix-"))
        self.assertEqual(self.calls, [])
        self.assertEqual(w.tree_hash(self.prefix)[0], self.original_hash)

    def test_sandbox_environment_excludes_injected_wine_and_steam_settings(self):
        session = self.prepared()
        paths = w.session_paths(session)
        with patch.dict(os.environ, {"WINELOADER": "/malicious", "LD_PRELOAD": "/evil", "STEAM_COMPAT_DATA_PATH": "/steam"}):
            args, env = w.sandbox_command(session, paths["work"], ["/usr/bin/winecfg"])
        self.assertEqual(args[args.index("--ro-bind") + 1:args.index("--ro-bind") + 3], ["/", "/"])
        self.assertNotIn("WINELOADER", env)
        self.assertNotIn("LD_PRELOAD", env)
        self.assertNotIn("STEAM_COMPAT_DATA_PATH", env)
        self.assertNotIn("WINEDLLOVERRIDES", env)
        self.assertEqual(env["WINEPREFIX"], str(paths["work"]))
        self.assertEqual(args.count("--bind"), 2)

    def test_graphics_and_fixme_are_separate_from_loader_failure(self):
        warnings = "fixme: example\nMESA-EGL: failed dri2\nerr:vulkan: init_physical_devices"
        findings = w.classify_output(warnings, 0)
        self.assertTrue(findings["graphics_warnings"])
        self.assertTrue(findings["fixme_messages"])
        self.assertFalse(findings["fatal"])
        self.assertTrue(w.classify_output("wine: could not load kernel32.dll, status c0000135", 0)["fatal"])

    def test_mime_update_and_rollback_never_write_desktop_files(self):
        apps = self.home / ".local/share/applications"
        apps.mkdir(parents=True)
        desktop = apps / "wine.desktop"
        desktop.write_text("[Desktop Entry]\nExec=wine start /unix %f\n")
        before = desktop.read_bytes()
        defaults = {mime: "custom-proton.desktop" for mime in w.MIMES}
        def query(command, timeout=15):
            if len(command) == 4:
                defaults[command[2]] = command[3]
            return {"code": 0, "text": "Default application for “" + command[2] + "”: " + defaults[command[2]] + "\n"}
        with patch.object(w, "query", side_effect=query), patch.object(w.shutil, "which", return_value="/usr/bin/gio"):
            sid = w.set_wine_mime(True)
            self.assertEqual(set(defaults.values()), {"wine.desktop"})
            w.rollback_mime(sid, True)
            self.assertEqual(set(defaults.values()), {"custom-proton.desktop"})
        self.assertEqual(desktop.read_bytes(), before)


class UnmockedGuards(unittest.TestCase):
    def test_namespace_probe_failure_never_executes_wine(self):
        import subprocess
        with patch.object(w.shutil, "which", side_effect=lambda name, path=None: "/usr/bin/" + name), \
                patch.object(w.subprocess, "run", return_value=subprocess.CompletedProcess([], 1, "", "namespaces blocked")) as run:
            with self.assertRaisesRegex(ValueError, "namespaces are blocked"):
                w.wine_tools()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][0], "/usr/bin/bwrap")
            self.assertEqual(run.call_args.args[0][-1], "/bin/true")

    def test_root_guard_has_no_environment_bypass(self):
        with patch.object(w.os, "geteuid", return_value=0), patch.dict(os.environ, {"KENOFORGE_TEST_SIMULATE": "1"}):
            with self.assertRaisesRegex(ValueError, "never run as root"):
                w.normal_user()

    def test_process_prefix_matching_uses_wine_processes_not_shell_variables(self):
        with tempfile.TemporaryDirectory() as folder:
            proc = Path(folder)
            for number, comm, prefix in (("1000001", "wine", "/tmp/a"), ("1000002", "python", "/tmp/a"), ("1000003", "app.exe", "/tmp/b")):
                item = proc / number
                item.mkdir()
                (item / "comm").write_text(comm)
                (item / "environ").write_bytes(b"WINEPREFIX=" + prefix.encode() + b"\0")
            active = w.active_processes(["/tmp/a"], proc)
            self.assertEqual([x["pid"] for x in active], [1000001])
            long_name = proc / "1000004"
            long_name.mkdir()
            (long_name / "comm").write_text("Security Valt.e")
            (long_name / "environ").write_bytes(b"WINEPREFIX=/tmp/a\0")
            (long_name / "exe").symlink_to("/usr/lib/wine/wine64-preloader")
            active = w.active_processes(["/tmp/a"], proc)
            self.assertEqual(sorted(x["pid"] for x in active), [1000001, 1000004])


if __name__ == "__main__":
    unittest.main(verbosity=2)
