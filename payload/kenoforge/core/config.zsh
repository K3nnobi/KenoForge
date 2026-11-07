# ==========================================
# KenoForge Configuration Loader
# Intelligence meets Linux
# ==========================================

export KENOFORGE_CONFIG_DIR="${KENOFORGE_CONFIG_DIR:-$HOME/.kenoforge/Config}"
export KENOFORGE_CONFIG_FILE="${KENOFORGE_CONFIG_FILE:-$KENOFORGE_CONFIG_DIR/kenoforge.conf}"

# Default values
export KENOFORGE_AI_DEFAULT_MODEL="${KENOFORGE_AI_DEFAULT_MODEL:-qwen2.5-coder:7b}"
export KENOFORGE_THEME="${KENOFORGE_THEME:-cyber}"
export KENOFORGE_STARTUP_ENABLED="${KENOFORGE_STARTUP_ENABLED:-true}"
export KENOFORGE_STARTUP_FASTFETCH="${KENOFORGE_STARTUP_FASTFETCH:-true}"
export KENOFORGE_CLEAR_MENU_ON_EXIT="${KENOFORGE_CLEAR_MENU_ON_EXIT:-true}"
export KENOFORGE_UPDATE_CHECK_AUR="${KENOFORGE_UPDATE_CHECK_AUR:-true}"
export KENOFORGE_VENV_DIR="${KENOFORGE_VENV_DIR:-.venv}"

_kenoforge_config_trim() {
    local value="$1"

    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    print -r -- "$value"
}

_kenoforge_config_valid_boolean() {
    case "${1:l}" in
        true|false)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

_kenoforge_config_apply() {
    local key="$1"
    local value="$2"

    case "$key" in
        AI_DEFAULT_MODEL)
            [[ -n "$value" ]] &&
                export KENOFORGE_AI_DEFAULT_MODEL="$value"
            ;;

        THEME)
            [[ -n "$value" ]] &&
                export KENOFORGE_THEME="$value"
            ;;

        STARTUP_ENABLED)
            if _kenoforge_config_valid_boolean "$value"; then
                export KENOFORGE_STARTUP_ENABLED="${value:l}"
            fi
            ;;

        STARTUP_FASTFETCH)
            if _kenoforge_config_valid_boolean "$value"; then
                export KENOFORGE_STARTUP_FASTFETCH="${value:l}"
            fi
            ;;

        CLEAR_MENU_ON_EXIT)
            if _kenoforge_config_valid_boolean "$value"; then
                export KENOFORGE_CLEAR_MENU_ON_EXIT="${value:l}"
            fi
            ;;

        UPDATE_CHECK_AUR)
            if _kenoforge_config_valid_boolean "$value"; then
                export KENOFORGE_UPDATE_CHECK_AUR="${value:l}"
            fi
            ;;

        VENV_DIR)
            [[ -n "$value" ]] &&
                export KENOFORGE_VENV_DIR="$value"
            ;;
    esac
}

kenoforge_config_load() {
    [[ -f "$KENOFORGE_CONFIG_FILE" ]] || return 0

    local line
    local key
    local value

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="$(_kenoforge_config_trim "$line")"

        [[ -z "$line" ]] && continue
        [[ "$line" == \#* ]] && continue
        [[ "$line" != *"="* ]] && continue

        key="${line%%=*}"
        value="${line#*=}"

        key="$(_kenoforge_config_trim "$key")"
        value="$(_kenoforge_config_trim "$value")"

        _kenoforge_config_apply "$key" "$value"
    done < "$KENOFORGE_CONFIG_FILE"
}

kenoforge_config_load
