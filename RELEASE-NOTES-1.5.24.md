# KenoForge 1.5.24

- Install runtime, settings, logs, cache and default backups in `~/.kenoforge`.
- Move an existing `~/KenoForge` installation with its contents. Retarget
  shell imports, launchers, GameMode and the user maintenance unit.
- Refuse conflicting roots and roll back the move if installation fails.
- Restore configuration references from older backups to the hidden root.

See [MIGRATION.md](MIGRATION.md) before installing. Use
`./install.sh --dry-run` to preview the move.
