#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

readonly PACKAGE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
readonly VERSION="$(<"$PACKAGE_ROOT/VERSION")"
readonly TEST_ROOT="$(mktemp -d)"
readonly RUN_FILE="$TEST_ROOT/KenoForge-${VERSION}-Installer.run"

cleanup() {
    rm -rf -- "$TEST_ROOT"
}
trap cleanup EXIT

"$PACKAGE_ROOT/installer/build-run-installer.sh" "$RUN_FILE"
[[ -x "$RUN_FILE" ]]

version_output="$(KENOFORGE_RUN_IN_TERMINAL=1 "$RUN_FILE" --version)"
[[ "$version_output" == *"${VERSION}"* ]]

KENOFORGE_RUN_IN_TERMINAL=1 "$RUN_FILE" --check

mkdir -p "$TEST_ROOT/extracted"
KENOFORGE_RUN_IN_TERMINAL=1 "$RUN_FILE" --extract "$TEST_ROOT/extracted"
[[ -x "$TEST_ROOT/extracted/KenoForge-${VERSION}/install.sh" ]]
cmp -s \
    "$PACKAGE_ROOT/payload/kenoforge/theme/startup.zsh" \
    "$TEST_ROOT/extracted/KenoForge-${VERSION}/payload/kenoforge/theme/startup.zsh"

mkdir -p "$TEST_ROOT/mock-bin"
cat > "$TEST_ROOT/mock-bin/gnome-terminal" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" > "${KENOFORGE_TERMINAL_TEST_LOG:?}"
EOF
chmod 755 "$TEST_ROOT/mock-bin/gnome-terminal"

PATH="$TEST_ROOT/mock-bin:/usr/bin:/bin" \
KENOFORGE_TERMINAL_TEST_LOG="$TEST_ROOT/terminal.log" \
    "$RUN_FILE"

grep -qF 'KENOFORGE_RUN_IN_TERMINAL=1' "$TEST_ROOT/terminal.log"
grep -qF "bash $RUN_FILE" "$TEST_ROOT/terminal.log"

cp -- "$RUN_FILE" "$TEST_ROOT/tampered.run"
printf 'X' >> "$TEST_ROOT/tampered.run"
if KENOFORGE_RUN_IN_TERMINAL=1 \
    "$TEST_ROOT/tampered.run" --check \
    > "$TEST_ROOT/tampered.log" 2>&1; then
    printf '[ERROR] The tampered installer was accepted.\n' >&2
    exit 1
fi
grep -qF 'self-extracting installer failed its integrity check' \
    "$TEST_ROOT/tampered.log"

printf '[OK] .run installer: terminal, checksum, extraction, and embedded package.\n'
