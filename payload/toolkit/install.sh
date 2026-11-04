#!/usr/bin/env bash
set -Eeuo pipefail

readonly ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly TARGET="${HOME}/KenoForge/System/Toolkit"
readonly TARGET_BIN="${HOME}/.local/bin"

ensure_path_in_shell_file() {
  local file="$1"
  local line='export PATH="$HOME/.local/bin:$PATH"'

  [[ ! -e "$file" || -f "$file" ]] || return 0
  [[ ! -e "$file" || -w "$file" ]] || return 0
  [[ ! -f "$file" ]] || ! grep -qxF "$line" "$file" || return 0

  [[ -e "$file" ]] || { : > "$file"; chmod 600 -- "$file"; }
  printf '\n%s\n' "$line" >> "$file"
}

if (( EUID == 0 )); then
  printf '[ERROR] Run as your normal user, without sudo.\n' >&2
  exit 1
fi

if [[ "${ROOT}" != "${TARGET}" ]]; then
  mkdir -p -- "${TARGET}"
  cp -a -- "${ROOT}/." "${TARGET}/"
fi

chmod 755 -- \
  "${TARGET}/bin/kenoforge-console" \
  "${TARGET}/bin/kenoforge" \
  "${TARGET}/bin/kenoforge-monitor" \
  "${TARGET}/bin/kenoforge-music"

mkdir -p -- "${TARGET_BIN}"
ln -sfn -- "${TARGET}/bin/kenoforge-console" "${TARGET_BIN}/kenoforge-console"
ln -sfn -- "${TARGET}/bin/kenoforge-console" "${TARGET_BIN}/kenoforge"
ln -sfn -- "${TARGET}/bin/kenoforge-monitor" "${TARGET_BIN}/kenoforge-monitor"

ln -sfn -- "${TARGET}/bin/kenoforge-music" "${TARGET_BIN}/kenoforge-music"

ensure_path_in_shell_file "${HOME}/.bashrc"
ensure_path_in_shell_file "${HOME}/.zshrc"

printf '\nKenoForge Toolkit 1.5.23 installed.\n'
printf 'Main interface: kenoforge-console\n'
printf 'Compatible command: kenoforge\n'

if [[ ":${PATH}:" != *":${HOME}/.local/bin:"* ]]; then
  printf '\nPATH was configured for Bash and Zsh. Reopen the terminal or run:\n'
  printf '%s\n' 'export PATH="$HOME/.local/bin:$PATH"'
fi
