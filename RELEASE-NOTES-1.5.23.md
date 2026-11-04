# KenoForge 1.5.23

KenoForge continues ArchMind under a new name in this repository. The previous
1.5.18 release remains available. Install as your normal user and open a new
terminal afterward; see [MIGRATION.md](MIGRATION.md) for the handling of legacy
shell integrations and archived data.

- Backups now cover maintenance state, Core and Toolkit, custom MIME launchers,
  and managed Wine recovery data. The new format validates files and symlinks,
  protects earlier archives, and keeps older runtime snapshots separate from
  the installed code.
- Wine Prefix Repair diagnoses broken Wine/Proton links and prepares a repair
  in a separate copy. Activation and rollback remain explicit. Recovered Wine
  snapshots can be imported offline to a new prefix path.
- Music Center adds the MediaDeck player and fullscreen control. The Nautilus
  integration restores transparent backgrounds for executable thumbnails.

Create a new backup after upgrading. Existing archives retain their original
coverage. Active Wine prefixes and personal media need a separate backup.
See [BACKUPS.pt-BR.md](BACKUPS.pt-BR.md) for details.

The packaged update passed 76 automated Python tests and the integrated
installation and restoration checks in disposable environments.
See [VALIDATION-BACKUPS.md](VALIDATION-BACKUPS.md) for test scope.
