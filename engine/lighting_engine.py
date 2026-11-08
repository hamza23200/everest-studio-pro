"""
Everest Studio Pro - Dedicated Lighting Engine QThread.
Maintains 35 FPS hardware-synchronized frame clock, socket stability,
device enumeration retry loops, zero-copy Signal(object) frame emission,
full 44-LED underglow management, persistent background auto-reconnect supervisor,
and low-latency global pynput hooks.
"""

import sys
import time
import socket
import subprocess
import os
import threading
from typing import Dict, List, Tuple, Optional, Set
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
    EDGE_INDICES,
    SWITCH_INDICES,
    build_matrix_coords,
    build_key_lookups,
)
from engine.effects import EffectRenderer, scale_brightness, blend_colors


def check_socket_open(host: str = "127.0.0.1", port: int = 6742, timeout: float = 0.30) -> bool:
    """Verifies if OpenRGB SDK Server is actively listening on the target TCP port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def spawn_openrgb_server() -> bool:
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
        os.path.join(base_dir, "OpenRGB.exe"),
        os.path.join(base_dir, "dist", "OpenRGB.exe"),
        os.path.join(os.getcwd(), "OpenRGB.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "OpenRGB", "OpenRGB.exe"),
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "OpenRGB", "OpenRGB.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "OpenRGB", "OpenRGB.exe"),
        "C:\\OpenRGB\\OpenRGB.exe",
    ]

    target = next((p for p in candidates if os.path.exists(p)), None)
    if not target:
        import shutil
        target = shutil.which("OpenRGB.exe") or shutil.which("OpenRGB")

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
            for _ in range(15):
                time.sleep(0.4)
                if check_socket_open():
                    return True
        except Exception:
            pass
    return False


class LightingEngineThread(QThread):
    """
    Dedicated QThread maintaining continuous USB output at 35 FPS,
    RAM buffer mutation, and UI visualizer sync via zero-copy Signal(object).
    Features persistent background auto-reconnect supervisor and device enumeration handling.
    """
    # Zero-copy object signal: emits list of 64 RGB tuples [(r, g, b), ...] for slots 0..63
    frame_rendered = Signal(object)
    underglow_rendered = Signal(object)
    connection_changed = Signal(bool, str)
    connection_status_changed = Signal(bool, str)  # Backward compatibility alias
    key_struck = Signal(int)                       # Emits slot index 0..63

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fps = 35.0
        self.frame_interval = 1.0 / self.fps
        self.running = False
        self.lock = threading.Lock()

        # Matrix mapping reference
        self.matrix = matrix

        # OpenRGB Client & Device Handle
        self.client: Optional[OpenRGBClient] = None
        self.kb = None
        self.name_to_index: Dict[str, int] = {}
        self.key_coords: Dict[int, Tuple[float, float]] = {}
        self.idx_to_slot: Dict[int, int] = {}
        self.vk_map: Dict[int, int] = {}
        self.char_map: Dict[str, int] = {}
        self.special_map: Dict[keyboard.Key, int] = {}
        self.switch_indices: Set[int] = set(SWITCH_INDICES)
        self.edge_indices: List[int] = list(EDGE_INDICES)

        # Initialize default geometry even before OpenRGB connects so visualizer works offline
        self._init_default_mappings()

        # Effect Renderer & Configuration
        self.renderer = EffectRenderer()
        self._effect_name = "static"       # 'static', 'wave', 'tornado', 'breathing', 'laser', 'matrix', 'ripple', 'punch', 'custom', 'off'
        self._mode_type = "dual"           # 'single', 'dual', 'rainbow', 'matrix_classic'
        self._color_a = RGBColor(255, 255, 0)   # Primary / Strike Color (Yellow)
        self._color_b = RGBColor(0, 0, 255)     # Secondary / Base Color (Blue)
        self.void_color = RGBColor(0, 0, 0)    # Matrix Void Base
        self._brightness = 1.0             # 0.0 to 1.0
        self.speed = 5.0                  # 1.0 to 10.0 (Wave / Tornado / Breathing)
        self.matrix_speed = 6.0           # 2.0 to 15.0 rows/s
        self.direction = "right"          # 'right', 'left', 'down', 'up', 'diagonal'
        self.tornado_cw = True

        # Custom Per-Key dictionary (indexed by slot 0..63 AND hardware LED index)
        self.custom_key_colors: Dict[int, RGBColor] = {
            k["default_idx"]: RGBColor(0, 120, 215) for k in KEY_DEFINITIONS
        }
        self.custom_colors = self.custom_key_colors  # Alias

        # Dedicated Underglow Settings
        self._underglow_mode = "sync"      # 'sync', 'static', 'off'
        self._underglow_color = RGBColor(0, 120, 215)
        self._underglow_brightness = 40    # 0 to 100, default 40%

        # Static mode dirty-checking flag
        self._static_dirty = True

        # Reactive Tuning Parameters
        self.laser_speed = 60.0           # 15.0 to 120.0 keys/s (default 60.0)
        self.laser_decay = 0.16           # 0.05 to 0.50s (default 0.16s)
        self.pulse_width = 2.0            # Beam head width
        self.punch_decay = 0.35           # 0.10 to 2.50s (default 0.35s)
        self.ripple_speed = 15.0
        self.ripple_width = 2.4           # Enhanced wave crest width (up from 1.6)
        self.ripple_decay = 0.65

        # Reactive State Channels
        self.active_rows: Dict[int, Tuple[float, float]] = {}  # row -> (origin_x, t0)
        self.active_ripples: List[Dict[str, float]] = []       # [{'x', 'y', 't0'}]
        self.active_punches: Dict[int, float] = {}             # led_idx -> t0

        # Low-latency background keyboard listener
        self.listener: Optional[keyboard.Listener] = None
        self.last_key_time = time.time()
        self.last_heartbeat = time.time()
        self._last_offline_reconnect = 0.0

    @property
    def effect_name(self) -> str:
        return self._effect_name

    @effect_name.setter
    def effect_name(self, val: str):
        if self._effect_name != val:
            self._effect_name = val
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
    def brightness(self) -> float:
        return self._brightness

    @brightness.setter
    def brightness(self, val: float):
        self._brightness = val
        self._static_dirty = True

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
            if self.kb is None or self.client is None:
                return False
            sock = getattr(self.client, "sock", None)
            if sock is None:
                return False
            try:
                return sock.fileno() != -1
            except Exception:
                return False

    def _init_default_mappings(self):
        """Builds fallback coordinate and key lookup tables prior to OpenRGB connection."""
        default_names = {k["name"].lower(): k["default_idx"] for k in KEY_DEFINITIONS}
        self.name_to_index = default_names
        self.key_coords, self.idx_to_slot = build_matrix_coords(self.name_to_index)
        self.vk_map, self.char_map, self.special_map = build_key_lookups(self.name_to_index)
        self.key_to_index = self.matrix.key_to_index
        self.ordered_keys = self.matrix.ordered_keys
        self.KEY_COORDINATES = self.matrix.KEY_COORDINATES

        # Explicitly collect all unique integer switch indices
        self.switch_indices = set(idx for idx in self.matrix.key_to_index.values() if idx is not None)
        self.switch_indices.add(27)  # Explicit guarantee for Key 3
        assert 27 in self.switch_indices, "Hardware Index 27 missing from switch_indices!"

        self.edge_indices = [i for i in range(147) if i not in self.switch_indices]
        assert 27 not in self.edge_indices, "Hardware Index 27 must not be in edge_indices!"

    def _emit_connection_status(self, connected: bool, message: str):
        self.connection_changed.emit(connected, message)
        self.connection_status_changed.emit(connected, message)

    def connect(self) -> Tuple[bool, str]:
        """Public manual connect method."""
        return self.connect_openrgb(silent=False)

    def connect_openrgb(self, silent: bool = False) -> Tuple[bool, str]:
        """
        Connects to OpenRGB SDK Server, handles device discovery race conditions,
        enforces Direct Mode, and initializes internal matrix lookup tables.
        """
        if not check_socket_open():
            spawn_openrgb_server()

        try:
            client = OpenRGBClient()
            if hasattr(client, "sock") and client.sock:
                client.sock.settimeout(3.0)  # Generous window for 147-LED enumeration

            # Retry querying devices up to 5 times (500ms delay) to handle OpenRGB USB enumeration race
            kb = None
            for _ in range(5):
                try:
                    if hasattr(client, "update_devices"):
                        client.update_devices()
                except Exception:
                    pass
                kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
                if kb:
                    break
                time.sleep(0.5)

            if not kb:
                with self.lock:
                    self.client = client
                    self.kb = None
                msg = "OFFLINE / SIMULATOR"
                self._emit_connection_status(False, msg)
                return False, msg

            # Explicit Direct Mode activation
            direct_mode = next((m for m in kb.modes if m.name.lower() == "direct"), None)
            if direct_mode:
                try:
                    kb.set_mode(direct_mode)
                except Exception:
                    pass
            else:
                try:
                    kb.set_mode("direct")
                except Exception:
                    pass

            # Once device enumeration and mode configuration are complete,
            # switch to low-latency timeout for the 35 FPS rendering loop
            if hasattr(client, "sock") and client.sock:
                client.sock.settimeout(0.2)

            with self.lock:
                self.client = client
                self.kb = kb
                self.name_to_index = {led.name.lower(): idx for idx, led in enumerate(self.kb.leds)}
                self.key_coords, self.idx_to_slot = build_matrix_coords(self.name_to_index)
                self.vk_map, self.char_map, self.special_map = build_key_lookups(self.name_to_index)
                self.key_to_index = self.matrix.key_to_index
                self.ordered_keys = self.matrix.ordered_keys
                self.KEY_COORDINATES = self.matrix.KEY_COORDINATES

                # Explicitly collect all unique integer switch indices
                self.switch_indices = set(idx for idx in self.matrix.key_to_index.values() if idx is not None)
                self.switch_indices.add(27)  # Explicit guarantee for Key 3
                assert 27 in self.switch_indices, "Hardware Index 27 missing from switch_indices!"

                # Dynamically classify EVERY remaining LED as an edge/perimeter diffuser (all 83 LEDs)
                total_led_count = len(self.kb.colors)
                self.edge_indices = [i for i in range(total_led_count) if i not in self.switch_indices]
                assert 27 not in self.edge_indices, "Hardware Index 27 must not be in edge_indices!"
                print(f"[ENGINE] Detected {len(self.switch_indices)} key switches and {len(self.edge_indices)} perimeter edge diffusers.")

                # Initialize all 147 LEDs cleanly in RAM (pre-fill black) and flush
                for i in range(total_led_count):
                    self.kb.colors[i] = RGBColor(0, 0, 0)
                try:
                    self.kb.show(fast=True)
                except Exception:
                    pass

                self._static_dirty = True

            self._emit_connection_status(True, "CONNECTED")
            return True, "CONNECTED"
        except Exception as exc:
            with self.lock:
                try:
                    if "client" in locals() and client and hasattr(client, "sock") and client.sock:
                        client.sock.close()
                except Exception:
                    pass
                self.kb = None
                self.client = None
            msg = "OFFLINE / SIMULATOR"
            self._emit_connection_status(False, msg)
            return False, f"Connection error: {exc}"

    def _handle_disconnect(self):
        """Safely cleans up socket and transitions state to simulator/offline."""
        with self.lock:
            try:
                if self.client and hasattr(self.client, "sock") and self.client.sock:
                    self.client.sock.close()
            except Exception:
                pass
            self.kb = None
            self.client = None
        self._emit_connection_status(False, MSG_OFFLINE_SIMULATOR)

    def _resolve_key(self, key) -> Optional[int]:
        """
        Maps incoming pynput key event to OpenRGB hardware switch index.
        Guarantees that index 0 or any perimeter underglow index is NEVER returned.
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
                    if lookup in self.name_to_index:
                        idx = self.name_to_index[lookup]
                    else:
                        idx = self.name_to_index.get(lookup)

            # Strict perimeter & invalid index elimination
            if idx is None or idx in self.edge_indices or idx not in self.key_coords:
                return None
            return idx
        except Exception:
            return None

    def trigger_switch(self, led_idx: int):
        """Triggers reactive state channels for a given switch LED index."""
        if led_idx is None or led_idx in self.edge_indices or led_idx not in self.key_coords:
            return
        x, y = self.key_coords[led_idx]
        row = int(round(y))
        now = time.time()

        slot = self.idx_to_slot.get(led_idx)
        if slot is not None:
            self.key_struck.emit(slot)

        with self.lock:
            self.active_rows[row] = (x, now)
            self.active_punches[led_idx] = now
            self.active_ripples.append({"x": x, "y": y, "t0": now})
            if len(self.active_ripples) > 4:
                self.active_ripples.pop(0)

    def _is_reactive_trigger(self, key) -> bool:
        """
        Determines whether an incoming key event is a genuine keystroke that should
        trigger reactive effects (Ripple, Laser, Punch), filtering out phantom background
        polling, OS telemetry, mouse driver queries, and standalone modifier presses.
        """
        # 1. Filter Modifier VK Codes
        # 16=Shift, 17=Ctrl, 18=Alt, 20=CapsLock, 91=LWin, 92=RWin, 93=Apps/Menu
        # 160=LShift, 161=RShift, 162=LCtrl, 163=RCtrl, 164=LAlt, 165=RAlt
        # 229=IME process / composition key
        MODIFIER_VKS = {16, 17, 18, 20, 91, 92, 93, 160, 161, 162, 163, 164, 165, 229}
        if hasattr(key, "vk") and key.vk is not None:
            if key.vk in MODIFIER_VKS:
                return False

        # 2. Filter Modifier Names
        modifier_names = {
            "shift", "shift_l", "shift_r",
            "ctrl", "ctrl_l", "ctrl_r",
            "alt", "alt_l", "alt_r", "alt_gr",
            "caps_lock",
            "cmd", "cmd_l", "cmd_r",
            "menu"
        }
        key_name = getattr(key, "name", None)
        if key_name in modifier_names:
            return False

        # 3. Printable Characters (Strict check: must be non-empty printable string)
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

        try:
            functional_keys = {
                keyboard.Key.space,
                keyboard.Key.enter,
                keyboard.Key.backspace,
                keyboard.Key.tab,
                keyboard.Key.delete,
                keyboard.Key.up,
                keyboard.Key.down,
                keyboard.Key.left,
                keyboard.Key.right,
                keyboard.Key.esc,
            }
            if key in functional_keys:
                return True
        except Exception:
            pass

        return False

    def _on_press(self, key):
        """Zero-latency keystroke callback with phantom modifier filtering."""
        try:
            self.last_key_time = time.time()
            if not self._is_reactive_trigger(key):
                return
            idx = self._resolve_key(key)
            if idx is None or idx in self.edge_indices or idx not in self.key_coords:
                return
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

    def set_custom_key_color(self, slot_or_idx: int, color: RGBColor):
        """Updates custom per-key color by slot (0..63) or hardware LED index."""
        with self.lock:
            if 0 <= slot_or_idx < len(KEY_DEFINITIONS):
                k = KEY_DEFINITIONS[slot_or_idx]
                led_idx = k.get("resolved_idx", k["default_idx"])
                self.custom_key_colors[led_idx] = color
                self.custom_key_colors[k["default_idx"]] = color
            else:
                self.custom_key_colors[slot_or_idx] = color

    def fill_all_custom_keys(self, color: RGBColor):
        """Fills all 64 switches with the given color in Custom Per-Key mode."""
        with self.lock:
            for k in KEY_DEFINITIONS:
                led_idx = k.get("resolved_idx", k["default_idx"])
                self.custom_key_colors[led_idx] = color
                self.custom_key_colors[k["default_idx"]] = color

    def run(self):
        """Main QThread execution loop running at fixed 35 FPS on a single hardware-synchronized thread."""
        self.running = True
        self.connect_openrgb()
        self._start_listener()

        watchdog_check_time = time.time()

        while self.running:
            t_start = time.time()
            now = t_start

            # Watchdog check for keyboard hook health every 2 seconds
            if now - watchdog_check_time > 2.0:
                if not self.listener or not self.listener.is_alive():
                    self._start_listener()
                watchdog_check_time = now

            # If offline / simulator, attempt reconnection every 5s from the render thread
            if self.kb is None and (now - self._last_offline_reconnect > 5.0):
                self._last_offline_reconnect = now
                try:
                    self.connect_openrgb(silent=True)
                except Exception:
                    pass

            if self.effect_name in ("static", "static_color"):
                if self._static_dirty:
                    self._render_static_frame(now)
                    self._static_dirty = False
                else:
                    time.sleep(0.05)
                continue

            self._render_loop_step(now)

            # High-precision 35 FPS frame pacing
            elapsed = time.time() - t_start
            sleep_time = max(0.001, self.frame_interval - elapsed)
            time.sleep(sleep_time)

    def _render_static_frame(self, now: float):
        """
        Renders and flushes a single static frame to hardware and visualizer.
        Writes static color directly to all switch indices using self.switch_indices
        and drives all edge diffusers according to the underglow mode.
        """
        assert 27 in self.switch_indices, "Hardware Index 27 missing from switch_indices!"
        assert self.matrix.key_to_index.get('3') == 27, "Key 3 is not mapped to index 27!"

        b_val = self.brightness if self.brightness <= 1.0 else self.brightness / 100.0
        b_factor = max(0.0, min(1.0, b_val))
        target_color = RGBColor(
            int(self.color_a.red * b_factor),
            int(self.color_a.green * b_factor),
            int(self.color_a.blue * b_factor)
        )
        edge_factor = max(0.0, min(1.0, self.underglow_brightness / 100.0))

        if self.underglow_brightness == 0 or self.underglow_mode == "off":
            edge_c = RGBColor(0, 0, 0)
        elif self.underglow_mode == "static":
            edge_c = RGBColor(
                int(self.underglow_color.red * edge_factor),
                int(self.underglow_color.green * edge_factor),
                int(self.underglow_color.blue * edge_factor),
            )
        elif self.underglow_mode == "sync":
            edge_c = RGBColor(
                int(self.color_a.red * edge_factor),
                int(self.color_a.green * edge_factor),
                int(self.color_a.blue * edge_factor),
            )
        else:
            edge_c = RGBColor(0, 0, 0)

        # In Static mode: all 64 items must equal the active static color
        static_tuple = (target_color.red, target_color.green, target_color.blue)
        frame_colors: List[Tuple[int, int, int]] = [static_tuple] * 64

        with self.lock:
            if self.kb and hasattr(self.kb, "colors"):
                num_hw_leds = len(self.kb.colors)
                # Ensure edge indices are isolated from switches
                self.edge_indices = [i for i in range(num_hw_leds) if i not in self.switch_indices]
                assert 27 not in self.edge_indices, "Hardware Index 27 must not be in edge_indices!"

                for i in range(num_hw_leds):
                    self.kb.colors[i] = RGBColor(0, 0, 0)

                # Write target_color directly to all switch indices
                for idx in self.switch_indices:
                    if idx < num_hw_leds:
                        self.kb.colors[idx] = target_color

                # Explicitly verify Key 3 (Index 27) received target_color
                if num_hw_leds > 27:
                    assert self.kb.colors[27] == target_color, f"Key 3 (index 27) failed assertion! Got {self.kb.colors[27]}"

                # Underglow Isolation: Key 3 is never overwritten by underglow logic
                for idx in self.edge_indices:
                    if idx < num_hw_leds:
                        self.kb.colors[idx] = edge_c

                print("[MATRIX] Key 3 (Index 27) successfully written.")

                try:
                    self.kb.show(fast=True)
                    self.last_heartbeat = now
                except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                    print(f"[ENGINE] Connection lost in static frame ({exc}). Reconnecting...")
                    self._handle_disconnect()
                    try:
                        self.connect_openrgb(silent=True)
                    except Exception:
                        pass
                except Exception as e:
                    print(f"[ENGINE] Static hardware show error: {e}")

        assert len(frame_colors) == 64, f"frame_colors must be 64 items, got {len(frame_colors)}"
        # Ensure slot 3 (Key 3) receives the active yellow RGB tuple
        frame_colors[3] = static_tuple
        self.frame_rendered.emit(frame_colors)
        self.underglow_rendered.emit((edge_c.red, edge_c.green, edge_c.blue))

    def _render_loop_step(self, now: float):
        """Computes a single 35 FPS frame for all 64 switches and 44 edge LEDs."""
        assert 27 in self.switch_indices, "Hardware Index 27 missing from switch_indices!"
        assert self.matrix.key_to_index.get('3') == 27, "Key 3 is not mapped to index 27!"
        assert 27 not in self.edge_indices, "Hardware Index 27 must not be in edge_indices!"

        with self.lock:
            max_laser_life = (15.0 / max(10.0, self.laser_speed)) + self.laser_decay
            self.active_rows = {
                r: v for r, v in self.active_rows.items() if (now - v[1]) < max_laser_life
            }
            self.active_punches = {
                k: t for k, t in self.active_punches.items() if (now - t) < self.punch_decay
            }
            self.active_ripples = [
                w for w in self.active_ripples if (now - w["t0"]) < self.ripple_decay
            ]

            rows_snap = dict(self.active_rows)
            punches_snap = dict(self.active_punches)
            ripples_snap = list(self.active_ripples)
            custom_snap = dict(self.custom_key_colors)

        # Lightweight list of 64 RGB tuples [(r, g, b), ...] strictly for switches 0..63
        frame_colors: List[Tuple[int, int, int]] = [(0, 0, 0)] * 64

        kb_colors = self.kb.colors if (self.kb and hasattr(self.kb, "colors")) else None
        num_hw_leds = len(kb_colors) if kb_colors is not None else 0

        # Step 1: Pre-fill entire 147-LED buffer with black
        if kb_colors is not None:
            for i in range(num_hw_leds):
                kb_colors[i] = RGBColor(0, 0, 0)

        # Step 2: Render switches ONLY (64 keys)
        if self.effect_name == "static":
            b_factor = max(0.0, min(1.0, self.brightness))
            static_c = RGBColor(
                int(self.color_a.red * b_factor),
                int(self.color_a.green * b_factor),
                int(self.color_a.blue * b_factor),
            )
            static_tuple = (static_c.red, static_c.green, static_c.blue)
            frame_colors = [static_tuple] * 64
            if kb_colors is not None:
                for k in KEY_DEFINITIONS:
                    led_idx = k.get("resolved_idx", k["default_idx"])
                    if led_idx < num_hw_leds:
                        kb_colors[led_idx] = static_c
        else:
            for slot_idx, k in enumerate(KEY_DEFINITIONS):
                led_idx = k.get("resolved_idx", k["default_idx"])
                kx, ky = self.key_coords.get(led_idx, (k["x"] + k["w"] / 2.0, k["y"]))

                c = self._compute_key_color(
                    led_idx, kx, ky, now, rows_snap, punches_snap, ripples_snap, custom_snap
                )
                frame_colors[slot_idx] = (c.red, c.green, c.blue)

                if kb_colors is not None and led_idx < num_hw_leds:
                    kb_colors[led_idx] = c

        # Hard-wire guarantee: Ensure self.kb.colors[27] (Key 3) receives the active key color on every frame
        if kb_colors is not None and num_hw_leds > 27:
            k3_c = frame_colors[3]
            kb_colors[27] = RGBColor(k3_c[0], k3_c[1], k3_c[2])

        # Hard-wire guarantee: Ensure self.kb.colors[112] (Spacebar) receives active key color on every frame
        if kb_colors is not None and num_hw_leds > 112:
            sp_c = frame_colors[58]
            kb_colors[112] = RGBColor(sp_c[0], sp_c[1], sp_c[2])

        # Step 3: Absolute Final Pass — All 83 Edge Diffusers
        edge_factor = max(0.0, min(1.0, self.underglow_brightness / 100.0))

        for idx in self.edge_indices:
            if self.underglow_brightness == 0 or self.underglow_mode == "off" or self.effect_name == "off":
                edge_c = RGBColor(0, 0, 0)
            elif self.underglow_mode == "static":
                edge_c = RGBColor(
                    int(self.underglow_color.red * edge_factor),
                    int(self.underglow_color.green * edge_factor),
                    int(self.underglow_color.blue * edge_factor),
                )
            elif self.underglow_mode == "sync":
                if self.effect_name in ("punch", "laser", "ripple"):
                    ambient_base = self.base_color
                    edge_c = RGBColor(
                        int(ambient_base.red * edge_factor),
                        int(ambient_base.green * edge_factor),
                        int(ambient_base.blue * edge_factor),
                    )
                else:
                    raw_c = self._compute_underglow_color(now, rows_snap, punches_snap, ripples_snap)
                    edge_c = RGBColor(
                        int(raw_c.red * edge_factor),
                        int(raw_c.green * edge_factor),
                        int(raw_c.blue * edge_factor),
                    )
            else:
                edge_c = RGBColor(0, 0, 0)

            if kb_colors is not None and idx < num_hw_leds:
                kb_colors[idx] = edge_c

        # Step 4: Flush single USB report
        if kb_colors is not None:
            try:
                with self.lock:
                    if self.kb:
                        self.kb.show(fast=True)
                self.last_heartbeat = now
            except (BrokenPipeError, ConnectionResetError, OSError) as exc:
                print(f"[ENGINE] Connection lost in render loop ({exc}). Reconnecting...")
                self._handle_disconnect()
                try:
                    self.connect_openrgb(silent=True)
                except Exception:
                    pass
            except Exception as e:
                print(f"[ENGINE] Hardware show error: {e}")

        # 3. Emit zero-copy list of 64 RGB tuples via Signal(object) to UI visualizer
        assert len(frame_colors) == 64, f"frame_colors must be 64 items, got {len(frame_colors)}"
        self.frame_rendered.emit(frame_colors)
        self.underglow_rendered.emit((edge_c.red, edge_c.green, edge_c.blue))

    _render_loop = _render_loop_step

    def _compute_key_color(
        self,
        idx: int,
        x: float,
        y: float,
        now: float,
        rows_snap: Dict[int, Tuple[float, float]],
        punches_snap: Dict[int, float],
        ripples_snap: List[Dict[str, float]],
        custom_snap: Dict[int, RGBColor],
    ) -> RGBColor:
        """Evaluates active mathematical effect for switch at (x, y)."""
        eff = self.effect_name

        if eff == "static":
            return self.renderer.render_static(self.color_a, self.brightness)

        if eff == "wave":
            return self.renderer.render_color_wave(
                x, y, now, self.direction, self.speed, self.mode_type,
                self.color_a, self.color_b, self.brightness
            )

        if eff == "tornado":
            return self.renderer.render_tornado(
                x, y, now, self.tornado_cw, self.speed, self.mode_type,
                self.color_a, self.color_b, self.brightness
            )

        if eff == "breathing":
            return self.renderer.render_breathing(
                now, self.speed, self.mode_type,
                self.color_a, self.color_b, self.brightness
            )

        if eff == "laser":
            return self.renderer.render_laser(
                x, y, now, rows_snap, self.laser_speed,
                self.pulse_width, self.laser_decay, self.mode_type,
                self.color_a, self.color_b, self.brightness
            )

        if eff == "matrix":
            return self.renderer.render_matrix_rain(
                x, y, now, self.matrix_speed, self.mode_type,
                self.color_a, self.color_b, self.void_color, self.brightness
            )

        if eff == "ripple":
            return self.renderer.render_ripple(
                x, y, now, ripples_snap, self.ripple_speed,
                self.ripple_width, self.ripple_decay, self.mode_type,
                self.color_a, self.color_b, self.brightness
            )

        if eff == "punch":
            return self.renderer.render_punch(
                idx, now, punches_snap, self.punch_decay, self.mode_type,
                self.color_a, self.color_b, self.brightness
            )

        if eff == "custom":
            return self.renderer.render_custom_key(
                idx, custom_snap, self.color_a, self.brightness
            )

        return self.renderer.render_off()

    def _compute_underglow_color(
        self,
        now: float,
        rows_snap: Dict[int, Tuple[float, float]],
        punches_snap: Dict[int, float],
        ripples_snap: List[Dict[str, float]],
    ) -> RGBColor:
        """
        Determines unscaled base color for all 44 perimeter underglow LEDs.
        Master keyboard brightness affects only switches; underglow is scaled
        independently by self.underglow_brightness.
        """
        if self.underglow_mode == "off" or self.effect_name == "off":
            return RGBColor(0, 0, 0)

        if self.underglow_mode == "static":
            return self.underglow_color

        # 'sync' mode: smoothly inherits active effect without erratic averaging
        eff = self.effect_name
        if eff in ("static", "custom"):
            return self.color_a

        if eff == "wave":
            return self.renderer.render_color_wave(
                7.25, 2.0, now, self.direction, self.speed, self.mode_type,
                self.color_a, self.color_b, 1.0
            )

        if eff == "tornado":
            return self.renderer.render_tornado(
                0.0, 0.0, now, self.tornado_cw, self.speed, self.mode_type,
                self.color_a, self.color_b, 1.0
            )

        if eff == "breathing":
            return self.renderer.render_breathing(
                now, self.speed, self.mode_type,
                self.color_a, self.color_b, 1.0
            )

        if eff == "matrix":
            if self.mode_type == "dual":
                return self.color_b
            return RGBColor(0, 80, 25)

        # Reactive modes ('laser', 'punch', 'ripple'):
        # Perimeter underglow is decoupled from keystroke flares.
        # It displays only ambient base color (or black in single mode).
        if eff in ("punch", "laser", "ripple"):
            return RGBColor(0, 0, 0) if self.mode_type == "single" else self.base_color

        return self.base_color

    def stop(self):
        """Cleans up threads, hooks, and resets lighting on shutdown."""
        self.running = False
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

