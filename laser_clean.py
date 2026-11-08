import time
import threading
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
from pynput import keyboard

# ==============================================================================
# HARDWARE CALIBRATED TUNING (AULA REPLICA)
# ==============================================================================
BASE_COLOR   = RGBColor(15, 0, 40)       # Dark purple base
REACT_COLOR  = RGBColor(0, 255, 255)    # Ice Blue / Cyan laser
LASER_SPEED  = 75.0                     # Keys per second (sweeps row in ~85ms)
PULSE_WIDTH  = 2.2                      # Thickness of the moving laser head
TRAIL_DECAY  = 0.14                     # Crisp, snappy fade (vanishes in 140ms)
FPS          = 32

# Repeated string constants (SonarLint S1192)
KEY_MINUS = "key: -"
KEY_EQUALS = "key: ="
KEY_LBRACKET = "key: ["
KEY_RBRACKET = "key: ]"
KEY_LSHIFT = "key: left shift"
KEY_COMMA = "key: ,"
KEY_DOT = "key: ."
KEY_LCTRL = "key: left control"
KEY_LALT = "key: left alt"
KEY_RALT = "key: right alt"

client = OpenRGBClient()
if hasattr(client, 'sock') and client.sock:
    client.sock.settimeout(0.2)

kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("[ERROR] Everest 60 not found. Verify OpenRGB SDK Server is running.")
    exit(1)

# Ensure Direct mode
for mode in kb.modes:
    if mode.name.lower() == "direct":
        try:
            kb.set_mode(mode)
        except Exception:
            pass
        break

kb.set_color(BASE_COLOR)
name_to_index = {led.name.lower(): idx for idx, led in enumerate(kb.leds)}

# Exact physical (X, Y) coordinates
KEY_COORDS = {
    # Row 0
    name_to_index.get("key: escape", 24): (0.0, 0), name_to_index.get("key: 1", 25): (1.0, 0),
    name_to_index.get("key: 2", 26): (2.0, 0), name_to_index.get("key: 3", 27): (3.0, 0),
    name_to_index.get("key: 4", 28): (4.0, 0), name_to_index.get("key: 5", 29): (5.0, 0),
    name_to_index.get("key: 6", 30): (6.0, 0), name_to_index.get("key: 7", 31): (7.0, 0),
    name_to_index.get("key: 8", 32): (8.0, 0), name_to_index.get("key: 9", 33): (9.0, 0),
    name_to_index.get("key: 0", 34): (10.0, 0), name_to_index.get(KEY_MINUS, 35): (11.0, 0),
    name_to_index.get(KEY_EQUALS, 36): (12.0, 0), name_to_index.get("key: backspace", 37): (13.75, 0),

    # Row 1
    name_to_index.get("key: tab", 46): (0.25, 1), name_to_index.get("key: q", 47): (1.5, 1),
    name_to_index.get("key: w", 48): (2.5, 1), name_to_index.get("key: e", 49): (3.5, 1),
    name_to_index.get("key: r", 50): (4.5, 1), name_to_index.get("key: t", 51): (5.5, 1),
    name_to_index.get("key: y", 52): (6.5, 1), name_to_index.get("key: u", 53): (7.5, 1),
    name_to_index.get("key: i", 54): (8.5, 1), name_to_index.get("key: o", 55): (9.5, 1),
    name_to_index.get("key: p", 56): (10.5, 1), name_to_index.get(KEY_LBRACKET, 57): (11.5, 1),
    name_to_index.get(KEY_RBRACKET, 58): (12.5, 1), name_to_index.get("key: \\ (ansi)", 59): (13.75, 1),

    # Row 2
    name_to_index.get("key: caps lock", 68): (0.35, 2), name_to_index.get("key: a", 69): (1.75, 2),
    name_to_index.get("key: s", 70): (2.75, 2), name_to_index.get("key: d", 71): (3.75, 2),
    name_to_index.get("key: f", 72): (4.75, 2), name_to_index.get("key: g", 73): (5.75, 2),
    name_to_index.get("key: h", 74): (6.75, 2), name_to_index.get("key: j", 75): (7.75, 2),
    name_to_index.get("key: k", 76): (8.75, 2), name_to_index.get("key: l", 77): (9.75, 2),
    name_to_index.get("key: ;", 78): (10.75, 2), name_to_index.get("key: '", 79): (11.75, 2),
    name_to_index.get("key: enter", 80): (13.5, 2),

    # Row 3
    name_to_index.get(KEY_LSHIFT, 88): (0.6, 3), name_to_index.get("key: z", 89): (2.1, 3),
    name_to_index.get("key: x", 90): (3.1, 3), name_to_index.get("key: c", 91): (4.1, 3),
    name_to_index.get("key: v", 92): (5.1, 3), name_to_index.get("key: b", 93): (6.1, 3),
    name_to_index.get("key: n", 94): (7.1, 3), name_to_index.get("key: m", 95): (8.1, 3),
    name_to_index.get(KEY_COMMA, 96): (9.1, 3), name_to_index.get(KEY_DOT, 97): (10.1, 3),
    name_to_index.get("key: /", 99): (11.1, 3), name_to_index.get("key: right shift", 98): (12.2, 3),
    name_to_index.get("key: up arrow", 101): (13.3, 3), name_to_index.get("key: delete", 100): (14.3, 3),

    # Row 4
    name_to_index.get(KEY_LCTRL, 109): (0.5, 4), name_to_index.get("key: left windows", 110): (1.7, 4),
    name_to_index.get(KEY_LALT, 111): (2.9, 4), name_to_index.get("key: space", 112): (6.7, 4),
    name_to_index.get(KEY_RALT, 113): (10.5, 4), name_to_index.get("key: right fn", 114): (11.5, 4),
    name_to_index.get("key: left arrow", 115): (12.5, 4), name_to_index.get("key: down arrow", 116): (13.5, 4),
    name_to_index.get("key: right arrow", 117): (14.5, 4),
}
KEY_COORDS = {k: v for k, v in KEY_COORDS.items() if k is not None}

# Lookup maps for Windows Virtual Keys, Characters, and Modifiers
quote_idx = (
    name_to_index.get("key: '")
    or name_to_index.get("key: \'", 79)
    or name_to_index.get("key: quote")
    or 79
)
slash_idx = name_to_index.get("key: /", 99) or 99
semicolon_idx = name_to_index.get("key: ;", 78) or 78
backslash_idx = name_to_index.get("key: \\ (ansi)", 59) or 59

VK_MAP = {
    186: semicolon_idx,                # OEM_1 (;:)
    187: name_to_index.get(KEY_EQUALS, 36),       # OEM_PLUS (=+)
    188: name_to_index.get(KEY_COMMA, 96),       # OEM_COMMA (,<)
    189: name_to_index.get(KEY_MINUS, 35),       # OEM_MINUS (-_)
    190: name_to_index.get(KEY_DOT, 97),         # OEM_PERIOD (.>)
    191: slash_idx,                    # OEM_2 (/?)
    192: name_to_index.get("key: `", 24),          # OEM_3 (`~)
    219: name_to_index.get(KEY_LBRACKET, 57),       # OEM_4 ([{)
    220: backslash_idx,                # OEM_5 (\|)
    221: name_to_index.get(KEY_RBRACKET, 58),       # OEM_6 (]}
    222: quote_idx,                    # OEM_7 ('")
}

CHAR_MAP = {
    ';': semicolon_idx, ':': semicolon_idx,
    "'": quote_idx, '"': quote_idx,
    '/': slash_idx, '?': slash_idx,
    '-': name_to_index.get(KEY_MINUS, 35), '_': name_to_index.get(KEY_MINUS, 35),
    '=': name_to_index.get(KEY_EQUALS, 36), '+': name_to_index.get(KEY_EQUALS, 36),
    '[': name_to_index.get(KEY_LBRACKET, 57), '{': name_to_index.get(KEY_LBRACKET, 57),
    ']': name_to_index.get(KEY_RBRACKET, 58), '}': name_to_index.get(KEY_RBRACKET, 58),
    '\\': backslash_idx, '|': backslash_idx,
    ',': name_to_index.get(KEY_COMMA, 96), '<': name_to_index.get(KEY_COMMA, 96),
    '.': name_to_index.get(KEY_DOT, 97), '>': name_to_index.get(KEY_DOT, 97),
    '`': 24, '~': 24,
    '!': name_to_index.get("key: 1", 25), '@': name_to_index.get("key: 2", 26),
    '#': name_to_index.get("key: 3", 27), '$': name_to_index.get("key: 4", 28),
    '%': name_to_index.get("key: 5", 29), '^': name_to_index.get("key: 6", 30),
    '&': name_to_index.get("key: 7", 31), '*': name_to_index.get("key: 8", 32),
    '(': name_to_index.get("key: 9", 33), ')': name_to_index.get("key: 0", 34),
}

SPECIAL_MAP = {
    keyboard.Key.space: name_to_index.get("key: space", 112),
    keyboard.Key.enter: name_to_index.get("key: enter", 80),
    keyboard.Key.backspace: name_to_index.get("key: backspace", 37),
    keyboard.Key.tab: name_to_index.get("key: tab", 46),
    keyboard.Key.caps_lock: name_to_index.get("key: caps lock", 68),
    keyboard.Key.shift: name_to_index.get(KEY_LSHIFT, 88),
    keyboard.Key.shift_l: name_to_index.get(KEY_LSHIFT, 88),
    keyboard.Key.shift_r: name_to_index.get("key: right shift", 98),
    keyboard.Key.ctrl: name_to_index.get(KEY_LCTRL, 109),
    keyboard.Key.ctrl_l: name_to_index.get(KEY_LCTRL, 109),
    keyboard.Key.ctrl_r: name_to_index.get(KEY_LCTRL, 109),
    keyboard.Key.alt: name_to_index.get(KEY_LALT, 111),
    keyboard.Key.alt_l: name_to_index.get(KEY_LALT, 111),
    keyboard.Key.alt_r: name_to_index.get(KEY_RALT, 113),
    keyboard.Key.alt_gr: name_to_index.get(KEY_RALT, 113),
    keyboard.Key.delete: name_to_index.get("key: delete", 100),
    keyboard.Key.up: name_to_index.get("key: up arrow", 101),
    keyboard.Key.down: name_to_index.get("key: down arrow", 116),
    keyboard.Key.left: name_to_index.get("key: left arrow", 115),
    keyboard.Key.right: name_to_index.get("key: right arrow", 117),
    keyboard.Key.esc: name_to_index.get("key: escape", 24),
}

active_rows = {}
lock = threading.Lock()
running = True

def resolve_key(key):
    try:
        if hasattr(key, 'vk') and key.vk in VK_MAP:
            return VK_MAP[key.vk]
        if key in SPECIAL_MAP:
            return SPECIAL_MAP[key]
        if hasattr(key, 'char') and key.char:
            c = key.char
            if c in CHAR_MAP:
                return CHAR_MAP[c]
            return name_to_index.get(f"key: {c.lower()}")
        return None
    except Exception:
        return None

def on_press(key):
    try:
        idx = resolve_key(key)
        if idx is not None and idx in KEY_COORDS:
            x, y = KEY_COORDS[idx]
            row = int(y)
            with lock:
                # Re-trigger instantly on row overwrite
                active_rows[row] = (x, time.time())
    except Exception:
        pass

def compute_laser_intensity(kx: float, ky: float, current_rows: dict, now: float) -> float:
    """Calculates laser intensity for a single key coordinate."""
    row = int(ky)
    if row not in current_rows:
        return 0.0

    ox, t0 = current_rows[row]
    dt = now - t0
    dist = abs(kx - ox)

    wave_head = LASER_SPEED * dt
    delta = wave_head - dist

    tail_len = LASER_SPEED * TRAIL_DECAY
    if 0.0 <= delta < tail_len:
        decay_progress = delta / tail_len
        return (1.0 - decay_progress) ** 1.8
    if -PULSE_WIDTH <= delta < 0.0:
        return 1.0 + (delta / PULSE_WIDTH)

    return 0.0


def _render_active_frame(current_rows: dict, now: float):
    """Updates key colors and displays frame to hardware."""
    for idx, (kx, ky) in KEY_COORDS.items():
        intensity = compute_laser_intensity(kx, ky, current_rows, now)
        if intensity > 0.0:
            intensity = min(1.0, max(0.0, intensity))
            r = int(BASE_COLOR.red + (REACT_COLOR.red - BASE_COLOR.red) * intensity)
            g = int(BASE_COLOR.green + (REACT_COLOR.green - BASE_COLOR.green) * intensity)
            b = int(BASE_COLOR.blue + (REACT_COLOR.blue - BASE_COLOR.blue) * intensity)
            kb.colors[idx] = RGBColor(r, g, b)
        else:
            kb.colors[idx] = BASE_COLOR

    try:
        kb.show(fast=True)
    except Exception:
        pass


def _render_flush_base():
    """Restores all keys to the base idle color."""
    for idx in KEY_COORDS:
        kb.colors[idx] = BASE_COLOR
    try:
        kb.show(fast=True)
    except Exception:
        pass


def render_loop():
    global running
    frame_interval = 1.0 / FPS
    # Complete event lifetime: travel time to row edge (~0.18s) + tight trail decay (~0.14s)
    max_row_life = (14.0 / LASER_SPEED) + TRAIL_DECAY
    was_active = False

    while running:
        t_start = time.time()
        now = t_start

        with lock:
            expired = [r for r, (_, t0) in active_rows.items() if (now - t0) >= max_row_life]
            for r in expired:
                del active_rows[r]
            current_rows = dict(active_rows)

        if current_rows:
            was_active = True
            _render_active_frame(current_rows, now)
        elif was_active:
            _render_flush_base()
            was_active = False

        elapsed = time.time() - t_start
        time.sleep(max(0.001, frame_interval - elapsed))

render_thread = threading.Thread(target=render_loop, daemon=True)
render_thread.start()

print("==================================================")
print(f" Aula Laser Clean: Speed={LASER_SPEED} | Decay={TRAIL_DECAY}s | {FPS} FPS")
print(" Press Ctrl+C to exit.")
print("==================================================")

try:
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()
except KeyboardInterrupt:
    pass
finally:
    running = False
    time.sleep(0.05)
    kb.set_color(BASE_COLOR)

