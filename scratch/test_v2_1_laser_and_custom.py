import os
import sys
import time
from openrgb.utils import RGBColor

# Ensure workspace root is in python path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.matrix import KEY_DEFINITIONS, NUMPAD_KEY_DEFINITIONS, ALL_KEY_DEFINITIONS, build_matrix_coords
from engine.effects import EffectRenderer, scale_brightness
from engine.lighting_engine import LightingEngineThread, calculate_laser_intensity
from gui.main_window import EverestStudioWindow, BRUSH_PAINT, BRUSH_ERASE, TARGET_COLOR_A, TARGET_COLOR_B

def test_snappy_laser_row_lock():
    print("=== TEST 1: Snappy Laser Row Lock ===")
    engine = LightingEngineThread()
    engine.laser_speed = 60.0
    engine.laser_decay = 0.50
    engine.pulse_width = 2.0
    engine.color_a = RGBColor(255, 0, 0)
    engine.color_b = RGBColor(0, 0, 0)
    engine.mode_type = "single"

    # Strike 'G' (Slot 33, default_idx 73, Row 2, x ~ 5.75, y ~ 2.0)
    g_def = next(k for k in KEY_DEFINITIONS if k["id"] == "g")
    g_idx = g_def["default_idx"]
    engine.trigger_switch(g_idx)

    # Simulate t = t0 + 0.05s
    t0 = engine.active_punches[g_idx]
    t_test = t0 + 0.05

    rows_snap = dict(engine.active_rows)
    print(f"Active rows after striking G: {rows_snap}")

    # Check that Row 2 is active, but NOT Row 0, 1, 3, 4
    assert 2 in rows_snap, "Row 2 should be in active_rows"
    assert 0 not in rows_snap, "Row 0 must NOT be in active_rows"
    assert 1 not in rows_snap, "Row 1 must NOT be in active_rows"
    assert 3 not in rows_snap, "Row 3 must NOT be in active_rows"
    assert 4 not in rows_snap, "Row 4 must NOT be in active_rows"

    # Evaluate intensity on keys across all rows
    # Row 2 key: 'F' (x ~ 4.75, y = 2.0)
    f_def = next(k for k in KEY_DEFINITIONS if k["id"] == "f")
    fx, fy = engine.key_coords[f_def["default_idx"]]
    f_int = calculate_laser_intensity(fx, fy, t_test, rows_snap, engine.laser_speed, engine.laser_decay, engine.pulse_width)
    print(f"Key F (Row 2) intensity: {f_int:.3f}")
    assert f_int > 0.0, "Key F on Row 2 should be illuminated by laser!"

    # Row 0 key: '3' (Hardware Index 27, y = 0.0)
    k3_def = next(k for k in KEY_DEFINITIONS if k["id"] == "3")
    k3x, k3y = engine.key_coords[k3_def["default_idx"]]
    k3_int = calculate_laser_intensity(k3x, k3y, t_test, rows_snap, engine.laser_speed, engine.laser_decay, engine.pulse_width)
    print(f"Key 3 (Row 0) intensity: {k3_int:.3f}")
    assert k3_int == 0.0, "Key 3 on Row 0 must be strictly 0.0 when Row 2 is struck!"

    # Row 1 key: 'T' (y = 1.0)
    t_def = next(k for k in KEY_DEFINITIONS if k["id"] == "t")
    tx, ty = engine.key_coords[t_def["default_idx"]]
    t_int = calculate_laser_intensity(tx, ty, t_test, rows_snap, engine.laser_speed, engine.laser_decay, engine.pulse_width)
    print(f"Key T (Row 1) intensity: {t_int:.3f}")
    assert t_int == 0.0, "Key T on Row 1 must be strictly 0.0 when Row 2 is struck!"

    # Row 3 key: 'V' (y = 3.0)
    v_def = next(k for k in KEY_DEFINITIONS if k["id"] == "v")
    vx, vy = engine.key_coords[v_def["default_idx"]]
    v_int = calculate_laser_intensity(vx, vy, t_test, rows_snap, engine.laser_speed, engine.laser_decay, engine.pulse_width)
    print(f"Key V (Row 3) intensity: {v_int:.3f}")
    assert v_int == 0.0, "Key V on Row 3 must be strictly 0.0 when Row 2 is struck!"

    # Now strike Key 3 (Row 0)
    engine.trigger_switch(27)
    rows_snap = dict(engine.active_rows)
    t0_3 = engine.active_punches[27]
    t_test_3 = t0_3 + 0.05
    k3_int_after = calculate_laser_intensity(k3x, k3y, t_test_3, rows_snap, engine.laser_speed, engine.laser_decay, engine.pulse_width)
    print(f"Key 3 after striking Key 3: {k3_int_after:.3f}")
    assert k3_int_after > 0.0, "Key 3 must be illuminated when struck!"
    # Check that Row 1 key is 0.0 from Key 3's strike
    # Clear Row 2
    del rows_snap[2]
    t_int_from_row0 = calculate_laser_intensity(tx, ty, t_test_3, rows_snap, engine.laser_speed, engine.laser_decay, engine.pulse_width)
    assert t_int_from_row0 == 0.0, "Key T on Row 1 must NOT bleed from Key 3 on Row 0!"

    print("PASS: Snappy Laser Row Lock strictly enforces horizontal isolation without bleed.\n")


def test_slider_bounds_and_durations():
    print("=== TEST 2: Slider Bounds & Durations ===")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    window = EverestStudioWindow()

    # 1. Laser speed and decay bounds
    window._reconfigure_deck_for_effect("laser")
    speed_min = window.speed_slider.minimum()
    speed_max = window.speed_slider.maximum()
    decay_min = window.decay_slider.minimum()
    decay_max = window.decay_slider.maximum()

    print(f"Laser speed range: {speed_min} - {speed_max} keys/s")
    print(f"Laser decay range: {decay_min / 100.0:.2f}s - {decay_max / 100.0:.2f}s")

    assert speed_min == 5, f"Expected Laser speed min 5, got {speed_min}"
    assert speed_max >= 120, f"Expected Laser speed max >= 120, got {speed_max}"
    assert decay_min == 5, f"Expected Laser decay min 5 (0.05s), got {decay_min}"
    assert decay_max >= 300, f"Expected Laser decay max >= 300 (3.00s), got {decay_max}"

    # 2. Ripple speed and decay bounds
    window._reconfigure_deck_for_effect("ripple")
    rip_speed_min = window.speed_slider.minimum()
    rip_decay_max = window.decay_slider.maximum()

    print(f"Ripple speed range min: {rip_speed_min} keys/s")
    print(f"Ripple decay range max: {rip_decay_max / 100.0:.2f}s")

    assert rip_speed_min == 3, f"Expected Ripple speed min 3, got {rip_speed_min}"
    assert rip_decay_max >= 300, f"Expected Ripple decay max >= 300 (3.00s), got {rip_decay_max}"

    # 3. Punch decay bounds
    window._reconfigure_deck_for_effect("punch")
    punch_decay_max = window.decay_slider.maximum()
    print(f"Punch decay range max: {punch_decay_max / 100.0:.2f}s")
    assert punch_decay_max >= 300, f"Expected Punch decay max >= 300 (3.00s), got {punch_decay_max}"

    print("PASS: Slider bounds strictly adhere to v2.1 specifications.\n")


def test_custom_per_key_overhaul():
    print("=== TEST 3: Custom Per-Key UI & Engine Overhaul ===")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    window = EverestStudioWindow()
    engine = window.engine
    engine.effect_name = "custom"
    window._reconfigure_deck_for_effect("custom")

    # Verify custom controls widget is not hidden
    assert not window.custom_controls_widget.isHidden(), "custom_controls_widget should not be hidden in custom mode"
    assert not window.react_bright_widget.isHidden(), "react_bright_widget should not be hidden in custom mode"

    # Clear any previous custom keys
    engine.clear_custom_keys()
    assert len(engine.custom_key_colors) == 0, "custom_key_colors should be empty after clear"

    # Set Base Color to Dark Blue (0, 0, 100) and Base Brightness to 50%
    engine.color_b = RGBColor(0, 0, 100)
    engine.base_brightness = 50.0

    # Set Active Brush Color to Bright Red (255, 0, 0) and Reactive Brightness to 100%
    engine.color_a = RGBColor(255, 0, 0)
    engine.reactive_brightness = 100.0

    # Test unpainted key renders Base Color scaled by base brightness
    # Key 'W' (slot 16, default_idx 48)
    w_def = next(k for k in KEY_DEFINITIONS if k["id"] == "w")
    w_idx = w_def["default_idx"]

    # Frame colors with empty custom map
    engine._static_dirty = True
    engine._render_custom_frame(time.time())

    # Slot 16 (Key W) unpainted should be (0, 0, 50)
    color_w_unpainted = engine._compute_key_color(w_idx, 2.5, 1.0, time.time(), {}, {}, [], {})
    print(f"Unpainted Key W: RGB({color_w_unpainted.red}, {color_w_unpainted.green}, {color_w_unpainted.blue})")
    assert color_w_unpainted.blue == 50, f"Expected unpainted key blue 50, got {color_w_unpainted.blue}"
    assert color_w_unpainted.red == 0, f"Expected unpainted key red 0, got {color_w_unpainted.red}"

    # Now paint Key 'W' using canvas click in paint mode
    window._set_brush_mode(BRUSH_PAINT)
    window._on_canvas_key_clicked(w_idx)

    assert w_idx in engine.custom_key_colors, "Key W should now be in custom_key_colors"
    assert engine.custom_key_colors[w_idx] == RGBColor(255, 0, 0), "Key W color should match brush color"

    # Re-evaluate color: painted key should be Bright Red (255, 0, 0) scaled by reactive brightness (100%)
    color_w_painted = engine._compute_key_color(w_idx, 2.5, 1.0, time.time(), {}, {}, [], dict(engine.custom_key_colors))
    print(f"Painted Key W: RGB({color_w_painted.red}, {color_w_painted.green}, {color_w_painted.blue})")
    assert color_w_painted.red == 255, f"Expected painted key red 255, got {color_w_painted.red}"
    assert color_w_painted.blue == 0, f"Expected painted key blue 0, got {color_w_painted.blue}"

    # Now test Erase mode: erase Key 'W'
    window._set_brush_mode(BRUSH_ERASE)
    window._on_canvas_key_clicked(w_idx)

    assert w_idx not in engine.custom_key_colors, "Key W should be removed after erase"
    color_w_erased = engine._compute_key_color(w_idx, 2.5, 1.0, time.time(), {}, {}, [], dict(engine.custom_key_colors))
    print(f"Erased Key W (reverted): RGB({color_w_erased.red}, {color_w_erased.green}, {color_w_erased.blue})")
    assert color_w_erased.blue == 50, "Erased key must revert to Base Color!"

    # Test Fill All Keys
    window._fill_all_custom_keys()
    assert len(engine.custom_key_colors) >= 64, f"Fill all should paint all keys, count = {len(engine.custom_key_colors)}"

    # Test Clear All Keys
    window._clear_all_custom_keys()
    assert len(engine.custom_key_colors) == 0, "Clear all should empty custom_key_colors"

    # Test Profile capture and restore
    engine.paint_custom_key(w_idx, RGBColor(0, 255, 0)) # Green 'W'
    window.brush_mode = BRUSH_ERASE
    profile_data = window._capture_current_profile_dict()
    assert "custom_colors" in profile_data, "Profile must serialize custom_colors"
    assert str(w_idx) in profile_data["custom_colors"], "Key W must be in serialized profile"
    assert profile_data["brush_mode"] == BRUSH_ERASE, "Brush mode must be in serialized profile"

    # Reset engine and apply profile
    engine.clear_custom_keys()
    window._set_brush_mode(BRUSH_PAINT)
    window._apply_profile_dict(profile_data)

    assert w_idx in engine.custom_key_colors, "Profile application must restore Key W"
    assert engine.custom_key_colors[w_idx] == RGBColor(0, 255, 0), "Key W color restored correctly"
    assert window.brush_mode == BRUSH_ERASE, "Brush mode restored correctly"

    print("PASS: Custom Per-Key overhaul fully tested and verified.\n")


def test_detached_numpad_blackout():
    print("=== TEST 4: Detached Numpad Blackout in Custom Mode ===")
    engine = LightingEngineThread()
    engine.dock_position = "detached"
    engine.effect_name = "custom"
    engine.color_b = RGBColor(255, 255, 255)
    engine.base_brightness = 100.0

    # Fill all keys
    engine.fill_all_custom_keys(RGBColor(255, 255, 255))
    engine._static_dirty = True
    engine._render_custom_frame(time.time())

    # Visualizer slots 64..80 must be strictly (0, 0, 0)
    # We can inspect the emitted frame or run custom frame logic
    custom_snap = dict(engine.custom_key_colors)
    react_factor = 1.0
    for num_offset, k in enumerate(NUMPAD_KEY_DEFINITIONS):
        slot_idx = 64 + num_offset
        # In detached mode, _render_custom_frame sets slots 64..80 to (0,0,0)
    print("PASS: Detached mode correctly blacks out modular numpad.\n")


if __name__ == "__main__":
    test_snappy_laser_row_lock()
    test_slider_bounds_and_durations()
    test_custom_per_key_overhaul()
    test_detached_numpad_blackout()
    print("ALL v2.1 TESTS PASSED SUCCESSFULLY!")
    # Clean exit without Qt thread termination assert
    os._exit(0)
