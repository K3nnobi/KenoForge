# ==========================================
# KenoForge Configuration Module
# Intelligence meets Linux
# ==========================================

_kenoforge_config_file() {
    print -r -- "${KENOFORGE_USER_CONFIG:-$HOME/.kenoforge/Config}/settings.zsh"
}

_kenoforge_config_require_file() {
    local config_file
    config_file="$(_kenoforge_config_file)"

    if [[ ! -f "$config_file" ]]; then
        _kenoforge_error "Configuration file not found."
        printf "Expected at: %s\n" "$config_file"
        return 1
    fi
}

_kenoforge_config_valid_key() {
    case "$1" in
        KENOFORGE_THEME|\
        KENOFORGE_AI_DEFAULT_MODEL|\
        KENOFORGE_STARTUP_ENABLED|\
        KENOFORGE_STARTUP_CLEAR|\
        KENOFORGE_STARTUP_FASTFETCH|\
        KENOFORGE_CONFIRM_ACTIONS|\
        KENOFORGE_UPDATE_CHECK|\
        KENOFORGE_VENV_DIR|\
        KENOFORGE_EDITOR|\
        KENOFORGE_MENU_CLEAR|\
        KENOFORGE_MENU_PAUSE)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
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

_kenoforge_config_is_boolean_key() {
    case "$1" in
        KENOFORGE_STARTUP_ENABLED|\
        KENOFORGE_STARTUP_CLEAR|\
        KENOFORGE_STARTUP_FASTFETCH|\
        KENOFORGE_CONFIRM_ACTIONS|\
        KENOFORGE_UPDATE_CHECK|\
        KENOFORGE_MENU_CLEAR|\
        KENOFORGE_MENU_PAUSE)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

_kenoforge_config_escape_value() {
    local value="$1"

    value="${value//\\/\\\\}"
    value="${value//\"/\\\"}"
    value="${value//\$/\\\$}"
    value="${value//\`/\\\`}"

    print -r -- "$value"
}

_kenoforge_config_write() {
    local key="$1"
    local value="$2"
    local config_file
    local escaped_value
    local temporary_file

    config_file="$(_kenoforge_config_file)"
    escaped_value="$(_kenoforge_config_escape_value "$value")"
    temporary_file="${config_file}.tmp.$$"

    if grep -q "^export ${key}=" "$config_file" 2>/dev/null; then
        awk \
            -v key="$key" \
            -v value="$escaped_value" \
            '
            $0 ~ "^export " key "=" {
                print "export " key "=\"" value "\""
                next
            }

            {
                print
            }
            ' "$config_file" > "$temporary_file"
    else
        cat "$config_file" > "$temporary_file"
        printf 'export %s="%s"\n' "$key" "$escaped_value" >> "$temporary_file"
    fi

    if mv "$temporary_file" "$config_file"; then
        export "$key=$value"
        return 0
    fi

    rm -f "$temporary_file"
    return 1
}

kenoforge_config_show() {
    _kenoforge_config_require_file || return 1

    echo
    print -P "%F{cyan}%BKENOFORGE CONFIG%b%f"
    print -P "%F{magenta}Current settings%f"
    echo

    printf "%-27s %s\n" "Theme:" "$KENOFORGE_THEME"
    printf "%-27s %s\n" "AI model:" "$KENOFORGE_AI_DEFAULT_MODEL"
    printf "%-27s %s\n" "Startup:" "$KENOFORGE_STARTUP_ENABLED"
    printf "%-27s %s\n" "Clear on startup:" "$KENOFORGE_STARTUP_CLEAR"
    printf "%-27s %s\n" "Startup Fastfetch:" "$KENOFORGE_STARTUP_FASTFETCH"
    printf "%-27s %s\n" "Confirm actions:" "$KENOFORGE_CONFIRM_ACTIONS"
    printf "%-27s %s\n" "Check updates:" "$KENOFORGE_UPDATE_CHECK"
    printf "%-27s %s\n" "Virtualenv directory:" "$KENOFORGE_VENV_DIR"
    printf "%-27s %s\n" "Editor:" "$KENOFORGE_EDITOR"
    printf "%-27s %s\n" "Clear menus:" "$KENOFORGE_MENU_CLEAR"
    printf "%-27s %s\n" "Pause after commands:" "$KENOFORGE_MENU_PAUSE"

    echo
    printf "File: %s\n" "$(_kenoforge_config_file)"
    echo
}

kenoforge_config_get() {
    local key="$1"

    if [[ -z "$key" ]]; then
        _kenoforge_error "Specify the setting name."
        echo
        echo "Example:"
        echo "  kenoforge config get KENOFORGE_THEME"
        return 1
    fi

    if ! _kenoforge_config_valid_key "$key"; then
        _kenoforge_error "Unknown setting: $key"
        return 1
    fi

    print -r -- "${(P)key}"
}

kenoforge_config_set() {
    _kenoforge_config_require_file || return 1

    local key="$1"
    local value="$2"

    if [[ -z "$key" || -z "$value" ]]; then
        _kenoforge_error "Specify the setting and its new value."
        echo
        echo "Example:"
        echo "  kenoforge config set KENOFORGE_THEME cyber"
        return 1
    fi

    if ! _kenoforge_config_valid_key "$key"; then
        _kenoforge_error "Setting not allowed: $key"
        return 1
    fi

    if _kenoforge_config_is_boolean_key "$key"; then
        value="${value:l}"

        if ! _kenoforge_config_valid_boolean "$value"; then
            _kenoforge_error "This setting accepts only true or false."
            return 1
        fi
    fi

    if _kenoforge_config_write "$key" "$value"; then
        _kenoforge_ok "$key changed to '$value'"
    else
        _kenoforge_error "Could not save the setting."
        return 1
    fi
}

kenoforge_config_edit() {
    _kenoforge_config_require_file || return 1

    local editor="${KENOFORGE_EDITOR:-${EDITOR:-nano}}"
    local editor_command

    editor_command="${editor%% *}"

    if ! command -v "$editor_command" >/dev/null 2>&1; then
        _kenoforge_error "Editor not found: $editor_command"
        return 1
    fi

    "$editor" "$(_kenoforge_config_file)"
}

kenoforge_config_reload() {
    _kenoforge_config_require_file || return 1

    source "$(_kenoforge_config_file)"
    _kenoforge_ok "Settings reloaded."
}

kenoforge_config_reset() {
    local config_file
    config_file="$(_kenoforge_config_file)"

    echo
    print -P "%F{yellow}%BRESTORE SETTINGS%b%f"
    echo
    echo "Current settings will be replaced with defaults."
    echo

    local confirmation
    read "confirmation?Continue? [y/N] "

    case "${confirmation:l}" in
        y|yes)
            cat > "$config_file" <<'EOF'
# ==========================================
# KenoForge User Settings
# ==========================================

export KENOFORGE_THEME="cyber"
export KENOFORGE_AI_DEFAULT_MODEL="qwen2.5-coder:7b"

export KENOFORGE_STARTUP_ENABLED="true"
export KENOFORGE_STARTUP_CLEAR="false"
export KENOFORGE_STARTUP_FASTFETCH="true"

export KENOFORGE_CONFIRM_ACTIONS="true"
export KENOFORGE_UPDATE_CHECK="true"

export KENOFORGE_VENV_DIR=".venv"
export KENOFORGE_EDITOR="${EDITOR:-nano}"

export KENOFORGE_MENU_CLEAR="true"
export KENOFORGE_MENU_PAUSE="true"
EOF

            source "$config_file"
            _kenoforge_ok "Settings restored."
            ;;
        *)
            _kenoforge_warn "Restoration cancelled."
            return 1
            ;;
    esac
}

kenoforge_config_help() {
    echo
    print -P "%F{cyan}%BKENOFORGE CONFIG%b%f"
    echo
    echo "Usage:"
    echo "  kenoforge config show"
    echo "  kenoforge config get CHAVE"
    echo "  kenoforge config set CHAVE VALOR"
    echo "  kenoforge config edit"
    echo "  kenoforge config reload"
    echo "  kenoforge config reset"
    echo
    echo "Exemplos:"
    echo "  kenoforge config set KENOFORGE_THEME cyber"
    echo "  kenoforge config set KENOFORGE_MENU_CLEAR false"
    echo "  kenoforge config set KENOFORGE_AI_DEFAULT_MODEL qwen2.5-coder:7b"
    echo
}

kenoforge_config() {
    local command="${1:-show}"

    if (( $# > 0 )); then
        shift
    fi

    case "$command" in
        show|list)
            kenoforge_config_show
            ;;
        get)
            kenoforge_config_get "$@"
            ;;
        set)
            kenoforge_config_set "$@"
            ;;
        edit)
            kenoforge_config_edit
            ;;
        reload)
            kenoforge_config_reload
            ;;
        reset)
            kenoforge_config_reset
            ;;
        help|--help|-h)
            kenoforge_config_help
            ;;
        *)
            _kenoforge_error "Unknown configuration command: $command"
            echo "Use: kenoforge config help"
            return 1
            ;;
    esac
}
