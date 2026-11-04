#!/usr/bin/env zsh
# Quick read-only KenoForge Doctor pass after a successful package transaction.

emulate -L zsh
setopt localoptions typesetsilent

typeset -g KENOFORGE_ROOT="${${(%):-%N}:A:h:h}"
typeset -g KENOFORGE_DATA_HOME="${KENOFORGE_DATA_HOME:-$HOME/KenoForge}"

[[ -r "$KENOFORGE_ROOT/services/doctor.zsh" ]] || {
    print -u2 -- "KenoForge Doctor service is unavailable."
    exit 1
}

source "$KENOFORGE_ROOT/services/doctor.zsh"
doctor_collect_quick
doctor_record_report PostUpdate "${DOCTOR_QUICK_LINES[@]}" || true

print -r -- "KenoForge Doctor / Post-update"
print
print -rl -- "${DOCTOR_QUICK_LINES[@]}"
print
print -r -- "${DOCTOR_REPORT_NOTE:-Report was not saved.}"

(( DOCTOR_WARNINGS == 0 ))
