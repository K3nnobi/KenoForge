# ==========================================
# KenoForge Cyber Colors
# Intelligence meets Linux
# ==========================================

typeset -g KENOFORGE_COLOR_PRIMARY="39"
typeset -g KENOFORGE_COLOR_SECONDARY="45"
typeset -g KENOFORGE_COLOR_ACCENT="99"

typeset -g KENOFORGE_COLOR_SUCCESS="82"
typeset -g KENOFORGE_COLOR_WARNING="220"
typeset -g KENOFORGE_COLOR_ERROR="196"
typeset -g KENOFORGE_COLOR_MUTED="245"
typeset -g KENOFORGE_COLOR_TEXT="255"

_kenoforge_color() {
    local color="$1"
    shift

    print -P "%F{$color}$*%f"
}

_kenoforge_bold() {
    print -P "%B$*%b"
}

_kenoforge_title() {
    print -P "%F{$KENOFORGE_COLOR_PRIMARY}%B$*%b%f"
}

_kenoforge_subtitle() {
    print -P "%F{$KENOFORGE_COLOR_ACCENT}$*%f"
}

_kenoforge_muted() {
    print -P "%F{$KENOFORGE_COLOR_MUTED}$*%f"
}

_kenoforge_success() {
    print -P "%F{$KENOFORGE_COLOR_SUCCESS}✔%f $*"
}

_kenoforge_warning() {
    print -P "%F{$KENOFORGE_COLOR_WARNING}⚠%f $*"
}

_kenoforge_failure() {
    print -P "%F{$KENOFORGE_COLOR_ERROR}✖%f $*"
}

_kenoforge_separator() {
    local width="${1:-46}"
    local line=""

    while (( ${#line} < width )); do
        line+="─"
    done

    print -P "%F{$KENOFORGE_COLOR_MUTED}${line}%f"
}
