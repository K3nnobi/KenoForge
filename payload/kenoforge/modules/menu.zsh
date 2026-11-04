# ==========================================
# KenoForge Interactive Menu
# Intelligence meets Linux
# ==========================================

_kenoforge_menu_pause() {
    if [[ "${KENOFORGE_MENU_PAUSE:-true}" != "true" ]]; then
        return 0
    fi

    echo
    read -rk 1 "?Press any key to continue..."
}

_kenoforge_menu_header() {
    if [[ "${KENOFORGE_MENU_CLEAR:-true}" == "true" ]]; then
        clear
    fi

    _kenoforge_ui_header \
        "KENOFORGE" \
        "Intelligence meets Linux"

    printf "  Version %s" "${KENOFORGE_VERSION:-0.2.0}"
    printf "  •  %s\n" "${KENOFORGE_CODENAME:-Cyber Interface}"

    echo
}

_kenoforge_menu_system() {
    while true; do
        _kenoforge_menu_header

        print -P "%F{cyan}%BSYSTEM%b%f"
        echo
        echo "  1) Machine summary"
        echo "  2) Quick status"
        echo "  3) Memory"
        echo "  4) Disks"
        echo "  5) Battery"
        echo "  6) Updates"
        echo
        echo "  0) Back"
        echo

        local choice
        read "choice?Choice: "

        case "$choice" in
            1)
                kenoforge_system
                _kenoforge_menu_pause
                ;;
            2)
                kenoforge_status
                _kenoforge_menu_pause
                ;;
            3)
                kenoforge_memory
                _kenoforge_menu_pause
                ;;
            4)
                kenoforge_disk
                _kenoforge_menu_pause
                ;;
            5)
                kenoforge_battery
                _kenoforge_menu_pause
                ;;
            6)
                kenoforge_updates
                _kenoforge_menu_pause
                ;;
            0)
                return 0
                ;;
            *)
                _kenoforge_warn "Invalid option."
                sleep 1
                ;;
        esac
    done
}

_kenoforge_menu_monitor() {
    while true; do
        _kenoforge_menu_header

        print -P "%F{cyan}%BMONITORING%b%f"
        echo
        echo "  1) Live monitor"
        echo "  2) Temperatures"
        echo "  3) GPU"
        echo "  4) Processes by CPU"
        echo "  5) Processes by memory"
        echo
        echo "  0) Back"
        echo

        local choice
        read "choice?Choice: "

        case "$choice" in
            1)
                kenoforge_monitor
                ;;
            2)
                kenoforge_temperatures
                _kenoforge_menu_pause
                ;;
            3)
                kenoforge_gpu
                _kenoforge_menu_pause
                ;;
            4)
                kenoforge_processes
                _kenoforge_menu_pause
                ;;
            5)
                kenoforge_memory_processes
                _kenoforge_menu_pause
                ;;
            0)
                return 0
                ;;
            *)
                _kenoforge_warn "Invalid option."
                sleep 1
                ;;
        esac
    done
}

_kenoforge_menu_python() {
    while true; do
        _kenoforge_menu_header

        print -P "%F{cyan}%BPYTHON%b%f"
        echo
        echo "  1) Status"
        echo "  2) Create virtual environment"
        echo "  3) Activate virtual environment"
        echo "  4) Deactivate virtual environment"
        echo "  5) List packages"
        echo "  6) Install requirements.txt"
        echo "  7) Generate requirements.txt"
        echo "  8) Update pip"
        echo
        echo "  0) Back"
        echo

        local choice
        read "choice?Choice: "

        case "$choice" in
            1)
                kenoforge_python_status
                _kenoforge_menu_pause
                ;;
            2)
                local venv_name
                read "venv_name?Environment directory [${KENOFORGE_VENV_DIR:-.venv}]: "
                kenoforge_python_create "${venv_name:-${KENOFORGE_VENV_DIR:-.venv}}"
                _kenoforge_menu_pause
                ;;
            3)
                local venv_name
                read "venv_name?Environment directory [${KENOFORGE_VENV_DIR:-.venv}]: "
                kenoforge_python_activate "${venv_name:-${KENOFORGE_VENV_DIR:-.venv}}"
                _kenoforge_menu_pause
                ;;
            4)
                kenoforge_python_deactivate
                _kenoforge_menu_pause
                ;;
            5)
                kenoforge_python_list
                _kenoforge_menu_pause
                ;;
            6)
                local requirements
                read "requirements?File [requirements.txt]: "
                kenoforge_python_requirements "${requirements:-requirements.txt}"
                _kenoforge_menu_pause
                ;;
            7)
                local requirements
                read "requirements?File [requirements.txt]: "
                kenoforge_python_freeze "${requirements:-requirements.txt}"
                _kenoforge_menu_pause
                ;;
            8)
                kenoforge_python_upgrade_pip
                _kenoforge_menu_pause
                ;;
            0)
                return 0
                ;;
            *)
                _kenoforge_warn "Invalid option."
                sleep 1
                ;;
        esac
    done
}

_kenoforge_menu_git() {
    while true; do
        _kenoforge_menu_header

        print -P "%F{cyan}%BGIT%b%f"
        echo
        echo "  1) Status"
        echo "  2) History"
        echo "  3) Branches"
        echo "  4) Changes"
        echo "  5) Staged changes"
        echo "  6) Add changes"
        echo "  7) Create commit"
        echo "  8) Pull"
        echo "  9) Push"
        echo " 10) Synchronize"
        echo
        echo "  0) Back"
        echo

        local choice
        read "choice?Choice: "

        case "$choice" in
            1)
                kenoforge_git_status
                _kenoforge_menu_pause
                ;;
            2)
                kenoforge_git_log
                _kenoforge_menu_pause
                ;;
            3)
                kenoforge_git_branches
                _kenoforge_menu_pause
                ;;
            4)
                kenoforge_git_diff
                ;;
            5)
                kenoforge_git_diff_staged
                ;;
            6)
                kenoforge_git_add
                _kenoforge_menu_pause
                ;;
            7)
                local message
                read "message?Commit message: "

                if [[ -n "$message" ]]; then
                    kenoforge_git_commit "$message"
                else
                    _kenoforge_warn "The message cannot be empty."
                fi

                _kenoforge_menu_pause
                ;;
            8)
                kenoforge_git_pull
                _kenoforge_menu_pause
                ;;
            9)
                kenoforge_git_push
                _kenoforge_menu_pause
                ;;
            10)
                kenoforge_git_sync
                _kenoforge_menu_pause
                ;;
            0)
                return 0
                ;;
            *)
                _kenoforge_warn "Invalid option."
                sleep 1
                ;;
        esac
    done
}

_kenoforge_menu_ai() {
    while true; do
        _kenoforge_menu_header

        print -P "%F{cyan}%BLOCAL INTELLIGENCE%b%f"
        echo
        printf "  Default model: %s\n" "${KENOFORGE_AI_DEFAULT_MODEL:-qwen2.5-coder:7b}"
        echo
        echo "  1) Status"
        echo "  2) Chat with the default model"
        echo "  3) List models"
        echo "  4) Running models"
        echo "  5) Download model"
        echo "  6) Remove model"
        echo "  7) Set default model"
        echo "  8) Check GPU"
        echo "  9) Start Ollama"
        echo " 10) Stop Ollama service"
        echo
        echo "  0) Back"
        echo

        local choice
        read "choice?Choice: "

        case "$choice" in
            1)
                kenoforge_ai_status
                _kenoforge_menu_pause
                ;;
            2)
                kenoforge_ai_run "${KENOFORGE_AI_DEFAULT_MODEL:-qwen2.5-coder:7b}"
                ;;
            3)
                kenoforge_ai_list
                _kenoforge_menu_pause
                ;;
            4)
                kenoforge_ai_running
                _kenoforge_menu_pause
                ;;
            5)
                local model
                read "model?Model [${KENOFORGE_AI_DEFAULT_MODEL:-qwen2.5-coder:7b}]: "
                kenoforge_ai_pull "${model:-${KENOFORGE_AI_DEFAULT_MODEL:-qwen2.5-coder:7b}}"
                _kenoforge_menu_pause
                ;;
            6)
                local model
                read "model?Model to remove: "
                kenoforge_ai_remove "$model"
                _kenoforge_menu_pause
                ;;
            7)
                local model
                read "model?New default model: "

                if [[ -n "$model" ]]; then
                    kenoforge_config_set KENOFORGE_AI_DEFAULT_MODEL "$model"
                else
                    _kenoforge_warn "The model cannot be empty."
                fi

                _kenoforge_menu_pause
                ;;
            8)
                kenoforge_ai_gpu
                _kenoforge_menu_pause
                ;;
            9)
                kenoforge_ai_start
                _kenoforge_menu_pause
                ;;
            10)
                kenoforge_ai_stop_service
                _kenoforge_menu_pause
                ;;
            0)
                return 0
                ;;
            *)
                _kenoforge_warn "Invalid option."
                sleep 1
                ;;
        esac
    done
}

_kenoforge_menu_config() {
    while true; do
        _kenoforge_menu_header

        print -P "%F{cyan}%BSETTINGS%b%f"
        echo
        echo "  1) Show settings"
        echo "  2) Change default model"
        echo "  3) Enable/disable startup screen"
        echo "  4) Enable/disable Fastfetch"
        echo "  5) Enable/disable menu clearing"
        echo "  6) Enable/disable menu pause"
        echo "  7) Change virtualenv directory"
        echo "  8) Change editor"
        echo "  9) Edit file manually"
        echo " 10) Restore defaults"
        echo
        echo "  0) Back"
        echo

        local choice
        read "choice?Choice: "

        case "$choice" in
            1)
                kenoforge_config_show
                _kenoforge_menu_pause
                ;;
            2)
                local model
                read "model?Default model: "

                if [[ -n "$model" ]]; then
                    kenoforge_config_set KENOFORGE_AI_DEFAULT_MODEL "$model"
                else
                    _kenoforge_warn "The model cannot be empty."
                fi

                _kenoforge_menu_pause
                ;;
            3)
                if [[ "${KENOFORGE_STARTUP_ENABLED:-true}" == "true" ]]; then
                    kenoforge_config_set KENOFORGE_STARTUP_ENABLED false
                else
                    kenoforge_config_set KENOFORGE_STARTUP_ENABLED true
                fi

                _kenoforge_menu_pause
                ;;
            4)
                if [[ "${KENOFORGE_STARTUP_FASTFETCH:-true}" == "true" ]]; then
                    kenoforge_config_set KENOFORGE_STARTUP_FASTFETCH false
                else
                    kenoforge_config_set KENOFORGE_STARTUP_FASTFETCH true
                fi

                _kenoforge_menu_pause
                ;;
            5)
                if [[ "${KENOFORGE_MENU_CLEAR:-true}" == "true" ]]; then
                    kenoforge_config_set KENOFORGE_MENU_CLEAR false
                else
                    kenoforge_config_set KENOFORGE_MENU_CLEAR true
                fi

                _kenoforge_menu_pause
                ;;
            6)
                if [[ "${KENOFORGE_MENU_PAUSE:-true}" == "true" ]]; then
                    kenoforge_config_set KENOFORGE_MENU_PAUSE false
                else
                    kenoforge_config_set KENOFORGE_MENU_PAUSE true
                fi

                _kenoforge_menu_pause
                ;;
            7)
                local directory
                read "directory?Virtualenv directory [.venv]: "
                kenoforge_config_set KENOFORGE_VENV_DIR "${directory:-.venv}"
                _kenoforge_menu_pause
                ;;
            8)
                local editor
                read "editor?Editor: "

                if [[ -n "$editor" ]]; then
                    kenoforge_config_set KENOFORGE_EDITOR "$editor"
                else
                    _kenoforge_warn "The editor cannot be empty."
                fi

                _kenoforge_menu_pause
                ;;
            9)
                kenoforge_config_edit
                ;;
            10)
                kenoforge_config_reset
                _kenoforge_menu_pause
                ;;
            0)
                return 0
                ;;
            *)
                _kenoforge_warn "Invalid option."
                sleep 1
                ;;
        esac
    done
}

kenoforge_menu() {
    while true; do
        _kenoforge_menu_header

        echo "  1) System"
        echo "  2) Monitoring"
        echo "  3) Local intelligence"
        echo "  4) Git"
        echo "  5) Python"
        echo "  6) Settings"
        echo "  7) Backup, restoration, and installation"
        echo "  8) KenoForge Doctor"
        echo "  9) About"
        echo " 10) Help"
        echo
        echo "  0) Exit"
        echo

        local choice
        read "choice?Choose an option: "

        case "$choice" in
            1)
                _kenoforge_menu_system
                ;;
            2)
                _kenoforge_menu_monitor
                ;;
            3)
                _kenoforge_menu_ai
                ;;
            4)
                _kenoforge_menu_git
                ;;
            5)
                _kenoforge_menu_python
                ;;
            6)
                _kenoforge_menu_config
                ;;
            7)
                kenoforge_manager
                ;;
            8)
                kenoforge_doctor
                _kenoforge_menu_pause
                ;;
            9)
                kenoforge_about
                _kenoforge_menu_pause
                ;;
            10)
                kenoforge_help
                _kenoforge_menu_pause
                ;;
            0|q|Q)
                if [[ "${KENOFORGE_MENU_CLEAR:-true}" == "true" ]]; then
                    clear
                fi
                return 0
                ;;
            *)
                _kenoforge_warn "Invalid option."
                sleep 1
                ;;
        esac
    done
}
