"""
Everest Studio Pro - Dedicated Lighting Engine QThread.
Maintains 35 FPS hardware-synchronized frame clock, socket stability,
device enumeration retry loops, zero-copy Signal(object) frame emission,
full 147-LED modular underglow and numpad dock management (Detached/Left/Right),
dual base/reactive brightness pipeline, and low-latency global pynput hooks.
"""

import sys
import time
import socket
import subprocess
import os
import math
import threading
import traceback
import ctypes
from typing import Any, Dict, List, Tuple, Optional, Set
from PySide6.QtCore import QThread, Signal
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
from pynput import keyboard

# Support both .red/.green/.blue and .r/.g/.b on OpenRGB RGBColor
if not hasattr(RGBColor, "r"):
    setattr(RGBColor, "r", property(lambda s: s.red, lambda s, v: setattr(s, "red", v)))
if not hasattr(RGBColor, "g"):
    setattr(RGBColor, "g", property(lambda s: s.green, lambda s, v: setattr(s, "green", v)))
if not hasattr(RGBColor, "b"):
    setattr(RGBColor, "b", property(lambda s: s.blue, lambda s, v: setattr(s, "blue", v)))

from engine import matrix
from engine.matrix import (
    KEY_DEFINITIONS,
    NUMPAD_KEY_DEFINITIONS,
    ALL_KEY_DEFINITIONS,
    MAIN_SWITCH_INDICES,
    NUMPAD_SWITCH_INDICES,
    ALL_SWITCH_INDICES,
    MAIN_EDGE_INDICES,
    NUMPAD_EDGE_INDICES,
    ALL_EDGE_INDICES,
    NUMPAD_VKS,
    INDEX_TO_KEY,
    build_key_coordinates,
    build_matrix_coords,
    build_edge_coords,
    build_key_lookups,
)
from engine.effects import (
    EffectRenderer,
    scale_brightness,
    calculate_crosshair_intensity,
    calculate_explosion_color,
    heatmap_color,
)
from engine.audio_worker import AudioCaptureWorker
from engine.screen_worker import ScreenCaptureWorker

OPENRGB_EXE = "OpenRGB.exe"
EXPECTED_LED_COUNT = 147
MSG_OFFLINE_SIMULATOR = "OFFLINE / SIMULATOR"
MSG_CONNECTED = "CONNECTED"


def check_socket_open(host: str = "127.0.0.1", port: int = 6742, timeout: float = 0.30) -> bool:
    """Verifies if OpenRGB SDK Server is actively listening on the target TCP port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except OSError:
        return False


def spawn_openrgb_server(wait_seconds: float = 8.0) -> bool:
    """
    Auto-spawns OpenRGB in silent minimized server mode if installed locally.
    Uses CREATE_NO_WINDOW and SW_HIDE so no console window flashes.
    """
    base_dir = (
        os.path.dirname(sys.executable)
        if getattr(sys, "frozen", False)
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    candidates = [
        os.path.join(base_dir, OPENRGB_EXE),
        os.path.join(base_dir, "dist", OPENRGB_EXE),
        os.path.join(os.getcwd(), OPENRGB_EXE),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "OpenRGB", OPENRGB_EXE),
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "OpenRGB", OPENRGB_EXE),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "OpenRGB", OPENRGB_EXE),
        os.path.join("C:\\OpenRGB", OPENRGB_EXE),
    ]

    target = next((p for p in candidates if os.path.exists(p)), None)
    if not target:
        import shutil
        target = shutil.which(OPENRGB_EXE) or shutil.which("OpenRGB")

    if target:
        try:
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            info.wShowWindow = subprocess.SW_HIDE
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            subprocess.Popen(
                [target, "--server", "--startminimized"],
                startupinfo=info,
                creationflags=creationflags,
            )
            deadline = time.time() + max(0.5, float(wait_seconds))
            while time.time() < deadline:
                time.sleep(0.25)
                if check_socket_open():
                    return True
        except Exception:
            pass
    return False


def _client_socket(client):
    """Returns the underlying TCP socket of an OpenRGBClient (client.comms.sock)."""
    comms = getattr(client, "comms", None)
    return getattr(comms, "sock", None) or getattr(client, "sock", None)


def is_openrgb_process_running() -> bool:
    """Returns True if an OpenRGB.exe process already exists (never spawn a second one)."""
    if os.name != "nt":
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {OPENRGB_EXE}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout
        return OPENRGB_EXE.lower() in out.lower()
    except Exception:
        return False


def ensure_openrgb_server() -> bool:
    """
    Guarantees the SDK server is reachable WITHOUT creating duplicate instances:
    port open -> done; process already running -> wait for its port; else spawn once.
    """
    if check_socket_open():
        return True
    if is_openrgb_process_running():
        for _ in range(15):
            time.sleep(0.4)
            if check_socket_open():
                return True
        return False
    return spawn_openrgb_server()


def calculate_ripple_intensity(
    x: float,
    y: float,
    now: float,
    active_ripples: List[Dict[str, float]],
    speed: float,
    decay: float
) -> float:
    """Calculates normalized wave intensity (0.0 to 1.0) from expanding ripple rings."""
    max_intensity = 0.0
    safe_decay = max(0.05, decay)
    for w in active_ripples:
        dt = now - w["t0"]
        if dt >= safe_decay or dt < 0.0:
            continue
        dist = math.hypot(x - w["x"], y - w["y"])
        wave_r = speed * dt
        ring_width = min(1.3, 0.7 + (dt * 1.2))
        delta = abs(dist - wave_r)
        if delta < ring_width:
            norm = delta / ring_width
            ring_shape = 0.5 * (1.0 + math.cos(math.pi * norm))
            time_fade = 1.0 - (dt / safe_decay)
            attenuation = 1.0 / (1.0 + 0.12 * dist)
            val = ring_shape * time_fade * attenuation
            if val > max_intensity:
                max_intensity = val
    return max(0.0, min(1.0, max_intensity))


def _calc_single_laser_wave(
    x: float,
    y: float,
    now: float,
    laser_y: float,
    origin_x: float,
    t0: float,
    laser_speed: float,
    laser_decay: float,
    pulse_width: float,
) -> float:
    """Calculates laser intensity from a single row strike with strict row-lock isolation."""
    if abs(y - laser_y) > 0.15:
        return 0.0

    dt = now - t0
    if dt < 0.0:
        return 0.0

    dist = abs(x - origin_x)
    laser_head = dt * laser_speed
    delta = laser_head - dist
    tail_len = max(0.1, laser_speed * laser_decay)

    if 0.0 <= delta < tail_len:
        decay_progress = delta / tail_len
        return (1.0 - decay_progress) ** 2.0
    if -pulse_width <= delta < 0.0:
        return 1.0 + (delta / pulse_width)
    return 0.0


def calculate_laser_intensity(
    x: float,
    y: float,
    now: float,
    active_rows: Dict[Any, Tuple[float, ...]],
    laser_speed: float,
    laser_decay: float,
    pulse_width: float,
) -> float:
    """Calculates laser beam intensity with strict row-lock isolation."""
    if not active_rows:
        return 0.0

    max_intensity = 0.0
    for laser_y_key, row_data in list(active_rows.items()):
        if len(row_data) >= 3:
            ox, ly, t0 = row_data[0], row_data[1], row_data[2]
        elif len(row_data) == 2:
            ox, t0 = row_data
            try:
                ly_val = float(laser_y_key)
                ly = ly_val + 0.5 if abs(ly_val - round(ly_val)) < 0.01 else ly_val
            except (ValueError, TypeError):
                continue
        else:
            continue

        intensity = _calc_single_laser_wave(
            x, y, now, ly, ox, t0, laser_speed, laser_decay, pulse_width
        )
        if intensity > max_intensity:
            max_intensity = intensity

    return max(0.0, min(1.0, max_intensity))


def calculate_punch_intensity(
    idx: int,
    now: float,
    active_punches: Dict[int, float],
    punch_decay: float
) -> float:
    """Calculates linear decay flare intensity for a single key index."""
    if idx not in active_punches:
        return 0.0
    dt = now - active_punches[idx]
    safe_decay = max(0.05, punch_decay)
    if dt < safe_decay:
        return max(0.0, min(1.0, 1.0 - (dt / safe_decay)))
    return 0.0


def calculate_punch_edge_intensity(
    ex: float,
    ey: float,
    now: float,
    active_punches: Dict[int, float],
    punch_decay: float,
    key_coords: Dict[int, Tuple[float, float]]
) -> float:
    """Calculates falloff flare intensity on perimeter diffusers from punched switches."""
    if not active_punches:
        return 0.0
    safe_decay = max(0.05, punch_decay)
    max_intensity = 0.0
    for p_idx, t0 in active_punches.items():
        dt = now - t0
        if dt < safe_decay:
            kx, ky = key_coords.get(p_idx, (7.5, 2.0))
            dist = math.hypot(ex - kx, ey - ky)
            fade = 1.0 - (dt / safe_decay)
            falloff = 1.0 / (1.0 + 0.35 * dist)
            val = fade * falloff
            if val > max_intensity:
                max_intensity = val
    return max(0.0, min(1.0, max_intensity))


def blend_reactive(idle_base: RGBColor, strike_color: RGBColor, react_factor: float, intensity: float) -> RGBColor:
    """
    Independent dual-brightness blend:
    r = min(255, int(base_r) + int(color_a.r * react_factor * intensity))
    """
    r = min(255, int(idle_base.red + strike_color.red * react_factor * intensity))
    g = min(255, int(idle_base.green + strike_color.green * react_factor * intensity))
    b = min(255, int(idle_base.blue + strike_color.blue * react_factor * intensity))
    return RGBColor(r, g, b)


class LightingEngineThread(QThread):
    """
    Dedicated QThread maintaining continuous USB output at 35 FPS,
    RAM buffer mutation, and UI visualizer sync via zero-copy Signal(object).
    Supports 147 LEDs, 39-LED modular numpad (Detached/Left/Right),
    dual brightness, and anti-burst underglow synchronization.
    """
    # Emits list of 81 RGB tuples [(r, g, b), ...] for slots 0..80
    frame_rendered = Signal(object)
    underglow_rendered = Signal(object)
    connection_changed = Signal(bool, str)
    connection_status_changed = Signal(bool, str)
    key_struck = Signal(int)
    key_pressed = Signal(int)  # alias of key_struck for the visualizer flare (slot index)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 35.0
        self.frame_interval = 1.0 / self.fps
        self.running = False
        self.lock = threading.Lock()
        self._reconnect_busy = threading.Lock()

        # Matrix mapping reference
        self.matrix = matrix

        # OpenRGB Client & Device Handle
        self.client: Optional[OpenRGBClient] = None
        self.kb = None
        self.name_to_index: Dict[str, int] = {}
        self.key_coords: Dict[int, Tuple[float, float]] = {}
        self.edge_coords: Dict[int, Tuple[float, float]] = {}
        self.idx_to_slot: Dict[int, int] = {}
        self.vk_map: Dict[int, int] = {}
        self.char_map: Dict[str, int] = {}
        self.special_map: Dict[keyboard.Key, int] = {}
        self.switch_indices: Set[int] = set(ALL_SWITCH_INDICES)
        self.edge_indices: List[int] = list(ALL_EDGE_INDICES)

        # Modular Numpad Dock Position: "right", "left", "detached"
        self._dock_position: str = "right"

        # Initialize default geometry even before OpenRGB connects so visualizer works offline
        self._init_default_mappings()

        # Effect Renderer & Configuration
        self.renderer = EffectRenderer()
        self._effect_name = "static"       # 'static', 'wave', 'tornado', 'breathing', 'laser', 'matrix', 'ripple', 'punch', 'custom', 'off'
        self._mode_type = "dual"           # 'single', 'dual', 'rainbow', 'matrix_classic'
        self._color_a = RGBColor(255, 255, 0)   # Primary / Strike Color (Yellow)
        self._color_b = RGBColor(0, 0, 255)     # Secondary / Base Color (Blue)
        self.void_color = RGBColor(0, 0, 0)

        # Dual Brightness Pipeline (0.0 to 100.0)
        self._base_brightness: float = 20.0       # Ambient/Idle brightness (%)
        self._reactive_brightness: float = 100.0  # Keystroke flare/wave peak (%)

        self.speed = 5.0                  # 1.0 to 10.0
        self.matrix_speed = 6.0           # 2.0 to 15.0 rows/s
        self.direction = "right"          # 'right', 'left', 'down', 'up', 'diagonal'
        self.tornado_cw = True

        # Custom Per-Key dictionary: maps hardware LED index to painted RGBColor
        # Keys not present in this dictionary automatically render using base_color
        self.custom_key_colors: Dict[int, RGBColor] = {}
        self.custom_colors = self.custom_key_colors

        # Dedicated Underglow Settings
        self._underglow_mode = "sync"      # 'sync', 'static', 'off'
        self._underglow_color = RGBColor(0, 120, 215)
        self._underglow_brightness = 40    # 0 to 100%

        # Static mode dirty-checking flag
        self._static_dirty = True

        # Reactive Tuning Parameters
        self.laser_speed = 60.0
        self.laser_decay = 0.16
        self.pulse_width = 2.0
        self.punch_decay = 0.35
        self.ripple_speed = 15.0
        self.ripple_width = 2.4
        self.ripple_decay = 0.65

        # v3.0 Phase 1 Effect Tuning Parameters
        self.sweep_speed = 25.0
        self.sweep_trail = 4.0
        self.aurora_scale = 1.0
        self.breath_min_floor = 10.0
        self.star_density = 5.0
        self.storm_intensity = 5.0
        self.glitch_freq = 5.0
        self.dna_twist = 5.0
        self.dna_outward = True
        self.meteor_count = 6
        self.crosshair_speed = 50.0
        self.crosshair_decay = 0.45
        self.flash_decay = 0.40
        self.explosion_speed = 28.0
        self.explosion_decay = 0.65
        self.heatmap_mode = "live"
        self.heatmap_cooldown = 5.0

        # v3.0 Phase 2 System Sync Parameters & Decoupled Workers
        self.audio_style = "bars"         # 'bars' or 'bass_pulse'
        self.audio_gain = 1.5             # 0.5x to 4.0x
        self.audio_smoothing = 0.50       # 0.00 to 0.90
        self.screen_mode = "grid"         # 'grid' or 'edges'
        self.screen_smoothing = 0.55      # 0.00 to 0.90
        self.screen_saturation = 1.50     # 1.0x to 2.5x
        self.screen_monitor = 1

        self.audio_worker = AudioCaptureWorker(num_bands=20)
        self.screen_worker = ScreenCaptureWorker(monitor_index=1)

        # Reactive State Channels
        self.active_rows: Dict[int, Tuple[float, ...]] = {}
        self.active_ripples: List[Dict[str, float]] = []
        self.active_punches: Dict[int, float] = {}
        self.active_crosshairs: List[Dict[str, float]] = []
        self.active_explosions: List[Dict[str, Any]] = []
        self.flash_energy: float = 0.0
        self.key_heat: Dict[int, float] = {}
        self._last_render_time: float = time.time()
        self._last_key_press_times: Dict[int, float] = {}

        # Low-latency background keyboard listener
        self.listener: Optional[keyboard.Listener] = None
        self.last_key_time = time.time()
        self.last_heartbeat = time.time()
        self._last_offline_reconnect = 0.0
        self._is_connected: bool = False

    @property
    def dock_position(self) -> str:
        return self._dock_position

    @dock_position.setter
    def dock_position(self, val: str):
        val_clean = val.lower() if isinstance(val, str) else "right"
        if val_clean not in ("right", "left", "detached"):
            val_clean = "right"
        if self._dock_position != val_clean:
            self._dock_position = val_clean
            self._update_geometry()
            self._sync_system_workers()
            self._static_dirty = True

    @property
    def base_brightness(self) -> float:
        return self._base_brightness

    @base_brightness.setter
    def base_brightness(self, val: float):
        self._base_brightness = max(0.0, min(100.0, float(val)))
        self._static_dirty = True

    @property
    def reactive_brightness(self) -> float:
        return self._reactive_brightness

    @reactive_brightness.setter
    def reactive_brightness(self, val: float):
        self._reactive_brightness = max(0.0, min(100.0, float(val)))
        self._static_dirty = True

    @property
    def brightness(self) -> float:
        return self._base_brightness / 100.0

    @brightness.setter
    def brightness(self, val: float):
        f_val = float(val)
        self._base_brightness = f_val * 100.0 if f_val <= 1.0 else f_val
        self._static_dirty = True

    @property
    def edge_brightness(self) -> int:
        return self._underglow_brightness

    @edge_brightness.setter
    def edge_brightness(self, val: int):
        self.underglow_brightness = val

    def reset_heatmap(self):
        """Clears per-key typing heatmap accumulation."""
        with self.lock:
            self.key_heat.clear()
            self._static_dirty = True

    def _get_board_bounds(self) -> Tuple[float, float, float, float]:
        """Returns (x_min, x_max, cx, cy) dynamically for the active dock layout."""
        if self._dock_position == "left":
            return (-4.5, 15.0, 5.25, 2.5)
        if self._dock_position == "detached":
            return (0.0, 15.0, 7.5, 2.5)
        return (0.0, 19.5, 9.75, 2.5)

    def _sync_system_workers(self):
        """Starts/stops WASAPI audio and mss screen threads exclusively when their mode is active."""
        bands = 15 if self._dock_position == "detached" else 20
        self.audio_worker.set_num_bands(bands)
        self.audio_worker.sensitivity = float(self.audio_gain)
        self.audio_worker.smoothing = float(self.audio_smoothing)

        self.screen_worker.capture_mode = self.screen_mode
        self.screen_worker.smoothing = float(self.screen_smoothing)
        self.screen_worker.saturation_boost = float(self.screen_saturation)
        self.screen_worker.monitor_index = max(1, int(self.screen_monitor))

        if self._effect_name == "audio_equalizer":
            self.screen_worker.stop()
            self.audio_worker.start()
        elif self._effect_name == "screen_ambilight":
            self.audio_worker.stop()
            self.screen_worker.start()
        else:
            self.audio_worker.stop()
            self.screen_worker.stop()

    @property
    def effect_name(self) -> str:
        return self._effect_name

    @effect_name.setter
    def effect_name(self, val: str):
        if self._effect_name != val:
            self._effect_name = val
            self._sync_system_workers()
            self._static_dirty = True

    @property
    def mode_type(self) -> str:
        return self._mode_type

    @mode_type.setter
    def mode_type(self, val: str):
        if self._mode_type != val:
            self._mode_type = val
            self._static_dirty = True

    @property
    def color_a(self) -> RGBColor:
        return self._color_a

    @color_a.setter
    def color_a(self, val: RGBColor):
        self._color_a = val
        self._static_dirty = True

    @property
    def color_b(self) -> RGBColor:
        return self._color_b

    @color_b.setter
    def color_b(self, val: RGBColor):
        self._color_b = val
        self._static_dirty = True

    @property
    def base_color(self) -> RGBColor:
        return self.color_b

    @base_color.setter
    def base_color(self, val: RGBColor):
        self.color_b = val

    @property
    def react_color(self) -> RGBColor:
        return self.color_a

    @react_color.setter
    def react_color(self, val: RGBColor):
        self.color_a = val

    @property
    def underglow_mode(self) -> str:
        return self._underglow_mode

    @underglow_mode.setter
    def underglow_mode(self, val: str):
        self._underglow_mode = val
        self._static_dirty = True

    @property
    def underglow_color(self) -> RGBColor:
        return self._underglow_color

    @underglow_color.setter
    def underglow_color(self, val: RGBColor):
        self._underglow_color = val
        self._static_dirty = True

    @property
    def underglow_brightness(self) -> int:
        return self._underglow_brightness

    @underglow_brightness.setter
    def underglow_brightness(self, val: int):
        self._underglow_brightness = val
        self._static_dirty = True

    @property
    def static_dirty(self) -> bool:
        return self._static_dirty

    @static_dirty.setter
    def static_dirty(self, val: bool):
        self._static_dirty = val

    def mark_dirty(self):
        """Forces an immediate hardware refresh in static mode."""
        self._static_dirty = True

    @property
    def is_connected(self) -> bool:
        with self.lock:
            if not getattr(self, "_is_connected", False):
                return False
            if self.kb is None or self.client is None:
                return False
            sock = _client_socket(self.client)
            if sock is None:
                return False
            try:
                return sock.fileno() != -1
            except Exception:
                return False

    @is_connected.setter
    def is_connected(self, val: bool):
        with self.lock:
            self._is_connected = bool(val)

    def _init_default_mappings(self):
        """Builds fallback coordinate and key lookup tables prior to OpenRGB connection."""
        default_names = {k["name"].lower(): k["default_idx"] for k in ALL_KEY_DEFINITIONS}
        self.name_to_index = default_names
        self.key_coords, self.idx_to_slot = build_matrix_coords(
            self.name_to_index, dock_position=self._dock_position
        )
        self.edge_coords = build_edge_coords(
            self.name_to_index, dock_position=self._dock_position
        )
        self.vk_map, self.char_map, self.special_map = build_key_lookups(self.name_to_index)
        self.key_to_index = self.matrix.key_to_index
        self.ordered_keys = self.matrix.ORDERED_KEYS
        self.index_to_key = INDEX_TO_KEY
        self.KEY_COORDINATES = build_key_coordinates(self._dock_position)

        if self._dock_position == "detached":
            self.switch_indices = set(MAIN_SWITCH_INDICES)
            self.edge_indices = list(MAIN_EDGE_INDICES)
        else:
            self.switch_indices = set(ALL_SWITCH_INDICES)
            self.edge_indices = list(ALL_EDGE_INDICES)

        self.switch_indices.add(27)  # Explicit guarantee for Key 3
        assert 27 in self.switch_indices, "Hardware Index 27 missing from switch_indices!"
        assert 27 not in self.edge_indices, "Hardware Index 27 must not be in edge_indices!"

    def _update_geometry(self):
        """Updates coordinate mapping and active index sets when dock_position changes."""
        with self.lock:
            self.KEY_COORDINATES = build_key_coordinates(self._dock_position)
            self.key_coords, self.idx_to_slot = build_matrix_coords(
                self.name_to_index, dock_position=self._dock_position
            )
            self.edge_coords = build_edge_coords(
                self.name_to_index, dock_position=self._dock_position
            )
            if self._dock_position == "detached":
                self.switch_indices = set(MAIN_SWITCH_INDICES)
                self.edge_indices = list(MAIN_EDGE_INDICES)
            else:
                self.switch_indices = set(ALL_SWITCH_INDICES)
                self.edge_indices = list(ALL_EDGE_INDICES)
            self.switch_indices.add(27)

    def _emit_connection_status(self, connected: bool, message: str):
        self.connection_changed.emit(connected, message)
        self.connection_status_changed.emit(connected, message)

    def connect(self) -> Tuple[bool, str]:
        """Public manual connect method."""
        try:
            return self.connect_openrgb(silent=False)
        except Exception as exc:
            return False, str(exc)

    def _close_client(self):
        """Closes any stale OpenRGB socket and clears device handles."""
        with self.lock:
            self._is_connected = False
            client = self.client
            self.kb = None
            self.client = None
        if client is not None:
            try:
                sock = _client_socket(client)
                if sock is not None:
                    sock.close()
            except Exception:
                pass

    @staticmethod
    def _find_everest(client, attempts: int):
        """Scans the live USB bus for the Everest 60 (>= 147 LEDs). Returns device or None."""
        for attempt in range(max(1, attempts)):
            try:
                client.update_devices()  # Force OpenRGB to scan live USB ports
            except Exception:
                pass
            for d in client.devices:
                if "everest" in d.name.lower() and len(d.colors) >= EXPECTED_LED_COUNT:
                    return d
            if attempt < attempts - 1:
                time.sleep(2.0)  # Wait for Windows USB drivers to wake up
        return None

    @staticmethod
    def _assert_direct_mode(kb):
        """Explicitly finds and sets Direct Mode. Called once per (re)connect only."""
        direct_mode = next((m for m in kb.modes if m.name.lower() == "direct"), None)
        if direct_mode is not None:
            kb.set_mode(direct_mode)
        else:
            kb.set_mode("direct")

    def connect_openrgb(self, silent: bool = False, attempts: int = 6, emit_connected: bool = True) -> Tuple[bool, str]:
        """
        Connects to the OpenRGB SDK server at 127.0.0.1:6742, acquires the Everest 60,
        asserts Direct Mode, flushes a first frame, and ONLY THEN reports CONNECTED.
        """
        self._close_client()

        def _fail(msg: str):
            self._close_client()
            self._emit_connection_status(False, MSG_OFFLINE_SIMULATOR)
            raise ConnectionError(msg)

        if not ensure_openrgb_server():
            _fail("OpenRGB SDK server is not reachable on 127.0.0.1:6742.")

        try:
            client = OpenRGBClient("127.0.0.1", 6742, "Everest Studio Pro")
        except Exception as exc:
            _fail(f"OpenRGB client handshake failed: {exc}")

        kb = self._find_everest(client, attempts)
        if kb is None:
            try:
                client.disconnect()
            except Exception:
                pass
            _fail("Mountain Everest 60 (>=147 LEDs) not found on live USB bus.")

        # FORCE WAKE-UP: Send a dummy packet to clear the USB pipeline before asserting Direct Mode
        try:
            kb.set_color(RGBColor(0, 0, 0))
            kb.show(fast=True)
            time.sleep(0.5)
        except Exception:
            pass

        try:
            self._assert_direct_mode(kb)
            time.sleep(0.2)

            name_to_index = {led.name.lower(): idx for idx, led in enumerate(kb.leds)}
            for i in range(len(kb.colors)):
                kb.colors[i] = RGBColor(0, 0, 0)
            kb.show(fast=True)  # First frame must flush cleanly
        except Exception as exc:
            try:
                client.disconnect()
            except Exception:
                pass
            _fail(f"Direct Mode / first frame flush failed: {exc}")

        with self.lock:
            self.client = client
            self.kb = kb
            self._is_connected = True
            self.name_to_index = name_to_index
            self.key_coords, self.idx_to_slot = build_matrix_coords(
                self.name_to_index, dock_position=self._dock_position
            )
            self.edge_coords = build_edge_coords(
                self.name_to_index, dock_position=self._dock_position
            )
            self.vk_map, self.char_map, self.special_map = build_key_lookups(self.name_to_index)
            self.key_to_index = self.matrix.key_to_index
            self.ordered_keys = self.matrix.ORDERED_KEYS
            self.index_to_key = INDEX_TO_KEY
            self.KEY_COORDINATES = build_key_coordinates(self._dock_position)

            if self._dock_position == "detached":
                self.switch_indices = set(MAIN_SWITCH_INDICES)
                self.edge_indices = list(MAIN_EDGE_INDICES)
            else:
                self.switch_indices = set(ALL_SWITCH_INDICES)
                self.edge_indices = list(ALL_EDGE_INDICES)
            self.switch_indices.add(27)

            self._static_dirty = True

        if not silent:
            print(
                f"[ENGINE] Detected {len(self.switch_indices)} key switches and "
                f"{len(self.edge_indices)} perimeter edge diffusers."
            )
        if emit_connected:
            self._emit_connection_status(True, MSG_CONNECTED)
        return True, MSG_CONNECTED

    def _reset_everest_usb(self):
        """Restarts Mountain Everest 60 USB sub-interfaces (MI_00..MI_02) via pnputil."""
        if os.name != "nt":
            return
        ps_cmd = (
            "Get-PnpDevice -PresentOnly | "
            "Where-Object { $_.InstanceId -like 'USB\\VID_3282&PID_0005&MI_*' } | "
            "ForEach-Object { pnputil /restart-device $_.InstanceId }"
        )
        try:
            is_admin = bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            is_admin = False

        try:
            if is_admin:
                subprocess.run(
                    ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=10,
                    check=False,
                )
            else:
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    "powershell.exe",
                    f'-NoProfile -WindowStyle Hidden -Command "{ps_cmd}"',
                    None,
                    0,
                )
                time.sleep(2.0)
        except Exception as exc:
            print(f"[ENGINE] Virtual USB reset failed: {exc}")

    def force_hardware_sync(self, reset_usb: bool = True):
        """
        Full hardware recovery:
        1. Mark disconnected & emit connection_changed(False).
        2. Close stale TCP client socket.
        3. Kill OpenRGB.exe so MI_02 HID handle is released (sleep 0.4s).
        4. Optionally virtual-unplug Everest 60 MI_00..MI_02 via pnputil (sleep 1.5s).
        5. Respawn OpenRGB.exe --server --startminimized (wait up to 8s for port 6742).
        6. Connect, verify >=147 LEDs, assert Direct Mode once, set _static_dirty=True,
           and immediately push a full 147-LED base/effect frame via kb.show(fast=True).
        7. Emit connection_changed(True).
        """
        if not self._reconnect_busy.acquire(blocking=False):
            print("[ENGINE] Sync already in progress.")
            return
        try:
            # Step 1 & 2: Mark disconnected, emit False, and close existing client socket
            self._close_client()
            self._emit_connection_status(False, MSG_OFFLINE_SIMULATOR)

            # Step 3: Kill OpenRGB.exe BEFORE pnputil so MI_02 never locks
            if os.name == "nt":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", OPENRGB_EXE],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        timeout=5,
                        check=False,
                    )
                except Exception as exc:
                    print(f"[ENGINE] taskkill {OPENRGB_EXE} warning: {exc}")
                time.sleep(0.4)

            # Step 4: Virtual USB reset for MI_00, MI_01, MI_02
            if reset_usb:
                self._reset_everest_usb()
                time.sleep(1.5)

            # Step 5: Respawn OpenRGB daemon cleanly and wait up to 8s for port 6742
            if not spawn_openrgb_server(wait_seconds=8.0) and not check_socket_open():
                raise ConnectionError("OpenRGB SDK server failed to start on port 6742 within 8s.")

            # Step 6: Connect, assert Direct Mode once, mark dirty, and flush full 147-LED frame
            self.connect_openrgb(silent=False, attempts=3, emit_connected=False)
            self._static_dirty = True
            self._push_full_frame()

            # Step 7: Emit CONNECTED only if frame push kept connection alive
            if self.is_connected:
                self._emit_connection_status(True, MSG_CONNECTED)
                print("[ENGINE] Force hardware sync complete (USB reset, OpenRGB restarted, Direct Mode + 147-LED frame pushed).")
        except Exception as exc:
            print(f"[ENGINE] Force sync failed: {exc}")
            self._close_client()
            self._emit_connection_status(False, MSG_OFFLINE_SIMULATOR)
        finally:
            self._reconnect_busy.release()

    def _push_full_frame(self):
        """Immediately flushes a full 147-LED frame (current effect) to the hardware."""
        self._static_dirty = True
        now = time.time()
        if self.effect_name in ("static", "static_color"):
            self._render_static_frame(now)
        elif self.effect_name == "custom":
            self._render_custom_frame(now)
        else:
            self._render_loop_step(now)
        self._static_dirty = False

    def _reconnect_worker(self):
        """Background hardware (re)connect so the render/visualizer loop never blocks."""
        if not self._reconnect_busy.acquire(blocking=False):
            return
        try:
            self.connect_openrgb(silent=True, attempts=1)
        except Exception:
            pass
        finally:
            self._reconnect_busy.release()

    def _handle_disconnect(self):
        """Safely cleans up socket and transitions state to simulator/offline."""
        self._close_client()
        self._emit_connection_status(False, MSG_OFFLINE_SIMULATOR)

    def _on_hardware_error(self, exc: Exception, where: str):
        """Marks hardware offline after a socket error; the visualizer keeps animating."""
        print(f"[ENGINE] Connection lost in {where} ({exc}). Marking offline; auto-reconnect pending.")
        self._handle_disconnect()

    def _resolve_key(self, key) -> Optional[int]:
        """
        Maps incoming pynput key event to OpenRGB hardware switch index.
        Guarantees that index 0 or perimeter underglow indices are NEVER returned.
        Ignores numpad keys if dock_position is 'detached'.
        """
        try:
            idx = None
            if hasattr(key, "vk") and key.vk in self.vk_map:
                idx = self.vk_map[key.vk]
            elif key in self.special_map:
                idx = self.special_map[key]
            elif hasattr(key, "char") and key.char:
                c = key.char
                if c in self.char_map:
                    idx = self.char_map[c]
                else:
                    lower_c = c.lower()
                    lookup = f"key: {lower_c}"
                    idx = self.name_to_index.get(lookup)

            if idx is None or idx in self.edge_indices or idx not in self.key_coords:
                return None
            if self._dock_position == "detached" and idx in NUMPAD_SWITCH_INDICES:
                return None
            return idx
        except Exception:
            return None

    def trigger_switch(self, led_idx: int):
        """Triggers reactive state channels for a given switch LED index."""
        if led_idx is None or led_idx in self.edge_indices or led_idx not in self.key_coords:
            return
        if self._dock_position == "detached" and led_idx in NUMPAD_SWITCH_INDICES:
            return

        x, y = self.key_coords[led_idx]
        row = int(y)
        now = time.time()

        slot = self.idx_to_slot.get(led_idx)
        if slot is not None:
            self.key_struck.emit(slot)
            self.key_pressed.emit(slot)

        with self.lock:
            # Row-lock state: (origin_x, origin_y, t0). Numpad strikes get their own slot
            # (row + 100) so they never overwrite a simultaneous strike on the main board row.
            laser_key = row + 100 if led_idx in NUMPAD_SWITCH_INDICES else row
            self.active_rows[laser_key] = (x, y, now)
            self.active_punches[led_idx] = now
            self.active_ripples.append({"x": x, "y": y, "t0": now})
            if len(self.active_ripples) > 4:
                self.active_ripples.pop(0)

            self.active_crosshairs.append({"x": x, "y": y, "t0": now})
            if len(self.active_crosshairs) > 6:
                self.active_crosshairs.pop(0)

            seed = int((now * 100000) % 99991) ^ int(led_idx)
            self.active_explosions.append({"x": x, "y": y, "t0": now, "seed": seed})
            if len(self.active_explosions) > 5:
                self.active_explosions.pop(0)

            self.flash_energy = min(1.0, self.flash_energy * 0.35 + 0.80)
            self.key_heat[led_idx] = min(1.0, self.key_heat.get(led_idx, 0.0) + 0.28)

    def _is_reactive_trigger(self, key) -> bool:
        """
        Determines whether an incoming key event is a genuine keystroke that should
        trigger reactive effects, with fast O(1) VK bypass for zero typing lag.
        """
        try:
            # Fast O(1) bypass for Whitelisted Numpad Virtual Key Codes
            if hasattr(key, "vk") and key.vk in NUMPAD_VKS:
                return True

            # 1. Filter Modifier VK Codes
            MODIFIER_VKS = {16, 17, 18, 20, 91, 92, 93, 160, 161, 162, 163, 164, 165, 229}
            if hasattr(key, "vk") and key.vk is not None and key.vk in MODIFIER_VKS:
                return False

            # 2. Filter Modifier Names
            modifier_names = {
                "shift", "shift_l", "shift_r",
                "ctrl", "ctrl_l", "ctrl_r",
                "alt", "alt_l", "alt_r", "alt_gr",
                "caps_lock", "cmd", "cmd_l", "cmd_r", "menu"
            }
            key_name = getattr(key, "name", None)
            if key_name in modifier_names:
                return False

            # 3. Printable Characters
            if hasattr(key, "char") and key.char is not None:
                if isinstance(key.char, str) and key.char.isprintable() and len(key.char) > 0:
                    return True
                return False

            # 4. Whitelisted Functional Typing Keys
            functional_names = {
                "space", "enter", "backspace", "tab", "delete",
                "up", "down", "left", "right", "esc"
            }
            if key_name in functional_names:
                return True

            functional_keys = {
                keyboard.Key.space, keyboard.Key.enter, keyboard.Key.backspace,
                keyboard.Key.tab, keyboard.Key.delete, keyboard.Key.up,
                keyboard.Key.down, keyboard.Key.left, keyboard.Key.right,
                keyboard.Key.esc,
            }
            if key in functional_keys:
                return True
        except Exception:
            pass

        return False

    def _on_press(self, key):
        """Zero-latency keystroke callback with 80ms debounce and instant error suppression."""
        try:
            now = time.time()
            self.last_key_time = now
            if not self._is_reactive_trigger(key):
                return
            idx = self._resolve_key(key)
            if idx is None or idx in self.edge_indices or idx not in self.key_coords:
                return
            if (now - self._last_key_press_times.get(idx, 0.0)) < 0.08:
                return
            self._last_key_press_times[idx] = now
            self.trigger_switch(idx)
        except Exception:
            pass

    def _start_listener(self):
        try:
            if self.listener:
                self.listener.stop()
        except Exception:
            pass
        self.listener = keyboard.Listener(on_press=self._on_press)
        self.listener.start()

    def _resolve_switch_led_idx(self, key_ref) -> Optional[int]:
        """Resolves hardware LED index, slot index (0..80), or key name string to switch LED index."""
        if isinstance(key_ref, int):
            if key_ref in self.switch_indices or key_ref in self.key_coords:
                return key_ref
            if 0 <= key_ref < len(ALL_KEY_DEFINITIONS):
                k = ALL_KEY_DEFINITIONS[key_ref]
                return k.get("resolved_idx", k["default_idx"])
            return key_ref
        if isinstance(key_ref, str):
            clean_name = key_ref.lower()
            if clean_name in self.name_to_index:
                return self.name_to_index[clean_name]
            for k in ALL_KEY_DEFINITIONS:
                if k["id"].lower() == clean_name or k["name"].lower() == clean_name:
                    return k.get("resolved_idx", k["default_idx"])
        return None

    def paint_custom_key(self, key_ref, color: RGBColor):
        """Paints a single switch with the custom color."""
        led_idx = self._resolve_switch_led_idx(key_ref)
        if led_idx is not None:
            with self.lock:
                self.custom_key_colors[led_idx] = color
                self._static_dirty = True

    def erase_custom_key(self, key_ref):
        """Erases custom color from switch, reverting it to base color."""
        led_idx = self._resolve_switch_led_idx(key_ref)
        if led_idx is not None:
            with self.lock:
                self.custom_key_colors.pop(led_idx, None)
                self._static_dirty = True

    def clear_custom_keys(self):
        """Clears all painted custom keys, reverting every key to base color."""
        with self.lock:
            self.custom_key_colors.clear()
            self._static_dirty = True

    def fill_all_custom_keys(self, color: RGBColor):
        """Fills all switches with the given paint color in Custom Per-Key mode."""
        with self.lock:
            for k in ALL_KEY_DEFINITIONS:
                idx = k.get("resolved_idx", k["default_idx"])
                self.custom_key_colors[idx] = color
            self._static_dirty = True

    def set_custom_key_color(self, slot_or_idx: int, color: RGBColor):
        """Backwards-compatibility alias for paint_custom_key."""
        self.paint_custom_key(slot_or_idx, color)

    def run(self):
        """Main QThread execution loop running at fixed 35 FPS on a single hardware-synchronized thread."""
        self.running = True
        # Hardware connect runs in the background: the render loop and on-screen visualizer
        # must start immediately and keep animating even if USB/OpenRGB is unavailable.
        threading.Thread(target=self._reconnect_worker, daemon=True).start()
        self._start_listener()

        watchdog_check_time = time.time()

        while self.running:
            t_start = time.time()
            now = t_start

            if now - watchdog_check_time > 2.0:
                if not self.listener or not self.listener.is_alive():
                    self._start_listener()
                watchdog_check_time = now

            if self.kb is None and (now - self._last_offline_reconnect > 5.0):
                self._last_offline_reconnect = now
                threading.Thread(target=self._reconnect_worker, daemon=True).start()

            try:
                if self.effect_name in ("static", "static_color"):
                    if self._static_dirty:
                        self._render_static_frame(now)
                        self._static_dirty = False
                    else:
                        time.sleep(0.05)
                    continue

                if self.effect_name == "custom":
                    if self._static_dirty:
                        self._render_custom_frame(now)
                        self._static_dirty = False
                    else:
                        time.sleep(0.05)
                    continue

                self._render_loop_step(now)
            except Exception as e:
                print(f"[ENGINE CRASH PREVENTED] {e}")
                traceback.print_exc()

            elapsed = time.time() - t_start
            sleep_time = max(0.001, self.frame_interval - elapsed)
            time.sleep(sleep_time)

    def _render_static_frame(self, now: float):
        """
        Renders and flushes a single static frame to hardware and visualizer.
        Writes static color directly to switch indices and drives diffusers.
        Forces numpad LEDs to black when detached.
        """
        assert 27 in self.switch_indices, "Hardware Index 27 missing from switch_indices!"
        assert self.matrix.key_to_index.get('3') == 27, "Key 3 is not mapped to index 27!"

        b_factor = max(0.0, min(1.0, self.base_brightness / 100.0))
        target_color = scale_brightness(self.color_a, b_factor)
        static_tuple = (target_color.red, target_color.green, target_color.blue)

        edge_factor = max(0.0, min(1.0, self.underglow_brightness / 100.0))
        if self.underglow_brightness == 0 or self.underglow_mode == "off":
            edge_c = RGBColor(0, 0, 0)
        elif self.underglow_mode == "static":
            edge_c = scale_brightness(self.underglow_color, edge_factor)
        elif self.underglow_mode == "sync":
            edge_c = scale_brightness(self.color_a, edge_factor)
        else:
            edge_c = RGBColor(0, 0, 0)

        # 81 switch items for visualizer (slots 64..80 black when detached)
        if self._dock_position == "detached":
            frame_colors: List[Tuple[int, int, int]] = [static_tuple] * 64 + [(0, 0, 0)] * 17
        else:
            frame_colors = [static_tuple] * 81

        with self.lock:
            if self.kb and hasattr(self.kb, "colors"):
                num_hw_leds = len(self.kb.colors)
                for i in range(num_hw_leds):
                    self.kb.colors[i] = RGBColor(0, 0, 0)

                for idx in self.switch_indices:
                    if idx < num_hw_leds:
                        self.kb.colors[idx] = target_color

                for idx in self.edge_indices:
                    if idx < num_hw_leds:
                        self.kb.colors[idx] = edge_c

                if self._dock_position == "detached":
                    for idx in NUMPAD_SWITCH_INDICES:
                        if idx < num_hw_leds:
                            self.kb.colors[idx] = RGBColor(0, 0, 0)
                    for idx in NUMPAD_EDGE_INDICES:
                        if idx < num_hw_leds:
                            self.kb.colors[idx] = RGBColor(0, 0, 0)

                if num_hw_leds > 27:
                    self.kb.colors[27] = target_color

                try:
                    self.kb.show(fast=True)
                    self.last_heartbeat = now
                except OSError as exc:
                    self._on_hardware_error(exc, "static frame")
                except Exception as e:
                    self._on_hardware_error(e, "Static hardware show")

        frame_colors[3] = static_tuple
        self.frame_rendered.emit(frame_colors)
        self.underglow_rendered.emit((edge_c.red, edge_c.green, edge_c.blue))

    def _render_custom_frame(self, now: float):
        """
        Renders and flushes a single Custom Per-Key frame to hardware and visualizer.
        Unpainted switches render base_color scaled by base_brightness.
        Painted switches render custom color scaled by reactive_brightness.
        Detached modular numpad LEDs are strictly blacked out.
        """
        assert 27 in self.switch_indices, "Hardware Index 27 missing from switch_indices!"
        assert self.matrix.key_to_index.get('3') == 27, "Key 3 is not mapped to index 27!"

        base_factor = max(0.0, min(1.0, self.base_brightness / 100.0))
        react_factor = max(0.0, min(1.0, self.reactive_brightness / 100.0))
        idle_base = scale_brightness(self.color_b, base_factor)
        idle_tuple = (idle_base.red, idle_base.green, idle_base.blue)

        edge_factor = max(0.0, min(1.0, self.underglow_brightness / 100.0))
        if self.underglow_brightness == 0 or self.underglow_mode == "off":
            edge_c = RGBColor(0, 0, 0)
        elif self.underglow_mode == "static":
            edge_c = scale_brightness(self.underglow_color, edge_factor)
        elif self.underglow_mode == "sync":
            edge_c = scale_brightness(self.color_a, edge_factor * base_factor)
        else:
            edge_c = RGBColor(0, 0, 0)

        with self.lock:
            custom_snap = dict(self.custom_key_colors)

        frame_colors: List[Tuple[int, int, int]] = [idle_tuple] * 81
        for slot_idx, k in enumerate(KEY_DEFINITIONS):
            led_idx = k.get("resolved_idx", k["default_idx"])
            if led_idx in custom_snap:
                c = scale_brightness(custom_snap[led_idx], react_factor)
                frame_colors[slot_idx] = (c.red, c.green, c.blue)

        if self._dock_position != "detached":
            for num_offset, k in enumerate(NUMPAD_KEY_DEFINITIONS):
                slot_idx = 64 + num_offset
                led_idx = k.get("resolved_idx", k["default_idx"])
                if led_idx in custom_snap:
                    c = scale_brightness(custom_snap[led_idx], react_factor)
                    frame_colors[slot_idx] = (c.red, c.green, c.blue)
        else:
            for slot_idx in range(64, 81):
                frame_colors[slot_idx] = (0, 0, 0)

        with self.lock:
            if self.kb and hasattr(self.kb, "colors"):
                num_hw_leds = len(self.kb.colors)
                for i in range(num_hw_leds):
                    self.kb.colors[i] = RGBColor(0, 0, 0)

                for idx in self.switch_indices:
                    if idx < num_hw_leds:
                        if idx in custom_snap:
                            self.kb.colors[idx] = scale_brightness(custom_snap[idx], react_factor)
                        else:
                            self.kb.colors[idx] = idle_base

                for idx in self.edge_indices:
                    if idx < num_hw_leds:
                        self.kb.colors[idx] = edge_c

                if self._dock_position == "detached":
                    for idx in NUMPAD_SWITCH_INDICES:
                        if idx < num_hw_leds:
                            self.kb.colors[idx] = RGBColor(0, 0, 0)
                    for idx in NUMPAD_EDGE_INDICES:
                        if idx < num_hw_leds:
                            self.kb.colors[idx] = RGBColor(0, 0, 0)

                if num_hw_leds > 27:
                    k3_c = frame_colors[3]
                    self.kb.colors[27] = RGBColor(k3_c[0], k3_c[1], k3_c[2])

                try:
                    self.kb.show(fast=True)
                    self.last_heartbeat = now
                except OSError as exc:
                    self._on_hardware_error(exc, "custom frame")
                except Exception as e:
                    self._on_hardware_error(e, "Custom hardware show")

        self.frame_rendered.emit(frame_colors)
        self.underglow_rendered.emit((edge_c.red, edge_c.green, edge_c.blue))

    def _render_loop_step(self, now: float):
        """Computes a single 35 FPS frame for switches and edge diffusers."""
        assert 27 in self.switch_indices, "Hardware Index 27 missing from switch_indices!"
        assert self.matrix.key_to_index.get('3') == 27, "Key 3 is not mapped to index 27!"

        frame_dt = max(0.001, min(0.15, now - self._last_render_time))
        self._last_render_time = now

        with self.lock:
            max_laser_life = (30.0 / max(3.0, self.laser_speed)) + self.laser_decay
            self.active_rows = {
                r: v for r, v in self.active_rows.items() if (now - v[-1]) < max_laser_life
            }
            self.active_punches = {
                k: t for k, t in self.active_punches.items() if (now - t) < self.punch_decay
            }
            self.active_ripples = [
                w for w in self.active_ripples if (now - w["t0"]) < self.ripple_decay
            ]

            max_ch_life = (25.0 / max(5.0, self.crosshair_speed)) + self.crosshair_decay
            self.active_crosshairs = [
                c for c in self.active_crosshairs if (now - c["t0"]) < max_ch_life
            ]
            self.active_explosions = [
                ex for ex in self.active_explosions if (now - ex["t0"]) < self.explosion_decay
            ]

            self.flash_energy *= math.exp(-frame_dt / max(0.05, self.flash_decay * 0.45))
            if self.flash_energy < 0.005:
                self.flash_energy = 0.0

            if self.heatmap_mode == "live" and self.key_heat:
                cool_step = frame_dt * (0.015 + self.heatmap_cooldown * 0.025)
                self.key_heat = {
                    k: v - cool_step for k, v in self.key_heat.items() if (v - cool_step) > 0.001
                }

            rows_snap = dict(self.active_rows)
            punches_snap = dict(self.active_punches)
            ripples_snap = list(self.active_ripples)
            custom_snap = dict(self.custom_key_colors)
            state_snap = {
                "bounds": self._get_board_bounds(),
                "crosshairs": list(self.active_crosshairs),
                "explosions": list(self.active_explosions),
                "flash": self.flash_energy,
                "heat": dict(self.key_heat),
            }

        if self.effect_name == "audio_equalizer":
            self.audio_worker.set_num_bands(15 if self._dock_position == "detached" else 20)
            self.audio_worker.sensitivity = float(self.audio_gain)
            self.audio_worker.smoothing = float(self.audio_smoothing)
            bands, bass, _ = self.audio_worker.get_snapshot()
            state_snap["audio_bands"] = bands
            state_snap["audio_bass"] = bass
        elif self.effect_name == "screen_ambilight":
            self.screen_worker.capture_mode = self.screen_mode
            self.screen_worker.smoothing = float(self.screen_smoothing)
            self.screen_worker.saturation_boost = float(self.screen_saturation)
            self.screen_worker.monitor_index = max(1, int(self.screen_monitor))
            grid, edges, _ = self.screen_worker.get_snapshot()
            state_snap["screen_grid"] = grid
            state_snap["screen_edges"] = edges

        self.renderer.step_frame(
            self.effect_name,
            now,
            state_snap["bounds"],
            {
                "star_density": self.star_density,
                "storm_intensity": self.storm_intensity,
                "glitch_freq": self.glitch_freq,
                "meteor_count": self.meteor_count,
                "speed": self.speed,
                "mode_type": self.mode_type,
                "color_a": self.color_a,
                "color_b": self.color_b,
            },
        )

        frame_colors: List[Tuple[int, int, int]] = [(0, 0, 0)] * 81
        kb_colors = self.kb.colors if (self.kb and hasattr(self.kb, "colors")) else None
        num_hw_leds = len(kb_colors) if kb_colors is not None else 0

        if kb_colors is not None:
            for i in range(num_hw_leds):
                kb_colors[i] = RGBColor(0, 0, 0)

        # Step 1: Render main 64 switches
        for slot_idx, k in enumerate(KEY_DEFINITIONS):
            led_idx = k.get("resolved_idx", k["default_idx"])
            kx, ky = self.key_coords.get(led_idx, (k["x"] + k["w"] / 2.0, k["y"]))
            try:
                c = self._compute_key_color(
                    led_idx, kx, ky, now, rows_snap, punches_snap, ripples_snap, custom_snap, state_snap
                )
            except Exception as e:
                print(f"[ENGINE CRASH PREVENTED] {e}")
                traceback.print_exc()
                c = RGBColor(0, 0, 0)
            frame_colors[slot_idx] = (c.red, c.green, c.blue)
            if kb_colors is not None and led_idx < num_hw_leds:
                kb_colors[led_idx] = c

        # Step 2: Render 17 modular numpad switches if attached
        if self._dock_position != "detached":
            for num_offset, k in enumerate(NUMPAD_KEY_DEFINITIONS):
                slot_idx = 64 + num_offset
                led_idx = k.get("resolved_idx", k["default_idx"])
                kx, ky = self.key_coords.get(led_idx, (k.get("rel_x", 0.0) + 15.5, k["y"]))
                try:
                    c = self._compute_key_color(
                        led_idx, kx, ky, now, rows_snap, punches_snap, ripples_snap, custom_snap, state_snap
                    )
                except Exception as e:
                    print(f"[ENGINE CRASH PREVENTED] {e}")
                    traceback.print_exc()
                    c = RGBColor(0, 0, 0)
                frame_colors[slot_idx] = (c.red, c.green, c.blue)
                if kb_colors is not None and led_idx < num_hw_leds:
                    kb_colors[led_idx] = c
        elif kb_colors is not None:
            for idx in NUMPAD_SWITCH_INDICES:
                if idx < num_hw_leds:
                    kb_colors[idx] = RGBColor(0, 0, 0)

        # Hard-wire guarantees for Key 3 (Index 27) and Spacebar (Index 112)
        if kb_colors is not None and num_hw_leds > 27:
            k3_c = frame_colors[3]
            kb_colors[27] = RGBColor(k3_c[0], k3_c[1], k3_c[2])
        if kb_colors is not None and num_hw_leds > 112:
            sp_c = frame_colors[58]
            kb_colors[112] = RGBColor(sp_c[0], sp_c[1], sp_c[2])

        # Step 3: Edge Diffusers Pass with Anti-Burst Dampening
        last_edge_c = RGBColor(0, 0, 0)
        for idx in self.edge_indices:
            try:
                edge_c = self._compute_edge_color(
                    idx, now, rows_snap, punches_snap, ripples_snap, state_snap
                )
            except Exception as e:
                print(f"[ENGINE CRASH PREVENTED] {e}")
                traceback.print_exc()
                edge_c = RGBColor(0, 0, 0)
            last_edge_c = edge_c
            if kb_colors is not None and idx < num_hw_leds:
                kb_colors[idx] = edge_c

        # Strictly zero out numpad diffusers if detached
        if self._dock_position == "detached" and kb_colors is not None:
            for idx in NUMPAD_EDGE_INDICES:
                if idx < num_hw_leds:
                    kb_colors[idx] = RGBColor(0, 0, 0)

        # Step 4: Flush single USB report
        if kb_colors is not None:
            try:
                with self.lock:
                    if self.kb:
                        self.kb.show(fast=True)
                self.last_heartbeat = now
            except OSError as exc:
                self._on_hardware_error(exc, "render loop")
            except Exception as e:
                self._on_hardware_error(e, "Hardware show")

        self.frame_rendered.emit(frame_colors)
        self.underglow_rendered.emit((last_edge_c.red, last_edge_c.green, last_edge_c.blue))

    _render_loop = _render_loop_step

    def _compute_v3_ambient_color(
        self, eff: str, x: float, y: float, now: float,
        bounds: Tuple[float, float, float, float], factor: float,
    ) -> Optional[RGBColor]:
        """Evaluates v3.0 Phase 1 ambient & dynamic FX effects for switches or diffusers."""
        x_min, x_max, cx, cy = bounds
        if eff == "row_sweep":
            return self.renderer.render_row_sweep(
                x, y, now, x_min, x_max, self.sweep_speed, self.sweep_trail,
                self.mode_type, self.color_a, self.color_b, factor,
            )
        if eff == "waterfall":
            return self.renderer.render_waterfall(
                x, y, now, self.speed, self.mode_type, self.color_a, self.color_b, factor,
            )
        if eff == "aurora":
            return self.renderer.render_aurora(x, y, now, self.speed, self.aurora_scale, factor)
        if eff == "gradient_breathing":
            return self.renderer.render_gradient_breathing(
                x, y, now, x_min, x_max, self.speed, self.breath_min_floor,
                self.color_a, self.color_b, factor,
            )
        if eff == "cosmic_drift":
            return self.renderer.render_cosmic_drift(x, y, now, self.speed, factor)
        if eff == "thunderstorm":
            return self.renderer.render_thunderstorm(x, y, now, factor)
        if eff == "system_malfunction":
            return self.renderer.render_system_malfunction(
                x, y, now, x_min, x_max, self.color_a, self.color_b, factor,
            )
        if eff == "dna_spiral":
            x_half = max(3.5, (x_max - x_min) * 0.5)
            return self.renderer.render_dna_spiral(
                x, y, now, cx, cy, x_half, self.speed, self.dna_twist, self.dna_outward,
                self.color_a, self.color_b, factor,
            )
        if eff == "meteor_shower":
            return self.renderer.render_meteor_shower(x, y, self.mode_type, self.color_b, factor)
        return None

    def _compute_v3_reactive_color(
        self, eff: str, idx: int, x: float, y: float, now: float,
        base_factor: float, react_factor: float, state_snap: Dict[str, Any],
    ) -> Optional[RGBColor]:
        """Evaluates v3.0 Phase 1 reactive switch effects."""
        idle_base = RGBColor(0, 0, 0) if self.mode_type == "single" else scale_brightness(self.color_b, base_factor)
        if eff == "crosshair":
            intensity = calculate_crosshair_intensity(
                x, y, now, state_snap.get("crosshairs", []), self.crosshair_speed, self.crosshair_decay,
            )
            return blend_reactive(idle_base, self.color_a, react_factor, intensity)
        if eff == "full_board_flash":
            return blend_reactive(idle_base, self.color_a, react_factor, state_snap.get("flash", 0.0))
        if eff == "explosion_burst":
            col, _ = calculate_explosion_color(
                x, y, now, state_snap.get("explosions", []), self.explosion_speed,
                self.explosion_decay, idle_base, self.color_a, react_factor,
            )
            return col
        if eff == "typing_heatmap":
            heat = state_snap.get("heat", {}).get(idx, 0.0)
            return heatmap_color(heat, base_factor, react_factor)
        return None

    def _compute_key_color(
        self,
        idx: int,
        x: float,
        y: float,
        now: float,
        rows_snap: Dict[int, Tuple[float, ...]],
        punches_snap: Dict[int, float],
        ripples_snap: List[Dict[str, float]],
        custom_snap: Dict[int, RGBColor],
        state_snap: Optional[Dict[str, Any]] = None,
    ) -> RGBColor:
        """Evaluates active effect for a switch with independent dual brightness blending."""
        eff = self.effect_name
        base_factor = max(0.0, min(1.0, self.base_brightness / 100.0))
        react_factor = max(0.0, min(1.0, self.reactive_brightness / 100.0))
        snap = state_snap if state_snap is not None else {}
        bounds = snap.get("bounds") or self._get_board_bounds()

        v3_ambient = self._compute_v3_ambient_color(eff, x, y, now, bounds, base_factor)
        if v3_ambient is not None:
            return v3_ambient

        v3_reactive = self._compute_v3_reactive_color(eff, idx, x, y, now, base_factor, react_factor, snap)
        if v3_reactive is not None:
            return v3_reactive

        if eff == "audio_equalizer":
            return self.renderer.render_audio_equalizer(
                x, y, bounds[0], bounds[1],
                snap.get("audio_bands", []), snap.get("audio_bass", 0.0),
                self.audio_style, self.mode_type, self.color_a, self.color_b,
                base_factor, react_factor,
            )

        if eff == "screen_ambilight":
            return self.renderer.render_screen_ambilight(
                x, y, bounds[0], bounds[1], snap.get("screen_grid"), base_factor,
            )

        if eff == "static":
            return scale_brightness(self.color_a, base_factor)

        if eff == "wave":
            return self.renderer.render_color_wave(
                x, y, now, self.direction, self.speed, self.mode_type,
                self.color_a, self.color_b, base_factor
            )

        if eff == "tornado":
            return self.renderer.render_tornado(
                x, y, now, self.tornado_cw, self.speed, self.mode_type,
                self.color_a, self.color_b, base_factor
            )

        if eff == "breathing":
            return self.renderer.render_breathing(
                now, self.speed, self.mode_type,
                self.color_a, self.color_b, base_factor
            )

        if eff == "laser":
            try:
                idle_base = RGBColor(0, 0, 0) if self.mode_type == "single" else scale_brightness(self.color_b, base_factor)
                intensity = calculate_laser_intensity(x, y, now, rows_snap, self.laser_speed, self.laser_decay, self.pulse_width)
                return blend_reactive(idle_base, self.color_a, react_factor, intensity)
            except Exception as e:
                print(f"[ENGINE CRASH PREVENTED] {e}")
                traceback.print_exc()
                return scale_brightness(self.color_b, base_factor) if self.mode_type != "single" else RGBColor(0, 0, 0)

        if eff == "matrix":
            return self.renderer.render_matrix_rain(
                x, y, now, self.matrix_speed, self.mode_type,
                self.color_a, self.color_b, self.void_color, base_factor
            )

        if eff == "ripple":
            idle_base = RGBColor(0, 0, 0) if self.mode_type == "single" else scale_brightness(self.color_b, base_factor)
            intensity = calculate_ripple_intensity(x, y, now, ripples_snap, self.ripple_speed, self.ripple_decay)
            return blend_reactive(idle_base, self.color_a, react_factor, intensity)

        if eff == "punch":
            idle_base = RGBColor(0, 0, 0) if self.mode_type == "single" else scale_brightness(self.color_b, base_factor)
            intensity = calculate_punch_intensity(idx, now, punches_snap, self.punch_decay)
            return blend_reactive(idle_base, self.color_a, react_factor, intensity)

        if eff == "custom":
            if idx in custom_snap:
                return scale_brightness(custom_snap[idx], react_factor)
            return scale_brightness(self.color_b, base_factor)

        return self.renderer.render_off()

    def _compute_edge_color(
        self,
        idx: int,
        now: float,
        rows_snap: Dict[int, Tuple[float, ...]],
        punches_snap: Dict[int, float],
        ripples_snap: List[Dict[str, float]],
        state_snap: Optional[Dict[str, Any]] = None,
    ) -> RGBColor:
        """
        Anti-Burst Underglow Sync:
        Calculates distance from reactive wave origin to edge diffuser coordinates.
        Applies strict 0.4 dampening multiplier to wave_intensity on perimeter diffusers;
        scales by underglow_brightness. Preserves total black when underglow_brightness == 0.
        """
        if self.underglow_brightness == 0 or self.underglow_mode == "off" or self.effect_name == "off":
            return RGBColor(0, 0, 0)

        edge_ug_factor = max(0.0, min(1.0, self.underglow_brightness / 100.0))

        if self.underglow_mode == "static":
            return scale_brightness(self.underglow_color, edge_ug_factor)

        # Mode is "sync"
        eff = self.effect_name
        ex, ey = self.edge_coords.get(idx, (7.5, 2.0))
        base_factor = max(0.0, min(1.0, self.base_brightness / 100.0))
        react_factor = max(0.0, min(1.0, self.reactive_brightness / 100.0))
        snap = state_snap if state_snap is not None else {}
        bounds = snap.get("bounds") or self._get_board_bounds()

        if eff in ("ripple", "laser", "punch", "crosshair", "full_board_flash", "explosion_burst"):
            try:
                if eff == "ripple":
                    wave_intensity = calculate_ripple_intensity(
                        ex, ey, now, ripples_snap, self.ripple_speed, self.ripple_decay
                    )
                elif eff == "laser":
                    wave_intensity = calculate_laser_intensity(
                        ex, ey, now, rows_snap, self.laser_speed, self.laser_decay, self.pulse_width
                    )
                elif eff == "punch":
                    wave_intensity = calculate_punch_edge_intensity(
                        ex, ey, now, punches_snap, self.punch_decay, self.key_coords
                    )
                elif eff == "crosshair":
                    wave_intensity = calculate_crosshair_intensity(
                        ex, ey, now, snap.get("crosshairs", []), self.crosshair_speed, self.crosshair_decay
                    )
                elif eff == "full_board_flash":
                    wave_intensity = snap.get("flash", 0.0)
                else:
                    _, wave_intensity = calculate_explosion_color(
                        ex, ey, now, snap.get("explosions", []), self.explosion_speed,
                        self.explosion_decay, RGBColor(0, 0, 0), self.color_a, 1.0,
                    )
            except Exception as e:
                print(f"[ENGINE CRASH PREVENTED] {e}")
                traceback.print_exc()
                wave_intensity = 0.0

            ambient_base = scale_brightness(
                self.color_b if self.mode_type != "single" else RGBColor(0, 0, 0),
                edge_ug_factor * base_factor
            )
            dampened_intensity = wave_intensity * 0.4 * edge_ug_factor * react_factor
            return blend_reactive(ambient_base, self.color_a, 1.0, dampened_intensity)

        if eff == "thunderstorm":
            return self.renderer.get_thunderclap_edge_color(ex, ey, now, edge_ug_factor * base_factor)

        if eff == "typing_heatmap":
            heat_vals = list(snap.get("heat", {}).values())
            avg_heat = (sum(heat_vals) / len(heat_vals)) if heat_vals else 0.0
            return heatmap_color(avg_heat, edge_ug_factor * base_factor, edge_ug_factor * react_factor)

        if eff == "audio_equalizer":
            ambient_base = scale_brightness(self.color_b, edge_ug_factor * base_factor)
            bass = snap.get("audio_bass", 0.0)
            dampened = bass * 0.4 * edge_ug_factor * react_factor
            return blend_reactive(ambient_base, self.color_a, 1.0, dampened)

        if eff == "screen_ambilight":
            return self.renderer.render_screen_edge(
                ex, ey, bounds[0], bounds[1], snap.get("screen_edges"), edge_ug_factor * base_factor,
            )

        v3_edge = self._compute_v3_ambient_color(eff, ex, ey, now, bounds, edge_ug_factor * base_factor)
        if v3_edge is not None:
            return v3_edge

        if eff in ("static", "custom"):
            return scale_brightness(self.color_a, edge_ug_factor * base_factor)

        if eff == "wave":
            return self.renderer.render_color_wave(
                ex, ey, now, self.direction, self.speed, self.mode_type,
                self.color_a, self.color_b, edge_ug_factor * base_factor
            )

        if eff == "tornado":
            return self.renderer.render_tornado(
                ex, ey, now, self.tornado_cw, self.speed, self.mode_type,
                self.color_a, self.color_b, edge_ug_factor * base_factor
            )

        if eff == "breathing":
            return self.renderer.render_breathing(
                now, self.speed, self.mode_type,
                self.color_a, self.color_b, edge_ug_factor * base_factor
            )

        if eff == "matrix":
            if self.mode_type == "dual":
                return scale_brightness(self.color_b, edge_ug_factor * base_factor)
            return scale_brightness(RGBColor(0, 80, 25), edge_ug_factor * base_factor)

        return scale_brightness(self.base_color, edge_ug_factor * base_factor)

    def stop(self):
        """Cleans up threads, hooks, system sync workers, and resets lighting on shutdown."""
        self.running = False
        self.audio_worker.stop()
        self.screen_worker.stop()
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
        self.wait(600)
        with self.lock:
            if self.kb:
                try:
                    self.kb.set_color(self.color_b, fast=True)
                except Exception:
                    pass


# Module-level aliases
LightingEngine = LightingEngineThread
