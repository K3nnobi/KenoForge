#!/usr/bin/env python3
"""Music integration: launch guards, persistence, real QML and audio decoding.

Qt tests skip when optional player dependencies are absent. No system changes.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import wave

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "payload/kenoforge"
APP = CORE / "apps/mediadeck"
spec = importlib.util.spec_from_file_location("music_bridge", CORE / "tools/mediadeck.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class LaunchGuards(unittest.TestCase):
    def test_tty_is_rejected_before_starting_qt(self):
        with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}), \
                patch.object(bridge, "missing_modules", return_value=[]), \
                patch.object(bridge.os, "execv") as execute:
            self.assertEqual(bridge.launch(), 1)
            execute.assert_not_called()

    def test_missing_dependency_does_not_launch_or_install(self):
        with patch.object(bridge, "missing_modules", return_value=["pyside6"]), \
                patch.object(bridge.os, "execv") as execute, \
                patch.object(bridge.subprocess, "run") as run:
            self.assertEqual(bridge.launch(), 1)
            execute.assert_not_called()
            run.assert_not_called()

    def test_dependency_install_cancelled(self):
        with patch.object(bridge.os, "geteuid", return_value=1000), \
                patch.object(bridge.shutil, "which", return_value="/mock/bin"), \
                patch("builtins.input", return_value="n"), \
                patch.object(bridge.subprocess, "run") as run:
            self.assertEqual(bridge.install_dependencies(), 0)
            run.assert_not_called()

    def test_paths_with_spaces_and_shell_characters_remain_arguments(self):
        with tempfile.TemporaryDirectory(prefix="music ; path ") as folder, \
                patch.dict(os.environ, {"KENOFORGE_DATA_HOME": folder, "DISPLAY": ":1"}), \
                patch.object(bridge, "missing_modules", return_value=[]), \
                patch.object(bridge.subprocess, "Popen") as popen:
            popen.return_value.wait.side_effect = subprocess.TimeoutExpired("player", .8)
            self.assertEqual(bridge.launch(True), 0)
            self.assertEqual(popen.call_args.args[0], [sys.executable, "-B", str(bridge.APP)])
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            self.assertTrue((Path(folder) / "Logs/MediaDeck/player.log").is_file())


QT_AVAILABLE = not bridge.missing_modules()


@unittest.skipUnless(QT_AVAILABLE, "optional PySide6, NumPy, and Mutagen required")
class MusicRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        sys.path.insert(0, str(APP))
        from PySide6.QtGui import QGuiApplication
        cls.qt = QGuiApplication.instance() or QGuiApplication([])

    def setUp(self):
        from services.music_player import MusicPlayerService
        self.tmp = tempfile.TemporaryDirectory(prefix="kenoforge music ")
        self.root = Path(self.tmp.name)
        self.env = patch.dict(os.environ, {"HOME": str(self.root)})
        self.env.start()
        self.config = self.root / "Config/MediaDeck/music.json"
        self.config.parent.mkdir(parents=True)
        self.folder = self.root / "my music"
        self.folder.mkdir()
        for name in ("First track", "Second track"):
            with wave.open(str(self.folder / (name + ".wav")), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b"\0\0" * 24000)
        self.music = MusicPlayerService(self.config, self.root / "Cache/covers")
        self.music.setMusicFolder(str(self.folder))

    def tearDown(self):
        self.music.shutdown()
        self.qt.processEvents()
        self.env.stop()
        self.tmp.cleanup()

    def test_library_playlists_favorites_and_queue_survive_reload(self):
        from services.music_player import MusicPlayerService
        self.assertEqual(self.music.songCount, 2)
        track = self.music.songs[0]["path"]
        self.music.toggleFavoritePath(track)
        self.assertTrue(self.music.createPlaylist("Night drive"))
        self.assertTrue(self.music.addPathToPlaylist("Night drive", track))
        self.music.addToQueue(track)
        restored = MusicPlayerService(self.config, self.root / "Cache/covers")
        try:
            self.assertEqual(restored.favoriteSongs[0]["path"], track)
            self.assertEqual(restored.playlistSongs("Night drive")[0]["path"], track)
            self.assertEqual(restored.queueSongs[0]["path"], track)
        finally:
            restored.shutdown()

    def test_interrupted_config_publish_preserves_previous_json(self):
        original = self.config.read_bytes()
        with patch("services.music_player.os.replace", side_effect=OSError("interrupted")):
            self.music.createPlaylist("unsaved")
        self.assertEqual(self.config.read_bytes(), original)
        self.assertEqual(list(self.config.parent.glob(".music-*")), [])

    def test_real_qml_load_and_visualization(self):
        from PySide6.QtCore import QUrl, QMetaObject, Qt
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuick import QQuickWindow
        from PySide6.QtTest import QTest
        from services.audio_visualizer import AudioVisualizerService
        spec = importlib.util.spec_from_file_location("music_host", APP / "main.py")
        host = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(host)
        # Keep CI independent of a desktop audio monitor.
        visual_config = self.config.parent / "visualizer.json"
        visual_config.write_text('{"enabled": false}')
        visualizer = AudioVisualizerService(visual_config)
        volume = host.PlayerVolume(self.music)
        engine = QQmlApplicationEngine()
        warnings = []
        engine.warnings.connect(lambda items: warnings.extend(x.toString() for x in items))
        for key, value in (("musicService", self.music), ("visualizerService", visualizer), ("audioService", volume)):
            engine.rootContext().setContextProperty(key, value)
        engine.load(QUrl.fromLocalFile(str(APP / "ui/KenoMusic.qml")))
        self.assertTrue(engine.rootObjects(), warnings)
        window = engine.rootObjects()[0]
        QTest.qWait(250)
        # Construct both the library and visualizer and render a real frame.
        shot = os.environ.get("KENOFORGE_MUSIC_TEST_SCREENSHOT")
        if shot:
            self.assertTrue(window.grabWindow().save(shot))
        window.setProperty("visualization", True)
        QTest.qWait(100)
        window.setProperty("visualization", False)
        volume.setVolume(37)
        self.assertEqual(volume.volume, 37)
        self.assertEqual(warnings, [])
        window.close()
        visualizer.shutdown()
        import shiboken6
        shiboken6.delete(engine)

    def test_qt_decodes_audio_and_advances_playback(self):
        from PySide6.QtMultimedia import QAudioBufferOutput
        from PySide6.QtTest import QTest
        output = QAudioBufferOutput(self.music.player)
        buffers = []
        output.audioBufferReceived.connect(lambda audio: buffers.append(audio.frameCount()))
        self.music.player.setAudioBufferOutput(output)
        self.music.playIndex(0)
        for _ in range(40):
            QTest.qWait(50)
            if any(buffers) and self.music.position > 0:
                break
        self.assertTrue(any(buffers), self.music.errorText)
        self.assertGreater(self.music.position, 0)

    def test_real_entrypoint_rejects_second_instance(self):
        env = dict(os.environ, KENOFORGE_DATA_HOME=str(self.root),
                   QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software")
        (self.config.parent / "visualizer.json").write_text('{"enabled": false}')
        with (self.root / "startup.log").open("w+") as log:
            first = subprocess.Popen([sys.executable, "-B", str(APP / "main.py")],
                                     env=env, stdout=log, stderr=log)
            try:
                deadline = time.monotonic() + 5
                while not (self.config.parent / "player.lock").exists() and time.monotonic() < deadline:
                    if first.poll() is not None:
                        break
                    time.sleep(.05)
                self.assertIsNone(first.poll())
                self.assertTrue((self.config.parent / "player.lock").exists())
                second = subprocess.run([sys.executable, "-B", str(APP / "main.py")],
                                        env=env, capture_output=True, text=True, timeout=5)
                self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
                self.assertIn("already open", second.stdout)
            finally:
                first.terminate()
                first.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
