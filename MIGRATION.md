# Moving KenoForge to `~/.kenoforge` (1.5.24)

Close KenoForge and its player. Run `./install.sh --dry-run` from a source
checkout or extracted package outside the old data folder, then run
`./install.sh` as your usual user.

The installer moves the whole existing `~/KenoForge` directory to
`~/.kenoforge` on the same filesystem. Settings, state, backup archives,
recovery data and logs move together. The old visible path is removed.
The installer updates references in active settings and shell integrations,
recreates managed launchers, and reloads the relocated systemd unit when
possible. Open a new terminal afterward.

If both directories exist, the installer stops before merging or replacing
either one. Review the two installations before retrying. A symlink or an
unrecognized folder at the old path is also refused.

If installation fails after the move, the installer restores the old root
and the integrations it changed. The safety copy and migration journal are
retained. Archives and historical logs are kept as records; backups made
with the old root can be restored with the current backup tool. Custom backup
destinations outside the data root stay where they were.

## Earlier migration from ArchMind (1.5.21)

All project runtime names, commands, UI labels and generated integrations use
KenoForge / kenoforge / KENOFORGE. The main command is `kenoforge`;
`kenoforge-console` opens the same interface and `kenoforge-monitor` the monitor.

The installer now retires previous-brand shell integrations. It rewrites the
previous identity in regular shell startup files and user Zsh configuration,
then archives the previous project directory, config/toolkit links, launchers
and matching desktop launchers into its transaction's `previous-brand` folder.
A journal preserves original shell files and paths. Installer rollback restores
these integrations if a later installation step fails. Repeated installation
is safe. Symlinked shell files and unrecognized launcher files are refused.

Open a **new terminal** after installation. A currently running shell retains
functions already loaded from a previous release. `exec zsh -l` also replaces
that shell. No previous-name compatibility command is installed.

Personal data in the previous installation, including configuration, backups
and patch rollback state, is archived without changing its contents. Current
KenoForge configuration is retained. Archived patch state is not automatically
imported: changed markers and absolute paths require a dedicated converter.
Do not rename old backup formats or blindly replace markers in system boot,
GNOME, Firefox or keyd files. The old identity remains only in the migration
reader and its tests so it can recognize and retire old installations.

Patch Persistence and the Plymouth Themes menu are included. Migration has
been tested in disposable HOME directories; live Arch boot validation is still
required. No public repository or publication is configured by this archive.
