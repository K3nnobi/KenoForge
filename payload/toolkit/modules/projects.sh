#!/usr/bin/env bash

project_backup() {
  mkdir -p "$KENOFORGE_PROJECT_DIR"

  local stamp archive
  stamp="$(date +'%Y%m%d-%H%M%S')"
  archive="${KENOFORGE_BACKUP_DIR}/KenoForge-project-${stamp}.kenoforge"

  if [[ -z "$(find "$KENOFORGE_PROJECT_DIR" -mindepth 1 -print -quit)" ]]; then
    ui_warn "The project directory is empty: $KENOFORGE_PROJECT_DIR"
    return 0
  fi

  ui_info "Saving the entire KenoForge project..."

  local work
  work="$(mktemp -d "${KENOFORGE_TEMP_DIR}/project.XXXXXX")"
  mkdir -p "${work}/project"
  cp -a "${KENOFORGE_PROJECT_DIR}/." "${work}/project/"

  cat > "${work}/manifest.json" <<EOF
{
  "format": "kenoforge-project",
  "version": "2.0.0",
  "created": "$(date --iso-8601=seconds)"
}
EOF

  (
    cd "$work"
    find . -type f ! -name checksums.sha256 -print0 \
      | sort -z \
      | xargs -0 sha256sum > checksums.sha256
  )

  tar -C "$work" -caf "$archive" .
  sha256sum "$archive" > "${archive}.sha256"
  rm -rf "$work"

  ui_ok "Project saved: $archive"
}

project_restore() {
  local backup
  backup="$(
    find "$KENOFORGE_BACKUP_DIR" -maxdepth 1 -type f \
      -name 'KenoForge-project-*.kenoforge' \
      -printf '%T@ %p\n' 2>/dev/null \
      | sort -nr \
      | head -n1 \
      | cut -d' ' -f2-
  )"

  [[ -n "$backup" ]] || {
    ui_error "No project backup was found."
    return 1
  }

  ui_info "Project backup: $backup"
  confirm "Replace the current project contents?" || return 0

  local extracted safety
  extracted="$(extract_kenoforge_backup "$backup")"
  safety="${KENOFORGE_BACKUP_DIR}/project-safety-$(date +'%Y%m%d-%H%M%S')"

  if [[ -n "$(find "$KENOFORGE_PROJECT_DIR" -mindepth 1 -print -quit 2>/dev/null)" ]]; then
    mkdir -p "$safety"
    cp -a "${KENOFORGE_PROJECT_DIR}/." "$safety/"
  ui_ok "Safety copy: $safety"
  fi

  rm -rf "${KENOFORGE_PROJECT_DIR:?}/"*
  cp -a "${extracted}/project/." "$KENOFORGE_PROJECT_DIR/"
  rm -rf "$extracted"

  ui_ok "KenoForge project restored."
}
