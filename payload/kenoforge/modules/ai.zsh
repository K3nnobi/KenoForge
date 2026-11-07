# ==========================================
# KenoForge AI Module
# Ollama and Local Models
# Intelligence meets Linux
# ==========================================

_kenoforge_ai_require_ollama() {
    if ! command -v ollama >/dev/null 2>&1; then
        _kenoforge_error "Ollama is not installed."
        echo
        echo "See:"
        echo "  kenoforge ai install-help"
        return 1
    fi
}

_kenoforge_ai_service_running() {
    if command -v systemctl >/dev/null 2>&1; then
        systemctl is-active --quiet ollama 2>/dev/null && return 0
        systemctl --user is-active --quiet ollama 2>/dev/null && return 0
    fi

    pgrep -x ollama >/dev/null 2>&1
}

_kenoforge_ai_model_exists() {
    local model="$1"

    ollama list 2>/dev/null |
        awk 'NR > 1 {print $1}' |
        grep -Fxq -- "$model"
}

kenoforge_ai_status() {
    echo
    print -P "%F{cyan}%BKENOFORGE AI%b%f"
    print -P "%F{magenta}Local intelligence status%f"
    echo

    if ! command -v ollama >/dev/null 2>&1; then
        printf "%-18s %s\n" "Ollama:" "not installed"
        printf "%-18s %s\n" "Default model:" "$KENOFORGE_AI_DEFAULT_MODEL"
        echo
        _kenoforge_warn "The module is loaded, but Ollama was not found."
        return 1
    fi

    printf "%-18s %s\n" "Executable:" "$(command -v ollama)"

    local version
    version="$(ollama --version 2>&1 | head -n 1)"
    printf "%-18s %s\n" "Version:" "$version"

    if _kenoforge_ai_service_running; then
        printf "%-18s %s\n" "Service:" "active"
    else
        printf "%-18s %s\n" "Service:" "inactive"
    fi

    printf "%-18s %s\n" "Default model:" "$KENOFORGE_AI_DEFAULT_MODEL"

    local model_count
    model_count="$(
        ollama list 2>/dev/null |
        awk 'NR > 1 && NF {count++} END {print count + 0}'
    )"

    printf "%-18s %s\n" "Local models:" "$model_count"

    if command -v nvidia-smi >/dev/null 2>&1; then
        local gpu_name
        gpu_name="$(
            nvidia-smi \
                --query-gpu=name \
                --format=csv,noheader \
                2>/dev/null |
            head -n 1
        )"

        printf "%-18s %s\n" "NVIDIA GPU:" "${gpu_name:-not detected}"
    elif command -v lspci >/dev/null 2>&1; then
        local gpu_name
        gpu_name="$(
            lspci |
            grep -Ei 'vga|3d|display' |
            head -n 1 |
            sed 's/^[^ ]* //'
        )"

        printf "%-18s %s\n" "GPU:" "${gpu_name:-not detected}"
    fi

    echo
}

kenoforge_ai_start() {
    _kenoforge_ai_require_ollama || return 1

    if _kenoforge_ai_service_running; then
        _kenoforge_ok "The Ollama service is already active."
        return 0
    fi

    if systemctl list-unit-files ollama.service >/dev/null 2>&1; then
        sudo systemctl start ollama
    elif systemctl --user list-unit-files ollama.service >/dev/null 2>&1; then
        systemctl --user start ollama
    else
        _kenoforge_warn "systemd service not found."
        echo "Starting ollama serve in the background..."

        mkdir -p "$HOME/.kenoforge/Logs" || return 1

        nohup ollama serve \
            >"$HOME/.kenoforge/Logs/ollama.log" \
            2>&1 &

        sleep 2
    fi

    if _kenoforge_ai_service_running; then
        _kenoforge_ok "Ollama started."
    else
        _kenoforge_error "Could not start Ollama."
        return 1
    fi
}

kenoforge_ai_stop_service() {
    _kenoforge_ai_require_ollama || return 1

    if ! _kenoforge_ai_service_running; then
        _kenoforge_warn "The Ollama service is already inactive."
        return 0
    fi

    if systemctl is-active --quiet ollama 2>/dev/null; then
        sudo systemctl stop ollama
    elif systemctl --user is-active --quiet ollama 2>/dev/null; then
        systemctl --user stop ollama
    else
        pkill -x ollama
    fi

    if _kenoforge_ai_service_running; then
        _kenoforge_error "The service is still active."
        return 1
    fi

    _kenoforge_ok "Ollama service stopped."
}

kenoforge_ai_restart() {
    _kenoforge_ai_require_ollama || return 1

    if systemctl list-unit-files ollama.service >/dev/null 2>&1; then
        sudo systemctl restart ollama
    elif systemctl --user list-unit-files ollama.service >/dev/null 2>&1; then
        systemctl --user restart ollama
    else
        kenoforge_ai_stop_service
        kenoforge_ai_start
        return
    fi

    _kenoforge_ok "Ollama service restarted."
}

kenoforge_ai_logs() {
    _kenoforge_ai_require_ollama || return 1

    if systemctl list-unit-files ollama.service >/dev/null 2>&1; then
        journalctl -u ollama -n 100 --no-pager
    elif systemctl --user list-unit-files ollama.service >/dev/null 2>&1; then
        journalctl --user -u ollama -n 100 --no-pager
    elif [[ -f "$HOME/.kenoforge/Logs/ollama.log" ]]; then
        tail -n 100 "$HOME/.kenoforge/Logs/ollama.log"
    else
        _kenoforge_warn "No log file was found."
        return 1
    fi
}

kenoforge_ai_list() {
    _kenoforge_ai_require_ollama || return 1

    echo
    print -P "%F{cyan}%BINSTALLED MODELS%b%f"
    echo

    ollama list
    echo
}

kenoforge_ai_running() {
    _kenoforge_ai_require_ollama || return 1

    echo
    print -P "%F{cyan}%BRUNNING MODELS%b%f"
    echo

    ollama ps
    echo
}

kenoforge_ai_pull() {
    _kenoforge_ai_require_ollama || return 1

    local model="${1:-$KENOFORGE_AI_DEFAULT_MODEL}"

    echo
    print -P "%F{cyan}%BDOWNLOADING MODEL%b%f"
    echo
    printf "Model: %s\n\n" "$model"

    ollama pull "$model"
}

kenoforge_ai_remove() {
    _kenoforge_ai_require_ollama || return 1

    local model="$1"

    if [[ -z "$model" ]]; then
        _kenoforge_error "Specify the model to remove."
        echo
        echo "Example:"
        echo "  kenoforge ai remove qwen2.5-coder:3b"
        return 1
    fi

    if ! _kenoforge_ai_model_exists "$model"; then
        _kenoforge_error "Model '$model' is not installed."
        return 1
    fi

    echo
    print -P "%F{yellow}%BREMOVE MODEL%b%f"
    echo
    printf "Model: %s\n\n" "$model"

    local confirmation
    read "confirmation?Remove permanently? [y/N] "

    case "${confirmation:l}" in
        y|yes)
            ollama rm "$model"
            ;;
        *)
            _kenoforge_warn "Removal cancelled."
            return 1
            ;;
    esac
}

kenoforge_ai_run() {
    _kenoforge_ai_require_ollama || return 1

    local model="${1:-$KENOFORGE_AI_DEFAULT_MODEL}"

    if (( $# > 0 )); then
        shift
    fi

    if ! _kenoforge_ai_service_running; then
        _kenoforge_warn "The Ollama service is inactive."
        kenoforge_ai_start || return 1
    fi

    if ! _kenoforge_ai_model_exists "$model"; then
        _kenoforge_warn "Model '$model' is not installed yet."

        local confirmation
        read "confirmation?Download the model now? [y/N] "

        case "${confirmation:l}" in
            y|yes)
                ollama pull "$model" || return 1
                ;;
            *)
                _kenoforge_warn "Execution cancelled."
                return 1
                ;;
        esac
    fi

    if (( $# > 0 )); then
        ollama run "$model" "$*"
    else
        ollama run "$model"
    fi
}

kenoforge_ai_stop_model() {
    _kenoforge_ai_require_ollama || return 1

    local model="${1:-$KENOFORGE_AI_DEFAULT_MODEL}"

    ollama stop "$model"
}

kenoforge_ai_set_default() {
    local model="$1"

    if [[ -z "$model" ]]; then
        _kenoforge_error "Specify the default model."
        echo
        echo "Example:"
        echo "  kenoforge ai default qwen2.5-coder:7b"
        return 1
    fi

    local variables_file="$KENOFORGE_HOME/core/variables.zsh"

    if grep -q '^export KENOFORGE_AI_DEFAULT_MODEL=' "$variables_file" 2>/dev/null; then
        sed -i \
            "s|^export KENOFORGE_AI_DEFAULT_MODEL=.*|export KENOFORGE_AI_DEFAULT_MODEL=\"$model\"|" \
            "$variables_file"
    else
        echo \
            "export KENOFORGE_AI_DEFAULT_MODEL=\"$model\"" \
            >> "$variables_file"
    fi

    export KENOFORGE_AI_DEFAULT_MODEL="$model"

    _kenoforge_ok "Default model changed to '$model'."
}

kenoforge_ai_gpu() {
    _kenoforge_ai_require_ollama || return 1

    echo
    print -P "%F{cyan}%BAI AND GPU%b%f"
    echo

    if command -v nvidia-smi >/dev/null 2>&1; then
        nvidia-smi
        echo
        print -P "%BOllama processes%b"
        ollama ps
    else
        _kenoforge_warn "nvidia-smi was not found."
        echo
        echo "Loaded models:"
        ollama ps
    fi

    echo
}

kenoforge_ai_install_help() {
    echo
    print -P "%F{cyan}%BOLLAMA INSTALLATION%b%f"
    echo
    echo "On Arch Linux, first search the repositories:"
    echo
    echo "  pacman -Ss ollama"
    echo
    echo "Then install the package suitable for your GPU."
    echo
    echo "After installation:"
    echo
    echo "  sudo systemctl enable --now ollama"
    echo
    echo "Validate with:"
    echo
    echo "  ollama --version"
    echo "  kenoforge ai status"
    echo
}

kenoforge_ai() {
    local command="${1:-status}"

    if (( $# > 0 )); then
        shift
    fi

    case "$command" in
        status)
            kenoforge_ai_status
            ;;
        start)
            kenoforge_ai_start
            ;;
        stop-service)
            kenoforge_ai_stop_service
            ;;
        restart)
            kenoforge_ai_restart
            ;;
        logs)
            kenoforge_ai_logs
            ;;
        list|models)
            kenoforge_ai_list
            ;;
        running|ps)
            kenoforge_ai_running
            ;;
        pull|download)
            kenoforge_ai_pull "$@"
            ;;
        remove|rm)
            kenoforge_ai_remove "$@"
            ;;
        run|chat)
            kenoforge_ai_run "$@"
            ;;
        stop)
            kenoforge_ai_stop_model "$@"
            ;;
        default)
            kenoforge_ai_set_default "$@"
            ;;
        gpu)
            kenoforge_ai_gpu
            ;;
        install-help)
            kenoforge_ai_install_help
            ;;
        help|--help|-h)
            echo
            print -P "%F{cyan}KenoForge AI%f"
            echo
            echo "Usage:"
            echo "  kenoforge ai status"
            echo "  kenoforge ai start"
            echo "  kenoforge ai stop-service"
            echo "  kenoforge ai restart"
            echo "  kenoforge ai logs"
            echo "  kenoforge ai list"
            echo "  kenoforge ai running"
            echo "  kenoforge ai pull [model]"
            echo "  kenoforge ai remove model"
            echo "  kenoforge ai run [model] [question]"
            echo "  kenoforge ai stop [model]"
            echo "  kenoforge ai default model"
            echo "  kenoforge ai gpu"
            echo
            ;;
        *)
            _kenoforge_error "Unknown AI command: $command"
            echo "Use: kenoforge ai help"
            return 1
            ;;
    esac
}

# Direct shortcuts

ai() {
    kenoforge_ai_run "$@"
}

qwen() {
    kenoforge_ai_run "$KENOFORGE_AI_DEFAULT_MODEL" "$@"
}

aimodels() {
    kenoforge_ai_list
}

aistatus() {
    kenoforge_ai_status
}

aigpu() {
    kenoforge_ai_gpu
}
