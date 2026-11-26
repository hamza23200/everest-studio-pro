"""
Everest 60 Physical Matrix, Modular Numpad Mapping, and Keycode Lookups.
Maps all 64 standard physical switches, 17 modular numpad switches (Left/Right/Detached),
all 44 standard + 22 numpad perimeter diffusers (147 total LEDs), and provides Windows OEM
virtual keycode tables.
"""

from typing import Dict, Tuple, List, Set, Optional
from pynput import keyboard

# Target Hardware Information
DEVICE_NAME_FILTER = "everest"
TARGET_VID = 0x3282
TARGET_PID = 0x0005
TOTAL_LEDS = 147

# Critical Upstream Hardware Index Overrides
SLASH_INDEX = 99        # Key: / (? switch), VK 191
RIGHT_SHIFT_INDEX = 98  # Key: Right Shift (1.0u)
DELETE_INDEX = 100      # Key: Delete (1.0u)
UP_ARROW_INDEX = 101    # Key: Up Arrow (1.0u)
RIGHT_ALT_INDEX = 113   # Key: Right Alt (1.0u)
RIGHT_FN_INDEX = 114    # Key: Right Fn (1.0u)

# Whitelisted Windows Virtual Key Codes for Numpad Keys (Instant O(1) resolution)
NUMPAD_VKS: Set[int] = {
    96,   # VK_NUMPAD0
    97,   # VK_NUMPAD1
    98,   # VK_NUMPAD2
    99,   # VK_NUMPAD3
    100,  # VK_NUMPAD4
    101,  # VK_NUMPAD5
    102,  # VK_NUMPAD6
    103,  # VK_NUMPAD7
    104,  # VK_NUMPAD8
    105,  # VK_NUMPAD9
    106,  # VK_MULTIPLY (*)
    107,  # VK_ADD (+)
    109,  # VK_SUBTRACT (-)
    110,  # VK_DECIMAL (.)
    111,  # VK_DIVIDE (/)
    144,  # VK_NUMLOCK
}

# 64 Physical Key Definitions for the 60% Core Board
# Ordered 0..63. Total keyboard width: 15.0u | Total height: 5.0u
KEY_DEFINITIONS: List[Dict] = [
    # --- Row 0 (14 keys, slots 0..13) ---
    {"slot": 0, "id": "esc", "name": "key: escape", "label": "ESC", "sublabel": "`", "x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 24},
    {"slot": 1, "id": "1", "name": "key: 1", "label": "1", "sublabel": "!", "x": 1.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 25},
    {"slot": 2, "id": "2", "name": "key: 2", "label": "2", "sublabel": "@", "x": 2.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 26},
    {"slot": 3, "id": "3", "name": "key: 3", "label": "3", "sublabel": "#", "x": 3.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 27},
    {"slot": 4, "id": "4", "name": "key: 4", "label": "4", "sublabel": "$", "x": 4.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 28},
    {"slot": 5, "id": "5", "name": "key: 5", "label": "5", "sublabel": "%", "x": 5.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 29},
    {"slot": 6, "id": "6", "name": "key: 6", "label": "6", "sublabel": "^", "x": 6.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 30},
    {"slot": 7, "id": "7", "name": "key: 7", "label": "7", "sublabel": "&", "x": 7.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 31},
    {"slot": 8, "id": "8", "name": "key: 8", "label": "8", "sublabel": "*", "x": 8.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 32},
    {"slot": 9, "id": "9", "name": "key: 9", "label": "9", "sublabel": "(", "x": 9.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 33},
    {"slot": 10, "id": "0", "name": "key: 0", "label": "0", "sublabel": ")", "x": 10.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 34},
    {"slot": 11, "id": "-", "name": "key: -", "label": "-", "sublabel": "_", "x": 11.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 35},
    {"slot": 12, "id": "=", "name": "key: =", "label": "=", "sublabel": "+", "x": 12.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 36},
    {"slot": 13, "id": "backspace", "name": "key: backspace", "label": "BACK", "sublabel": "", "x": 13.0, "y": 0.0, "w": 2.0, "h": 1.0, "default_idx": 37},

    # --- Row 1 (14 keys, slots 14..27) ---
    {"slot": 14, "id": "tab", "name": "key: tab", "label": "TAB", "sublabel": "", "x": 0.0, "y": 1.0, "w": 1.5, "h": 1.0, "default_idx": 46},
    {"slot": 15, "id": "q", "name": "key: q", "label": "Q", "sublabel": "", "x": 1.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 47},
    {"slot": 16, "id": "w", "name": "key: w", "label": "W", "sublabel": "", "x": 2.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 48},
    {"slot": 17, "id": "e", "name": "key: e", "label": "E", "sublabel": "", "x": 3.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 49},
    {"slot": 18, "id": "r", "name": "key: r", "label": "R", "sublabel": "", "x": 4.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 50},
    {"slot": 19, "id": "t", "name": "key: t", "label": "T", "sublabel": "", "x": 5.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 51},
    {"slot": 20, "id": "y", "name": "key: y", "label": "Y", "sublabel": "", "x": 6.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 52},
    {"slot": 21, "id": "u", "name": "key: u", "label": "U", "sublabel": "", "x": 7.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 53},
    {"slot": 22, "id": "i", "name": "key: i", "label": "I", "sublabel": "", "x": 8.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 54},
    {"slot": 23, "id": "o", "name": "key: o", "label": "O", "sublabel": "", "x": 9.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 55},
    {"slot": 24, "id": "p", "name": "key: p", "label": "P", "sublabel": "", "x": 10.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 56},
    {"slot": 25, "id": "[", "name": "key: [", "label": "[", "sublabel": "{", "x": 11.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 57},
    {"slot": 26, "id": "]", "name": "key: ]", "label": "]", "sublabel": "}", "x": 12.5, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 58},
    {"slot": 27, "id": "backslash", "name": "key: \\ (ansi)", "label": "\\", "sublabel": "|", "x": 13.5, "y": 1.0, "w": 1.5, "h": 1.0, "default_idx": 59},

    # --- Row 2 (13 keys, slots 28..40) ---
    {"slot": 28, "id": "caps", "name": "key: caps lock", "label": "CAPS", "sublabel": "", "x": 0.0, "y": 2.0, "w": 1.75, "h": 1.0, "default_idx": 68},
    {"slot": 29, "id": "a", "name": "key: a", "label": "A", "sublabel": "", "x": 1.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 69},
    {"slot": 30, "id": "s", "name": "key: s", "label": "S", "sublabel": "", "x": 2.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 70},
    {"slot": 31, "id": "d", "name": "key: d", "label": "D", "sublabel": "", "x": 3.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 71},
    {"slot": 32, "id": "f", "name": "key: f", "label": "F", "sublabel": "", "x": 4.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 72},
    {"slot": 33, "id": "g", "name": "key: g", "label": "G", "sublabel": "", "x": 5.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 73},
    {"slot": 34, "id": "h", "name": "key: h", "label": "H", "sublabel": "", "x": 6.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 74},
    {"slot": 35, "id": "j", "name": "key: j", "label": "J", "sublabel": "", "x": 7.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 75},
    {"slot": 36, "id": "k", "name": "key: k", "label": "K", "sublabel": "", "x": 8.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 76},
    {"slot": 37, "id": "l", "name": "key: l", "label": "L", "sublabel": "", "x": 9.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 77},
    {"slot": 38, "id": ";", "name": "key: ;", "label": ";", "sublabel": ":", "x": 10.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 78},
    {"slot": 39, "id": "'", "name": "key: '", "label": "'", "sublabel": "\"", "x": 11.75, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 79},
    {"slot": 40, "id": "enter", "name": "key: enter", "label": "ENTER", "sublabel": "", "x": 12.75, "y": 2.0, "w": 2.25, "h": 1.0, "default_idx": 80},

    # --- Row 3 (14 keys, slots 41..54) ---
    {"slot": 41, "id": "lshift", "name": "key: left shift", "label": "SHIFT", "sublabel": "", "x": 0.0, "y": 3.0, "w": 2.0, "h": 1.0, "default_idx": 88},
    {"slot": 42, "id": "z", "name": "key: z", "label": "Z", "sublabel": "", "x": 2.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 89},
    {"slot": 43, "id": "x", "name": "key: x", "label": "X", "sublabel": "", "x": 3.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 90},
    {"slot": 44, "id": "c", "name": "key: c", "label": "C", "sublabel": "", "x": 4.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 91},
    {"slot": 45, "id": "v", "name": "key: v", "label": "V", "sublabel": "", "x": 5.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 93},
    {"slot": 46, "id": "b", "name": "key: b", "label": "B", "sublabel": "", "x": 6.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 92},
    {"slot": 47, "id": "n", "name": "key: n", "label": "N", "sublabel": "", "x": 7.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 94},
    {"slot": 48, "id": "m", "name": "key: m", "label": "M", "sublabel": "", "x": 8.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 95},
    {"slot": 49, "id": ",", "name": "key: ,", "label": ",", "sublabel": "<", "x": 9.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 96},
    {"slot": 50, "id": ".", "name": "key: .", "label": ".", "sublabel": ">", "x": 10.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 97},
    {"slot": 51, "id": "/", "name": "key: /", "label": "/", "sublabel": "?", "x": 11.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": SLASH_INDEX},
    {"slot": 52, "id": "rshift", "name": "key: right shift", "label": "SHIFT", "sublabel": "", "x": 12.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": RIGHT_SHIFT_INDEX},
    {"slot": 53, "id": "up", "name": "key: up arrow", "label": "▲", "sublabel": "", "x": 13.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": UP_ARROW_INDEX},
    {"slot": 54, "id": "del", "name": "key: delete", "label": "DEL", "sublabel": "", "x": 14.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": DELETE_INDEX},

    # --- Row 4 (9 keys, slots 55..63) ---
    {"slot": 55, "id": "lctrl", "name": "key: left control", "label": "CTRL", "sublabel": "", "x": 0.0, "y": 4.0, "w": 1.25, "h": 1.0, "default_idx": 109},
    {"slot": 56, "id": "lwin", "name": "key: left windows", "label": "WIN", "sublabel": "", "x": 1.25, "y": 4.0, "w": 1.25, "h": 1.0, "default_idx": 110},
    {"slot": 57, "id": "lalt", "name": "key: left alt", "label": "ALT", "sublabel": "", "x": 2.5, "y": 4.0, "w": 1.25, "h": 1.0, "default_idx": 111},
    {"slot": 58, "id": "space", "name": "key: space", "label": "", "sublabel": "", "x": 3.75, "y": 4.0, "w": 6.25, "h": 1.0, "default_idx": 112},
    {"slot": 59, "id": "ralt", "name": "key: right alt", "label": "ALT", "sublabel": "", "x": 10.0, "y": 4.0, "w": 1.0, "h": 1.0, "default_idx": RIGHT_ALT_INDEX},
    {"slot": 60, "id": "rfn", "name": "key: right fn", "label": "FN", "sublabel": "", "x": 11.0, "y": 4.0, "w": 1.0, "h": 1.0, "default_idx": RIGHT_FN_INDEX},
    {"slot": 61, "id": "left", "name": "key: left arrow", "label": "◀", "sublabel": "", "x": 12.0, "y": 4.0, "w": 1.0, "h": 1.0, "default_idx": 115},
    {"slot": 62, "id": "down", "name": "key: down arrow", "label": "▼", "sublabel": "", "x": 13.0, "y": 4.0, "w": 1.0, "h": 1.0, "default_idx": 116},
    {"slot": 63, "id": "right", "name": "key: right arrow", "label": "▶", "sublabel": "", "x": 14.0, "y": 4.0, "w": 1.0, "h": 1.0, "default_idx": 117},
]

# 17 Modular Numpad Key Definitions (relative coordinates: rel_x from 0.0 to 3.0)
NUMPAD_KEY_DEFINITIONS: List[Dict] = [
    # Row 0
    {"slot": 64, "id": "num_lock", "name": "key: num lock", "label": "NUM", "sublabel": "", "rel_x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 39, "vk": 144},
    {"slot": 65, "id": "num_div", "name": "key: number pad /", "label": "/", "sublabel": "", "rel_x": 1.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 40, "vk": 111},
    {"slot": 66, "id": "num_mul", "name": "key: number pad *", "label": "*", "sublabel": "", "rel_x": 2.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 41, "vk": 106},
    {"slot": 67, "id": "num_sub", "name": "key: number pad -", "label": "-", "sublabel": "", "rel_x": 3.0, "y": 0.0, "w": 1.0, "h": 1.0, "default_idx": 42, "vk": 109},

    # Row 1
    {"slot": 68, "id": "num_7", "name": "key: number pad 7", "label": "7", "sublabel": "HOME", "rel_x": 0.0, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 61, "vk": 103},
    {"slot": 69, "id": "num_8", "name": "key: number pad 8", "label": "8", "sublabel": "▲", "rel_x": 1.0, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 62, "vk": 104},
    {"slot": 70, "id": "num_9", "name": "key: number pad 9", "label": "9", "sublabel": "PGUP", "rel_x": 2.0, "y": 1.0, "w": 1.0, "h": 1.0, "default_idx": 63, "vk": 105},
    {"slot": 71, "id": "num_add", "name": "key: number pad +", "label": "+", "sublabel": "", "rel_x": 3.0, "y": 1.0, "w": 1.0, "h": 2.0, "default_idx": 64, "vk": 107},

    # Row 2
    {"slot": 72, "id": "num_4", "name": "key: number pad 4", "label": "4", "sublabel": "◀", "rel_x": 0.0, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 82, "vk": 100},
    {"slot": 73, "id": "num_5", "name": "key: number pad 5", "label": "5", "sublabel": "", "rel_x": 1.0, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 83, "vk": 101},
    {"slot": 74, "id": "num_6", "name": "key: number pad 6", "label": "6", "sublabel": "▶", "rel_x": 2.0, "y": 2.0, "w": 1.0, "h": 1.0, "default_idx": 84, "vk": 102},

    # Row 3
    {"slot": 75, "id": "num_1", "name": "key: number pad 1", "label": "1", "sublabel": "END", "rel_x": 0.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 103, "vk": 97},
    {"slot": 76, "id": "num_2", "name": "key: number pad 2", "label": "2", "sublabel": "▼", "rel_x": 1.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 104, "vk": 98},
    {"slot": 77, "id": "num_3", "name": "key: number pad 3", "label": "3", "sublabel": "PGDN", "rel_x": 2.0, "y": 3.0, "w": 1.0, "h": 1.0, "default_idx": 105, "vk": 99},
    {"slot": 78, "id": "num_enter", "name": "key: number pad enter", "label": "ENTER", "sublabel": "", "rel_x": 3.0, "y": 3.0, "w": 1.0, "h": 2.0, "default_idx": 121, "vk": 13},

    # Row 4
    {"slot": 79, "id": "num_0", "name": "key: number pad 0", "label": "0", "sublabel": "INS", "rel_x": 0.0, "y": 4.0, "w": 2.0, "h": 1.0, "default_idx": 119, "vk": 96},
    {"slot": 80, "id": "num_dot", "name": "key: number pad .", "label": ".", "sublabel": "DEL", "rel_x": 2.0, "y": 4.0, "w": 1.0, "h": 1.0, "default_idx": 120, "vk": 110},
]

ALL_KEY_DEFINITIONS: List[Dict] = KEY_DEFINITIONS + NUMPAD_KEY_DEFINITIONS

# Disjoint Index Sets
MAIN_SWITCH_INDICES: Set[int] = {k["default_idx"] for k in KEY_DEFINITIONS}
NUMPAD_SWITCH_INDICES: Set[int] = {k["default_idx"] for k in NUMPAD_KEY_DEFINITIONS}
ALL_SWITCH_INDICES: Set[int] = MAIN_SWITCH_INDICES | NUMPAD_SWITCH_INDICES

# 44 Main Chassis Perimeter Edge LEDs
MAIN_EDGE_INDICES: List[int] = [
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 23, 38, 45, 60, 67,
    81, 87, 102, 108, 118, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134,
    135, 136, 137, 138, 139, 140
]

# 22 Modular Numpad Perimeter Edge LEDs
NUMPAD_EDGE_INDICES: List[int] = [
    17, 18, 19, 20, 21, 22, 43, 44, 65, 66, 85, 86, 106, 107, 122, 123, 141, 142,
    143, 144, 145, 146
]

ALL_EDGE_INDICES: List[int] = sorted(MAIN_EDGE_INDICES + NUMPAD_EDGE_INDICES)

# Backward-compatible aliases
SWITCH_INDICES: Set[int] = MAIN_SWITCH_INDICES
EDGE_INDICES: List[int] = MAIN_EDGE_INDICES

# Key mapping dictionary with extensive aliases for all switches (Core 64 + Numpad 17)
KEY_TO_INDEX: Dict[str, int] = {k["id"]: k["default_idx"] for k in ALL_KEY_DEFINITIONS}
KEY_TO_INDEX.update({k["name"].lower(): k["default_idx"] for k in ALL_KEY_DEFINITIONS})

# Special aliases
KEY_TO_INDEX.update({
    "space": 112,
    "key: space": 112,
    "Key.space": 112,
    " ": 112,
    "vk_32": 112,
    32: 112,
    "3": 27,
    3: 27,
    "key: 3": 27,
    "#": 27,
    "vk_51": 27,
    51: 27,
})

# Numpad aliases
for nk in NUMPAD_KEY_DEFINITIONS:
    KEY_TO_INDEX[nk["id"]] = nk["default_idx"]
    KEY_TO_INDEX[nk["name"]] = nk["default_idx"]
    KEY_TO_INDEX[f"vk_{nk['vk']}"] = nk["default_idx"]
    KEY_TO_INDEX[nk["vk"]] = nk["default_idx"]

key_to_index: Dict[str, int] = KEY_TO_INDEX

# Ordered lists for rendering
# Legacy 64-key main board list (kept for backward compatibility)
ordered_keys: List[Tuple[str, int]] = [
    (k["id"], k.get("resolved_idx", k["default_idx"])) for k in KEY_DEFINITIONS
]

# All 81 switches in canonical order: 64 main board keys followed by 17 numpad keys.
# Each entry is (key_name, openrgb_led_index); position == visualizer slot.
ORDERED_KEYS: List[Tuple[str, int]] = [
    (k["id"], k.get("resolved_idx", k["default_idx"])) for k in ALL_KEY_DEFINITIONS
]
ALL_ORDERED_KEYS: List[Tuple[str, int]] = ORDERED_KEYS

# Reverse mapping {led_idx: key_name} for all 81 switches
INDEX_TO_KEY: Dict[int, str] = {idx: name for name, idx in ORDERED_KEYS}
index_to_key: Dict[int, str] = INDEX_TO_KEY

# Coordinates dictionary (Default: docked right)
KEY_COORDINATES: Dict[str, Tuple[float, float]] = {k["id"]: (k["x"], k["y"]) for k in KEY_DEFINITIONS}
KEY_COORDINATES.update({k["name"].lower(): (k["x"], k["y"]) for k in KEY_DEFINITIONS})
KEY_COORDINATES["3"] = (3.0, 0.0)
KEY_COORDINATES[3] = (3.0, 0.0)

for nk in NUMPAD_KEY_DEFINITIONS:
    KEY_COORDINATES[nk["id"]] = (15.5 + nk["rel_x"], nk["y"])
    KEY_COORDINATES[nk["name"]] = (15.5 + nk["rel_x"], nk["y"])

key_coordinates: Dict[str, Tuple[float, float]] = KEY_COORDINATES


def build_key_coordinates(dock_position: str = "right") -> Dict[str, Tuple[float, float]]:
    """Returns {key_name: (x, y)} for all 81 switches (key centers) for the given dock position.

    The numpad is omitted when 'detached'.
    """
    coords: Dict[str, Tuple[float, float]] = {}
    for k in KEY_DEFINITIONS:
        coords[k["id"]] = (k["x"] + k["w"] / 2.0, k["y"] + k["h"] / 2.0)
    if dock_position != "detached":
        base_x = 15.5 if dock_position == "right" else -4.5
        for nk in NUMPAD_KEY_DEFINITIONS:
            coords[nk["id"]] = (
                base_x + nk["rel_x"] + nk["w"] / 2.0,
                nk["y"] + nk["h"] / 2.0,
            )
    return coords


def build_matrix_coords(
    name_to_index: Dict[str, int],
    dock_position: str = "right"
) -> Tuple[Dict[int, Tuple[float, float]], Dict[int, int]]:
    """
    Computes exact physical center coordinate (center_x, center_y) for each key switch index
    and maps hardware LED index -> slot (0..63 for 60%, 64..80 for numpad).
    Respects dock_position: 'right', 'left', or 'detached'.
    """
    coords: Dict[int, Tuple[float, float]] = {}
    idx_to_slot: Dict[int, int] = {}

    # 1. Main 64 switches
    for k in KEY_DEFINITIONS:
        openrgb_name = k["name"].lower()
        if k["id"] == "3" or openrgb_name == "key: 3":
            idx = 27
        elif k["id"] == "space" or openrgb_name == "key: space":
            idx = 112
        elif openrgb_name == "key: '":
            idx = (
                name_to_index.get("key: '")
                or name_to_index.get("key: \'", 79)
                or name_to_index.get("key: quote")
                or 79
            )
        elif openrgb_name == "key: \\ (ansi)":
            idx = name_to_index.get("key: \\ (ansi)", 59) or name_to_index.get("key: \\", 59) or 59
        else:
            idx = name_to_index.get(openrgb_name, k["default_idx"])

        center_x = k["x"] + (k["w"] / 2.0)
        center_y = k["y"] + (k["h"] / 2.0)
        coords[idx] = (center_x, center_y)
        idx_to_slot[idx] = k["slot"]
        k["resolved_idx"] = idx

    # 2. Numpad 17 switches (only if not detached)
    if dock_position != "detached":
        base_x = 15.5 if dock_position == "right" else -4.5
        for nk in NUMPAD_KEY_DEFINITIONS:
            openrgb_name = nk["name"].lower()
            idx = name_to_index.get(openrgb_name, nk["default_idx"])
            center_x = base_x + nk["rel_x"] + (nk["w"] / 2.0)
            center_y = nk["y"] + (nk["h"] / 2.0)
            coords[idx] = (center_x, center_y)
            idx_to_slot[idx] = nk["slot"]
            nk["resolved_idx"] = idx

    return coords, idx_to_slot


def build_edge_coords(
    name_to_index: Dict[str, int],
    dock_position: str = "right"
) -> Dict[int, Tuple[float, float]]:
    """
    Computes physical (x, y) coordinates for all perimeter edge diffusers
    to enable mathematically seamless wave propagation into the underglow.
    """
    edge_coords: Dict[int, Tuple[float, float]] = {}

    # Main Board: 44 Edge Diffusers around 15.0u x 5.0u rectangle
    # Top edge (0..16): X 0.0 to 15.0, Y = -0.5
    top_indices = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    for i, idx in enumerate(top_indices):
        edge_coords[idx] = (i * (15.0 / max(1, len(top_indices) - 1)), -0.5)

    # Right edge (17..21, 38, 60, 81, 102, 118)
    right_indices = [38, 60, 81, 102, 118]
    for i, idx in enumerate(right_indices):
        edge_coords[idx] = (15.4, i * (5.0 / max(1, len(right_indices) - 1)))

    # Bottom edge (22..37, 124..140)
    bot_indices = [124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140]
    for i, idx in enumerate(bot_indices):
        edge_coords[idx] = (15.0 - i * (15.0 / max(1, len(bot_indices) - 1)), 5.5)

    # Left edge (0, 23, 45, 67, 87, 108)
    left_indices = [0, 23, 45, 67, 87, 108]
    for i, idx in enumerate(left_indices):
        edge_coords[idx] = (-0.5, 5.0 - i * (5.0 / max(1, len(left_indices) - 1)))

    # Numpad Diffusers (22 LEDs)
    if dock_position != "detached":
        base_x = 15.5 if dock_position == "right" else -4.5
        # Top (18..22)
        top_np = [18, 19, 20, 21, 22]
        for i, idx in enumerate(top_np):
            edge_coords[idx] = (base_x + i * 0.8, -0.5)

        # Right (44, 66, 86, 107, 123)
        right_np = [44, 66, 86, 107, 123]
        for i, idx in enumerate(right_np):
            edge_coords[idx] = (base_x + 4.4, i * 1.0)

        # Bottom (141..146)
        bot_np = [141, 142, 143, 144, 145, 146]
        for i, idx in enumerate(bot_np):
            edge_coords[idx] = (base_x + 4.0 - i * 0.67, 5.5)

        # Left (17, 43, 65, 85, 106, 122)
        left_np = [17, 43, 65, 85, 106, 122]
        for i, idx in enumerate(left_np):
            edge_coords[idx] = (base_x - 0.4, 5.0 - i * 0.83)

    return edge_coords


def build_key_lookups(
    name_to_index: Dict[str, int]
) -> Tuple[Dict[int, int], Dict[str, int], Dict[keyboard.Key, int]]:
    """
    Builds direct Windows Virtual Keycode, character, and special key lookup dictionaries.
    Includes all 17 numpad virtual keycodes for sub-microsecond non-blocking keystroke dispatch.
    """
    n = name_to_index

    def _safe_switch(idx: Optional[int], default_idx: int) -> int:
        if idx is not None and idx in ALL_SWITCH_INDICES:
            return idx
        return default_idx

    space_idx = _safe_switch(n.get("key: space") or n.get("space") or n.get("Key.space"), 112)
    key_3_idx = _safe_switch(n.get("key: 3") or n.get("3"), 27)
    quote_idx = _safe_switch(
        n.get("key: '") or n.get("key: \'", 79) or n.get("key: quote") or n.get("key: single quote"),
        79
    )
    slash_idx = _safe_switch(n.get("key: /"), SLASH_INDEX)
    backslash_idx = _safe_switch(n.get("key: \\ (ansi)") or n.get("key: \\"), 59)
    semicolon_idx = _safe_switch(n.get("key: ;"), 78)

    # Windows Virtual Key Codes
    vk_map: Dict[int, int] = {
        # Core 60% keys
        32: space_idx,                                         # VK_SPACE
        48: _safe_switch(n.get("key: 0"), 34),                # VK_0
        49: _safe_switch(n.get("key: 1"), 25),                # VK_1
        50: _safe_switch(n.get("key: 2"), 26),                # VK_2
        51: key_3_idx,                                         # VK_3
        52: _safe_switch(n.get("key: 4"), 28),                # VK_4
        53: _safe_switch(n.get("key: 5"), 29),                # VK_5
        54: _safe_switch(n.get("key: 6"), 30),                # VK_6
        55: _safe_switch(n.get("key: 7"), 31),                # VK_7
        56: _safe_switch(n.get("key: 8"), 32),                # VK_8
        57: _safe_switch(n.get("key: 9"), 33),                # VK_9
        186: semicolon_idx,                                    # OEM_1 (;:)
        187: _safe_switch(n.get("key: ="), 36),               # OEM_PLUS (=+)
        188: _safe_switch(n.get("key: ,"), 96),               # OEM_COMMA (,<)
        189: _safe_switch(n.get("key: -"), 35),               # OEM_MINUS (-_)
        190: _safe_switch(n.get("key: ."), 97),               # OEM_PERIOD (.>)
        191: slash_idx,                                        # OEM_2 (/?)
        192: _safe_switch(n.get("key: `"), 24),               # OEM_3 (`~)
        219: _safe_switch(n.get("key: ["), 57),               # OEM_4 ([{)
        220: backslash_idx,                                    # OEM_5 (\|)
        221: _safe_switch(n.get("key: ]"), 58),               # OEM_6 (]}
        222: quote_idx,                                        # OEM_7 ('")

        # Numpad VKs (Direct fast-path)
        144: _safe_switch(n.get("key: num lock"), 39),        # VK_NUMLOCK
        111: _safe_switch(n.get("key: number pad /"), 40),    # VK_DIVIDE
        106: _safe_switch(n.get("key: number pad *"), 41),    # VK_MULTIPLY
        109: _safe_switch(n.get("key: number pad -"), 42),    # VK_SUBTRACT
        103: _safe_switch(n.get("key: number pad 7"), 61),    # VK_NUMPAD7
        104: _safe_switch(n.get("key: number pad 8"), 62),    # VK_NUMPAD8
        105: _safe_switch(n.get("key: number pad 9"), 63),    # VK_NUMPAD9
        107: _safe_switch(n.get("key: number pad +"), 64),    # VK_ADD
        100: _safe_switch(n.get("key: number pad 4"), 82),    # VK_NUMPAD4
        101: _safe_switch(n.get("key: number pad 5"), 83),    # VK_NUMPAD5
        102: _safe_switch(n.get("key: number pad 6"), 84),    # VK_NUMPAD6
        97:  _safe_switch(n.get("key: number pad 1"), 103),   # VK_NUMPAD1
        98:  _safe_switch(n.get("key: number pad 2"), 104),   # VK_NUMPAD2
        99:  _safe_switch(n.get("key: number pad 3"), 105),   # VK_NUMPAD3
        96:  _safe_switch(n.get("key: number pad 0"), 119),   # VK_NUMPAD0
        110: _safe_switch(n.get("key: number pad ."), 120),   # VK_DECIMAL
    }

    # Shifted & Standard Character Normalization Map
    char_map: Dict[str, int] = {
        ' ': space_idx,
        '0': _safe_switch(n.get("key: 0"), 34),
        '1': _safe_switch(n.get("key: 1"), 25),
        '2': _safe_switch(n.get("key: 2"), 26),
        '3': key_3_idx,
        '4': _safe_switch(n.get("key: 4"), 28),
        '5': _safe_switch(n.get("key: 5"), 29),
        '6': _safe_switch(n.get("key: 6"), 30),
        '7': _safe_switch(n.get("key: 7"), 31),
        '8': _safe_switch(n.get("key: 8"), 32),
        '9': _safe_switch(n.get("key: 9"), 33),
        ';': semicolon_idx, ':': semicolon_idx,
        "'": quote_idx, '"': quote_idx,
        '/': slash_idx, '?': slash_idx,
        '-': _safe_switch(n.get("key: -"), 35), '_': _safe_switch(n.get("key: -"), 35),
        '=': _safe_switch(n.get("key: ="), 36), '+': _safe_switch(n.get("key: ="), 36),
        '[': _safe_switch(n.get("key: ["), 57), '{': _safe_switch(n.get("key: ["), 57),
        ']': _safe_switch(n.get("key: ]"), 58), '}': _safe_switch(n.get("key: ]"), 58),
        '\\': backslash_idx, '|': backslash_idx,
        ',': _safe_switch(n.get("key: ,"), 96), '<': _safe_switch(n.get("key: ,"), 96),
        '.': _safe_switch(n.get("key: ."), 97), '>': _safe_switch(n.get("key: ."), 97),
        '`': 24, '~': 24,
        '!': _safe_switch(n.get("key: 1"), 25), '@': _safe_switch(n.get("key: 2"), 26),
        '#': key_3_idx,                         '$': _safe_switch(n.get("key: 4"), 28),
        '%': _safe_switch(n.get("key: 5"), 29), '^': _safe_switch(n.get("key: 6"), 30),
        '&': _safe_switch(n.get("key: 7"), 31), '*': _safe_switch(n.get("key: 8"), 32),
        '(': _safe_switch(n.get("key: 9"), 33), ')': _safe_switch(n.get("key: 0"), 34),
    }

    # Special Modifiers & Navigation Keys
    special_map: Dict[keyboard.Key, int] = {
        keyboard.Key.space: space_idx,
        keyboard.Key.enter: _safe_switch(n.get("key: enter"), 80),
        keyboard.Key.backspace: _safe_switch(n.get("key: backspace"), 37),
        keyboard.Key.tab: _safe_switch(n.get("key: tab"), 46),
        keyboard.Key.caps_lock: _safe_switch(n.get("key: caps lock"), 68),
        keyboard.Key.shift: _safe_switch(n.get("key: left shift"), 88),
        keyboard.Key.shift_l: _safe_switch(n.get("key: left shift"), 88),
        keyboard.Key.shift_r: _safe_switch(n.get("key: right shift"), RIGHT_SHIFT_INDEX),
        keyboard.Key.ctrl: _safe_switch(n.get("key: left control"), 109),
        keyboard.Key.ctrl_l: _safe_switch(n.get("key: left control"), 109),
        keyboard.Key.ctrl_r: _safe_switch(n.get("key: left control"), 109),
        keyboard.Key.alt: _safe_switch(n.get("key: left alt"), 111),
        keyboard.Key.alt_l: _safe_switch(n.get("key: left alt"), 111),
        keyboard.Key.alt_r: _safe_switch(n.get("key: right alt"), RIGHT_ALT_INDEX),
        keyboard.Key.alt_gr: _safe_switch(n.get("key: right alt"), RIGHT_ALT_INDEX),
        keyboard.Key.delete: _safe_switch(n.get("key: delete"), DELETE_INDEX),
        keyboard.Key.up: _safe_switch(n.get("key: up arrow"), UP_ARROW_INDEX),
        keyboard.Key.down: _safe_switch(n.get("key: down arrow"), 116),
        keyboard.Key.left: _safe_switch(n.get("key: left arrow"), 115),
        keyboard.Key.right: _safe_switch(n.get("key: right arrow"), 117),
        keyboard.Key.esc: _safe_switch(n.get("key: escape"), 24),
    }

    return vk_map, char_map, special_map


def verify_matrix_mappings(name_to_index: Optional[Dict[str, int]] = None) -> bool:
    """Verifies that all 64 switches, Key 3 (index 27), Spacebar (index 112), and numpad keys are mapped."""
    coords, idx_to_slot = build_matrix_coords(name_to_index or {}, dock_position="right")
    switch_count = len(coords)
    key_3_mapped = (27 in coords) and (27 in idx_to_slot)
    spacebar_mapped = (112 in coords) and (112 in idx_to_slot)
    status_3 = "mapped" if key_3_mapped else "UNMAPPED"
    status_space = "mapped" if spacebar_mapped else "UNMAPPED"

    # Strict audit assertions for matrix collections
    assert key_to_index.get("3") == 27, "key_to_index['3'] != 27!"
    assert key_to_index.get(3) == 27, "key_to_index[3] != 27!"
    assert key_to_index.get("#") == 27, "key_to_index['#'] != 27!"
    assert ordered_keys[3] == ("3", 27), f"ordered_keys[3] is {ordered_keys[3]}, expected ('3', 27)!"
    assert ordered_keys[2] == ("2", 26), f"ordered_keys[2] is {ordered_keys[2]}, expected ('2', 26)!"
    assert ordered_keys[4] == ("4", 28), f"ordered_keys[4] is {ordered_keys[4]}, expected ('4', 28)!"
    assert KEY_COORDINATES.get("3") == (3.0, 0.0), f"KEY_COORDINATES['3'] is {KEY_COORDINATES.get('3')}!"

    print(f"[MATRIX] Verified {switch_count} key switches. Index 27 (Key 3): {status_3}. Spacebar: {status_space}.")
    return (switch_count == 81) and key_3_mapped and spacebar_mapped


class KeyboardMatrix:
    """Namespace / class wrapper for Everest 60 physical matrix definitions."""
    KEY_DEFINITIONS = KEY_DEFINITIONS
    NUMPAD_KEY_DEFINITIONS = NUMPAD_KEY_DEFINITIONS
    ALL_KEY_DEFINITIONS = ALL_KEY_DEFINITIONS
    MAIN_SWITCH_INDICES = MAIN_SWITCH_INDICES
    NUMPAD_SWITCH_INDICES = NUMPAD_SWITCH_INDICES
    ALL_SWITCH_INDICES = ALL_SWITCH_INDICES
    MAIN_EDGE_INDICES = MAIN_EDGE_INDICES
    NUMPAD_EDGE_INDICES = NUMPAD_EDGE_INDICES
    ALL_EDGE_INDICES = ALL_EDGE_INDICES
    KEY_TO_INDEX = KEY_TO_INDEX
    key_to_index = KEY_TO_INDEX
    ORDERED_KEYS = ORDERED_KEYS
    ordered_keys = ordered_keys
    INDEX_TO_KEY = INDEX_TO_KEY
    index_to_key = INDEX_TO_KEY
    KEY_COORDINATES = KEY_COORDINATES
    key_coordinates = KEY_COORDINATES
    EDGE_INDICES = MAIN_EDGE_INDICES
    SWITCH_INDICES = MAIN_SWITCH_INDICES
    dock_position = "right"

    @staticmethod
    def build_coords(name_to_index: Dict[str, int], dock_position: str = "right"):
        return build_matrix_coords(name_to_index, dock_position)

    @staticmethod
    def build_edge_coords(name_to_index: Dict[str, int], dock_position: str = "right"):
        return build_edge_coords(name_to_index, dock_position)

    @staticmethod
    def build_lookups(name_to_index: Dict[str, int]):
        return build_key_lookups(name_to_index)

    @staticmethod
    def verify(name_to_index: Optional[Dict[str, int]] = None) -> bool:
        return verify_matrix_mappings(name_to_index)


# Self-test upon module load
verify_matrix_mappings()
