import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

from PySide6.QtCore import QObject, Property, Signal, Slot


class AudioVisualizerService(QObject):
    """
    Spectrum global otimizado.

    - captura low latency
    - QML limitado a 30 FPS
    - liga/desliga em Configurações
    - preferência persistente em config/visualizer.json
    """

    frameChanged = Signal()
    activeChanged = Signal()
    statusChanged = Signal()
    enabledChanged = Signal()
    suspendedChanged = Signal()
    ecoModeChanged = Signal()

    BAR_COUNT = 28

    SAMPLE_RATE = 48000
    CHANNELS = 2

    FFT_FRAMES = 1024
    HOP_FRAMES = 512

    MIN_FREQ = 55.0
    MAX_FREQ = 16000.0

    UI_FPS = 30
    UI_INTERVAL = 1.0 / UI_FPS

    # Modo de baixa qualidade usado somente na visualização fullscreen.
    # O Spectrum normal continua em 30 FPS.
    ECO_UI_FPS = 20
    ECO_UI_INTERVAL = 1.0 / ECO_UI_FPS
    ECO_ANALYSIS_STRIDE = 3

    def __init__(self, config_path=None):
        super().__init__()

        self._config_path = (
            Path(config_path)
            if config_path is not None
            else None
        )

        self._levels = [0.0] * self.BAR_COUNT
        self._peaks = [0.0] * self.BAR_COUNT

        self._enabled = self._load_enabled()
        self._suspended = False
        self._eco_mode = False
        self._active = False

        self._status = (
            "Iniciando analisador..."
            if self._enabled
            else "Spectrum desativado"
        )

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._process = None
        self._thread = None

        self._last_ui_emit = 0.0

        if self._enabled:
            self._start_worker()

    def _load_enabled(self):
        if self._config_path is None:
            return True

        try:
            if not self._config_path.exists():
                return True

            data = json.loads(
                self._config_path.read_text(
                    encoding="utf-8"
                )
            )

            return bool(
                data.get("enabled", True)
            )

        except Exception:
            return True

    def _save_config(self):
        if self._config_path is None:
            return

        try:
            self._config_path.parent.mkdir(
                parents=True,
                exist_ok=True
            )

            self._config_path.write_text(
                json.dumps(
                    {
                        "enabled": self._enabled
                    },
                    indent=2,
                    ensure_ascii=False
                ) + "\n",
                encoding="utf-8"
            )

        except Exception as exc:
            print(
                "[MediaDeck] Não foi possível salvar "
                f"visualizer.json: {exc}"
            )

    @Property("QVariantList", notify=frameChanged)
    def levels(self):
        with self._lock:
            return list(self._levels)

    @Property("QVariantList", notify=frameChanged)
    def peaks(self):
        with self._lock:
            return list(self._peaks)

    @Property(bool, notify=activeChanged)
    def active(self):
        return self._active

    @Property(bool, notify=enabledChanged)
    def enabled(self):
        return self._enabled

    @Property(bool, notify=suspendedChanged)
    def suspended(self):
        return self._suspended

    @Property(bool, notify=ecoModeChanged)
    def ecoMode(self):
        return self._eco_mode

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(int, notify=ecoModeChanged)
    def uiFps(self):
        return (
            self.ECO_UI_FPS
            if self._eco_mode
            else self.UI_FPS
        )

    @Slot(bool)
    def setEnabled(self, enabled):
        enabled = bool(enabled)

        if enabled == self._enabled:
            return

        self._enabled = enabled
        self._save_config()
        self.enabledChanged.emit()

        if enabled:
            if self._suspended:
                self._set_status(
                    "Spectrum suspenso durante vídeo"
                )
            else:
                self._stop_event.clear()
                self._set_status(
                    "Reativando spectrum..."
                )
                self._start_worker()

        else:
            self._set_status(
                "Desativando spectrum..."
            )
            self._stop_capture()
            self._set_levels_zero()
            self._set_status(
                "Spectrum desativado"
            )

    @Slot(bool)
    def setEcoMode(self, enabled):
        """
        Reduz temporariamente custo de FFT e FPS do QML.
        Não altera a preferência enabled do usuário.
        """
        enabled = bool(enabled)

        if enabled == self._eco_mode:
            return

        self._eco_mode = enabled
        self._last_ui_emit = 0.0
        self.ecoModeChanged.emit()

        if self._enabled and not self._suspended:
            self._set_status(
                (
                    "Spectrum ativo • modo econômico • "
                    f"{self.ECO_UI_FPS} FPS"
                )
                if enabled
                else (
                    "Spectrum ativo • "
                    f"{self.UI_FPS} FPS"
                )
            )

    @Slot()
    def toggleEnabled(self):
        self.setEnabled(
            not self._enabled
        )

    @Slot()
    def suspendForVideo(self):
        """
        Suspende temporariamente o Spectrum sem alterar a preferência
        Ligado/Desligado salva pelo usuário.
        """
        if self._suspended:
            return

        self._suspended = True
        self.suspendedChanged.emit()

        if self._enabled:
            self._set_status(
                "Spectrum suspenso durante vídeo"
            )
            self._stop_capture()
            self._set_levels_zero()

    @Slot()
    def resumeAfterVideo(self):
        """
        Restaura o Spectrum após o vídeo somente se ele estava habilitado
        nas Configurações.
        """
        if not self._suspended:
            return

        self._suspended = False
        self.suspendedChanged.emit()

        if self._enabled:
            self._stop_event.clear()
            self._set_status(
                "Reativando spectrum..."
            )
            self._start_worker()
        else:
            self._set_status(
                "Spectrum desativado"
            )

    @Slot()
    def restart(self):
        if not self._enabled:
            return

        self._stop_capture()
        self._stop_event.clear()
        self._start_worker()

    def _set_active(self, value):
        value = bool(value)

        if value != self._active:
            self._active = value
            self.activeChanged.emit()

    def _set_status(self, text):
        text = str(text)

        if text != self._status:
            self._status = text
            self.statusChanged.emit()

    def _emit_frame_if_due(
        self,
        force=False
    ):
        now = time.monotonic()

        interval = (
            self.ECO_UI_INTERVAL
            if self._eco_mode
            else self.UI_INTERVAL
        )

        if (
            force
            or
            (now - self._last_ui_emit)
            >= interval
        ):
            self._last_ui_emit = now
            self.frameChanged.emit()

    def _set_levels_zero(self):
        with self._lock:
            self._levels = (
                [0.0] * self.BAR_COUNT
            )

            self._peaks = (
                [0.0] * self.BAR_COUNT
            )

        self._emit_frame_if_due(
            force=True
        )

        self._set_active(False)

    def _start_worker(self):
        if not self._enabled or self._suspended:
            return

        if (
            self._thread is not None
            and self._thread.is_alive()
        ):
            return

        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._worker_loop,
            name="MediaDeckSpectrumEcoGPU",
            daemon=True
        )

        self._thread.start()

    def _stop_capture(self):
        self._stop_event.set()

        process = self._process
        self._process = None

        if process is not None:
            try:
                process.terminate()
                process.wait(
                    timeout=0.25
                )
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass

        thread = self._thread

        if (
            thread is not None
            and thread.is_alive()
            and thread is not
            threading.current_thread()
        ):
            thread.join(
                timeout=0.45
            )

        if (
            self._thread is not None
            and not self._thread.is_alive()
        ):
            self._thread = None

        self._set_active(False)

    def _command_candidates(self):
        parec = shutil.which(
            "parec"
        )

        if not parec:
            return []

        base = [
            parec,
            "--raw",
            "--device=@DEFAULT_MONITOR@",
            "--format=s16le",
            f"--rate={self.SAMPLE_RATE}",
            f"--channels={self.CHANNELS}",
        ]

        return [
            (
                "low latency",
                base + [
                    "--latency-msec=10",
                    "--process-time-msec=5",
                ],
                "10",
            ),
            (
                "compatibilidade",
                list(base),
                "25",
            ),
        ]

    @staticmethod
    def _read_exact(
        stream,
        size,
        stop_event
    ):
        chunks = []
        remaining = size

        while (
            remaining > 0
            and not stop_event.is_set()
        ):
            chunk = stream.read(
                remaining
            )

            if not chunk:
                return None

            chunks.append(
                chunk
            )

            remaining -= len(
                chunk
            )

        if remaining > 0:
            return None

        return b"".join(
            chunks
        )

    def _worker_loop(self):
        candidates = (
            self._command_candidates()
        )

        if not candidates:
            self._set_status(
                "parec não encontrado — "
                "instale libpulse/pipewire-pulse"
            )
            self._set_levels_zero()
            return

        try:
            while (
                self._enabled
                and not self._suspended
                and not
                self._stop_event.is_set()
            ):
                captured = False

                for (
                    mode_name,
                    command,
                    pulse_latency
                ) in candidates:

                    if (
                        self._stop_event.is_set()
                        or not self._enabled
                    ):
                        break

                    self._set_status(
                        "Conectando ao áudio • "
                        f"{mode_name}..."
                    )

                    ok = (
                        self._capture_with_command(
                            command,
                            mode_name,
                            pulse_latency
                        )
                    )

                    if ok:
                        captured = True
                        break

                if (
                    self._stop_event.is_set()
                    or not self._enabled
                ):
                    break

                if not captured:
                    self._set_active(False)

                    self._set_status(
                        "Falha ao capturar monitor. "
                        "Tentando novamente..."
                    )

                    time.sleep(1.0)

        finally:
            self._set_active(False)

            if (
                threading.current_thread()
                is self._thread
            ):
                self._thread = None

    def _capture_with_command(
        self,
        command,
        mode_name,
        pulse_latency
    ):
        bytes_per_frame = (
            2 * self.CHANNELS
        )

        bytes_per_hop = (
            self.HOP_FRAMES *
            bytes_per_frame
        )

        window = np.hanning(
            self.FFT_FRAMES
        ).astype(
            np.float32
        )

        freqs = np.fft.rfftfreq(
            self.FFT_FRAMES,
            d=1.0 /
            self.SAMPLE_RATE
        )

        edges = np.geomspace(
            self.MIN_FREQ,
            self.MAX_FREQ,
            self.BAR_COUNT + 1
        )

        band_ranges = []

        for i in range(
            self.BAR_COUNT
        ):
            start = int(
                np.searchsorted(
                    freqs,
                    edges[i],
                    side="left"
                )
            )

            end = int(
                np.searchsorted(
                    freqs,
                    edges[i + 1],
                    side="left"
                )
            )

            end = max(
                end,
                start + 1
            )

            band_ranges.append(
                (
                    start,
                    min(
                        end,
                        len(freqs)
                    )
                )
            )

        previous = np.zeros(
            self.BAR_COUNT,
            dtype=np.float32
        )

        peaks = np.zeros(
            self.BAR_COUNT,
            dtype=np.float32
        )

        rolling = np.zeros(
            (
                self.FFT_FRAMES,
                self.CHANNELS
            ),
            dtype=np.float32
        )

        bass_boost = (
            np.linspace(
                1.12,
                1.0,
                self.BAR_COUNT,
                dtype=np.float32
            )
        )

        env = os.environ.copy()

        env[
            "PULSE_LATENCY_MSEC"
        ] = pulse_latency

        process = None

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
                env=env
            )

            self._process = process

            time.sleep(
                0.05
            )

            if (
                process.poll()
                is not None
            ):
                return False

            self._set_active(True)

            self._set_status(
                (
                    "Spectrum ativo • modo econômico • "
                    f"{self.ECO_UI_FPS} FPS • {mode_name}"
                )
                if self._eco_mode
                else (
                    "Spectrum ativo • "
                    f"{self.UI_FPS} FPS • {mode_name}"
                )
            )

            got_audio_blocks = 0
            analysis_counter = 0

            while (
                not
                self._stop_event.is_set()
                and self._enabled
                and process.poll()
                is None
            ):
                data = (
                    self._read_exact(
                        process.stdout,
                        bytes_per_hop,
                        self._stop_event
                    )
                )

                if data is None:
                    break

                got_audio_blocks += 1

                pcm_i16 = (
                    np.frombuffer(
                        data,
                        dtype="<i2"
                    )
                )

                expected = (
                    self.HOP_FRAMES *
                    self.CHANNELS
                )

                if (
                    pcm_i16.size
                    != expected
                ):
                    continue

                block = (
                    pcm_i16
                    .astype(
                        np.float32
                    )
                    .reshape(
                        self.HOP_FRAMES,
                        self.CHANNELS
                    )
                )

                rolling[
                    :-self.HOP_FRAMES
                ] = rolling[
                    self.HOP_FRAMES:
                ]

                rolling[
                    -self.HOP_FRAMES:
                ] = block

                analysis_counter += 1

                if (
                    self._eco_mode
                    and
                    (
                        analysis_counter
                        % self.ECO_ANALYSIS_STRIDE
                    ) != 0
                ):
                    continue

                mono = (
                    rolling.mean(
                        axis=1
                    )
                    / 32768.0
                )

                rms = float(
                    np.sqrt(
                        np.mean(
                            mono * mono
                        )
                        + 1e-12
                    )
                )

                if rms < 0.00010:
                    target = np.zeros(
                        self.BAR_COUNT,
                        dtype=np.float32
                    )

                else:
                    spectrum = (
                        np.abs(
                            np.fft.rfft(
                                mono * window
                            )
                        )
                        /
                        (
                            self.FFT_FRAMES
                            / 2.0
                        )
                    )

                    db = (
                        20.0 *
                        np.log10(
                            spectrum
                            + 1e-8
                        )
                    )

                    target = np.zeros(
                        self.BAR_COUNT,
                        dtype=np.float32
                    )

                    for (
                        i,
                        (
                            start,
                            end
                        )
                    ) in enumerate(
                        band_ranges
                    ):
                        band_db = float(
                            np.max(
                                db[
                                    start:end
                                ]
                            )
                        )

                        value = (
                            band_db
                            + 72.0
                        ) / 62.0

                        target[i] = (
                            np.clip(
                                value,
                                0.0,
                                1.0
                            )
                        )

                    target = (
                        np.clip(
                            target *
                            bass_boost,
                            0.0,
                            1.0
                        )
                    )

                rising = (
                    target > previous
                )

                smoothed = (
                    np.where(
                        rising,

                        previous *
                        0.12
                        +
                        target *
                        0.88,

                        previous *
                        0.55
                        +
                        target *
                        0.45
                    )
                )

                peaks = np.maximum(
                    peaks - 0.055,
                    smoothed
                )

                previous = (
                    smoothed
                )

                with self._lock:
                    self._levels = [
                        round(
                            float(v),
                            4
                        )
                        for v
                        in smoothed
                    ]

                    self._peaks = [
                        round(
                            float(v),
                            4
                        )
                        for v
                        in peaks
                    ]

                self._emit_frame_if_due()

            return (
                got_audio_blocks > 0
            )

        except Exception as exc:
            self._set_status(
                f"{mode_name}: {exc}"
            )
            return False

        finally:
            self._set_active(False)

            if process is not None:
                try:
                    process.terminate()
                except Exception:
                    pass

            if (
                self._process
                is process
            ):
                self._process = None

    def shutdown(self):
        # Preserve the enabled preference while stopping the capture process.
        self._stop_capture()
