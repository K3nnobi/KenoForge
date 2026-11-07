# ==========================================
# KenoForge Loader
# Intelligence meets Linux
# ==========================================

export KENOFORGE_HOME="${KENOFORGE_HOME:-$HOME/.kenoforge/System/Core}"
export KENOFORGE_DATA_HOME="${KENOFORGE_DATA_HOME:-$HOME/.kenoforge}"
export KENOFORGE_USER_CONFIG="${KENOFORGE_USER_CONFIG:-$KENOFORGE_DATA_HOME/Config}"

_kenoforge_source_file() {
    local file="$1"

    if [[ -r "$file" ]]; then
        source "$file"
        return 0
    fi

    return 1
}

# Required core

_kenoforge_source_file "$KENOFORGE_HOME/core/variables.zsh"
_kenoforge_source_file "$KENOFORGE_HOME/core/exports.zsh"

# User settings

if [[ -r "$KENOFORGE_USER_CONFIG/settings.zsh" ]]; then
    _kenoforge_source_file "$KENOFORGE_USER_CONFIG/settings.zsh"
else
    _kenoforge_source_file "$KENOFORGE_HOME/config/settings.zsh"
fi

# Remaining core

_kenoforge_source_file "$KENOFORGE_HOME/core/aliases.zsh"
_kenoforge_source_file "$KENOFORGE_HOME/core/functions.zsh"

# Modules

for module_file in "$KENOFORGE_HOME"/modules/*.zsh(N); do
    _kenoforge_source_file "$module_file"
done

# Theme

# Theme in controlled order
_kenoforge_source_file "$KENOFORGE_HOME/theme/palette.zsh"
_kenoforge_source_file "$KENOFORGE_HOME/theme/colors.zsh"
_kenoforge_source_file "$KENOFORGE_HOME/theme/icons.zsh"
_kenoforge_source_file "$KENOFORGE_HOME/theme/widgets.zsh"
_kenoforge_source_file "$KENOFORGE_HOME/theme/prompt.zsh"
_kenoforge_source_file "$KENOFORGE_HOME/theme/startup.zsh"
