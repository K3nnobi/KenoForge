#!/usr/bin/env python3
"""Music-only desktop host for the user-supplied MediaDeck 0.6.5.0."""
import os
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QLockFile
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow  # Register the concrete QML window wrapper.

from services.music_player import MusicPlayerService
from services.audio_visualizer import AudioVisualizerService

BASE = Path(__file__).resolve().parent


class PlayerVolume(QObject):
    """The integrated player's volume, without modifying the system sink."""
    volumeChanged = Signal()

    def __init__(self, music):
        super().__init__()
        self.music = music
        music.audio_output.volumeChanged.connect(self.volumeChanged)

    @Property(int, notify=volumeChanged)
    def volume(self):
        return round(self.music.audio_output.volume() * 100)

    @Slot(int)
    def setVolume(self, value):
        self.music.audio_output.setVolume(max(0, min(100, value)) / 100)


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("KenoForge Music")
    app.setOrganizationName("KenoForge")
    app.setQuitOnLastWindowClosed(True)

    data = Path(os.environ.get("KENOFORGE_DATA_HOME", str(Path.home() / "KenoForge"))).expanduser()
    config = data / "Config" / "MediaDeck"
    config.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(config / "player.lock"))
    # QLockFile checks PID/process liveness; a long listening session is valid.
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        print("KenoForge Music is already open, or its configuration is not writable.")
        return 1

    music = MusicPlayerService(config / "music.json", data / "Cache" / "MediaDeck" / "covers")
    visualizer = AudioVisualizerService(config / "visualizer.json")
    volume = PlayerVolume(music)
    app.aboutToQuit.connect(music.shutdown)
    app.aboutToQuit.connect(visualizer.shutdown)

    engine = QQmlApplicationEngine()
    context = engine.rootContext()
    context.setContextProperty("musicService", music)
    context.setContextProperty("visualizerService", visualizer)
    context.setContextProperty("audioService", volume)
    engine.load(QUrl.fromLocalFile(str(BASE / "ui" / "KenoMusic.qml")))
    if not engine.rootObjects():
        music.shutdown()
        visualizer.shutdown()
        return 1
    result = app.exec()
    # Destroy bindings before their Python-backed context objects disappear.
    del engine
    lock.unlock()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
