# ==========================================
# KenoForge Icons
# Requires a Nerd Font for complete rendering
# ==========================================

typeset -g KENOFORGE_ICON_ARCH="󰣇"
typeset -g KENOFORGE_ICON_AI="󰚩"
typeset -g KENOFORGE_ICON_CPU=""
typeset -g KENOFORGE_ICON_MEMORY=""
typeset -g KENOFORGE_ICON_DISK="󰋊"
typeset -g KENOFORGE_ICON_GPU="󰢮"
typeset -g KENOFORGE_ICON_TEMP=""
typeset -g KENOFORGE_ICON_NETWORK="󰖩"
typeset -g KENOFORGE_ICON_GIT=""
typeset -g KENOFORGE_ICON_BRANCH=""
typeset -g KENOFORGE_ICON_PYTHON=""
typeset -g KENOFORGE_ICON_FOLDER=""
typeset -g KENOFORGE_ICON_TERMINAL=""
typeset -g KENOFORGE_ICON_SETTINGS=""
typeset -g KENOFORGE_ICON_PACKAGE="󰏖"
typeset -g KENOFORGE_ICON_BATTERY=""
typeset -g KENOFORGE_ICON_SUCCESS=""
typeset -g KENOFORGE_ICON_WARNING=""
typeset -g KENOFORGE_ICON_ERROR=""
typeset -g KENOFORGE_ICON_ARROW="❯"

_kenoforge_icons_test() {
    echo
    _kenoforge_title "KENOFORGE ICON TEST"
    echo

    printf "%-18s %s\n" "Arch:" "$KENOFORGE_ICON_ARCH"
    printf "%-18s %s\n" "AI:" "$KENOFORGE_ICON_AI"
    printf "%-18s %s\n" "CPU:" "$KENOFORGE_ICON_CPU"
    printf "%-18s %s\n" "Memory:" "$KENOFORGE_ICON_MEMORY"
    printf "%-18s %s\n" "Disk:" "$KENOFORGE_ICON_DISK"
    printf "%-18s %s\n" "GPU:" "$KENOFORGE_ICON_GPU"
    printf "%-18s %s\n" "Temperature:" "$KENOFORGE_ICON_TEMP"
    printf "%-18s %s\n" "Network:" "$KENOFORGE_ICON_NETWORK"
    printf "%-18s %s\n" "Git:" "$KENOFORGE_ICON_GIT"
    printf "%-18s %s\n" "Python:" "$KENOFORGE_ICON_PYTHON"
    printf "%-18s %s\n" "Terminal:" "$KENOFORGE_ICON_TERMINAL"

    echo
}
