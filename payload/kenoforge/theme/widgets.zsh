# ==========================================
# KenoForge UI Widgets
# ==========================================

_kenoforge_ui_header() {
    local title="${1:-KENOFORGE}"
    local subtitle="${2:-Intelligence meets Linux}"

    echo
    print -P "%F{$KENOFORGE_COLOR_PRIMARY}%B"
    echo "╭──────────────────────────────────────────────╮"
    printf "│  %-44s│\n" "$KENOFORGE_ICON_ARCH  $title"
    printf "│  %-44s│\n" "$subtitle"
    echo "╰──────────────────────────────────────────────╯"
    print -P "%b%f"
}

_kenoforge_ui_section() {
    local icon="$1"
    local title="$2"

    echo
    print -P "%F{$KENOFORGE_COLOR_SECONDARY}%B${icon}  ${title}%b%f"
    _kenoforge_separator 46
}

_kenoforge_ui_item() {
    local label="$1"
    local value="$2"
    local icon="${3:-›}"

    printf "  %s  %-17s %s\n" "$icon" "$label" "$value"
}

_kenoforge_ui_status() {
    local state="$1"
    shift

    case "$state" in
        ok|success)
            print -P "  %F{$KENOFORGE_COLOR_SUCCESS}${KENOFORGE_ICON_SUCCESS}%f $*"
            ;;
        warning|warn)
            print -P "  %F{$KENOFORGE_COLOR_WARNING}${KENOFORGE_ICON_WARNING}%f $*"
            ;;
        error|fail)
            print -P "  %F{$KENOFORGE_COLOR_ERROR}${KENOFORGE_ICON_ERROR}%f $*"
            ;;
        *)
            print -r -- "  • $*"
            ;;
    esac
}

_kenoforge_ui_progress() {
    local value="${1:-0}"
    local width="${2:-20}"
    local filled=""
    local empty=""
    local filled_count
    local empty_count

    (( value < 0 )) && value=0
    (( value > 100 )) && value=100

    filled_count=$(( value * width / 100 ))
    empty_count=$(( width - filled_count ))

    while (( ${#filled} < filled_count )); do
        filled+="█"
    done

    while (( ${#empty} < empty_count )); do
        empty+="░"
    done

    if (( value >= 90 )); then
        print -P "%F{$KENOFORGE_COLOR_ERROR}${filled}%f%F{$KENOFORGE_COLOR_MUTED}${empty}%f"
    elif (( value >= 70 )); then
        print -P "%F{$KENOFORGE_COLOR_WARNING}${filled}%f%F{$KENOFORGE_COLOR_MUTED}${empty}%f"
    else
        print -P "%F{$KENOFORGE_COLOR_SECONDARY}${filled}%f%F{$KENOFORGE_COLOR_MUTED}${empty}%f"
    fi
}
