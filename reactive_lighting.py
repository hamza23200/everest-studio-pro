import time
import math
import threading
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
from pynput import keyboard

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# Available modes: 'laser', 'ripple', 'crosshair', 'reactive'
EFFECT_MODE = 'laser'

BASE_COLOR  = RGBColor(15, 0, 40)       # Dark purple idle base
REACT_COLOR = RGBColor(0, 255, 255)     # Ice blue / Cyan effect color

# Physics Tuning Parameters (Hardware-Calibrated Aula Replica)
LASER_SPEED       = 75.0   # Keys per second (sweeps row in ~85ms)
PULSE_WIDTH       = 2.2    # Thickness of the moving laser head
TRAIL_DECAY       = 0.14   # Crisp, snappy fade (vanishes in 140ms)
RIPPLE_SPEED      = 16.0   # Keys per second expansion rate
RIPPLE_WIDTH      = 1.5    # Thickness of expanding wave ring
RIPPLE_DURATION   = 0.70   # Total lifetime of each ripple wave
REACTIVE_DURATION = 0.25   # Seconds for single-key fade
FPS               = 45     # Frame rate (22ms frame pacing)

# Repeated string constants (SonarLint S1192)
KEY_LEFT_SHIFT = "key: left shift"
KEY_LEFT_CTRL = "key: left control"
KEY_LEFT_WIN = "key: left windows"
KEY_LEFT_ALT = "key: left alt"

# ==============================================================================
# OPENRGB INITIALIZATION
# ==============================================================================
try:
    client = OpenRGBClient()
except Exception as e:
    print(f"Error connecting to OpenRGB SDK Server: {e}")
    print("Verify OpenRGB is running and 'Start Server' is enabled.")
    exit(1)

kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("Everest 60 not found. Verify OpenRGB SDK Server is active.")
    exit(1)

# Ensure device is in 'Direct' mode so hardware accepts external SDK frames
for mode in kb.modes:
    if mode.name.lower() == "direct":
        try:
            kb.set_mode(mode)
        except Exception:
            pass
        break

# Initialize all 147 LEDs (keys + side diffusers) to base purple
kb.set_color(BASE_COLOR)
name_to_index = {led.name.lower(): idx for idx, led in enumerate(kb.leds)}

# ==============================================================================
# EVEREST 60 2D PHYSICAL COORDINATE GRID (X, Y in key units)
# ==============================================================================
# Row 0: Esc, 1..=, Backspace
KEY_COORDS = {
    name_to_index.get("key: escape", 24):    (0.0,  0.0),
    name_to_index.get("key: 1", 25):         (1.0,  0.0),
    name_to_index.get("key: 2", 26):         (2.0,  0.0),
    name_to_index.get("key: 3", 27):         (3.0,  0.0),
    name_to_index.get("key: 4", 28):         (4.0,  0.0),
    name_to_index.get("key: 5", 29):         (5.0,  0.0),
    name_to_index.get("key: 6", 30):         (6.0,  0.0),
    name_to_index.get("key: 7", 31):         (7.0,  0.0),
    name_to_index.get("key: 8", 32):         (8.0,  0.0),
    name_to_index.get("key: 9", 33):         (9.0,  0.0),
    name_to_index.get("key: 0", 34):         (10.0, 0.0),
    name_to_index.get("key: -", 35):         (11.0, 0.0),
    name_to_index.get("key: =", 36):         (12.0, 0.0),
    name_to_index.get("key: backspace", 37): (13.75, 0.0),

    # Row 1: Tab, Q..], \
    name_to_index.get("key: tab", 46):       (0.25, 1.0),
    name_to_index.get("key: q", 47):         (1.5,  1.0),
    name_to_index.get("key: w", 48):         (2.5,  1.0),
    name_to_index.get("key: e", 49):         (3.5,  1.0),
    name_to_index.get("key: r", 50):         (4.5,  1.0),
    name_to_index.get("key: t", 51):         (5.5,  1.0),
    name_to_index.get("key: y", 52):         (6.5,  1.0),
    name_to_index.get("key: u", 53):         (7.5,  1.0),
    name_to_index.get("key: i", 54):         (8.5,  1.0),
    name_to_index.get("key: o", 55):         (9.5,  1.0),
    name_to_index.get("key: p", 56):         (10.5, 1.0),
    name_to_index.get("key: [", 57):         (11.5, 1.0),
    name_to_index.get("key: ]", 58):         (12.5, 1.0),
    name_to_index.get("key: \\ (ansi)", 59): (13.75, 1.0),

    # Row 2: Caps, A..', Enter
    name_to_index.get("key: caps lock", 68): (0.35, 2.0),
    name_to_index.get("key: a", 69):         (1.75, 2.0),
    name_to_index.get("key: s", 70):         (2.75, 2.0),
    name_to_index.get("key: d", 71):         (3.75, 2.0),
    name_to_index.get("key: f", 72):         (4.75, 2.0),
    name_to_index.get("key: g", 73):         (5.75, 2.0),
    name_to_index.get("key: h", 74):         (6.75, 2.0),
    name_to_index.get("key: j", 75):         (7.75, 2.0),
    name_to_index.get("key: k", 76):         (8.75, 2.0),
    name_to_index.get("key: l", 77):         (9.75, 2.0),
    name_to_index.get("key: ;", 78):         (10.75, 2.0),
    name_to_index.get("key: '", 79):         (11.75, 2.0),
    name_to_index.get("key: enter", 80):     (13.5, 2.0),

    # Row 3: LShift, Z..M, ,, ., /, RShift, Up, Del
    name_to_index.get(KEY_LEFT_SHIFT, 88):   (0.6,  3.0),
    name_to_index.get("key: z", 89):         (2.1,  3.0),
    name_to_index.get("key: x", 90):         (3.1,  3.0),
    name_to_index.get("key: c", 91):         (4.1,  3.0),
    name_to_index.get("key: v", 92):         (5.1,  3.0),
    name_to_index.get("key: b", 93):         (6.1,  3.0),
    name_to_index.get("key: n", 94):         (7.1,  3.0),
    name_to_index.get("key: m", 95):         (8.1,  3.0),
    name_to_index.get("key: ,", 96):         (9.1,  3.0),
    name_to_index.get("key: .", 97):         (10.1, 3.0),
    name_to_index.get("key: /", 99):         (11.1, 3.0),
    name_to_index.get("key: right shift", 98):(12.2, 3.0),
    name_to_index.get("key: up arrow", 101): (13.3, 3.0),
    name_to_index.get("key: delete", 100):   (14.3, 3.0),

    # Row 4: LCtrl, LWin, LAlt, Space, RAlt, RFn, Left, Down, Right
    name_to_index.get(KEY_LEFT_CTRL, 109):   (0.5, 4.0),
    name_to_index.get(KEY_LEFT_WIN, 110):    (1.7, 4.0),
    name_to_index.get(KEY_LEFT_ALT, 111):    (2.9, 4.0),
    name_to_index.get("key: space", 112):        (6.7, 4.0),
    name_to_index.get("key: right alt", 113):    (10.5, 4.0),
    name_to_index.get("key: right fn", 114):     (11.5, 4.0),
    name_to_index.get("key: left arrow", 115):   (12.5, 4.0),
    name_to_index.get("key: down arrow", 116):   (13.5, 4.0),
    name_to_index.get("key: right arrow", 117):  (14.5, 4.0),
}
# Remove any unresolved None keys
KEY_COORDS = {k: v for k, v in KEY_COORDS.items() if k is not None}

# ==============================================================================
# KEY RESOLUTION
# ==============================================================================
SLASH_INDEX = name_to_index.get("key: /", 99)
RIGHT_ALT_INDEX = name_to_index.get("key: right alt", 113)
ESC_INDEX = name_to_index.get("key: escape", 24)
BACKSLASH_INDEX = name_to_index.get("key: \\ (ansi)", 59)

SHIFT_MAP = {
    '?': SLASH_INDEX, '/': SLASH_INDEX, '!': name_to_index.get("key: 1", 25),
    '@': name_to_index.get("key: 2", 26), '#': name_to_index.get("key: 3", 27),
    '$': name_to_index.get("key: 4", 28), '%': name_to_index.get("key: 5", 29),
    '^': name_to_index.get("key: 6", 30), '&': name_to_index.get("key: 7", 31),
    '*': name_to_index.get("key: 8", 32), '(': name_to_index.get("key: 9", 33),
    ')': name_to_index.get("key: 0", 34), '_': name_to_index.get("key: -", 35),
    '+': name_to_index.get("key: =", 36), '{': name_to_index.get("key: [", 57),
    '}': name_to_index.get("key: ]", 58), '|': BACKSLASH_INDEX,
    '\\': BACKSLASH_INDEX,
    ':': name_to_index.get("key: ;", 78), '"': name_to_index.get("key: '", 79),
    '<': name_to_index.get("key: ,", 96), '>': name_to_index.get("key: .", 97),
    '~': name_to_index.get("key: `", ESC_INDEX), '`': name_to_index.get("key: `", ESC_INDEX),
}

SPECIAL_KEYS = {
    keyboard.Key.space: name_to_index.get("key: space", 112),
    keyboard.Key.enter: name_to_index.get("key: enter", 80),
    keyboard.Key.backspace: name_to_index.get("key: backspace", 37),
    keyboard.Key.tab: name_to_index.get("key: tab", 46),
    keyboard.Key.caps_lock: name_to_index.get("key: caps lock", 68),
    keyboard.Key.shift: name_to_index.get(KEY_LEFT_SHIFT, 88),
    keyboard.Key.shift_l: name_to_index.get(KEY_LEFT_SHIFT, 88),
    keyboard.Key.shift_r: name_to_index.get("key: right shift", 98),
    keyboard.Key.ctrl: name_to_index.get(KEY_LEFT_CTRL, 109),
    keyboard.Key.ctrl_l: name_to_index.get(KEY_LEFT_CTRL, 109),
    keyboard.Key.ctrl_r: name_to_index.get(KEY_LEFT_CTRL, 109),
    keyboard.Key.alt: name_to_index.get(KEY_LEFT_ALT, 111),
    keyboard.Key.alt_l: name_to_index.get(KEY_LEFT_ALT, 111),
    keyboard.Key.alt_r: RIGHT_ALT_INDEX,
    keyboard.Key.alt_gr: RIGHT_ALT_INDEX,
    keyboard.Key.cmd: name_to_index.get(KEY_LEFT_WIN, 110),
    keyboard.Key.cmd_l: name_to_index.get(KEY_LEFT_WIN, 110),
    keyboard.Key.cmd_r: name_to_index.get(KEY_LEFT_WIN, 110),
    keyboard.Key.delete: name_to_index.get("key: delete", 100),
    keyboard.Key.up: name_to_index.get("key: up arrow", 101),
    keyboard.Key.down: name_to_index.get("key: down arrow", 116),
    keyboard.Key.left: name_to_index.get("key: left arrow", 115),
    keyboard.Key.right: name_to_index.get("key: right arrow", 117),
    keyboard.Key.esc: ESC_INDEX,
}

def resolve_key(key):
    try:
        if hasattr(key, 'vk') and key.vk == 191:
            return SLASH_INDEX
        if key in SPECIAL_KEYS:
            return SPECIAL_KEYS[key]
        if hasattr(key, 'char') and key.char:
            if key.char in SHIFT_MAP:
                return SHIFT_MAP[key.char]
            if ord(key.char) < 32:
                return None
            return name_to_index.get(f"key: {key.char.lower()}")
        return None
    except Exception:
        return None

# ==============================================================================
# 5-CHANNEL NON-STACKING ANIMATION ENGINE
# ==============================================================================
active_laser_rows = {}    # {row_idx (0..4): (origin_x, strike_timestamp)}
active_reactive_keys = {} # {key_idx: strike_timestamp}
active_ripples = []       # Capped at 4 latest
lock = threading.Lock()
running = True

def on_press(key):
    try:
        idx = resolve_key(key)
        if idx is not None and idx in KEY_COORDS:
            kx, ky = KEY_COORDS[idx]
            row_idx = int(round(ky))
            now = time.time()
            with lock:
                # Overwrite channel in-place: restarts wave immediately at t=0
                active_laser_rows[row_idx] = (kx, now)
                active_reactive_keys[idx] = now
                active_ripples.append({'idx': idx, 'x': kx, 'y': ky, 't0': now})
                if len(active_ripples) > 4:
                    active_ripples.pop(0)
    except Exception:
        pass

def _intensity_laser(row_idx: int, key_x: float, now: float) -> float:
    """Traveling pulse with defined front crest and trailing exponential decay."""
    if row_idx not in active_laser_rows:
        return 0.0
    origin_x, t0 = active_laser_rows[row_idx]
    dt = now - t0
    dist = abs(key_x - origin_x)
    wave_head = LASER_SPEED * dt
    delta = wave_head - dist
    tail_len = LASER_SPEED * TRAIL_DECAY

    if 0.0 <= delta < tail_len:
        decay_progress = delta / tail_len
        return (1.0 - decay_progress) ** 1.8
    if -PULSE_WIDTH <= delta < 0.0:
        return 1.0 + (delta / PULSE_WIDTH)
    return 0.0

def _compute_vertical_beam(origin_x: float, t0: float, key_x: float, key_y: float, r: int, now: float) -> float:
    """Calculates vertical beam intensity component for crosshair effect."""
    dt = now - t0
    max_life = (15.0 / LASER_SPEED) + TRAIL_DECAY
    if dt >= max_life or abs(key_x - origin_x) >= 0.8:
        return 0.0

    dist_y = abs(key_y - r)
    t_arrive_y = dist_y / (LASER_SPEED * 0.6)
    if dt < t_arrive_y:
        return 0.0

    tau_y = dt - t_arrive_y
    if tau_y < TRAIL_DECAY:
        fade_y = 1.0 - (tau_y / TRAIL_DECAY)
        return fade_y * fade_y
    return 0.0


def _intensity_crosshair(row_idx: int, key_x: float, key_y: float, now: float) -> float:
    val = _intensity_laser(row_idx, key_x, now)
    for r, (origin_x, t0) in active_laser_rows.items():
        pulse = _compute_vertical_beam(origin_x, t0, key_x, key_y, r, now)
        if pulse > val:
            val = pulse
    return val

def _intensity_reactive(key_idx: int, now: float) -> float:
    if key_idx not in active_reactive_keys:
        return 0.0
    dt = now - active_reactive_keys[key_idx]
    if dt < REACTIVE_DURATION:
        return 1.0 - (dt / REACTIVE_DURATION)
    return 0.0

def _intensity_ripple(key_x: float, key_y: float, now: float) -> float:
    max_val = 0.0
    for ev in active_ripples:
        dt = now - ev['t0']
        if dt < RIPPLE_DURATION:
            dist = math.hypot(key_x - ev['x'], key_y - ev['y'])
            curr_r = RIPPLE_SPEED * dt
            delta = abs(dist - curr_r)
            if delta < RIPPLE_WIDTH:
                val = (1.0 - (delta / RIPPLE_WIDTH)) * (1.0 - (dt / RIPPLE_DURATION))
                if val > max_val:
                    max_val = val
    return max_val

def compute_intensity(mode, idx, key_x, key_y, now):
    row_idx = int(round(key_y))
    if mode == 'laser':
        return _intensity_laser(row_idx, key_x, now)
    if mode == 'crosshair':
        return _intensity_crosshair(row_idx, key_x, key_y, now)
    if mode == 'reactive':
        return _intensity_reactive(idx, now)
    if mode == 'ripple':
        return _intensity_ripple(key_x, key_y, now)
    return 0.0

def _prune_expired(now: float):
    max_row_life = (14.0 / LASER_SPEED) + TRAIL_DECAY
    expired_rows = [r for r, (_, t0) in active_laser_rows.items() if (now - t0) >= max_row_life]
    for r in expired_rows:
        active_laser_rows.pop(r, None)

    expired_keys = [k for k, t0 in active_reactive_keys.items() if (now - t0) >= REACTIVE_DURATION]
    for k in expired_keys:
        active_reactive_keys.pop(k, None)

    active_ripples[:] = [e for e in active_ripples if (now - e['t0']) < RIPPLE_DURATION]

def _has_active(mode: str) -> bool:
    if mode in ('laser', 'crosshair'):
        return len(active_laser_rows) > 0
    if mode == 'reactive':
        return len(active_reactive_keys) > 0
    if mode == 'ripple':
        return len(active_ripples) > 0
    return False

def _render_active(now: float):
    for idx, (kx, ky) in KEY_COORDS.items():
        intensity = compute_intensity(EFFECT_MODE, idx, kx, ky, now)
        if intensity > 0.0:
            r = int(BASE_COLOR.red + (REACT_COLOR.red - BASE_COLOR.red) * intensity)
            g = int(BASE_COLOR.green + (REACT_COLOR.green - BASE_COLOR.green) * intensity)
            b = int(BASE_COLOR.blue + (REACT_COLOR.blue - BASE_COLOR.blue) * intensity)
            kb.colors[idx] = RGBColor(r, g, b)
        else:
            kb.colors[idx] = BASE_COLOR

    try:
        kb.show()
    except Exception:
        pass

def _render_flush_base():
    for idx in KEY_COORDS:
        kb.colors[idx] = BASE_COLOR
    try:
        kb.show()
    except Exception:
        pass

def render_loop():
    global running
    frame_interval = 1.0 / FPS
    was_active = False

    while running:
        start_frame = time.perf_counter()
        now = time.time()

        with lock:
            _prune_expired(now)
            active = _has_active(EFFECT_MODE)

        if active:
            was_active = True
            _render_active(now)
        elif was_active:
            was_active = False
            _render_flush_base()

        elapsed = time.perf_counter() - start_frame
        sleep_time = frame_interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
render_thread = threading.Thread(target=render_loop, daemon=True)
render_thread.start()

print("==================================================")
print(f" Mountain Everest 60 Engine: [{EFFECT_MODE.upper()} MODE]")
print(f" Base: RGB({BASE_COLOR.red}, {BASE_COLOR.green}, {BASE_COLOR.blue}) | Strike: RGB({REACT_COLOR.red}, {REACT_COLOR.green}, {REACT_COLOR.blue})")
print(f" Laser Speed: {LASER_SPEED} keys/s | Trail Decay: {TRAIL_DECAY}s")
print(" Press Ctrl+C in terminal to stop.")
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
    print("Base lighting restored cleanly.")
