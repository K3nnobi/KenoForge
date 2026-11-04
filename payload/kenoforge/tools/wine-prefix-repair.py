#!/usr/bin/env python3
"""KenoForge's interactive, reversible Wine Prefix Repair module."""
import argparse
import json
import os
from pathlib import Path
import sys

import wine_prefix as wine
from runtime_files import safe_text


def display(report):
    print("\nKenoForge — Wine / Proton Prefix Diagnosis\n")
    print("Prefix:", report["prefix"])
    print("Architecture:", report.get("architecture", "unavailable"))
    print("Wine:", report.get("wine", {}).get("text", "not queried").strip())
    print("Steam-managed:", report["managed_by_steam"], "(diagnosis only)" if report["managed_by_steam"] else "")
    print("Complete scan:", report["complete"])
    print("Broken links:", len(report["broken_links"]))
    print("Proton references:", len(report["proton_references"]))
    print("Supported repair scenario:", report["repair_scenario"])
    print("Wine-related processes:", report.get("processes", "not queried"))
    print("Isolated execution available:", report.get("sandbox", "not queried"))
    for name, state in report.get("registry", {}).items():
        print("Registry:", name, "—", state["state"])
    for path, state in report.get("essentials", {}).items():
        print(" ", path, "—", state["state"], state.get("target", ""))
    print("\nBroken symbolic links (outside Windows are never replaced):")
    for item in report["broken_links"]:
        print(" ", repr(item["path"]), "->", repr(item["target"]))
    print("\nProton references (a missing target may be on an unmounted disk):")
    for item in report["proton_references"]:
        print(" ", repr(item["path"]), "->", repr(item["target"]), "BROKEN" if item["broken"] else "valid")
    for mime, result in report.get("mime", {}).items():
        print("\nMIME", mime, "\n", safe_text(result["text"]).strip())
    if "packages" in report:
        print("\nPackage inventory:\n", report["packages"]["text"].strip())
    print("\nGraphics:", report.get("graphics", "not tested"))
    print("fixme messages alone are not fatal. Vulkan/Mesa warnings do not by themselves diagnose broken prefix DLLs.")
    print("kernel32.dll / c0000135 can have other causes; repair requires confirmed broken links.")
    for error in report["errors"]:
        print("Problem:", safe_text(error))


def confirm(token, message):
    print("\n" + message)
    if not sys.stdin.isatty():
        raise ValueError("This action requires a terminal and explicit typed confirmation.")
    return input(f"Type {token!r} to continue, or Enter to cancel: ").strip() == token


def choose_session():
    entries = wine.sessions()
    if not entries:
        print("No repair sessions recorded.")
        return None
    for index, item in enumerate(entries, 1):
        print(index, item["id"], item["phase"], item["source"])
    choice = input("Session number (Enter cancels): ").strip()
    return entries[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= len(entries) else None


def repair_action(prefix):
    report = wine.diagnose(prefix)
    display(report)
    if not report["repair_scenario"]:
        print("No repair: the supported scenario was not confirmed.")
        return
    print("\nClose Wine applications first. Source, verified backup and working copy are kept separately.")
    print("The fresh prefix and working-copy wineboot run with a read-only host filesystem.")
    if confirm("REPAIR", "Create a backup, working copy and clean donor prefix? Nothing will be activated."):
        session = wine.prepare(prefix)
        print("\nRepair session:", session["id"])
        print("Working prefix:", wine.session_paths(session)["work"])
        print("Replaced links:", len(session["changes"]))
        print("Unresolved links:", len(session["validation"]["broken_links"]))
        print("Next: run winecfg, optionally test a trusted executable, then activate separately.")


def validation_action(session, app=False):
    executable = None
    if app:
        executable = input("Absolute path of a trusted executable (Enter cancels): ").strip()
        if not executable:
            return
    if confirm("TEST", "Run the selected executable in the working copy?" if app else
               "Open winecfg in the repaired working copy? Close its window when finished."):
        wine.validate_session(session, executable)
        print("Test command completed. Inspect the application result yourself before activation.")


def activation_action(session):
    paths = wine.session_paths(session)
    print("Prefix to activate:", paths["source"])
    print("Original will remain at:", paths["original"])
    print("Unresolved links:", len(session.get("validation", {}).get("broken_links", [])))
    if confirm("ACTIVATE " + session["id"], "Confirm that winecfg and your desired application test worked. Activate the repaired copy?"):
        wine.activate(session, confirmed=True)
        print("Activated. The original and verified backup remain available for rollback.")


def rollback_action(session):
    print("Original:", wine.session_paths(session)["original"])
    if confirm("ROLLBACK " + session["id"], "Restore the original? The repaired prefix, including later data, is retained separately."):
        wine.rollback(session, confirmed=True)
        print("Original restored. No prefix was deleted.")


def menu(prefix):
    wine.normal_user()
    while True:
        print("\nWINE / PROTON PREFIX MAINTENANCE")
        print("Selected prefix:", prefix)
        print("1) Read-only diagnosis\n2) Select another prefix\n3) Prepare isolated repair (backup first)")
        print("4) Run winecfg in a repair session\n5) Test a selected executable\n6) Activate repaired prefix")
        print("7) Rollback / recover interrupted activation\n8) List sessions and unresolved links")
        print("9) Enable read-only Update Guardian checks\n10) Disable integrity watch")
        print("11) Optional Wine MIME defaults\n12) Rollback MIME defaults\n0) Back")
        choice = input("> ").strip()
        try:
            if choice == "0":
                return 0
            if choice == "1":
                display(wine.diagnose(prefix))
            elif choice == "2":
                value = input("Prefix path (Enter keeps current): ").strip()
                if value:
                    prefix = wine.prefix_path(value)
            elif choice == "3":
                repair_action(prefix)
            elif choice in ("4", "5", "6", "7"):
                session = choose_session()
                if session:
                    {"4": lambda: validation_action(session), "5": lambda: validation_action(session, True),
                     "6": lambda: activation_action(session), "7": lambda: rollback_action(session)}[choice]()
            elif choice == "8":
                for session in wine.sessions():
                    print(session["id"], session["phase"], session["source"])
                    for item in session.get("skipped", []):
                        print(" ", item["path"], "—", item["reason"])
                    for event in session.get("events", []):
                        if "log" in event:
                            print("  Execution log:", event["log"], "Status:", event["code"])
                            print("  Findings:", event["findings"])
                    if session.get("protected_changes"):
                        print("  Changes requiring manual review:", session["protected_changes"])
                    print("  Working copy:", wine.session_paths(session)["work"])
                    print("  Preserved original:", wine.session_paths(session)["original"])
            elif choice in ("9", "10"):
                if confirm("WATCH" if choice == "9" else "UNWATCH", "Change opt-in integrity checks for this prefix?"):
                    wine.watch_prefix(prefix, choice == "9")
                    print("Watch setting saved. Update Guardian checks essential DLLs only; it never repairs automatically.")
            elif choice == "11":
                print("This changes .exe MIME defaults to installed wine.desktop. It does not select a custom prefix.")
                print("Users intentionally using Proton should keep their current association.")
                if confirm("MIME", "Use Wine as the default for both executable MIME types?"):
                    print("MIME rollback receipt:", wine.set_wine_mime(True))
            elif choice == "12":
                sid = input("MIME receipt ID: ").strip()
                if confirm("MIME ROLLBACK", "Restore the recorded previous MIME defaults?"):
                    wine.rollback_mime(sid, True)
            else:
                print("Invalid option.")
        except (OSError, ValueError, TimeoutError) as exc:
            print("\nAction stopped:", safe_text(str(exc)))
            print("No prefix is deleted. Review the session journal before retrying.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", help="Defaults to WINEPREFIX or ~/.wine")
    parser.add_argument("--log", help="Inspect an existing Wine log, without executing Wine")
    parser.add_argument("--json", action="store_true")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--menu", "--interactive", action="store_true")
    group.add_argument("--diagnose", action="store_true")
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--sessions", action="store_true")
    group.add_argument("--winecfg", metavar="SESSION_ID")
    group.add_argument("--test-app", metavar="SESSION_ID")
    group.add_argument("--activate", metavar="SESSION_ID")
    group.add_argument("--rollback", metavar="SESSION_ID")
    args = parser.parse_args()
    prefix = wine.prefix_path(args.prefix)
    if args.menu:
        return menu(prefix)
    if args.prepare:
        repair_action(prefix)
    elif args.sessions:
        print(json.dumps(wine.sessions(), indent=2))
    elif args.winecfg or args.test_app:
        validation_action(wine.load_session(args.winecfg or args.test_app), bool(args.test_app))
    elif args.activate:
        activation_action(wine.load_session(args.activate))
    elif args.rollback:
        rollback_action(wine.load_session(args.rollback))
    else:
        report = wine.diagnose(prefix)
        if args.log:
            path = Path(os.path.abspath(os.path.expanduser(args.log)))
            with wine.directory(path.parent) as fd:
                text = wine.regular_bytes(fd, path.name, 8 * 1024 * 1024).decode(errors="replace")
            report["log_findings"] = wine.log_findings(text)
        print(json.dumps(report, ensure_ascii=False, indent=2)) if args.json else display(report)
        if report.get("log_findings") and not args.json:
            print("Log findings:", report["log_findings"])
        return int(not report["complete"] or bool(report["essential_problems"]))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, TimeoutError) as exc:
        print("Wine Prefix Repair:", safe_text(str(exc)), file=sys.stderr)
        raise SystemExit(1)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Prefixes and session data are retained for inspection or recovery.")
        raise SystemExit(130)
