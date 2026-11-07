#!/usr/bin/env bash

KENOFORGE_HOME="${HOME}/.kenoforge"
KENOFORGE_SYSTEM_DIR="${KENOFORGE_HOME}/System"
KENOFORGE_CORE_DIR="${KENOFORGE_SYSTEM_DIR}/Core"
KENOFORGE_TOOLKIT_DIR="${KENOFORGE_SYSTEM_DIR}/Toolkit"
KENOFORGE_BACKUP_DIR="${KENOFORGE_BACKUP_DIR:-${KENOFORGE_HOME}/Backups}"
KENOFORGE_PROJECT_DIR="${KENOFORGE_HOME}/Projects"
KENOFORGE_LOG_DIR="${KENOFORGE_HOME}/Logs"
KENOFORGE_TEMP_DIR="${KENOFORGE_HOME}/Temp"
KENOFORGE_CONFIG_DIR="${KENOFORGE_HOME}/Config"
KENOFORGE_PROFILE_FILE="${KENOFORGE_CONFIG_DIR}/profile.conf"
KENOFORGE_ZSH_DIR="${KENOFORGE_CONFIG_DIR}/Zsh"
KENOFORGE_ALIASES_FILE="${KENOFORGE_ZSH_DIR}/aliases.zsh"
KENOFORGE_P10K_FILE="${KENOFORGE_ZSH_DIR}/p10k.zsh"

has() {
  command -v "$1" >/dev/null 2>&1
}

kenoforge_init() {
  [[ "$EUID" -ne 0 ]] || {
        echo "Do not run KenoForge as root."
    exit 1
  }

  mkdir -p \
    "$KENOFORGE_BACKUP_DIR" \
    "$KENOFORGE_PROJECT_DIR" \
    "$KENOFORGE_LOG_DIR" \
    "$KENOFORGE_TEMP_DIR" \
    "$KENOFORGE_CONFIG_DIR" \
    "$KENOFORGE_ZSH_DIR"

  if [[ ! -f "$KENOFORGE_PROFILE_FILE" ]]; then
    cat > "$KENOFORGE_PROFILE_FILE" <<'EOF'
base=true
terminal=true
gaming=false
development=false
audio=true
EOF
  fi
}

require_arch() {
  [[ -f /etc/arch-release ]] || {
        ui_error "This module requires Arch Linux or a derivative."
    return 1
  }
}

latest_kenoforge_backup() {
  find "$KENOFORGE_BACKUP_DIR" -maxdepth 1 -type f -name '*.kenoforge' \
    -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr \
    | head -n1 \
    | cut -d' ' -f2-
}

confirm() {
  local answer
  read -rp "$1 [y/N]: " answer
  [[ "${answer,,}" == "y" || "${answer,,}" == "yes" ]]
}
