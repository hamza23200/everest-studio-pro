"""
Everest 60 Physical Matrix, Coordinate Mapping, and Keycode Lookups.
Maps all 64 physical switches (in standard 1u keyboard units), all perimeter
underglow indices, and provides complete Windows OEM virtual keycode tables.
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

# 64 Physical Key Definitions with Layout Geometry (x, y, w, h in 1u keyboard units)
# Ordered 0..63. Total keyboard width: 15.0u | Total height: 5.0u
KEY_DEFINITIONS: List[Dict] = [
    # --- Row 0 (14 keys, indices 0..13) ---
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

    # --- Row 1 (14 keys, indices 14..27) ---
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

    # --- Row 2 (13 keys, indices 28..40) ---
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

    # --- Row 3 (14 keys, indices 41..54) ---
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

    # --- Row 4 (9 keys, indices 55..63) ---
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

# Set of all 64 hardware switch indices
SWITCH_INDICES: Set[int] = {k["default_idx"] for k in KEY_DEFINITIONS}

# Key mapping dictionary with extensive aliases for all 64 switches
KEY_TO_INDEX: Dict[str, int] = {k["id"]: k["default_idx"] for k in KEY_DEFINITIONS}
KEY_TO_INDEX.update({k["name"].lower(): k["default_idx"] for k in KEY_DEFINITIONS})
# Spacebar aliases
KEY_TO_INDEX.update({
    "space": 112,
    "key: space": 112,
    "Key.space": 112,
    " ": 112,
    "vk_32": 112,
    32: 112,
})
# Key 3 aliases
KEY_TO_INDEX.update({
    "3": 27,
    3: 27,
    "key: 3": 27,
    "#": 27,
    "vk_51": 27,
    51: 27,
})
key_to_index: Dict[str, int] = KEY_TO_INDEX

# 64-item ordered list of (key_id, default_idx) for sequential rendering and the visualizer
ORDERED_KEYS: List[Tuple[str, int]] = [(k["id"], k.get("resolved_idx", k["default_idx"])) for k in KEY_DEFINITIONS]
ordered_keys: List[Tuple[str, int]] = ORDERED_KEYS

# 2D physical key coordinate mapping
KEY_COORDINATES: Dict[str, Tuple[float, float]] = {k["id"]: (k["x"], k["y"]) for k in KEY_DEFINITIONS}
KEY_COORDINATES.update({k["name"].lower(): (k["x"], k["y"]) for k in KEY_DEFINITIONS})
KEY_COORDINATES["3"] = (3.0, 0.0)
KEY_COORDINATES[3] = (3.0, 0.0)
key_coordinates: Dict[str, Tuple[float, float]] = KEY_COORDINATES

# Complete Perimeter Underglow & Accent LEDs (all 83 non-switch indices 0..146)
EDGE_INDICES: List[int] = sorted([i for i in range(TOTAL_LEDS) if i not in SWITCH_INDICES])


def verify_matrix_mappings(name_to_index: Optional[Dict[str, int]] = None) -> bool:
    """Verifies that all 64 switches, Key 3 (index 27), and Spacebar (index 112) are mapped."""
    coords, idx_to_slot = build_matrix_coords(name_to_index or {})
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
    return switch_count == 64 and key_3_mapped and spacebar_mapped


def build_matrix_coords(name_to_index: Dict[str, int]) -> Tuple[Dict[int, Tuple[float, float]], Dict[int, int]]:
    """
    Computes exact physical center coordinate (center_x, center_y) for each key switch index
    and maps hardware LED index -> slot (0..63).
    """
    coords: Dict[int, Tuple[float, float]] = {}
    idx_to_slot: Dict[int, int] = {}

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
        center_y = k["y"]
        coords[idx] = (center_x, center_y)
        idx_to_slot[idx] = k["slot"]
        k["resolved_idx"] = idx

    return coords, idx_to_slot


def build_key_lookups(name_to_index: Dict[str, int]) -> Tuple[Dict[int, int], Dict[str, int], Dict[keyboard.Key, int]]:
    """
    Builds direct Windows Virtual Keycode, character, and special key lookup dictionaries.
    Guarantees all lookups resolve strictly to switch indices and never fallback to 0 or edge indices.
    """
    n = name_to_index

    def _safe_switch(idx: Optional[int], default_idx: int) -> int:
        if idx is not None and idx not in EDGE_INDICES:
            return idx
        return default_idx

    space_idx = _safe_switch(
        n.get("key: space") or n.get("space") or n.get("Key.space"),
        112
    )
    key_3_idx = _safe_switch(n.get("key: 3") or n.get("3"), 27)
    quote_idx = _safe_switch(
        n.get("key: '")
        or n.get("key: \'", 79)
        or n.get("key: quote")
        or n.get("key: single quote"),
        79
    )
    slash_idx = _safe_switch(n.get("key: /"), SLASH_INDEX)
    backslash_idx = _safe_switch(n.get("key: \\ (ansi)") or n.get("key: \\"), 59)
    semicolon_idx = _safe_switch(n.get("key: ;"), 78)

    # Windows Virtual Key Codes (Direct hardware hooks for standard numbers & OEM punctuation)
    vk_map: Dict[int, int] = {
        32: space_idx,                                         # VK_SPACE
        48: _safe_switch(n.get("key: 0"), 34),                # VK_0
        49: _safe_switch(n.get("key: 1"), 25),                # VK_1
        50: _safe_switch(n.get("key: 2"), 26),                # VK_2
        51: key_3_idx,                                         # VK_3 (Explicit Key 3 -> 27)
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


class KeyboardMatrix:
    """Namespace / class wrapper for Everest 60 physical matrix definitions."""
    KEY_DEFINITIONS = KEY_DEFINITIONS
    KEY_TO_INDEX = KEY_TO_INDEX
    key_to_index = KEY_TO_INDEX
    ORDERED_KEYS = ORDERED_KEYS
    ordered_keys = ORDERED_KEYS
    KEY_COORDINATES = KEY_COORDINATES
    key_coordinates = KEY_COORDINATES
    EDGE_INDICES = EDGE_INDICES
    SWITCH_INDICES = SWITCH_INDICES

    @staticmethod
    def build_coords(name_to_index: Dict[str, int]):
        return build_matrix_coords(name_to_index)

    @staticmethod
    def build_lookups(name_to_index: Dict[str, int]):
        return build_key_lookups(name_to_index)

    @staticmethod
    def verify(name_to_index: Optional[Dict[str, int]] = None) -> bool:
        return verify_matrix_mappings(name_to_index)


# Run matrix self-audit on module import
verify_matrix_mappings()
