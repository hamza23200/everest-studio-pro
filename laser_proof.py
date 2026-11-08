import time
import threading
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
from pynput import keyboard

# ==============================================================================
# SMOOTH AULA LASER TUNING CONSTANTS
# ==============================================================================
BASE_COLOR   = RGBColor(15, 0, 40)       # Dark purple base
REACT_COLOR  = RGBColor(0, 255, 255)    # Bright Cyan laser
LASER_SPEED  = 40.0                     # Keys per second (fluid sweep across row)
TRAIL_DECAY  = 0.45                     # Extended silky afterglow (was 0.22)
ATTACK_TIME  = 0.04                     # Soft lead-in rise (eliminates strobe snap)
FPS          = 45                       # Smooth 22ms frame pacing

# Connect to OpenRGB
client = OpenRGBClient()
kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("[ERROR] Everest 60 not found. Ensure OpenRGB SDK Server is active!")
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

# Physical (X, Y) Coordinates
KEY_COORDS = {
    # Row 0
    name_to_index.get("key: escape", 24): (0.0, 0), name_to_index.get("key: 1", 25): (1.0, 0),
    name_to_index.get("key: 2", 26): (2.0, 0), name_to_index.get("key: 3", 27): (3.0, 0),
    name_to_index.get("key: 4", 28): (4.0, 0), name_to_index.get("key: 5", 29): (5.0, 0),
    name_to_index.get("key: 6", 30): (6.0, 0), name_to_index.get("key: 7", 31): (7.0, 0),
    name_to_index.get("key: 8", 32): (8.0, 0), name_to_index.get("key: 9", 33): (9.0, 0),
    name_to_index.get("key: 0", 34): (10.0, 0), name_to_index.get("key: -", 35): (11.0, 0),
    name_to_index.get("key: =", 36): (12.0, 0), name_to_index.get("key: backspace", 37): (13.75, 0),

    # Row 1
    name_to_index.get("key: tab", 46): (0.25, 1), name_to_index.get("key: q", 47): (1.5, 1),
    name_to_index.get("key: w", 48): (2.5, 1), name_to_index.get("key: e", 49): (3.5, 1),
    name_to_index.get("key: r", 50): (4.5, 1), name_to_index.get("key: t", 51): (5.5, 1),
    name_to_index.get("key: y", 52): (6.5, 1), name_to_index.get("key: u", 53): (7.5, 1),
    name_to_index.get("key: i", 54): (8.5, 1), name_to_index.get("key: o", 55): (9.5, 1),
    name_to_index.get("key: p", 56): (10.5, 1), name_to_index.get("key: [", 57): (11.5, 1),
    name_to_index.get("key: ]", 58): (12.5, 1), name_to_index.get("key: \\ (ansi)", 59): (13.75, 1),

    # Row 2
    name_to_index.get("key: caps lock", 68): (0.35, 2), name_to_index.get("key: a", 69): (1.75, 2),
    name_to_index.get("key: s", 70): (2.75, 2), name_to_index.get("key: d", 71): (3.75, 2),
    name_to_index.get("key: f", 72): (4.75, 2), name_to_index.get("key: g", 73): (5.75, 2),
    name_to_index.get("key: h", 74): (6.75, 2), name_to_index.get("key: j", 75): (7.75, 2),
    name_to_index.get("key: k", 76): (8.75, 2), name_to_index.get("key: l", 77): (9.75, 2),
    name_to_index.get("key: ;", 78): (10.75, 2), name_to_index.get("key: '", 79): (11.75, 2),
    name_to_index.get("key: enter", 80): (13.5, 2),

    # Row 3
    name_to_index.get("key: left shift", 88): (0.6, 3), name_to_index.get("key: z", 89): (2.1, 3),
    name_to_index.get("key: x", 90): (3.1, 3), name_to_index.get("key: c", 91): (4.1, 3),
    name_to_index.get("key: v", 92): (5.1, 3), name_to_index.get("key: b", 93): (6.1, 3),
    name_to_index.get("key: n", 94): (7.1, 3), name_to_index.get("key: m", 95): (8.1, 3),
    name_to_index.get("key: ,", 96): (9.1, 3), name_to_index.get("key: .", 97): (10.1, 3),
    name_to_index.get("key: /", 99): (11.1, 3), name_to_index.get("key: right shift", 98): (12.2, 3),
    name_to_index.get("key: up arrow", 101): (13.3, 3), name_to_index.get("key: delete", 100): (14.3, 3),

    # Row 4
    name_to_index.get("key: left control", 109): (0.5, 4), name_to_index.get("key: left windows", 110): (1.7, 4),
    name_to_index.get("key: left alt", 111): (2.9, 4), name_to_index.get("key: space", 112): (6.7, 4),
    name_to_index.get("key: right alt", 113): (10.5, 4), name_to_index.get("key: right fn", 114): (11.5, 4),
    name_to_index.get("key: left arrow", 115): (12.5, 4), name_to_index.get("key: down arrow", 116): (13.5, 4),
    name_to_index.get("key: right arrow", 117): (14.5, 4),
}
KEY_COORDS = {k: v for k, v in KEY_COORDS.items() if k is not None}

# Per-Row State Machine: {row_index: (origin_x, strike_timestamp)}
active_rows = {}
lock = threading.Lock()
running = True

def on_press(key):
    try:
        # Resolve key index
        idx = None
        if hasattr(key, 'vk') and key.vk == 191:
            idx = name_to_index.get("key: /", 99)
        elif key in (keyboard.Key.alt_r, keyboard.Key.alt_gr):
            idx = name_to_index.get("key: right alt", 113)
        elif key == keyboard.Key.space:
            idx = name_to_index.get("key: space", 112)
        elif key == keyboard.Key.enter:
            idx = name_to_index.get("key: enter", 80)
        elif key == keyboard.Key.backspace:
            idx = name_to_index.get("key: backspace", 37)
        elif hasattr(key, 'char') and key.char:
            idx = name_to_index.get(f"key: {key.char.lower()}")

        if idx is not None and idx in KEY_COORDS:
            x, y = KEY_COORDS[idx]
            row = int(y)
            with lock:
                # Overwrite immediately in place: zero queue delay
                active_rows[row] = (x, time.time())
            print(f"[HIT] Row {row} | Key index {idx} at X={x:.2f}")
    except Exception as e:
        print(f"[KEY ERROR] {e}")

def compute_laser_intensity(kx: float, ky: float, current_rows: dict, now: float) -> float:
    """Calculates laser effect intensity for key at (kx, ky)."""
    row = int(ky)
    if row not in current_rows:
        return 0.0

    ox, t0 = current_rows[row]
    dt = now - t0
    dist = abs(kx - ox)
    t_arrive = dist / LASER_SPEED

    # Smooth envelope: Soft rise -> Smooth lingering decay
    if dt < (t_arrive - ATTACK_TIME):
        return 0.0

    tau = dt - t_arrive
    if tau < 0.0:
        # Soft rising bloom as the beam reaches the key
        return 1.0 + (tau / ATTACK_TIME)
    if tau < TRAIL_DECAY:
        # Perceptually linear decay (power 1.4 prevents the early cliff)
        fade = 1.0 - (tau / TRAIL_DECAY)
        return fade ** 1.4

    return 0.0


def _render_active_frame(current_rows: dict, now: float) -> bool:
    """Renders active laser frame to buffer and transmits to keyboard."""
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
        kb.show()
        return True
    except Exception as e:
        print(f"[SOCKET ERROR] {e}")
        return False


def render_loop():
    global running
    frame_interval = 1.0 / FPS
    max_row_life = (15.0 / LASER_SPEED) + TRAIL_DECAY
    was_active = False

    while running:
        t_start = time.time()
        now = t_start

        with lock:
            # Purge expired rows
            expired = [r for r, (_, t0) in active_rows.items() if (now - t0) >= max_row_life]
            for r in expired:
                del active_rows[r]
            current_rows = dict(active_rows)

        if current_rows:
            was_active = True
            if not _render_active_frame(current_rows, now):
                break
        elif was_active:
            # Clean flush back to base color on completion
            for idx in KEY_COORDS:
                kb.colors[idx] = BASE_COLOR
            try:
                kb.show()
            except Exception:
                pass
            was_active = False

        elapsed = time.time() - t_start
        time.sleep(max(0.001, frame_interval - elapsed))

render_thread = threading.Thread(target=render_loop, daemon=True)
render_thread.start()

print("==================================================")
print(" Aula-Style Snappy Laser Engine Running.")
print(" Type in terminal. Press Ctrl+C to exit.")
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
    print("Clean exit.")

