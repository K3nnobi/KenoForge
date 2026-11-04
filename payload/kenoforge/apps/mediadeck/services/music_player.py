import json
import os
import tempfile
import random
import subprocess
import hashlib
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, QTimer
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QMediaDevices

try:
    from mutagen import File as MutagenFile
except Exception:
    MutagenFile = None


AUDIO_EXTENSIONS = {
    ".mp3", ".flac", ".ogg", ".oga", ".opus",
    ".wav", ".m4a", ".aac", ".wma"
}


class MusicPlayerService(QObject):
    libraryChanged = Signal()
    currentChanged = Signal()
    playbackChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    folderChanged = Signal()
    shuffleChanged = Signal()
    repeatChanged = Signal()
    errorChanged = Signal()
    favoritesChanged = Signal()
    recentsChanged = Signal()
    queueChanged = Signal()
    playlistsChanged = Signal()

    def __init__(self, config_file: Path, cache_dir=None):
        super().__init__()

        self.config_file = Path(config_file)
        self.cache_dir = Path(cache_dir) if cache_dir else self.config_file.parent.parent / "cache" / "covers"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._songs = []
        self._current_index = -1
        self._music_folder = ""
        self._shuffle = False
        self._repeat = False
        self._error_text = ""

        self._favorites = set()
        self._recents = []
        self._last_track_path = ""
        self._last_position = 0
        self._queue = []
        self._playlists = {}

        # Keep the internal player attached to the system's *current* default
        # output.  This matters on the H61 appliance: a Bluetooth sink may
        # appear after playback already started on HDMI.  Qt Multimedia can
        # switch QAudioOutput devices live without rebuilding the track.
        self.media_devices = QMediaDevices(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(1.0)
        self._sync_default_audio_device()
        self.media_devices.audioOutputsChanged.connect(self._sync_default_audio_device)

        # Fallback check for backends that update the default route without
        # changing the output-device list.  This is cheap: no shell command or
        # PipeWire polling is performed.
        self.audio_device_timer = QTimer(self)
        self.audio_device_timer.timeout.connect(self._sync_default_audio_device)
        self.audio_device_timer.start(1000)

        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self.durationChanged)
        self.player.playbackStateChanged.connect(self.playbackChanged)
        self.player.mediaStatusChanged.connect(self._on_media_status)
        self.player.errorOccurred.connect(self._on_error)

        self._load_config()

        if self._music_folder:
            self.scanLibrary()
        else:
            default = self._detect_default_music_folder()
            if default:
                self._music_folder = str(default)
                self.folderChanged.emit()
                self.scanLibrary()

        self._restore_last_track()


    @staticmethod
    def _audio_device_key(device):
        try:
            return bytes(device.id())
        except Exception:
            try:
                return str(device.id())
            except Exception:
                return b""

    @Slot()
    def _sync_default_audio_device(self):
        try:
            default_device = QMediaDevices.defaultAudioOutput()
            if default_device.isNull():
                return
            current_device = self.audio_output.device()
            if self._audio_device_key(default_device) == self._audio_device_key(current_device):
                return
            self.audio_output.setDevice(default_device)
        except Exception as exc:
            # Never let hot-plug routing interrupt playback/UI.
            print(f"[MediaDeck] Falha ao atualizar saída de áudio: {exc}")

    def _detect_default_music_folder(self):
        candidates = []

        try:
            result = subprocess.check_output(
                ["xdg-user-dir", "MUSIC"],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=1
            ).strip()
            if result:
                candidates.append(Path(result))
        except Exception:
            pass

        candidates.extend([
            Path.home() / "Music",
            Path.home() / "Música",
            Path.home() / "Musicas",
        ])

        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate

        return None

    def _load_config(self):
        try:
            if self.config_file.exists():
                data = json.loads(self.config_file.read_text(encoding="utf-8"))

                folder = data.get("music_folder", "")
                if folder and Path(folder).expanduser().is_dir():
                    self._music_folder = str(Path(folder).expanduser().resolve())

                self._favorites = set(data.get("favorites", []))
                self._recents = list(data.get("recents", []))[:30]
                self._last_track_path = str(data.get("last_track_path", "") or "")
                self._last_position = int(data.get("last_position", 0) or 0)
                self._shuffle = bool(data.get("shuffle", False))
                self._repeat = bool(data.get("repeat", False))
                self._queue = list(data.get("queue", []))
                raw_playlists = data.get("playlists", {})
                self._playlists = raw_playlists if isinstance(raw_playlists, dict) else {}

        except Exception:
            pass

    def _save_config(self):
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "music_folder": self._music_folder,
                "favorites": sorted(self._favorites),
                "recents": self._recents[:30],
                "last_track_path": self._last_track_path,
                "last_position": int(self._last_position),
                "shuffle": self._shuffle,
                "repeat": self._repeat,
                "queue": self._queue,
                "playlists": self._playlists,
            }

            # Publish complete JSON atomically; an interrupted write preserves
            # the previous library, favorites, queue, and playlists.
            fd, temporary = tempfile.mkstemp(prefix=".music-", dir=self.config_file.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False)
                    handle.write("\n")
                os.replace(temporary, self.config_file)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

        except Exception as exc:
            print(f"[MediaDeck] Não foi possível salvar music.json: {exc}")

    def _extract_cover(self, path: Path, mutagen_audio):
        if mutagen_audio is None:
            return ""

        try:
            image_bytes = None
            mime = "image/jpeg"

            # FLAC / files exposing .pictures
            pictures = getattr(mutagen_audio, "pictures", None)
            if pictures:
                picture = pictures[0]
                image_bytes = picture.data
                mime = getattr(picture, "mime", None) or "image/jpeg"

            # MP3 ID3 APIC frames
            if image_bytes is None:
                tags = getattr(mutagen_audio, "tags", None)
                if tags is not None and hasattr(tags, "values"):
                    for frame in tags.values():
                        if frame.__class__.__name__ == "APIC":
                            image_bytes = getattr(frame, "data", None)
                            mime = getattr(frame, "mime", None) or "image/jpeg"
                            if image_bytes:
                                break

            # MP4/M4A covr
            if image_bytes is None:
                tags = getattr(mutagen_audio, "tags", None)
                if tags:
                    covr = tags.get("covr")
                    if covr:
                        image_bytes = bytes(covr[0])
                        mime = "image/jpeg"

            if not image_bytes:
                return ""

            digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()
            ext = ".png" if "png" in str(mime).lower() else ".jpg"
            cover_path = self.cache_dir / f"{digest}{ext}"

            if not cover_path.exists():
                cover_path.write_bytes(image_bytes)

            return QUrl.fromLocalFile(str(cover_path)).toString()

        except Exception:
            return ""

    def _metadata_for(self, path: Path):
        title = path.stem
        artist = ""
        album = ""
        duration_ms = 0
        cover_url = ""

        if MutagenFile is not None:
            try:
                audio_full = MutagenFile(path)

                if audio_full is not None:
                    if getattr(audio_full, "info", None) is not None:
                        length = getattr(audio_full.info, "length", 0) or 0
                        duration_ms = int(length * 1000)

                    cover_url = self._extract_cover(path, audio_full)

                audio_easy = MutagenFile(path, easy=True)

                if audio_easy is not None and getattr(audio_easy, "tags", None):
                    tags = audio_easy.tags

                    title_values = tags.get("title", [])
                    artist_values = tags.get("artist", [])
                    album_values = tags.get("album", [])

                    if title_values:
                        title = str(title_values[0])
                    if artist_values:
                        artist = str(artist_values[0])
                    if album_values:
                        album = str(album_values[0])

            except Exception:
                pass

        return title, artist, album, duration_ms, cover_url

    @staticmethod
    def _duration_text(milliseconds):
        if not milliseconds or milliseconds < 0:
            return "--:--"

        total_seconds = int(milliseconds / 1000)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def _song_for_path(self, path):
        for song in self._songs:
            if song["path"] == path:
                return song
        return None

    def _index_for_path(self, path):
        for i, song in enumerate(self._songs):
            if song["path"] == path:
                return i
        return -1

    def _restore_last_track(self):
        if not self._last_track_path or not self._songs:
            return

        idx = self._index_for_path(self._last_track_path)
        if idx < 0:
            return

        self._current_index = idx
        song = self._songs[idx]
        self.player.setSource(QUrl.fromLocalFile(song["path"]))

        if self._last_position > 0:
            self.player.setPosition(self._last_position)

        self.currentChanged.emit()

    def _add_recent(self, path):
        self._recents = [p for p in self._recents if p != path]
        self._recents.insert(0, path)
        self._recents = self._recents[:30]
        self.recentsChanged.emit()

    @Property("QVariantList", notify=libraryChanged)
    def songs(self):
        return self._songs

    @Property("QVariantList", notify=libraryChanged)
    def albums(self):
        groups = {}

        for song in self._songs:
            album = song["album"] or "Sem álbum"
            key = album

            if key not in groups:
                groups[key] = {
                    "name": album,
                    "artist": song["artist"] or "Artista desconhecido",
                    "coverUrl": song["coverUrl"],
                    "count": 0,
                }

            groups[key]["count"] += 1

            if not groups[key]["coverUrl"] and song["coverUrl"]:
                groups[key]["coverUrl"] = song["coverUrl"]

        return sorted(groups.values(), key=lambda a: a["name"].lower())

    @Property("QVariantList", notify=libraryChanged)
    def artists(self):
        groups = {}

        for song in self._songs:
            artist = song["artist"] or "Artista desconhecido"

            if artist not in groups:
                groups[artist] = {
                    "name": artist,
                    "coverUrl": song["coverUrl"],
                    "count": 0,
                }

            groups[artist]["count"] += 1

            if not groups[artist]["coverUrl"] and song["coverUrl"]:
                groups[artist]["coverUrl"] = song["coverUrl"]

        return sorted(groups.values(), key=lambda a: a["name"].lower())

    @Property("QVariantList", notify=favoritesChanged)
    def favoriteSongs(self):
        result = []

        for path in self._favorites:
            song = self._song_for_path(path)
            if song:
                result.append(song)

        return sorted(result, key=lambda s: s["title"].lower())

    @Property("QVariantList", notify=recentsChanged)
    def recentSongs(self):
        result = []

        for path in self._recents:
            song = self._song_for_path(path)
            if song:
                result.append(song)

        return result

    @Property("QVariantList", notify=queueChanged)
    def queueSongs(self):
        result = []
        for path in self._queue:
            song = self._song_for_path(path)
            if song:
                result.append(song)
        return result

    @Property(int, notify=queueChanged)
    def queueCount(self):
        return len(self.queueSongs)

    @Property("QVariantList", notify=playlistsChanged)
    def playlists(self):
        result = []
        for name in sorted(self._playlists.keys(), key=lambda x: x.lower()):
            paths = self._playlists.get(name, [])
            valid = [p for p in paths if self._song_for_path(p)]
            cover = ""
            if valid:
                first = self._song_for_path(valid[0])
                cover = first.get("coverUrl", "") if first else ""

            result.append({
                "name": name,
                "count": len(valid),
                "coverUrl": cover
            })
        return result

    @Property(int, notify=libraryChanged)
    def songCount(self):
        return len(self._songs)

    @Property(str, notify=folderChanged)
    def musicFolder(self):
        return self._music_folder

    @Property(int, notify=currentChanged)
    def currentIndex(self):
        return self._current_index

    @Property(bool, notify=currentChanged)
    def hasCurrent(self):
        return 0 <= self._current_index < len(self._songs)

    @Property(str, notify=currentChanged)
    def currentPath(self):
        if self.hasCurrent:
            return self._songs[self._current_index]["path"]
        return ""

    @Property(str, notify=currentChanged)
    def currentTitle(self):
        if self.hasCurrent:
            return self._songs[self._current_index]["title"]
        return "Nenhuma música selecionada"

    @Property(str, notify=currentChanged)
    def currentArtist(self):
        if self.hasCurrent:
            return self._songs[self._current_index]["artist"]
        return ""

    @Property(str, notify=currentChanged)
    def currentAlbum(self):
        if self.hasCurrent:
            return self._songs[self._current_index]["album"]
        return ""

    @Property(str, notify=currentChanged)
    def currentCoverUrl(self):
        if self.hasCurrent:
            return self._songs[self._current_index]["coverUrl"]
        return ""

    @Property(bool, notify=currentChanged)
    def currentFavorite(self):
        if not self.hasCurrent:
            return False
        return self._songs[self._current_index]["path"] in self._favorites

    @Property(bool, notify=playbackChanged)
    def playing(self):
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    @Property(int, notify=positionChanged)
    def position(self):
        return int(self.player.position())

    @Property(int, notify=durationChanged)
    def duration(self):
        return int(self.player.duration())

    @Property(str, notify=positionChanged)
    def positionText(self):
        return self._duration_text(self.player.position())

    @Property(str, notify=durationChanged)
    def durationText(self):
        return self._duration_text(self.player.duration())

    @Property(bool, notify=shuffleChanged)
    def shuffle(self):
        return self._shuffle

    @Property(bool, notify=repeatChanged)
    def repeat(self):
        return self._repeat

    @Property(str, notify=errorChanged)
    def errorText(self):
        return self._error_text

    @Slot(str)
    def setMusicFolder(self, folder_url):
        raw = str(folder_url or "")

        if raw.startswith("file:"):
            parsed = urlparse(raw)
            path = Path(unquote(parsed.path))
        else:
            path = Path(raw)

        path = path.expanduser()

        if not path.exists() or not path.is_dir():
            self._set_error("A pasta de músicas selecionada não é válida.")
            return

        self._music_folder = str(path.resolve())
        self._save_config()
        self.folderChanged.emit()
        self.scanLibrary()

    @Slot()
    def scanLibrary(self):
        if not self._music_folder:
            self._songs = []
            self._current_index = -1
            self.libraryChanged.emit()
            self.currentChanged.emit()
            return

        folder = Path(self._music_folder)

        if not folder.is_dir():
            self._songs = []
            self.libraryChanged.emit()
            return

        old_path = None
        if self.hasCurrent:
            old_path = self._songs[self._current_index]["path"]

        found = []

        try:
            paths = sorted(
                (
                    p for p in folder.rglob("*")
                    if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
                ),
                key=lambda p: str(p).lower()
            )

            for path in paths:
                title, artist, album, duration_ms, cover_url = self._metadata_for(path)

                found.append({
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "path": str(path),
                    "url": QUrl.fromLocalFile(str(path)).toString(),
                    "coverUrl": cover_url,
                    "duration": duration_ms,
                    "durationText": self._duration_text(duration_ms),
                    "fileName": path.name,
                    "favorite": str(path) in self._favorites,
                })

        except Exception as exc:
            self._set_error(f"Erro ao ler biblioteca: {exc}")

        self._songs = found
        self._current_index = -1

        if old_path:
            self._current_index = self._index_for_path(old_path)

        if self._current_index < 0 and self._last_track_path:
            self._current_index = self._index_for_path(self._last_track_path)

        self.libraryChanged.emit()
        self.favoritesChanged.emit()
        self.recentsChanged.emit()
        self.queueChanged.emit()
        self.playlistsChanged.emit()
        self.currentChanged.emit()

    def _pause_external_players(self):
        """
        Dá foco de áudio ao player interno.

        Navegadores, Spotify, VLC e outros players MPRIS são pausados
        via playerctl antes de o QMediaPlayer começar a tocar.
        """
        try:
            subprocess.Popen(
                ["playerctl", "--all-players", "pause"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    @Slot()
    def pauseForExternal(self):
        """
        Usado quando um player externo começa a tocar.
        Evita que o player interno continue tocando junto.
        """
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.playbackChanged.emit()

    @Slot(str)
    def addToQueue(self, path):
        if not path or not self._song_for_path(path):
            return
        self._queue.append(path)
        self.queueChanged.emit()
        self._save_config()

    @Slot(int)
    def removeQueueIndex(self, index):
        if index < 0 or index >= len(self._queue):
            return
        self._queue.pop(index)
        self.queueChanged.emit()
        self._save_config()

    @Slot()
    def clearQueue(self):
        self._queue = []
        self.queueChanged.emit()
        self._save_config()

    @Slot(int, int)
    def moveQueueItem(self, source_index, target_index):
        if source_index < 0 or source_index >= len(self._queue):
            return
        if target_index < 0 or target_index >= len(self._queue):
            return
        if source_index == target_index:
            return

        item = self._queue.pop(source_index)
        self._queue.insert(target_index, item)
        self.queueChanged.emit()
        self._save_config()

    @Slot(str, result=bool)
    def createPlaylist(self, name):
        clean = str(name or "").strip()
        if not clean:
            return False

        if clean not in self._playlists:
            self._playlists[clean] = []
            self.playlistsChanged.emit()
            self._save_config()

        return True

    @Slot(str)
    def deletePlaylist(self, name):
        if name in self._playlists:
            del self._playlists[name]
            self.playlistsChanged.emit()
            self._save_config()

    @Slot(str, str, result=bool)
    def addPathToPlaylist(self, playlist_name, path):
        playlist_name = str(playlist_name or "").strip()
        path = str(path or "")

        if playlist_name not in self._playlists:
            return False

        if not self._song_for_path(path):
            return False

        items = self._playlists[playlist_name]

        if path not in items:
            items.append(path)
            self.playlistsChanged.emit()
            self._save_config()

        return True

    @Slot(str, str)
    def removePathFromPlaylist(self, playlist_name, path):
        if playlist_name not in self._playlists:
            return

        items = self._playlists[playlist_name]
        self._playlists[playlist_name] = [p for p in items if p != path]
        self.playlistsChanged.emit()
        self._save_config()

    @Slot(str)
    def playPlaylist(self, playlist_name):
        paths = [
            p for p in self._playlists.get(playlist_name, [])
            if self._song_for_path(p)
        ]
        if not paths:
            return

        first = paths[0]
        self._queue = paths[1:]
        self.queueChanged.emit()
        self.playPath(first)

    @Slot(str, result="QVariantList")
    def playlistSongs(self, playlist_name):
        result = []
        for path in self._playlists.get(playlist_name, []):
            song = self._song_for_path(path)
            if song:
                result.append(song)
        return result

    @Slot(int)
    def playIndex(self, index):
        if index < 0 or index >= len(self._songs):
            return

        self._current_index = index
        song = self._songs[index]

        self._pause_external_players()
        self.player.setSource(QUrl.fromLocalFile(song["path"]))
        self.player.play()

        self._last_track_path = song["path"]
        self._last_position = 0
        self._add_recent(song["path"])
        self._save_config()

        self._set_error("")
        self.currentChanged.emit()
        self.playbackChanged.emit()

    @Slot(str)
    def playPath(self, path):
        idx = self._index_for_path(path)
        if idx >= 0:
            self.playIndex(idx)

    @Slot(str)
    def playAlbum(self, album_name):
        for i, song in enumerate(self._songs):
            if (song["album"] or "Sem álbum") == album_name:
                self.playIndex(i)
                return

    @Slot(str)
    def playArtist(self, artist_name):
        for i, song in enumerate(self._songs):
            if (song["artist"] or "Artista desconhecido") == artist_name:
                self.playIndex(i)
                return

    @Slot()
    def playPause(self):
        if not self.hasCurrent:
            if self._songs:
                self.playIndex(0)
            return

        state = self.player.playbackState()

        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self._pause_external_players()

            if self.player.source().isEmpty():
                self.player.setSource(
                    QUrl.fromLocalFile(self._songs[self._current_index]["path"])
                )

            self.player.play()

        self.playbackChanged.emit()

    @Slot()
    def next(self):
        if not self._songs:
            return

        # A fila manual tem prioridade.
        if self._queue:
            next_path = self._queue.pop(0)
            self.queueChanged.emit()
            self._save_config()

            idx = self._index_for_path(next_path)
            if idx >= 0:
                self.playIndex(idx)
                return

        if self._shuffle and len(self._songs) > 1:
            choices = list(range(len(self._songs)))
            if self._current_index in choices:
                choices.remove(self._current_index)
            next_index = random.choice(choices)
        else:
            next_index = self._current_index + 1
            if next_index >= len(self._songs):
                next_index = 0

        self.playIndex(next_index)

    @Slot()
    def previous(self):
        if not self._songs:
            return

        if self.player.position() > 5000 and self.hasCurrent:
            self.player.setPosition(0)
            return

        previous_index = self._current_index - 1
        if previous_index < 0:
            previous_index = len(self._songs) - 1

        self.playIndex(previous_index)

    @Slot(int)
    def seek(self, milliseconds):
        if not self.hasCurrent:
            return

        value = max(0, min(int(milliseconds), max(0, self.player.duration())))
        self.player.setPosition(value)

    @Slot()
    def toggleShuffle(self):
        self._shuffle = not self._shuffle
        self.shuffleChanged.emit()
        self._save_config()

    @Slot()
    def playRandom(self):
        """
        Ativa o modo aleatório e inicia imediatamente uma faixa aleatória.
        Evita repetir a faixa atual quando há mais de uma música.
        """
        if not self._songs:
            return

        if not self._shuffle:
            self._shuffle = True
            self.shuffleChanged.emit()
            self._save_config()

        choices = list(
            range(
                len(self._songs)
            )
        )

        if (
            len(choices) > 1
            and self._current_index
            in choices
        ):
            choices.remove(
                self._current_index
            )

        if not choices:
            return

        self.playIndex(
            random.choice(
                choices
            )
        )

    @Slot()
    def toggleRepeat(self):
        self._repeat = not self._repeat
        self.repeatChanged.emit()
        self._save_config()

    @Slot(str)
    def toggleFavoritePath(self, path):
        if path in self._favorites:
            self._favorites.remove(path)
        else:
            self._favorites.add(path)

        for song in self._songs:
            if song["path"] == path:
                song["favorite"] = path in self._favorites

        self.favoritesChanged.emit()
        self.libraryChanged.emit()
        self.currentChanged.emit()
        self._save_config()

    @Slot()
    def toggleCurrentFavorite(self):
        if not self.hasCurrent:
            return
        self.toggleFavoritePath(self._songs[self._current_index]["path"])

    @Slot(result="QVariantList")
    def currentAlbumSongs(self):
        if not self.hasCurrent:
            return []

        album = self._songs[self._current_index]["album"] or "Sem álbum"
        return [
            s for s in self._songs
            if (s["album"] or "Sem álbum") == album
        ]

    def _on_position_changed(self, value):
        self._last_position = int(value or 0)
        self.positionChanged.emit()

        # Persist resume position at a low write rate.
        if self._last_position % 10000 < 800:
            self._save_config()

    def _on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.LoadedMedia and self._last_position > 0:
            self.player.setPosition(self._last_position)

        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            if self._repeat and self.hasCurrent:
                self._pause_external_players()
                self.player.setPosition(0)
                self.player.play()
            else:
                self.next()

    def _on_error(self, error, error_string):
        if error != QMediaPlayer.Error.NoError:
            self._set_error(
                error_string or
                "Não foi possível reproduzir este arquivo."
            )

    def _set_error(self, text):
        text = str(text or "")
        if text != self._error_text:
            self._error_text = text
            self.errorChanged.emit()

    def shutdown(self):
        # Stop may reset position, so save and disconnect first.
        self._last_position = self.player.position()
        self._save_config()
        self.player.positionChanged.disconnect(self._on_position_changed)
        self.audio_device_timer.stop()
        self.player.stop()
