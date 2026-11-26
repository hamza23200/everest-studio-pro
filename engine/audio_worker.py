"""
Everest Studio Pro - Dedicated Windows WASAPI Loopback Audio Worker.
Captures live playback audio via pyaudiowpatch without blocking the 35 FPS render loop,
performs Hann-windowed NumPy RFFT into 15 or 20 logarithmic bands, and auto-recovers
on playback device changes.
"""

import threading
import time
from typing import List, Optional, Tuple

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False

try:
    import pyaudiowpatch as pyaudio
    _HAS_PYAUDIO = True
except ImportError:
    pyaudio = None
    _HAS_PYAUDIO = False


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(val)))


class AudioCaptureWorker:
    """Thread-safe WASAPI loopback FFT capture daemon for Audio Equalizer mode."""

    def __init__(self, num_bands: int = 20):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.num_bands: int = 15 if num_bands == 15 else 20
        self.sensitivity: float = 1.5   # 0.5x to 4.0x
        self.smoothing: float = 0.50    # 0.00 to 0.90 (0.50 -> attack 0.65, decay 0.25)

        self._bands: List[float] = [0.0] * self.num_bands
        self._bass_energy: float = 0.0
        self._last_audio_time: float = 0.0
        self._sample_rate: int = 48000
        self._channels: int = 2
        self.status_message: str = "Idle"

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def set_num_bands(self, num_bands: int):
        target = 15 if int(num_bands) <= 15 else 20
        with self._lock:
            if target != self.num_bands:
                self.num_bands = target
                self._bands = [0.0] * target
                self._bass_energy = 0.0

    def start(self):
        """Starts the background WASAPI capture daemon if not already running."""
        if self.is_running:
            return
        if not (_HAS_NUMPY and _HAS_PYAUDIO):
            missing = []
            if not _HAS_NUMPY:
                missing.append("numpy")
            if not _HAS_PYAUDIO:
                missing.append("pyaudiowpatch")
            with self._lock:
                self.status_message = f"Audio unavailable (missing: {', '.join(missing)})"
            return

        self._stop_event.clear()
        with self._lock:
            self.status_message = "Starting WASAPI loopback..."
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="EverestAudioWorker")
        self._thread.start()

    def stop(self):
        """Signals capture thread to stop, releases WASAPI handle, and resets levels."""
        self._stop_event.set()
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=1.5)
        self._thread = None
        with self._lock:
            self._bands = [0.0] * self.num_bands
            self._bass_energy = 0.0
            self.status_message = "Stopped"

    def get_snapshot(self) -> Tuple[List[float], float, str]:
        """Thread-safe snapshot of normalized bands [0..1], bass energy, and device status."""
        with self._lock:
            return list(self._bands), float(self._bass_energy), self.status_message

    def _smoothing_rates(self) -> Tuple[float, float]:
        s = _clamp(self.smoothing, 0.0, 0.95)
        attack = _clamp(0.90 - s * 0.50, 0.20, 0.95)
        decay = _clamp(0.45 - s * 0.40, 0.05, 0.60)
        return attack, decay

    def decay_to_silence(self):
        """Smoothly decays active bands toward 0.0 during WASAPI playback silence."""
        with self._lock:
            _, decay = self._smoothing_rates()
            updated = [v * (1.0 - decay) for v in self._bands]
            updated = [0.0 if v < 0.008 else v for v in updated]
            self._bands = updated
            bass_cnt = max(2, len(updated) // 5)
            self._bass_energy = sum(updated[:bass_cnt]) / bass_cnt if updated else 0.0

    def process_pcm_chunk(
        self,
        samples,
        sample_rate: int,
        num_bands: Optional[int] = None,
        channels: int = 1,
    ) -> List[float]:
        """
        Pure FFT pipeline for unit tests and live WASAPI callbacks.
        Bins normalized audio into logarithmic frequency bands with attack/decay & noise gating.
        """
        if not _HAS_NUMPY:
            return list(self._bands)

        arr = np.asarray(samples, dtype=np.float32)
        if arr.size == 0:
            return list(self._bands)

        if arr.ndim == 2:
            arr = arr.mean(axis=1)
        elif channels > 1 and arr.size >= channels:
            trim = (arr.size // channels) * channels
            arr = arr[:trim].reshape(-1, channels).mean(axis=1)

        # Normalize int16-range arrays into [-1.0, 1.0]
        if np.issubdtype(np.asarray(samples).dtype, np.integer) or np.max(np.abs(arr)) > 2.0:
            arr = arr / 32768.0

        n = len(arr)
        if n < 32:
            return list(self._bands)

        window = np.hanning(n).astype(np.float32)
        win_sum = float(np.sum(window)) or float(n)
        spec = np.fft.rfft(arr * window)
        mags = (np.abs(spec) * 2.0) / win_sum
        sr = max(8000, int(sample_rate))
        freqs = np.fft.rfftfreq(n, d=1.0 / sr)
        df = sr / float(n)

        with self._lock:
            b_count = 15 if (num_bands or self.num_bands) <= 15 else 20
            if len(self._bands) != b_count:
                self._bands = [0.0] * b_count
            sens = _clamp(self.sensitivity, 0.5, 4.0)
            attack, decay = self._smoothing_rates()
            prev = list(self._bands)

        edges = np.geomspace(40.0, min(12000.0, sr * 0.48), b_count + 1)
        raw_bands = []
        for i in range(b_count):
            lo, hi = edges[i], edges[i + 1]
            mask = (freqs >= lo) & (freqs < hi)
            if np.any(mask):
                val = float(np.sqrt(np.mean(mags[mask] ** 2)))
            else:
                center_idx = int(round((0.5 * (lo + hi)) / max(1e-6, df)))
                center_idx = max(1, min(len(mags) - 1, center_idx))
                val = float(mags[center_idx])

            treble_boost = 1.0 + 1.2 * (i / max(1, b_count - 1))
            scaled = val * sens * 2.8 * treble_boost
            if scaled < 0.025:
                scaled = 0.0
            else:
                scaled = _clamp(scaled)
            raw_bands.append(scaled)

        smoothed = []
        for p, cur in zip(prev, raw_bands):
            rate = attack if cur > p else decay
            nxt = p + (cur - p) * rate
            smoothed.append(0.0 if nxt < 0.008 else _clamp(nxt))

        bass_cnt = max(2, b_count // 5)
        bass = _clamp(sum(smoothed[:bass_cnt]) / bass_cnt)

        with self._lock:
            self._bands = smoothed
            self._bass_energy = bass
            self._last_audio_time = time.time()

        return list(smoothed)

    def _find_default_loopback(self, p):
        """Finds the WASAPI loopback device matching the active Windows default playback device."""
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_out_idx = wasapi_info["defaultOutputDevice"]
        default_out = p.get_device_info_by_index(default_out_idx)
        if not default_out.get("isLoopbackDevice", False):
            for loopback in p.get_loopback_device_info_generator():
                if default_out["name"] in loopback["name"]:
                    return default_out_idx, loopback
            raise RuntimeError(f"No WASAPI loopback device for {default_out.get('name', 'output')}")
        return default_out_idx, default_out

    def _capture_loop(self):
        """Opens non-blocking WASAPI loopback callback stream and auto-recovers on device change."""
        while not self._stop_event.is_set():
            p = None
            stream = None
            try:
                p = pyaudio.PyAudio()
                default_out_idx, loopback = self._find_default_loopback(p)
                sr = int(loopback.get("defaultSampleRate", 48000))
                ch = max(1, int(loopback.get("maxInputChannels", 2)))
                self._sample_rate = sr
                self._channels = ch

                def _on_audio(in_data, frame_count, time_info, status_flags):
                    if not self._stop_event.is_set() and in_data:
                        pcm = np.frombuffer(in_data, dtype=np.int16)
                        self.process_pcm_chunk(pcm, sr, channels=ch)
                    flag = pyaudio.paComplete if self._stop_event.is_set() else pyaudio.paContinue
                    return (None, flag)

                stream = p.open(
                    format=pyaudio.paInt16,
                    channels=ch,
                    rate=sr,
                    frames_per_buffer=1024,
                    input=True,
                    input_device_index=loopback["index"],
                    stream_callback=_on_audio,
                )
                stream.start_stream()
                with self._lock:
                    self.status_message = f"WASAPI Loopback: {loopback['name']}"

                last_device_check = time.time()
                while not self._stop_event.is_set():
                    self._stop_event.wait(0.03)
                    now = time.time()
                    if (now - self._last_audio_time) > 0.12:
                        self.decay_to_silence()
                    if (now - last_device_check) >= 2.0:
                        last_device_check = now
                        if not stream.is_active():
                            raise RuntimeError("WASAPI audio stream stopped")
                        cur_wasapi = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                        if cur_wasapi.get("defaultOutputDevice") != default_out_idx:
                            raise RuntimeError("Default playback device changed")

            except Exception as exc:
                with self._lock:
                    self.status_message = f"Audio device unavailable ({exc}) — retrying..."
                    self._bands = [0.0] * self.num_bands
                    self._bass_energy = 0.0
            finally:
                if stream is not None:
                    try:
                        stream.stop_stream()
                    except Exception:
                        pass
                    try:
                        stream.close()
                    except Exception:
                        pass
                if p is not None:
                    try:
                        p.terminate()
                    except Exception:
                        pass

            if not self._stop_event.is_set():
                self._stop_event.wait(2.0)
