#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

PACKAGE_SOURCE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
TEST_ROOT="$(mktemp -d)"
PACKAGE_ROOT="${TEST_ROOT}/package"
TEST_HOME="${TEST_ROOT}/home"
MOCK_BIN="${TEST_ROOT}/mock-bin"
STATE="${TEST_ROOT}/state"
BACKUP_SOURCE="${TEST_ROOT}/backup-source"
TEST_USER="$(id -un)"

cleanup() {
  rm -rf -- "$TEST_ROOT"
}
trap cleanup EXIT

mkdir -p "$TEST_HOME" "$MOCK_BIN" "$STATE" "$BACKUP_SOURCE"
cp -a -- "$PACKAGE_SOURCE/." "$PACKAGE_ROOT/"

printf '%s\n' base > "${STATE}/installed.txt"
: > "${STATE}/foreign.txt"
printf '%s\n' \
  official-good flatpak zsh zsh-autosuggestions \
  zsh-syntax-highlighting zsh-completions python-pillow icoutils \
  papirus-icon-theme gamemode lib32-gamemode plymouth \
  > "${STATE}/official-available.txt"
printf '%s\n' aur-good zsh-theme-powerlevel10k-git icoextract \
  gnome-rounded-blur papirus-folders nvibrant \
  > "${STATE}/aur-available.txt"
printf '%s\n' true > "${STATE}/rounded-blur-state.txt"

cat > "${MOCK_BIN}/sudo" <<'EOF'
#!/usr/bin/env bash
exec "$@"
EOF

cat > "${MOCK_BIN}/pacman" <<'EOF'
#!/usr/bin/env bash
set -u
state="${KENOFORGE_TEST_STATE:?}"
case "${1:-}" in
  -Qq)
    if [[ "${2:-}" == "-m" || "${1:-}" == "-Qqm" ]]; then
      cat "${state}/foreign.txt"
    else
      cat "${state}/installed.txt"
    fi
    ;;
  -Qqm) cat "${state}/foreign.txt" ;;
  -Qqem) cat "${state}/foreign.txt" ;;
  -Qqen) cat "${state}/installed.txt" ;;
  -Qqe) cat "${state}/installed.txt"; cat "${state}/foreign.txt" ;;
  -Q) sed 's/$/ 1.0-1/' "${state}/installed.txt" ;;
  -Si)
    package="${*: -1}"
    grep -qxF "$package" "${state}/official-available.txt"
    ;;
  -Syu) exit 0 ;;
  -S)
    shift
    for package in "$@"; do
      [[ "$package" == -* ]] && continue
      grep -qxF "$package" "${state}/official-available.txt" || continue
      grep -qxF "$package" "${state}/installed.txt" || printf '%s\n' "$package" >> "${state}/installed.txt"
    done
    ;;
  -Sl) exit 0 ;;
  *) exit 0 ;;
esac
EOF

cat > "${MOCK_BIN}/yay" <<'EOF'
#!/usr/bin/env bash
set -u
state="${KENOFORGE_TEST_STATE:?}"
case "${1:-}" in
  -Si)
    package="${*: -1}"
    grep -qxF "$package" "${state}/aur-available.txt"
    ;;
  -S)
    package="${*: -1}"
    grep -qxF "$package" "${state}/aur-available.txt"
    grep -qxF "$package" "${state}/foreign.txt" || printf '%s\n' "$package" >> "${state}/foreign.txt"
    ;;
  *) exit 0 ;;
esac
EOF

cat > "${MOCK_BIN}/flatpak" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat > "${MOCK_BIN}/clear" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat > "${MOCK_BIN}/nautilus" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${KENOFORGE_TEST_STATE:?}/nautilus.log"
EOF

cat > "${MOCK_BIN}/gsettings" <<'EOF'
#!/usr/bin/env bash
case "${1:-}" in
  list-schemas) printf '%s\n' org.gnome.nautilus.preferences ;;
  set) printf '%s\n' "$*" >> "${KENOFORGE_TEST_STATE:?}/gsettings.log" ;;
esac
EOF

cat > "${MOCK_BIN}/exe-thumbnailer" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat > "${MOCK_BIN}/free" <<'EOF'
#!/usr/bin/env bash
if [[ "${LC_ALL:-}" == "C" ]]; then
  printf '%s\n' \
    '               total        used        free' \
    'Mem:            15Gi       4.4Gi       8.0Gi'
else
  printf '%s\n' \
    '               total       usada       livre' \
    'Mem.:           15Gi       4,4Gi       8,0Gi'
fi
EOF

cat > "${MOCK_BIN}/fastfetch" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${KENOFORGE_TEST_STATE:?}/fastfetch-args.txt"
# Simulate a version that uses absolute horizontal cursor movement even in pipe mode.
printf 'OS\033[10G::Arch Linux\n'
printf 'Kernel\033[10G::6.18.48-1-lts\n'
printf 'Uptime\033[10G::2 hours, 5 mins\n'
printf 'Packages\033[10G::1341 (pacman)\n'
printf 'Shell\033[10G::zsh 5.9\n'
printf 'DE\033[10G::GNOME 50.4\n'
printf 'WM\033[10G::Mutter (Wayland)\n'
printf 'Terminal\033[10G::GNOME Terminal 3.60.0\n'
printf 'Memory\033[10G::4.43 GiB / 15.30 GiB\n'
printf 'CPU\033[10G::Intel Core i7-12700K\n'
printf 'GPU\033[10G::NVIDIA RTX 4060\n'
printf 'Display\033[10G::1920x1080 @ 100 Hz\n'
EOF

cat > "${MOCK_BIN}/gnome-shell" <<'EOF'
#!/usr/bin/env bash
exit 0
EOF

cat > "${MOCK_BIN}/dconf" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == "read" && "${2:-}" == "/org/gnome/shell/extensions/blur-my-shell/rounded-blur-found" ]]; then
  cat "${KENOFORGE_TEST_STATE:?}/rounded-blur-state.txt"
fi
EOF

cat > "${MOCK_BIN}/papirus-folders" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${KENOFORGE_TEST_STATE:?}/papirus-folders.log"
EOF

cat > "${MOCK_BIN}/nvibrant" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${KENOFORGE_TEST_STATE:?}/nvibrant.log"
EOF

cat > "${MOCK_BIN}/systemctl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${KENOFORGE_TEST_STATE:?}/systemctl-user.log"
exit 0
EOF

chmod 755 "${MOCK_BIN}"/*

mkdir -p \
  "${BACKUP_SOURCE}/configs/.config/kenoforge/bin" \
  "${BACKUP_SOURCE}/configs/.config/example" \
  "${BACKUP_SOURCE}/configs/.config/gtk-4.0" \
  "${BACKUP_SOURCE}/configs/.local/share/thumbnailers" \
  "${BACKUP_SOURCE}/configs/kenoforge-config/NVIDIA" \
  "${BACKUP_SOURCE}/configs/kenoforge-config/Patches/Plymouth" \
  "${BACKUP_SOURCE}/configs/zsh-linked" \
  "${BACKUP_SOURCE}/packages" \
  "${BACKUP_SOURCE}/gnome" \
  "${BACKUP_SOURCE}/project/bin" \
  "${BACKUP_SOURCE}/project/config"

printf '%s\n' 'export TEST_RESTORED=1' > "${BACKUP_SOURCE}/configs/.zshrc"
printf '%s\n' "alias kenoforge_test='ok'" > "${BACKUP_SOURCE}/configs/.zsh_aliases"
cp -- "${BACKUP_SOURCE}/configs/.zshrc" "${BACKUP_SOURCE}/configs/zsh-linked/.zshrc"
cp -- "${BACKUP_SOURCE}/configs/.zsh_aliases" "${BACKUP_SOURCE}/configs/zsh-linked/.zsh_aliases"
printf '%s\n' legacy > "${BACKUP_SOURCE}/configs/.config/kenoforge/bin/old-manager"
printf '%s\n' restored > "${BACKUP_SOURCE}/configs/.config/example/settings.ini"
cat > "${BACKUP_SOURCE}/configs/.config/gtk-4.0/gtk.css" <<'EOF'
/* KenoForge: Nautilus transparent thumbnails */
.nautilus-window.view .thumbnail {
    background: none;
    box-shadow: none;
}
/* End KenoForge: Nautilus transparent thumbnails */
EOF
cat > "${BACKUP_SOURCE}/configs/.local/share/thumbnailers/exe-thumbnailer.thumbnailer" <<'EOF'
[Thumbnailer Entry]
TryExec=exe-thumbnailer
Exec=exe-thumbnailer -s %s %i %o
MimeType=application/x-ms-dos-executable;
EOF
cat > "${BACKUP_SOURCE}/configs/.config/gamemode.ini" <<'EOF'
; BEGIN KENOFORGE GAMEMODE BLUR
[custom]
start='/home/legacyuser/.kenoforge/System/Core/tools/gamemode-blur.sh' start
end='/home/legacyuser/.kenoforge/System/Core/tools/gamemode-blur.sh' end
; END KENOFORGE GAMEMODE BLUR
EOF
printf '%s\n' official-good official-obsolete > "${BACKUP_SOURCE}/packages/pacman-native.txt"
printf '%s\n' aur-good aur-obsolete nvibrant > "${BACKUP_SOURCE}/packages/pacman-aur.txt"
printf '%s\n' 'NVIBRANT_VALUE=512' \
  > "${BACKUP_SOURCE}/configs/kenoforge-config/NVIDIA/vibrance.conf"
cat > "${BACKUP_SOURCE}/configs/kenoforge-config/Patches/Plymouth/state.conf" <<'EOF'
FORMAT=1
MACHINE_ID=old-machine
THEME_PREVIOUS=fade-in
MKINITCPIO_ADDED=1
PLYMOUTH_HOOK_PREVIOUS_INDEX=-1
QUIET_ADDED=1
SPLASH_ADDED=1
EOF
printf '%s\n' org.example.App > "${BACKUP_SOURCE}/packages/flatpak-apps.txt"
printf '%s\n' legacy > "${BACKUP_SOURCE}/project/bin/old-manager"
printf '%s\n' 'KENOFORGE_TEST_SETTING=true' > "${BACKUP_SOURCE}/project/config/settings.zsh"

cat > "${BACKUP_SOURCE}/manifest.txt" <<'EOF'
format=kenoforge
version=1.4.1
mode=completo
created=2026-08-08T16:18:24-03:00
hostname=example-host
user=legacyuser
pacman_packages=2
aur_packages=2
flatpak_apps=1
gnome_extensions=0
has_configs=yes
has_gnome=yes
has_packages=yes
has_project=yes
EOF

(
  cd "$BACKUP_SOURCE"
  find . -type f ! -name checksums.sha256 -print0 \
    | LC_ALL=C sort -z \
    | xargs -0 sha256sum > checksums.sha256
)

mkdir -p "${TEST_HOME}/.kenoforge/Backups"
tar -C "$BACKUP_SOURCE" -czf \
  "${TEST_HOME}/.kenoforge/Backups/KenoForge-completo-test.kenoforge" .

run_as_test_user() {
  env HOME="$TEST_HOME" USER="$TEST_USER" \
    KENOFORGE_TEST_STATE="$STATE" \
    KENOFORGE_TEST_SIMULATE=1 \
    KENOFORGE_TEST_NVIDIA=1 \
    TERM=xterm-256color \
    PATH="${MOCK_BIN}:/usr/bin:/bin" "$@"
}

# Simulate a machine with 1.5.6 installed in the previous paths.
mkdir -p \
  "${TEST_HOME}/.config/kenoforge/config" \
  "${TEST_HOME}/.local/share/kenoforge-toolkit"
printf '%s\n' 'KENOFORGE_LEGACY_PREFERENCE=migrated' \
  > "${TEST_HOME}/.config/kenoforge/config/settings.zsh"
printf '%s\n' 'STARTUP_ENABLED=false' \
  > "${TEST_HOME}/.config/kenoforge/config/kenoforge.conf"
printf '%s\n' "alias legacy_alias='ok'" > "${TEST_HOME}/.zsh_aliases"
printf '%s\n' '# legacy p10k' > "${TEST_HOME}/.p10k.zsh"

run_as_test_user bash "${PACKAGE_ROOT}/install.sh" --check

# The automated environment runs as root. The disposable copy bypasses only
# this guard for the functional test; the original package remains protected
# and is tested separately for root refusal.
sed -i 's/if (( ! dry_run && ! check_only && EUID == 0 )); then/if (( 0 )); then/' \
  "${PACKAGE_ROOT}/install.sh"
run_as_test_user bash "${PACKAGE_ROOT}/install.sh"

grep -qxF 'KENOFORGE_LEGACY_PREFERENCE=migrated' \
  "${TEST_HOME}/.kenoforge/Config/settings.zsh"
grep -qxF 'STARTUP_ENABLED=false' \
  "${TEST_HOME}/.kenoforge/Config/kenoforge.conf"
grep -qxF "alias legacy_alias='ok'" \
  "${TEST_HOME}/.kenoforge/Config/Zsh/aliases.zsh"
grep -qxF '# legacy p10k' \
  "${TEST_HOME}/.kenoforge/Config/Zsh/p10k.zsh"
[[ -L "${TEST_HOME}/.zsh_aliases" ]]
[[ -L "${TEST_HOME}/.p10k.zsh" ]]

printf '%s\n' 'KENOFORGE_TEST_PREFERENCE=preserved' \
  > "${TEST_HOME}/.kenoforge/Config/settings.zsh"
run_as_test_user bash "${PACKAGE_ROOT}/install.sh"

grep -qxF 'KENOFORGE_TEST_PREFERENCE=preserved' \
  "${TEST_HOME}/.kenoforge/Config/settings.zsh"
[[ -d "${TEST_HOME}/.kenoforge/System/Core" ]]
[[ -d "${TEST_HOME}/.kenoforge/System/Toolkit" ]]
[[ -L "${TEST_HOME}/.config/kenoforge" ]]
[[ -L "${TEST_HOME}/.local/share/kenoforge-toolkit" ]]
grep -qxF 'Name=Run in Terminal' \
  "${TEST_HOME}/.local/share/applications/kenoforge-execute-terminal.desktop"
grep -qxF "Exec=\"${TEST_HOME}/.kenoforge/System/Core/tools/execute-in-terminal.sh\" %f" \
  "${TEST_HOME}/.local/share/applications/kenoforge-execute-terminal.desktop"
[[ -x "${TEST_HOME}/.kenoforge/System/Core/tools/execute-in-terminal.sh" ]]
[[ -x "${TEST_HOME}/.kenoforge/System/Core/tools/configure-gamemode-blur.sh" ]]
[[ -x "${TEST_HOME}/.kenoforge/System/Core/tools/gamemode-blur.sh" ]]
[[ -x "${TEST_HOME}/.kenoforge/System/Core/tools/configure-gnome-drag-hover.py" ]]
[[ -x "${TEST_HOME}/.kenoforge/System/Core/tools/configure-wine-compatibility.sh" ]]
[[ -x "${TEST_HOME}/.kenoforge/System/Core/tools/configure-nvibrant.sh" ]]
[[ -x "${TEST_HOME}/.kenoforge/System/Core/patches/plymouth/plymouth-patch.sh" ]]
[[ -x "${TEST_HOME}/.kenoforge/System/Core/patches/plymouth/plymouth-transform.py" ]]
[[ "$(grep -cxF 'export PATH="$HOME/.local/bin:$PATH"' "${TEST_HOME}/.bashrc")" -eq 1 ]]
[[ "$(grep -cxF 'export PATH="$HOME/.local/bin:$PATH"' "${TEST_HOME}/.zshrc")" -eq 1 ]]

sed -i '/^require_normal_user() {/,/^}/c\require_normal_user() { return 0; }' \
  "${TEST_HOME}/.config/kenoforge/bin/kenoforge-manager"
sed -i '/^require_arch() {/,/^}/c\require_arch() { return 0; }' \
  "${TEST_HOME}/.config/kenoforge/bin/kenoforge-manager"
sed -i 's/if (( EUID == 0 )); then/if (( 0 )); then/' \
  "${TEST_HOME}/.config/kenoforge/tools/configure-nautilus.sh"
sed -i 's/if (( EUID == 0 )); then/if (( 0 )); then/' \
  "${TEST_HOME}/.config/kenoforge/tools/configure-gnome-appearance.sh"
# Only the disposable fixture bypasses the Python helper root guard.
sed -i 's/if os.geteuid() == 0:/if False:/' \
  "${TEST_HOME}/.config/kenoforge/tools/nautilus-thumbnail-css.py"

mkdir -p "${TEST_HOME}/.cache/thumbnails/normal"
printf '%s\n' stale > "${TEST_HOME}/.cache/thumbnails/normal/stale.png"

grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' "${TEST_HOME}/.bashrc"
grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' "${TEST_HOME}/.zshrc"

run_restore() {
  printf '2\n1\ny\n\n0\n0\n' \
    | run_as_test_user bash "${TEST_HOME}/.config/kenoforge/bin/kenoforge-manager"
}

first_output="$(run_restore 2>&1)"
second_output="$(run_restore 2>&1)"

grep -A3 -F 'show_restore_plan "$source"' \
  "${TEST_HOME}/.config/kenoforge/bin/kenoforge-manager" \
  | grep -qF 'confirm "Execute this restoration plan?"'
[[ "$first_output" != *'is not sorted'* ]]
[[ "$second_output" != *'is not sorted'* ]]

grep -qxF "alias kenoforge_test='ok'" "${TEST_HOME}/.kenoforge/Config/Zsh/aliases.zsh"
[[ -L "${TEST_HOME}/.zsh_aliases" ]]
cmp -s "${TEST_HOME}/.zsh_aliases" "${TEST_HOME}/.kenoforge/Config/Zsh/aliases.zsh"
[[ "$(grep -cF '$HOME/.kenoforge/Config/Zsh/aliases.zsh' "${TEST_HOME}/.zshrc")" -eq 1 ]]
grep -qF '/usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh' "${TEST_HOME}/.zshrc"
grep -qF '/usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh' "${TEST_HOME}/.zshrc"
grep -qF 'autoload -Uz compinit' "${TEST_HOME}/.zshrc"
grep -qF 'VERSION="1.5.24"' "${TEST_HOME}/.config/kenoforge/bin/kenoforge-manager"
grep -qF 'Wine Compatibility Pack' \
  "${TEST_HOME}/.kenoforge/System/Core/core/afi/screens.zsh"
grep -qE '^official=.*wine.*winetricks.*cabextract.*unzip.*7zip' \
  "${TEST_HOME}/.kenoforge/System/Toolkit/profiles/gaming.conf"
[[ ! -e "${TEST_HOME}/.config/kenoforge/bin/old-manager" ]]
grep -qxF restored "${TEST_HOME}/.config/example/settings.ini"
find "${TEST_HOME}/.kenoforge/Recovered-Projects" -type f -path '*/bin/old-manager' -print -quit | grep -q .

grep -qxF official-good "${STATE}/installed.txt"
grep -qxF zsh-autosuggestions "${STATE}/installed.txt"
grep -qxF aur-good "${STATE}/foreign.txt"
grep -qxF zsh-theme-powerlevel10k-git "${STATE}/foreign.txt"
grep -qxF python-pillow "${STATE}/installed.txt"
grep -qxF icoutils "${STATE}/installed.txt"
grep -qxF icoextract "${STATE}/foreign.txt"
grep -qxF papirus-icon-theme "${STATE}/installed.txt"
grep -qxF gamemode "${STATE}/installed.txt"
grep -qxF lib32-gamemode "${STATE}/installed.txt"
grep -qxF plymouth "${STATE}/installed.txt"
grep -qxF nvibrant "${STATE}/foreign.txt"
grep -qxF gnome-rounded-blur "${STATE}/foreign.txt"
grep -qxF papirus-folders "${STATE}/foreign.txt"
grep -qxF -- '-C yellow --theme Papirus-Dark' "${STATE}/papirus-folders.log"
grep -qxF 'Exec=exe-thumbnailer -s %s %i %o' \
  "${TEST_HOME}/.local/share/thumbnailers/exe-thumbnailer.thumbnailer"
[[ "$(grep -cxF '/* KenoForge: Nautilus transparent thumbnails */' \
  "${TEST_HOME}/.config/gtk-4.0/gtk.css")" -eq 1 ]]
grep -qxF '.nautilus-image.file-thumbnail,' \
  "${TEST_HOME}/.config/gtk-4.0/gtk.css"
grep -qxF 'set org.gnome.nautilus.preferences sort-directories-first true' \
  "${STATE}/gsettings.log"
grep -qxF -- '-q' "${STATE}/nautilus.log"
[[ ! -e "${TEST_HOME}/.cache/thumbnails/normal/stale.png" ]]
grep -qF 'Nautilus Integration' \
  "${TEST_HOME}/.config/kenoforge/core/afi/screens.zsh"
grep -qF 'GNOME Visual Integration' \
  "${TEST_HOME}/.config/kenoforge/core/afi/screens.zsh"
grep -qF 'GameMode Blur Integration' \
  "${TEST_HOME}/.config/kenoforge/core/afi/screens.zsh"
grep -qF 'GNOME Drag Hover' \
  "${TEST_HOME}/.config/kenoforge/core/afi/screens.zsh"
grep -qF 'NVIDIA Vibrance' \
  "${TEST_HOME}/.config/kenoforge/core/afi/screens.zsh"
grep -qF 'Plymouth / Boot Visual' \
  "${TEST_HOME}/.config/kenoforge/core/afi/screens.zsh"
grep -qF 'Maintenance Center' \
  "${TEST_HOME}/.config/kenoforge/core/afi/screens.zsh"
for maintenance_tool in \
  hardware-profile.py pending-tasks.py update-guardian.py operating-profiles.py \
  cleanup-audit.py backup-catalog.py rollback-center.py configure-gnome-drag-hover.py; do
  [[ -x "${TEST_HOME}/.kenoforge/System/Core/tools/${maintenance_tool}" ]]
done
grep -qxF '; BEGIN KENOFORGE GAMEMODE BLUR' \
  "${TEST_HOME}/.config/gamemode.ini"
grep -qF "${TEST_HOME}/.kenoforge/System/Core/tools/gamemode-blur.sh" \
  "${TEST_HOME}/.config/gamemode.ini"
! grep -qF '/home/legacyuser/' "${TEST_HOME}/.config/gamemode.ini"
! grep -R -qF 'rounded-blur' "${TEST_HOME}/.config/gtk-4.0"

! grep -qF 'KENOFORGE_ANSI_' \
  "${TEST_HOME}/.config/kenoforge/theme/startup.zsh"
startup_output="$(run_as_test_user zsh -dfc '
  source "$HOME/.config/kenoforge/core/variables.zsh"
  source "$HOME/.config/kenoforge/theme/palette.zsh"
  source "$HOME/.config/kenoforge/theme/colors.zsh"
  source "$HOME/.config/kenoforge/theme/icons.zsh"
  source "$HOME/.config/kenoforge/theme/startup.zsh"
  KENOFORGE_STARTUP_FASTFETCH=false
  unset KENOFORGE_STARTUP_SHOWN
  kenoforge_startup
')"
[[ "$startup_output" == *'4.4Gi / 15Gi'* ]]
[[ "$startup_output" == *$'\e[38;5;45m'* ]]
[[ "$startup_output" == *$'\e[38;5;99m'* ]]

startup_wide="$(run_as_test_user zsh -dfc '
  source "$HOME/.config/kenoforge/core/variables.zsh"
  source "$HOME/.config/kenoforge/theme/palette.zsh"
  source "$HOME/.config/kenoforge/theme/colors.zsh"
  source "$HOME/.config/kenoforge/theme/icons.zsh"
  source "$HOME/.config/kenoforge/theme/startup.zsh"
  COLUMNS=140
  KENOFORGE_STARTUP_FASTFETCH=true
  unset KENOFORGE_STARTUP_SHOWN
  kenoforge_startup
')"
grep -qE 'KENOFORGE [0-9]+\.[0-9]+\.[0-9]+.*FASTFETCH' <<< "$startup_wide"
grep -qF 'GNOME Terminal 3.60.0' <<< "$startup_wide"
grep -qF -- '--config none --logo none --pipe --key-width 0 --separator ::' \
  "${STATE}/fastfetch-args.txt"
[[ "$startup_wide" != *$'\e[10G'* ]]
grep -qF 'OS        Arch Linux' <<< "$startup_wide"
[[ "$startup_wide" != *'oooo/'* ]]
STARTUP_WIDE="$startup_wide" python3 - <<'PY'
import os
import re

ansi = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
lines = [
    ansi.sub("", line)
    for line in os.environ["STARTUP_WIDE"].splitlines()
    if line
]
assert len(lines) == 17, len(lines)
split_at = lines[0].index("  ╭")
left = [line[:split_at] for line in lines]
right = [line[split_at + 2:] for line in lines]
assert all(line[split_at:split_at + 2] == "  " for line in lines)
assert len({len(line) for line in left}) == 1
assert len({len(line) for line in right}) == 1
assert all(len(line) < 140 for line in lines)

def longest_content(panel):
    return max(
        len(row[2:-2].rstrip())
        for row in panel
        if row.startswith("│")
    )

assert len(left[0]) == longest_content(left) + 4
assert len(right[0]) == longest_content(right) + 4
assert all(row[0] in "╭│├╰" and row[-1] in "╮│┤╯" for row in left)
assert all(row[0] in "╭│├╰" and row[-1] in "╮│┤╯" for row in right)
PY

startup_narrow="$(run_as_test_user zsh -dfc '
  source "$HOME/.config/kenoforge/core/variables.zsh"
  source "$HOME/.config/kenoforge/theme/palette.zsh"
  source "$HOME/.config/kenoforge/theme/colors.zsh"
  source "$HOME/.config/kenoforge/theme/icons.zsh"
  source "$HOME/.config/kenoforge/theme/startup.zsh"
  COLUMNS=70
  KENOFORGE_STARTUP_FASTFETCH=true
  unset KENOFORGE_STARTUP_SHOWN
  kenoforge_startup
')"
grep -qF 'KENOFORGE 1.5.24' <<< "$startup_narrow"
grep -qF 'FASTFETCH' <<< "$startup_narrow"
! grep -qE 'KENOFORGE [0-9]+\.[0-9]+\.[0-9]+.*FASTFETCH' <<< "$startup_narrow"

printf '%s\n' false > "${STATE}/rounded-blur-state.txt"
rounded_output="$(run_as_test_user bash \
  "${TEST_HOME}/.config/kenoforge/tools/configure-gnome-appearance.sh" --apply 2>&1)"
[[ "$rounded_output" == *'Logout/login may be required'* ]]
[[ "$rounded_output" == *'yay -S --rebuild gnome-rounded-blur'* ]]
find "${TEST_HOME}/.kenoforge/Logs" -type f -name official-still-missing.txt \
  -exec grep -qxF official-obsolete {} \; -print -quit | grep -q .
find "${TEST_HOME}/.kenoforge/Logs" -type f -name aur-still-missing.txt \
  -exec grep -qxF aur-obsolete {} \; -print -quit | grep -q .

run_backup() {
  printf '1\n1\n\n0\n0\n' \
    | run_as_test_user bash "${TEST_HOME}/.config/kenoforge/bin/kenoforge-manager"
}

mkdir -p "${TEST_HOME}/.kenoforge/Config/Zsh/Imported-Home/test-batch"
mkdir -p "${TEST_HOME}/.kenoforge/Config/Wine"
printf '%s\n' 'format=1' 'prefix_relative=.wine' \
  > "${TEST_HOME}/.kenoforge/Config/Wine/prefix-test.conf"
run_as_test_user python3 -B \
  "${TEST_HOME}/.kenoforge/System/Core/tools/operating-profiles.py" --set quiet
printf '%s\n' 'Diagnosis completed: test fixture; no packages changed.' | \
  run_as_test_user python3 -B "${TEST_HOME}/.kenoforge/System/Core/tools/doctor-report.py" --save Quick
[[ -L "${TEST_HOME}/.local/bin/kenoforge-monitor" ]]
run_as_test_user "${TEST_HOME}/.local/bin/kenoforge-monitor" --version
printf '%s\n' '# archived file for testing' \
  > "${TEST_HOME}/.kenoforge/Config/Zsh/Imported-Home/test-batch/startup.zsh"
run_backup
created_backup="$(
  find "${TEST_HOME}/.kenoforge/Backups" -maxdepth 1 -type f \
    -name 'KenoForge-completo-20*.kenoforge' -print -quit
)"
[[ -n "$created_backup" ]]
tar -tf "$created_backup" > "${STATE}/backup-list.txt"
grep -qF './configs/kenoforge-doctor-reports/report-' "${STATE}/backup-list.txt"
! grep -qF './configs/.local/bin/kenoforge-monitor' "${STATE}/backup-list.txt"
grep -qF './configs/.local/share/thumbnailers/exe-thumbnailer.thumbnailer' \
  "${STATE}/backup-list.txt"
grep -qF './configs/kenoforge-config/Zsh/Imported-Home/test-batch/startup.zsh' \
  "${STATE}/backup-list.txt"
grep -qF './configs/kenoforge-config/Maintenance/operating-profile.json' \
  "${STATE}/backup-list.txt"
grep -qF './configs/kenoforge-config/Wine/prefix-test.conf' \
  "${STATE}/backup-list.txt"
run_as_test_user env KENOFORGE_BACKUP_DIR="${TEST_HOME}/.kenoforge/Backups" \
  python3 -B \
    "${TEST_HOME}/.kenoforge/System/Core/tools/backup-catalog.py" --latest \
    | grep -qF 'KenoForge Backup Catalog'
mkdir -p "${STATE}/roundtrip"
tar -xf "$created_backup" -C "${STATE}/roundtrip"
[[ -f "${STATE}/roundtrip/configs/.zsh_aliases" && ! -L "${STATE}/roundtrip/configs/.zsh_aliases" ]]
cmp -s "${STATE}/roundtrip/configs/.zsh_aliases" \
  "${TEST_HOME}/.kenoforge/Config/Zsh/aliases.zsh"

# Toolkit delegates creation to the same Manager. Capture helpers belong to Core.
run_as_test_user bash -c '
  source "$1/payload/kenoforge/bin/kenoforge-manager"
  capture_configs "$2"
' bash "$PACKAGE_ROOT" "${STATE}/toolkit-configs"
cmp -s \
  "${TEST_HOME}/.kenoforge/Config/Zsh/Imported-Home/test-batch/startup.zsh" \
  "${STATE}/toolkit-configs/kenoforge-config/Zsh/Imported-Home/test-batch/startup.zsh"
[[ -f "${STATE}/toolkit-configs/.zsh_aliases" && ! -L "${STATE}/toolkit-configs/.zsh_aliases" ]]
find "${STATE}/toolkit-configs/kenoforge-doctor-reports" -name 'report-*.txt' -print -quit | grep -q .

# Restore this new backup under a different Home, not just the old fixture.
mkdir -p "${TEST_ROOT}/new-home"
env HOME="${TEST_ROOT}/new-home" USER="$TEST_USER" \
  PATH="${MOCK_BIN}:/usr/bin:/bin" KENOFORGE_TEST_STATE="$STATE" \
  bash -c '
    source "$1/payload/kenoforge/bin/kenoforge-manager"
    PROJECT_DIR="$1/payload/kenoforge"
    ensure_dirs
    restore_configs "$2"
  ' bash "$PACKAGE_ROOT" "${STATE}/roundtrip"
[[ -L "${TEST_ROOT}/new-home/.zsh_aliases" ]]
cmp -s "${TEST_ROOT}/new-home/.zsh_aliases" "${TEST_HOME}/.kenoforge/Config/Zsh/aliases.zsh"
cmp -s \
  "${TEST_HOME}/.kenoforge/Config/Zsh/Imported-Home/test-batch/startup.zsh" \
  "${TEST_ROOT}/new-home/.kenoforge/Config/Zsh/Imported-Home/test-batch/startup.zsh"
grep -qxF 'prefix_relative=.wine' \
  "${TEST_ROOT}/new-home/.kenoforge/Config/Wine/prefix-test.conf"
find "${TEST_ROOT}/new-home/.kenoforge/Logs/Doctor" -name 'report-*.txt' \
  -exec grep -qF 'Diagnosis completed: test fixture' {} \; -print -quit | grep -q .

printf '[OK] installation, restoration, compact startup, Nautilus, GNOME visuals, packages, Zsh, aliases, and downgrade protection.\n'
