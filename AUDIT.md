# Wine Prefix Repair follow-up — 2026-10-22

Integrated into both Maintenance Center interfaces, Rollback Center and the
opt-in Update Guardian path. Source prefix diagnosis does not initialize Wine.
Preparation, validation, activation, prefix rollback, MIME changes and MIME
rollback have separate operator confirmations. No automatic repair is registered.

Validation completed:

- 34 Wine-specific tests with simulated Wine commands and real filesystem operations.
- 7 existing Maintenance Center regression tests.
- 12 installer safety tests on disposable copies.
- Full stable regression: installation, repeated installation, restore, Nautilus,
  GNOME integration, startup panels, package mocks, Zsh, aliases, downgrade protection.
- 7 Nautilus CSS regression tests.
- Installer integrity and Bash/Python/Zsh syntax checks.

The Wine tests cover verified snapshot data/permissions/literal symlinks, unchanged
originals, Steam prefix refusal, architecture and donor checks, autostart refusal,
process identification (including truncated Windows process names), insufficient
space, copy/update failures, explicit activation, no-clobber collision handling,
interrupted activation and failed recovery, retained repaired data on rollback,
MIME rollback and opt-in Guardian alerts without Wine execution.

**Runtime limitation:** Wine is not installed in the build environment. The host
also rejects Bubblewrap namespace creation. Thus real Wine boot/update/winecfg,
GUI socket handoff and application execution have not been validated here.
The production module probes Bubblewrap before copying prefixes and refuses to
fall back to unsandboxed execution. Target-machine validation is still required.
No personal Wine prefix or host MIME preference was changed during tests.

See `WINE-PREFIX-REPAIR.pt-BR.md` for operational restrictions and recovery.
Earlier audits follow below.

---

## Nautilus transparency follow-up — 2026-10-22

The previous helper returned early for any existing KenoForge CSS marker and
used `.nautilus-window.view .thumbnail`, requiring both classes on one node.
The repaired helper upgrades the owned block and supports the current
`.nautilus-image.file-thumbnail` selector plus the legacy Nautilus thumbnail.

Seven regression tests passed: old-block migration and backup, idempotency,
malformed-marker refusal, duplicate collapse, managed-only removal, symlink
refusal and XDG configuration paths. The rules also passed GTK3's CSS parser;
that parser check does not establish Nautilus/GTK4 visual behavior.
The full mocked stable regression suite also passed, including Nautilus setup,
restore, reinstallation, and the new selector after upgrading an old CSS block.
The installer integrity and Bash/Python/Zsh syntax checks passed.
The target machine must confirm that the displayed background is removed.

Upstream CSS inspected:
https://github.com/GNOME/nautilus/blob/HEAD/src/resources/style.css
https://github.com/GNOME/nautilus/blob/gnome-49/src/resources/style.css

---

# KenoForge 1.5.22 — Music Center integration audit

Validation on 2026-10-16, using isolated temporary homes and the supplied MediaDeck sources.

| Check | Result |
| --- | --- |
| Music integration tests | 9 passed, including real Qt/QML and WAV decoding |
| Installer safety tests | 12 passed in disposable-copy root simulation |
| Migration/install/uninstall tests | 6 passed in disposable-copy root simulation |
| Real PTY incremental navigation tests | 2 passed, wide and compact terminals |
| Self-extracting installer regression | Passed: build, check, extract, terminal handoff, tamper rejection |
| Package manifest and shell/Python/Zsh syntax | Passed by installer validation |

The music suite covers persistent playlists/favorites/queue, interrupted JSON
publication, single-instance entry point, missing dependencies, TTY rejection,
installer cancellation and detached launch arguments. QML was rendered and
visually inspected at 1440 x 850 with the software backend. The test runtime
used PySide6 6.12; those development dependencies are not bundled in the package.

Tests do not establish audible playback on physical hardware. The development
environment has no physical audio output. The real Qt decoder produced audio
buffers and advanced playback; device hot-plug, Bluetooth, hardware rendering,
and formats beyond the WAV fixture require target-machine validation.

Follow-up: the visible fullscreen button was exercised through its QML click
signal in the real Qt window. Windowed -> fullscreen -> windowed transitions
and both button labels passed. QML loaded without warnings.

The prior audit below documents inherited limitations and remains applicable.

---

# KenoForge 1.5.21 — migration audit

Date: 2026-09-19. Status: **candidate for controlled testing, not a certified
stable public release**. No GitHub publication was performed.

## Provenance and scope

The baseline is the public 1.5.18 source. Source and payload-manifest identity
were checked against its published tag. The old identity was replaced in
project-owned files and paths; external program names, GNOME extension IDs,
upstream project URLs and command semantics were retained.

All production modules were retained. In addition to namespace changes, the
installer now checks Python, provides the two public Pacman aliases, honors
XDG integration locations and detects an old installation without importing it.
A reversible runtime uninstaller was added. No package-profile, bootloader,
Wine-prefix or graphics-driver operation was run on the user's machine.

## Checks completed

- Package SHA-256 verification; Bash/Zsh syntax and Python compilation.
- All 108 pre-existing unit tests, plus 4 migration tests.
- Responsive AFI PTY checks, Monitor handoff, startup geometry and control-code
  handling, full mocked install/restore scenarios, and self-extracting installer.
- `kenoforge` and `kenoforge-console`: version and live terminal-interface launch
  in an isolated HOME without DISPLAY, Wayland or a desktop D-Bus session.
- Repeated installation; configuration preservation; idempotent public aliases;
  old-installation sentinel preservation; reversible uninstall and reinstall.
- Paths containing spaces; custom XDG config/data directories; refusal of
  symlinked integration targets; preservation of unrelated command links.
- Doctor reports, update confirmation, hardware detection, maintenance state,
  Wine, Firefox, GameMode, GNOME, Caps Lock, NVIDIA and Plymouth test suites.
- Recursive identity/privacy scan, payload file permissions and sudo call-site
  inspection. No generic `install` or `update` alias is shipped.

Two pre-existing test expectations needed migration: the Monitor byte checksum
and escaped version strings. The Monitor file was independently compared with
its baseline after applying only identity replacements; its logic is unchanged.

The test environment permits only UID 0. Root-refusal guards were bypassed ONLY
in temporary fixture copies for installation tests, as in the original suites.
The delivered installer retains its refusal to run as root. The added suite
uses a different simulated USER and a fresh HOME. A genuine second Linux
account test remains outstanding; it is not represented as completed.

## Privacy results

No developer user identifier, personal home path, known machine disk UUID,
credential signature, private key, personal Git remote, personal log or backup
was found in the candidate. No cache, bytecode or repository metadata is
included. These are code/packaging checks, not a guarantee that an unknown
secret could never evade pattern detection.

Every remaining previous-brand occurrence was reviewed:

| Location | Reason |
| --- | --- |
| `install.sh`, `detect_previous_brand` | Detect and preserve the old installation; no import/deletion |
| `MIGRATION.md` | Explicit migration limitations and old paths |
| `tests/test-migration.py` | Synthetic sentinel verifies old data is untouched |

Production payload files contain no previous-brand references.

Other scan matches are intentional: loopback `127.0.0.1` for local Ollama,
public diagnostic resolver `1.1.1.1`, the upstream Dash-to-Dock extension ID,
synthetic `/home/test` and `/home/legacyuser` test fixtures, a quote/Unicode test
path, and a regex that rejects hard-coded home paths. None identifies the
user's computer. Generated runtime reports can contain the current machine's
information; review such reports separately before sharing them.

## Inherited defects confirmed during review

These reproduce in the baseline and in the renamed candidate. They were not
rewritten during the identity migration. Existing tests passing does not
invalidate these additional findings.

| Priority | Finding and impact | Source |
| --- | --- | --- |
| High | Restore follows an existing destination directory symlink and can overwrite data outside the intended HOME subtree. A disposable probe confirmed the write. | `payload/kenoforge/bin/kenoforge-manager`, `restore_home_item` |
| High | Restore without package installation still invokes GNOME/Nautilus/GameMode apply helpers, which may install dependencies. The option does not cover all integration calls. | Manager, `restore_selected_components` |
| High | Full config backup misses Firefox profile `chrome/userContent.css` / `user.js` and the original files needed by GNOME drag-hover rollback, although related state may be saved. | Manager, `capture_configs` and patch state/backup paths |
| Medium | The Manager uses its fixed backup directory instead of the directory selected in AFI, potentially creating backups somewhere the UI is not scanning. | Manager initialization and AFI backup setting |
| Medium | Backup catalog expects colon-separated metadata while the Manager writes `key=value`; valid current archives show Unknown metadata. | `tools/backup-catalog.py`, manifest parser |
| Medium | Laptop battery functions declare Zsh's read-only `status` parameter locally. A synthetic battery fixture produces an error and missing battery output. | `theme/startup.zsh`, `modules/system.zsh` |
| Medium | Update Guardian can clear a pending rounded-blur rebuild based on a stale `true` value from the running desktop session. | `tools/update-guardian.py`, rounded-blur scan |
| Low | Some unaccented Portuguese UI messages remain; the existing translation scanner misses them. A passing language audit is not complete English-translation proof. | Manager, toolkit backup, Python shell module |

Until the high-priority restore findings are corrected, use disposable test data
for restoration validation. Do not rely on this candidate as the sole means of
recovering a real system. The migration intentionally does not claim to repair
these baseline defects.

The clean-install missing-alias issue found in the baseline *was* addressed:
Zsh now receives an idempotent block with `pacinstall` and `pacupdate`. The full
startup loader is still an explicit shell customization.

## Privileged operations and reversibility

Initial installation offers only missing Zsh/Python prerequisites; it does not
apply optional system patches. Plymouth retains apply/status/remove and saved
configuration; Caps Lock, Firefox, GNOME drag-hover, NVIDIA and GameMode retain
their existing rollback/removal mechanisms. Wine uses selected-prefix backups.
Not every older desktop helper has a dedicated rollback command. The restore
package-selection defect above is an exception that must be fixed before a
stable release, not silently treated as safe.

Uninstall archives only the toolkit runtime and removes verified owned
integrations. It does not remove system packages or reverse applied desktop and
bootloader patches. Configurations and backups are preserved.

## Remaining target-machine checks

- Real Arch clean installation as an ordinary, differently named Linux account.
- Real TTY session, GNOME logout/login, Firefox rendering and a Steam/Proton game.
- Kernel/driver and bootloader changes on suitable test hardware, including a
  reboot after Plymouth. Current tests exercise mocked detection and patch
  transformations; no real GPU or boot chain was changed.
- Restore correctness after the inherited findings are fixed; explicit handling
  of old-format archives requires a separately tested converter.

A public repository URL and distribution license have not been selected for
this candidate. No old cloud installer URL is shipped.
