# ==========================================
# KenoForge Core Functions
# Intelligence meets Linux
# ==========================================

_kenoforge_ok() {
    print -P "%F{cyan}✔%f $1"
}

_kenoforge_warn() {
    print -P "%F{yellow}⚠%f $1"
}

_kenoforge_error() {
    print -P "%F{red}✘%f $1"
}

kenoforge_about() {
    echo
    print -P "%F{cyan}╔══════════════════════════════════════╗%f"
    printf "║ %-36s ║\n" "$KENOFORGE_NAME"
    printf "║ %-36s ║\n" "$KENOFORGE_MOTTO"
    print -P "%F{cyan}╠══════════════════════════════════════╣%f"
    printf "║ Version : %-25s ║\n" "$KENOFORGE_VERSION"
    printf "║ Codename: %-25s ║\n" "$KENOFORGE_CODENAME"
    printf "║ Theme   : %-25s ║\n" "$KENOFORGE_THEME"
    printf "║ AI      : %-25s ║\n" "$KENOFORGE_AI"
    printf "║ Shell   : %-25s ║\n" "$KENOFORGE_SHELL"
    printf "║ Author  : %-25s ║\n" "$KENOFORGE_AUTHOR"
    print -P "%F{cyan}╚══════════════════════════════════════╝%f"
    echo
}

kenoforge_doctor() {
    local errors=0
    local warnings=0

    echo
    print -P "%F{cyan}KENOFORGE DOCTOR%f"
    print -P "%F{magenta}Intelligence meets Linux%f"
    echo

    print -P "%BMain files%b"

    local required_files=(
        "$KENOFORGE_HOME/core/loader.zsh"
        "$KENOFORGE_HOME/core/variables.zsh"
        "$KENOFORGE_HOME/core/exports.zsh"
        "$KENOFORGE_HOME/core/aliases.zsh"
        "$KENOFORGE_HOME/core/functions.zsh"
        "$KENOFORGE_HOME/theme/colors.zsh"
        "$KENOFORGE_HOME/theme/icons.zsh"
        "$KENOFORGE_HOME/theme/prompt.zsh"
        "$KENOFORGE_HOME/theme/startup.zsh"
        "$KENOFORGE_HOME/modules/ai.zsh"
        "$KENOFORGE_HOME/modules/git.zsh"
        "$KENOFORGE_HOME/modules/monitor.zsh"
        "$KENOFORGE_HOME/modules/network.zsh"
        "$KENOFORGE_HOME/modules/python.zsh"
        "$KENOFORGE_HOME/modules/system.zsh"
        "$KENOFORGE_HOME/modules/menu.zsh"
	"$KENOFORGE_HOME/core/config.zsh"
	"$KENOFORGE_HOME/config/kenoforge.conf"
	"$KENOFORGE_HOME/modules/config.zsh"
	"$KENOFORGE_HOME/config/settings.zsh"
	"$KENOFORGE_HOME/modules/config.zsh"
    )

    local file
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            _kenoforge_ok "${file#$KENOFORGE_HOME/}"
        else
            _kenoforge_error "${file#$KENOFORGE_HOME/}"
            (( errors++ ))
        fi
    done

    echo
    print -P "%BDependencies%b"

    local commands=(
        zsh
        git
        python
        fastfetch
        btop
        ollama
    )

    local command_name
    for command_name in "${commands[@]}"; do
        if command -v "$command_name" >/dev/null 2>&1; then
            _kenoforge_ok "$command_name"
        else
            _kenoforge_warn "$command_name is not installed"
            (( warnings++ ))
        fi
    done

    echo
    print -P "%F{cyan}%BCONFIGURATION%b%f"
    echo

    if [[ -r "$KENOFORGE_CONFIG_FILE" ]]; then
        _kenoforge_ok "Configuration file is readable"
    else
        _kenoforge_error "Configuration file is inaccessible"
        ((errors++))
    fi

    if _kenoforge_config_valid_boolean "$KENOFORGE_STARTUP_ENABLED"; then
        _kenoforge_ok "STARTUP_ENABLED has a valid value"
    else
        _kenoforge_error "STARTUP_ENABLED has an invalid value"
        ((errors++))
    fi

    if _kenoforge_config_valid_boolean "$KENOFORGE_UPDATE_CHECK_AUR"; then
        _kenoforge_ok "UPDATE_CHECK_AUR has a valid value"
    else
        _kenoforge_error "UPDATE_CHECK_AUR has an invalid value"
        ((errors++))
    fi

    echo
    print -P "%BResult%b"

    if (( errors == 0 && warnings == 0 )); then
        print -P "%F{cyan}KenoForge system is healthy.%f"
    elif (( errors == 0 )); then
        print -P "%F{yellow}KenoForge is running with $warnings warning(s).%f"
    else
        print -P "%F{red}Found $errors error(s) and $warnings warning(s).%f"
    fi

    echo
}

kenoforge_help() {
    echo
    print -P "%F{cyan}KenoForge $KENOFORGE_VERSION%f"
    echo
    echo "Usage:"
    echo "  kenoforge              Show project information"
    echo "  kenoforge about        Show project information"
    echo "  kenoforge doctor       Check files and dependencies"
    echo "  kenoforge help         Show this help"
    echo "  kenoforge system       Show the machine summary"
    echo "  kenoforge memory       Show memory usage"
    echo "  kenoforge disk         Show disks and partitions"
    echo "  kenoforge battery      Show battery charge and health"
    echo "  kenoforge updates      Check available updates"
    echo "  kenoforge status       Show a quick machine overview"
    echo "  kenoforge monitor      Open btop, htop, or top"
    echo "  kenoforge temps        Show temperatures"
    echo "  kenoforge gpu          Show GPU information"
    echo "  kenoforge processes    List processes by CPU usage"
    echo "  kenoforge memps        List processes by memory usage"
    echo "  kenoforge git          Tools for Git repositories"
    echo "  kenoforge python       Manage Python projects and environments"
    echo "  kenoforge ai           Manage Ollama and local models"
    echo "  kenoforge manager      Backup, restoration, and installation"
    echo "  kenoforge              Open the interactive center"
    echo "  kenoforge menu         Open the interactive center"
    echo "  kenoforge config       Show and modify settings"
    echo "  kenoforge config       Manage KenoForge settings"
    echo "  kenoforge config       Manage KenoForge settings"
    echo
}

kenoforge() {
    case "${1:-menu}" in
        menu|console|--console)
            zsh "$KENOFORGE_HOME/console/main.zsh"
            ;;
        --version|-v)
            printf 'KenoForge %s (AFI)\n' "$KENOFORGE_VERSION"
            ;;
        about)
            kenoforge_about
            ;;
        doctor)
            kenoforge_doctor
            ;;
        system|sys)
            kenoforge_system
            ;;
        memory|mem)
            kenoforge_memory
            ;;
        disk)
            kenoforge_disk
            ;;
        battery|bat)
            kenoforge_battery
            ;;
        updates)
            kenoforge_updates
            ;;
        manager|backup|restore|install)
            kenoforge_manager
            ;;
        status)
            kenoforge_status
            ;;
        monitor)
            kenoforge_monitor
            ;;
        temperatures|temps)
            kenoforge_temperatures
            ;;
        gpu)
            kenoforge_gpu
            ;;
        processes|ps)
            kenoforge_processes
            ;;
        memory-processes|memps)
            kenoforge_memory_processes
            ;;
        git)
            shift
            kenoforge_git "$@"
            ;;
        python|py)
            shift
            kenoforge_python "$@"
            ;;
        ai)
            shift
            kenoforge_ai "$@"
            ;;
        config|settings)
            shift
            kenoforge_config "$@"
            ;;
        config|settings)
            shift
            kenoforge_config "$@"
            ;;
        config|settings)
            shift
            kenoforge_config "$@"
            ;;
        help|--help|-h)
            kenoforge_help
            ;;
        *)
            _kenoforge_error "Unknown command: $1"
            kenoforge_help
            return 1
            ;;
    esac
}
