# KenoForge

**Arch Linux Automation Toolkit** · Intelligence meets Linux

Version **1.5.23** introduces backup format 3 and portable recovery. KenoForge
continues ArchMind in this repository under its new name. See the
[release notes](RELEASE-NOTES-1.5.23.md) and [migration guide](MIGRATION.md).

KenoForge retains the blue AFI terminal interface, responsive startup panels,
Live Monitor, Doctor, maintenance tools, package profiles and optional desktop
and gaming patches. The core code remains derived from the previous stable
1.5.18 release; this is not a rewrite.

See `BACKUPS.pt-BR.md` for backup coverage, migration, offline Wine recovery and
compatibility with previous backups. Personal music and active Wine prefixes
need a separate personal-data backup.

## Install on Arch Linux, including a TTY

Use a normal user account with a writable home. Bash, coreutils, findutils,
grep, Zsh and Python 3.10+ are required. A minimal Arch installation normally
already has the first four. The installer can offer to install missing Zsh and
Python with Pacman and sudo. Without sudo, have an administrator install those
two packages first. A graphical desktop is not required for the console.

Install from this source tree:

```bash
git clone https://github.com/K3nnobi/archmind.git kenoforge
cd kenoforge
./install.sh --check
./install.sh --dry-run
./install.sh
export PATH="$HOME/.local/bin:$PATH"
kenoforge
```

For a single-file installer, export a clean source tree under the versioned
directory name, then build and check it:

```bash
build_dir="$(mktemp -d)"
git archive --prefix=KenoForge-1.5.23/ HEAD | tar -x -C "$build_dir"
"$build_dir/KenoForge-1.5.23/installer/build-run-installer.sh" "$PWD/KenoForge-1.5.23-Installer.run"
bash ./KenoForge-1.5.23-Installer.run --check
```
The [ArchMind 1.5.18 release](https://github.com/K3nnobi/archmind/releases/tag/v1.5.18)
and its pinned `get` bootstrap remain available for that historical version.

The installer installs the toolkit itself. Installing package profiles and
applying system patches are separate, explicit actions. Do not run the
installer as root. `--no-progress` disables the cosmetic minimum display time.

## Commands and paths

| Item | Location / command |
| --- | --- |
| Main console | `kenoforge` or `kenoforge-console` |
| Live Monitor | `kenoforge-monitor` |
| Runtime | `~/KenoForge/System` |
| User settings | `~/KenoForge/Config` |
| Backups | `~/KenoForge/Backups` |
| Installer safety copies | `~/KenoForge/Installer-Backups` |
| Commands | `~/.local/bin` |
| Core compatibility link | `${XDG_CONFIG_HOME:-$HOME/.config}/kenoforge` |
| Toolkit compatibility link | `${XDG_DATA_HOME:-$HOME/.local/share}/kenoforge-toolkit` |

Installer compatibility links and desktop entries honor XDG config/data paths.
The main KenoForge tree intentionally stays under `~/KenoForge`. External
applications such as Firefox retain their own profile locations. Use the same
XDG environment when installing and uninstalling.

The installer adds a managed Zsh alias block:

```bash
alias pacinstall='sudo pacman -S'
alias pacupdate='sudo pacman -Syu'
```

It does not define aliases named `install` or `update`, and does not erase
aliases already defined by the user. The complete theme/loader remains a
separate shell customization; the installer does not automatically source it.

## Music Center (1.5.23)

Open **Music Center** to launch the bundled MediaDeck 0.6.5.0 music player in a
separate desktop window. Review optional dependencies from the same menu.
The console stays usable during playback. Direct command: `kenoforge-music`;
use `--status`, `--install-deps`, or `--detach` as needed.

Library, playlists, favorites, queue, and visualization preferences are kept in
`~/KenoForge/Config/MediaDeck`; cover cache is in `~/KenoForge/Cache/MediaDeck`.
The existing desktop and sound stack are reused. Local music only; a graphical
session is required. See `MUSIC.pt-BR.md` for the Portuguese guide and testing limits.

## Wine / Proton prefix diagnosis and controlled repair

Open **Maintenance Center → Diagnosticar / Reparar Wine e Proton** for read-only
inspection, isolated repair preparation, explicit activation, and rollback.
Steam-managed prefixes are diagnosis-only. Wine execution requires Bubblewrap;
no root or unsandboxed fallback is allowed. The original stays untouched until
separately confirmed activation. Optional MIME defaults and opt-in Update Guardian
checks have their own actions. See `WINE-PREFIX-REPAIR.pt-BR.md` for workflow,
recovery, restrictions and target-machine validation requirements.

## Optional patches

Use the Package Center to select GNOME/Nautilus appearance, GameMode + Blur,
Wine Compatibility Pack, Firefox / ChatGPT color emoji, Caps Lock, NVIDIA
Vibrance, Plymouth and GNOME drag-hover integrations. The Wine pack remains
separate from Wine base installation. DXVK and 7-Zip are optional; .NET is not
automatically added. No files are copied from Proton prefixes.

System-changing patches retain their existing confirmation and rollback/status
mechanisms where available. Some system changes require sudo, a logout, or a
reboot. Review the selected patch's output and prerequisites first. Real GPU,
bootloader and desktop validation must be performed on the target machine.

## Reversible uninstall

```bash
./uninstall.sh          # preview
./uninstall.sh --apply  # explicit confirmation
```

The installed helper can also be used directly:

```bash
python3 "$HOME/KenoForge/System/Core/tools/uninstall.py" --apply
```

This archives the runtime in `Installer-Backups`, removes verified owned
launcher links and the managed aliases, and preserves personal settings,
backups and system packages. It does not reverse desktop/system patches.
Revert any such patches using their own rollback commands before uninstalling
if desired. Reinstalling reactivates the console. PATH and personal shell
customizations are retained.

## Validation

Tests are under `tests/`; package integrity is recorded in `PAYLOAD.sha256`.
See `AUDIT.md` for results, inherited defects and test limitations. Passing
mocked tests does not certify a real backup restore or a hardware change.

### Patch persistence (1.5.21 maintenance extension)

After installing this archive, open **KenoForge Manager → Maintenance Center →
Patch persistence → Configure automatic repair**. Select integrations that
should remain active. This enables a systemd **user** timer: first check two
minutes after the user manager starts, then ten minutes after each run ends.
Disable it from the same menu. Logs: `journalctl --user -u
kenoforge-patch-persistence.service`. An active user session is required.

Supported helpers: Plymouth / GRUB, Caps Lock No Delay (keyd), GNOME Drag Hover,
Firefox ChatGPT Emoji, and NVIDIA Vibrance. Healthy configurations are checked
without reapplying. Existing state is required for all except the explicitly
selected GNOME Drag Hover integration. Removing GNOME Drag Hover disables its
persistence; removing other integrations removes their saved state and stops
reapplication. Select only integrations you want maintained.

The timer defers while pacman's database is locked. It uses existing helpers,
compatibility checks and backups. Background sudo uses `-n`: no password prompt,
no sudoers changes and no new root daemon. Without existing authorization,
privileged repairs remain pending: use **Repair now** from a terminal to enter
sudo credentials. This is automatic detection and best-effort repair, not a
promise of unattended recovery for every patch. GNOME rounded blur recompilation
remains manual (`yay -S gnome-rounded-blur --rebuild`); old session detection no
longer clears its pending task. Unsupported helpers, session issues and failures
are reported in Pending Tasks. No AUR rebuild runs unattended.

**Plymouth → Plymouth Themes** lists installed themes, marks the active theme,
applies the selection and runs `mkinitcpio -P`. Failed boot regeneration attempts
to restore the previous theme and rebuild again. The saved selection is also used
by the Plymouth patch, so reapplication does not force spinner. Boot integration
still targets the existing supported GRUB + mkinitcpio configuration.

Validated using isolated simulated system commands, including persistence
success/failure, removal, stale blur detection, and existing patch rollback
suites. No live Arch Linux boot or user timer was exercised in the build container.

### 1.5.21 — unified terminal identity

The installer now archives previous-brand launchers and runtime directories,
updates shell startup references, and restores them on transaction failure.
After installing, open a new terminal and use `kenoforge`. Current configuration
is preserved; personal data from the previous installation remains in the
installer safety archive. See MIGRATION.md for scope and recovery details.

Project direction: Kenobi owns the project and product decisions; Aurora leads
technical maintenance in this collaboration. Prefer targeted changes, reversible
system operations, and validation of the actual Console flow before delivery.

### 1.5.21 — incremental Console navigation

Arrow keys now update only changed menu and Information panel rows. The Console
caches frame geometry and rendered rows; navigation does not reload settings or
query the static status panel. Scrolling updates changed rows and scroll hints
without clearing the terminal. Unhandled keys cause no repaint.

Screen changes, resize events, and return from dialogs or external tools still
build a complete frame. Minimum-size behavior is preserved. PTY tests cover
wide and compact layouts, scrolling, wrapping selection, up/down navigation,
comparison against a full redraw, resize, and dialog invalidation. The visual
layout is retained; static status data is refreshed on full redraws.
