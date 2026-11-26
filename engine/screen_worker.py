"""
Everest Studio Pro - Real-Time Multi-Monitor Screen Capture Worker.
Captures the selected display via mss (~22 FPS) in a decoupled daemon thread,
performs fast strided NumPy downsampling + saturation boost + EMA temporal smoothing,
and produces a 5x20 switch grid plus perimeter edge color strips.
"""

import threading
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    np = None
    _HAS_NUMPY = False

try:
    import mss
    _HAS_MSS = True
except ImportError:
    mss = None
    _HAS_MSS = False


def _clamp(val: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(val)))


def _downsample_2d(rgb: "np.ndarray", rows: int, cols: int) -> "np.ndarray":
    """Downsamples an (H, W, 3) float32 image into (rows, cols, 3) block means."""
    h, w, _ = rgb.shape
    row_bins = np.array_split(np.arange(h), rows)
    out = np.zeros((rows, cols, 3), dtype=np.float32)
    col_bins = np.array_split(np.arange(w), cols)
    for r_i, r_idx in enumerate(row_bins):
        if r_idx.size == 0:
            continue
        row_slice = rgb[r_idx[0]:r_idx[-1] + 1]
        for c_i, c_idx in enumerate(col_bins):
            if c_idx.size == 0:
                continue
            out[r_i, c_i] = row_slice[:, c_idx[0]:c_idx[-1] + 1].mean(axis=(0, 1))
    return out


class ScreenCaptureWorker:
    """Thread-safe mss screen capture + EMA color smoother for Screen Ambilight mode."""

    def __init__(self, monitor_index: int = 1):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self.monitor_index: int = max(1, int(monitor_index))
        self.capture_mode: str = "grid"     # 'grid' (Full Screen Grid) or 'edges' (Monitor Edges Only)
        self.smoothing: float = 0.55        # 0.00 to 0.90 (EMA retention weight)
        self.saturation_boost: float = 1.5  # 1.0x to 2.5x

        self._grid = None
        self._edges: Optional[Dict[str, Any]] = None
        self._has_frame: bool = False
        self.status_message: str = "Idle"

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @staticmethod
    def list_monitors() -> List[Tuple[int, str]]:
        """Enumerates available physical monitors cleanly without crashing if mss fails."""
        if not _HAS_MSS:
            return [(1, "Monitor 1 (mss unavailable)")]
        try:
            mss_cls = getattr(mss, "MSS", mss.mss)
            with mss_cls() as sct:
                mons = []
                for i, m in enumerate(sct.monitors[1:], start=1):
                    mons.append((i, f"Monitor {i} ({m['width']}x{m['height']})"))
                return mons or [(1, "Monitor 1 (Primary)")]
        except Exception:
            return [(1, "Monitor 1 (Primary)")]

    def start(self):
        """Starts the background screen capture daemon if not already running."""
        if self.is_running:
            return
        if not (_HAS_NUMPY and _HAS_MSS):
            missing = []
            if not _HAS_NUMPY:
                missing.append("numpy")
            if not _HAS_MSS:
                missing.append("mss")
            with self._lock:
                self.status_message = f"Screen capture unavailable (missing: {', '.join(missing)})"
            return

        self._stop_event.clear()
        with self._lock:
            self.status_message = "Starting screen capture..."
        self._thread = threading.Thread(target=self._capture_loop, daemon=True, name="EverestScreenWorker")
        self._thread.start()

    def stop(self):
        """Stops the background capture thread cleanly."""
        self._stop_event.set()
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=1.5)
        self._thread = None
        with self._lock:
            self._has_frame = False
            self._grid = None
            self._edges = None
            self.status_message = "Stopped"

    def get_snapshot(self) -> Tuple[Optional[Any], Optional[Dict[str, Any]], str]:
        """Returns copies of the smoothed (5, 20, 3) grid, edge strips, and status message."""
        with self._lock:
            grid = self._grid.copy() if self._grid is not None else None
            edges = {k: v.copy() for k, v in self._edges.items()} if self._edges else None
            return grid, edges, self.status_message

    @staticmethod
    def _boost_saturation(arr: "np.ndarray", sat: float) -> "np.ndarray":
        if sat <= 1.01:
            return np.clip(arr, 0.0, 255.0)
        lum = (arr[..., 0:1] * 0.299) + (arr[..., 1:2] * 0.587) + (arr[..., 2:3] * 0.114)
        boosted = lum + (arr - lum) * sat
        return np.clip(boosted, 0.0, 255.0)

    def process_frame(self, img: "np.ndarray", is_bgra: bool = True):
        """Downsamples raw screenshot (H, W, 3/4), boosts saturation, and updates EMA state."""
        if not _HAS_NUMPY or img is None or img.size == 0:
            return
        h, w = img.shape[:2]
        sy = max(1, h // 60)
        sx = max(1, w // 80)
        sub = img[::sy, ::sx]
        rgb = sub[..., 2::-1].astype(np.float32) if is_bgra else sub[..., :3].astype(np.float32)

        sh, sw = rgb.shape[:2]
        top_h = max(1, int(sh * 0.15))
        bot_h = max(1, int(sh * 0.15))
        side_w = max(1, int(sw * 0.12))

        top_strip = _downsample_2d(rgb[:top_h, :, :], 1, 20)[0]
        bot_strip = _downsample_2d(rgb[sh - bot_h:, :, :], 1, 20)[0]
        left_strip = _downsample_2d(rgb[:, :side_w, :], 5, 1)[:, 0]
        right_strip = _downsample_2d(rgb[:, sw - side_w:, :], 5, 1)[:, 0]

        with self._lock:
            mode = self.capture_mode
            sat = _clamp(self.saturation_boost, 1.0, 2.5)
            alpha = _clamp(1.0 - _clamp(self.smoothing, 0.0, 0.90), 0.05, 1.0)
            has_prev = self._has_frame

        if mode == "edges":
            grid_new = np.zeros((5, 20, 3), dtype=np.float32)
            for r in range(5):
                y_w = r / 4.0
                v_band = top_strip * (1.0 - y_w) + bot_strip * y_w
                for c in range(20):
                    x_w = c / 19.0
                    h_band = left_strip[r] * (1.0 - x_w) + right_strip[r] * x_w
                    # Emphasize border ring strongly for edges-only mode
                    edge_bias = 0.72 if (r in (0, 4) or c in (0, 19)) else 0.45
                    grid_new[r, c] = v_band * edge_bias + h_band * (1.0 - edge_bias)
        else:
            grid_new = _downsample_2d(rgb, 5, 20)

        grid_new = self._boost_saturation(grid_new, sat)
        edges_new = {
            "top": self._boost_saturation(top_strip, sat),
            "bottom": self._boost_saturation(bot_strip, sat),
            "left": self._boost_saturation(left_strip, sat),
            "right": self._boost_saturation(right_strip, sat),
        }

        with self._lock:
            if not has_prev or self._grid is None or self._edges is None:
                self._grid = grid_new
                self._edges = edges_new
                self._has_frame = True
            else:
                one_minus = 1.0 - alpha
                self._grid = (alpha * grid_new) + (one_minus * self._grid)
                for key in ("top", "bottom", "left", "right"):
                    self._edges[key] = (alpha * edges_new[key]) + (one_minus * self._edges[key])

    def _capture_loop(self):
        """Captures the selected monitor at ~22 FPS inside the mss context."""
        target_interval = 1.0 / 22.0
        mss_cls = getattr(mss, "MSS", mss.mss)
        while not self._stop_event.is_set():
            try:
                with mss_cls() as sct:
                    while not self._stop_event.is_set():
                        t0 = time.time()
                        mon_count = max(1, len(sct.monitors) - 1)
                        with self._lock:
                            idx = min(max(1, self.monitor_index), mon_count)
                        mon = sct.monitors[idx]
                        shot = sct.grab(mon)
                        arr = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
                        self.process_frame(arr, is_bgra=True)
                        with self._lock:
                            self.status_message = f"Capturing Monitor {idx} ({shot.width}x{shot.height})"
                        elapsed = time.time() - t0
                        wait_s = max(0.005, target_interval - elapsed)
                        self._stop_event.wait(wait_s)
            except Exception as exc:
                with self._lock:
                    self.status_message = f"Screen capture error ({exc}) — retrying..."
                self._stop_event.wait(1.5)
