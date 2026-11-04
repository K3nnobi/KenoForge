# ==========================================
# KenoForge Manager integration
# Backup, restoration, and installation
# ==========================================

kenoforge_manager() {
    local manager="${KENOFORGE_HOME}/bin/kenoforge-manager"

    if [[ ! -x "$manager" ]]; then
        _kenoforge_error "KenoForge Manager not found or not executable: $manager"
        return 1
    fi

    "$manager"
}

ambackup() {
    kenoforge_manager
}
