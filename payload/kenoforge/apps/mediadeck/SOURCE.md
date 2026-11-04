# MediaDeck music integration

Source: user-supplied `MediaDeck-0.6.5.0-Stable-Full-Package.zip`, containing
`MediaDeck-0.6.5.0-Stable.zip`. Both inner ZIP checksums matched the supplied
SHA256SUMS.txt before extraction.

This directory retains MediaDeck's music and audio visualizer services, music
library and visualizer QML pages, and their required QML components.

KenoForge adaptations:

- A music-only desktop entry point and KenoForge window shell.
- Persistent configuration and cover cache outside the replaceable runtime.
- Atomic music configuration publication and explicit playback/capture cleanup.
- Single-instance protection using QLockFile.
- Per-player volume and optional visualization toggle.
- Controller highlights disabled in the desktop host; mouse and standard Qt
  keyboard focus are used. Controller/session/video/game services are excluded.

The original MediaDeck dedicated-session installer and boot configuration are
not part of this integration. The music feature does not run those scripts.
