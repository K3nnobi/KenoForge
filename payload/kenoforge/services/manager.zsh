#!/usr/bin/env zsh

manager_find_script() {
    emulate -L zsh
    setopt localoptions typesetsilent nullglob

    local -a candidates
    local candidate=""

    candidates=(
        "$HOME/.kenoforge/System/Core/manager/kenoforge-manager.sh"
        "$HOME/.kenoforge/System/Core/modules/manager/kenoforge-manager.sh"
        "$HOME/.kenoforge/System/Core/modules/kenoforge-manager.sh"
        "$HOME/.kenoforge/System/Core/bin/kenoforge-manager"
        "$HOME/.local/bin/kenoforge-manager"
        "${XDG_CONFIG_HOME:-$HOME/.config}/kenoforge/bin/kenoforge-manager"
        "$HOME/.kenoforge/Projects/kenoforge-manager.sh"
    )

    for candidate in "${candidates[@]}"; do
        [[ -f "$candidate" ]] || continue
        print -r -- "$candidate"
        return 0
    done

    candidate="$(
        find "$HOME/.kenoforge/System/Core" "$HOME/.kenoforge/Projects" \
            -maxdepth 5 \
            -type f \
            \( -name 'kenoforge-manager*.sh' \
               -o -name 'kenoforge-manager' \) \
            2>/dev/null \
            | head -n 1
    )"

    [[ -n "$candidate" ]] || return 1

    print -r -- "$candidate"
}

manager_is_available() {
    emulate -L zsh

    manager_find_script >/dev/null 2>&1
}

manager_get_path() {
    emulate -L zsh

    local manager=""

    if manager="$(manager_find_script 2>/dev/null)"; then
        print -r -- "$manager"
    else
        print -r -- "Not found"
        return 1
    fi
}

manager_run() {
    emulate -L zsh
    setopt localoptions typesetsilent

    local manager=""

    manager="$(manager_find_script 2>/dev/null)" || {
        print -u2 -- "KenoForge Manager Not Found."
        return 1
    }

    if [[ -x "$manager" ]]; then
        KENOFORGE_BACKUP_DIR="$KENOFORGE_BACKUP_DIR" "$manager"
    else
        KENOFORGE_BACKUP_DIR="$KENOFORGE_BACKUP_DIR" bash "$manager"
    fi
}

manager_nautilus_helper() {
    emulate -L zsh

    local helper="$HOME/.kenoforge/System/Core/tools/configure-nautilus.sh"

    [[ -f "$helper" ]] || return 1
    print -r -- "$helper"
}

manager_configure_nautilus() {
    emulate -L zsh
    setopt localoptions typesetsilent

    local helper=""

    helper="$(manager_nautilus_helper 2>/dev/null)" || {
        print -u2 -- "The Nautilus configuration helper was not found."
        return 1
    }

    bash "$helper" --apply
}

manager_gnome_appearance_helper() {
    emulate -L zsh

    local helper="$HOME/.kenoforge/System/Core/tools/configure-gnome-appearance.sh"

    [[ -f "$helper" ]] || return 1
    print -r -- "$helper"
}

manager_configure_gnome_appearance() {
    emulate -L zsh
    setopt localoptions typesetsilent

    local helper=""

    helper="$(manager_gnome_appearance_helper 2>/dev/null)" || {
        print -u2 -- "The GNOME appearance helper was not found."
        return 1
    }

    bash "$helper" --apply
}

manager_gamemode_blur_helper() {
    emulate -L zsh

    local helper="$HOME/.kenoforge/System/Core/tools/configure-gamemode-blur.sh"

    [[ -f "$helper" ]] || return 1
    print -r -- "$helper"
}

manager_configure_gamemode_blur() {
    emulate -L zsh
    setopt localoptions typesetsilent

    local helper=""

    helper="$(manager_gamemode_blur_helper 2>/dev/null)" || {
        print -u2 -- "The GameMode + Blur configuration helper was not found."
        return 1
    }

    bash "$helper" --menu
}

manager_configure_gnome_drag_hover() {
    emulate -L zsh

    local helper="$HOME/.kenoforge/System/Core/tools/configure-gnome-drag-hover.py"
    [[ -f "$helper" && ! -L "$helper" ]] || {
        print -u2 -- "The GNOME Drag Hover helper was not found."
        return 1
    }
    (( $+commands[python3] )) || {
        print -u2 -- "Python 3 is required for GNOME Drag Hover."
        return 1
    }
    python3 -B "$helper" --menu
}

manager_configure_wine_compatibility() {
    emulate -L zsh

    local helper="$HOME/.kenoforge/System/Core/tools/configure-wine-compatibility.sh"
    [[ -f "$helper" ]] || {
        print -u2 -- "The Wine Compatibility Pack helper was not found."
        return 1
    }
    bash "$helper" --menu
}

manager_configure_capslock_nodelay() {
    emulate -L zsh

    local helper="$HOME/.kenoforge/System/Core/tools/configure-capslock-nodelay.sh"
    [[ -f "$helper" && ! -L "$helper" ]] || {
        print -u2 -- "The Caps Lock No Delay helper was not found."
        return 1
    }
    bash "$helper" --menu
}

manager_configure_firefox_chatgpt_emoji() {
    emulate -L zsh
    local helper="$HOME/.kenoforge/System/Core/tools/configure-firefox-chatgpt-emoji.py"
    [[ -f "$helper" && ! -L "$helper" ]] || {
        print -u2 -- "The Firefox / ChatGPT emoji helper was not found."
        return 1
    }
    python3 -B "$helper" --menu
}

manager_configure_nvibrant() {
    emulate -L zsh

    local helper="$HOME/.kenoforge/System/Core/tools/configure-nvibrant.sh"
    [[ -f "$helper" ]] || {
        print -u2 -- "The NVIDIA Vibrance helper was not found."
        return 1
    }
    bash "$helper" --menu
}

manager_configure_plymouth_patch() {
    emulate -L zsh

    local helper="$HOME/.kenoforge/System/Core/patches/plymouth/plymouth-patch.sh"
    [[ -f "$helper" ]] || {
        print -u2 -- "The Plymouth patch helper was not found."
        return 1
    }
    bash "$helper" --menu
}
