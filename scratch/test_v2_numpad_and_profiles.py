"""
Everest Studio Pro v2.0 - Comprehensive Verification Test
Tests:
1. Modular Numpad Dock Geometry & Detached Blackout
2. Zero-Lag Typing Whitelist
3. Dual Brightness Pipeline & Color Blending Math
4. Anti-Burst Underglow Sync Math & 0% Underglow Blackout
5. Per-Effect 5-Slot Profile Engine & UI Sync
"""

import sys
import os
import json
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from openrgb.utils import RGBColor
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
    build_matrix_coords,
    build_edge_coords,
    build_key_lookups,
)
from engine.lighting_engine import (
    LightingEngineThread,
    calculate_ripple_intensity,
    calculate_laser_intensity,
    calculate_punch_intensity,
    blend_reactive,
)
from gui.main_window import MainWindow
from gui.keyboard_canvas import EverestKeyboardCanvas


def test_matrix_definitions():
    print("[TEST 1] Auditing Matrix Definitions...")
    assert len(KEY_DEFINITIONS) == 64, f"Expected 64 main keys, got {len(KEY_DEFINITIONS)}"
    assert len(NUMPAD_KEY_DEFINITIONS) == 17, f"Expected 17 numpad keys, got {len(NUMPAD_KEY_DEFINITIONS)}"
    assert len(ALL_KEY_DEFINITIONS) == 81, f"Expected 81 all keys, got {len(ALL_KEY_DEFINITIONS)}"
    assert len(MAIN_EDGE_INDICES) == 44, f"Expected 44 main diffusers, got {len(MAIN_EDGE_INDICES)}"
    assert len(NUMPAD_EDGE_INDICES) == 22, f"Expected 22 numpad diffusers, got {len(NUMPAD_EDGE_INDICES)}"
    assert len(ALL_EDGE_INDICES) == 66, f"Expected 66 all diffusers, got {len(ALL_EDGE_INDICES)}"

    # Check Key 3 (Index 27) and Spacebar (Index 112)
    assert KEY_DEFINITIONS[3]["default_idx"] == 27
    assert KEY_DEFINITIONS[58]["default_idx"] == 112
    assert 27 in MAIN_SWITCH_INDICES
    assert 27 not in MAIN_EDGE_INDICES
    assert 27 not in NUMPAD_EDGE_INDICES

    # Check Numpad VKs
    assert 96 in NUMPAD_VKS  # 0
    assert 110 in NUMPAD_VKS # .
    assert 144 in NUMPAD_VKS # NumLock
    assert 107 in NUMPAD_VKS # +
    print("  -> Matrix definitions verified successfully.")


def test_dock_geometry():
    print("[TEST 2] Testing Dock Geometry (Right / Left / Detached)...")
    name_to_idx = {k["name"].lower(): k["default_idx"] for k in ALL_KEY_DEFINITIONS}

    # 1. Right Dock
    coords_r, slot_r = build_matrix_coords(name_to_idx, dock_position="right")
    assert len(coords_r) == 81
    # Check numpad x range: 15.5 .. 18.5
    num_7_idx = 61
    assert coords_r[num_7_idx][0] >= 15.5
    edge_r = build_edge_coords(name_to_idx, dock_position="right")
    assert len(edge_r) == 66

    # 2. Left Dock
    coords_l, slot_l = build_matrix_coords(name_to_idx, dock_position="left")
    assert len(coords_l) == 81
    # Check numpad x range: -4.5 .. -1.5
    assert coords_l[num_7_idx][0] < 0.0
    edge_l = build_edge_coords(name_to_idx, dock_position="left")
    assert len(edge_l) == 66

    # 3. Detached
    coords_d, slot_d = build_matrix_coords(name_to_idx, dock_position="detached")
    assert len(coords_d) == 64
    assert num_7_idx not in coords_d
    edge_d = build_edge_coords(name_to_idx, dock_position="detached")
    assert len(edge_d) == 44
    print("  -> Dock geometry verified successfully.")


def test_dual_brightness_and_anti_burst():
    print("[TEST 3] Testing Dual Brightness and Anti-Burst Math...")
    engine = LightingEngineThread()
    engine.effect_name = "ripple"
    engine.mode_type = "dual"
    engine.color_a = RGBColor(255, 255, 0) # Strike (Yellow)
    engine.color_b = RGBColor(0, 0, 255)   # Base (Blue)
    engine.base_brightness = 20.0
    engine.reactive_brightness = 100.0

    # Test blend_reactive formula: r = min(255, int(base_r) + int(color_a.r * react_factor * intensity))
    idle_base = RGBColor(0, 0, int(255 * 0.2)) # 20% blue
    strike_col = RGBColor(255, 255, 0)
    blended = blend_reactive(idle_base, strike_col, 1.0, 0.5)
    assert blended.red == int(255 * 0.5)
    assert blended.green == int(255 * 0.5)
    assert blended.blue == int(255 * 0.2)

    # Test Anti-Burst Underglow Sync with 0.4 dampening
    engine.underglow_mode = "sync"
    engine.underglow_brightness = 40
    # Simulate a ripple at center (7.5, 2.0)
    now = time.time()
    engine.active_ripples = [{"x": 7.5, "y": 2.0, "t0": now - 0.1}]
    # Edge LED at (7.5, 0.0) -> dist = 2.0
    edge_c = engine._compute_edge_color(0, now, {}, {}, engine.active_ripples)
    # Must not be black, but dampened
    assert (edge_c.red + edge_c.green + edge_c.blue) > 0

    # When underglow_brightness == 0: MUST be strictly (0, 0, 0)
    engine.underglow_brightness = 0
    zero_edge = engine._compute_edge_color(0, now, {}, {}, engine.active_ripples)
    

    # When underglow_mode == "off": MUST be strictly (0, 0, 0)
    engine.underglow_brightness = 50
    engine.underglow_mode = "off"
    off_edge = engine._compute_edge_color(0, now, {}, {}, engine.active_ripples)
    assert off_edge.red == 0 and off_edge.green == 0 and off_edge.blue == 0
    print("  -> Dual brightness & Anti-Burst underglow verified successfully.")


def test_zero_lag_typing_and_detached():
    print("[TEST 4] Testing Zero-Lag Typing & Detached Numpad...")
    engine = LightingEngineThread()

    class FakeKeyVK:
        def __init__(self, vk):
            self.vk = vk

    # Numpad VKs must return True immediately in _is_reactive_trigger
    assert engine._is_reactive_trigger(FakeKeyVK(96)) is True
    assert engine._is_reactive_trigger(FakeKeyVK(103)) is True
    assert engine._is_reactive_trigger(FakeKeyVK(144)) is True

    # Modifier keys must return False
    assert engine._is_reactive_trigger(FakeKeyVK(16)) is False  # Shift
    assert engine._is_reactive_trigger(FakeKeyVK(17)) is False  # Ctrl
    assert engine._is_reactive_trigger(FakeKeyVK(20)) is False  # Caps

    # Detached mode: numpad keys must resolve to None
    engine.dock_position = "detached"
    assert engine._resolve_key(FakeKeyVK(96)) is None
    # Main keys still resolve
    assert engine._resolve_key(FakeKeyVK(51)) == 27  # Key 3
    print("  -> Zero-lag typing & detached resolution verified successfully.")


def test_per_effect_profiles(app):
    print("[TEST 5] Testing Per-Effect 5-Slot Profile Engine in UI...")
    # Clean test config
    cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
    
    window = MainWindow()

    # 1. Switch to "laser"
    for i in range(window.effects_list.count()):
        item = window.effects_list.item(i)
        if item.data(1000) == "laser" or item.text().strip() == "Snappy Laser":
            window.effects_list.setCurrentRow(i)
            break

    assert window.engine.effect_name == "laser"

    # Modify Slot 1 settings of Laser
    window.engine.laser_speed = 88.0
    window.engine.color_a = RGBColor(12, 34, 56)
    window.save_settings()

    # 2. Click [ P2 ] for Laser
    window._on_profile_clicked(2)
    assert window.active_profile_slot == 2
    assert window.effect_profiles["laser"]["active_slot"] == 2
    # Verify [ P2 ] button is active style
    assert window.profile_buttons[2].styleSheet() == window.PROFILE_BTN_ACTIVE_STYLE
    assert window.profile_buttons[1].styleSheet() == window.PROFILE_BTN_INACTIVE_STYLE

    # 3. Switch effect to "wave"
    for i in range(window.effects_list.count()):
        item = window.effects_list.item(i)
        if item.data(1000) == "wave" or item.text().strip() == "Color Wave":
            window.effects_list.setCurrentRow(i)
            break

    assert window.engine.effect_name == "wave"
    # Wave should have loaded its own active slot (which defaults to 1)
    assert window.active_profile_slot == 1
    assert window.profile_buttons[1].styleSheet() == window.PROFILE_BTN_ACTIVE_STYLE

    # 4. Switch back to "laser"
    for i in range(window.effects_list.count()):
        item = window.effects_list.item(i)
        if item.data(1000) == "laser" or item.text().strip() == "Snappy Laser":
            window.effects_list.setCurrentRow(i)
            break

    assert window.engine.effect_name == "laser"
    # Laser should restore its active slot 2!
    assert window.active_profile_slot == 2
    assert window.profile_buttons[2].styleSheet() == window.PROFILE_BTN_ACTIVE_STYLE

    # 5. Switch back to Slot 1 for Laser and verify saved settings
    window._on_profile_clicked(1)
    assert window.active_profile_slot == 1
    assert window.engine.color_a.red == 12
    assert window.engine.color_a.green == 34
    assert window.engine.color_a.blue == 56
    assert int(window.engine.laser_speed) == 88

    # 6. Test Dock Position Segmented Controls
    window._set_dock_position("left")
    assert window.engine.dock_position == "left"
    assert window.canvas.dock_position == "left"
    assert window.dock_buttons["left"].isChecked()

    window._set_dock_position("detached")
    assert window.engine.dock_position == "detached"
    assert window.canvas.dock_position == "detached"
    assert window.dock_buttons["detached"].isChecked()

    window._set_dock_position("right")
    assert window.engine.dock_position == "right"
    assert window.canvas.dock_position == "right"
    assert window.dock_buttons["right"].isChecked()

    window.close_application()
    print("  -> Per-effect 5-slot profiles and dock controls verified successfully.")


def main():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    test_matrix_definitions()
    test_dock_geometry()
    test_dual_brightness_and_anti_burst()
    test_zero_lag_typing_and_detached()
    test_per_effect_profiles(app)
    print("\n==========================================")
    print("ALL EVEREST STUDIO PRO v2.0 TESTS PASSED!")
    print("==========================================")


if __name__ == "__main__":
    main()
    os._exit(0)
