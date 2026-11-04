#!/usr/bin/env bash
# Compatibility entry point. The Core manager owns the backup format and restore policy.
restore_backup() {
  local mode="${1:-complete}"
  case "$mode" in
    complete) mode=completo ;;
    configs) mode=configuracoes ;;
    packages) mode=pacotes ;;
    project) mode=projeto ;;
  esac
  KENOFORGE_BACKUP_DIR="${KENOFORGE_BACKUP_DIR:-$HOME/KenoForge/Backups}" \
    bash "${KENOFORGE_CORE_DIR:-$HOME/KenoForge/System/Core}/bin/kenoforge-manager" --restore-latest "$mode"
}
