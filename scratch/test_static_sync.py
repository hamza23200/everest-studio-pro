"""
Automated Verification for Mission:
Hardwire Hardware Index 27 (Key 3) Across All Matrix Collections & Render Loops
"""

import sys
import os
import time
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openrgb.utils import RGBColor
from pynput import keyboard

from engine.lighting_engine import LightingEngineThread, LightingEngine
from engine.matrix import (
    KeyboardMatrix,
    KEY_DEFINITIONS,
    KEY_TO_INDEX,
    key_to_index,
    ORDERED_KEYS,
    ordered_keys,
    KEY_COORDINATES,
    key_coordinates,
)
from gui.main_window import MainWindow
import everest_engine
import everest_gui


def test_mission_key_3_hardwire():
    print("=== STARTING KEY 3 HARDWIRE & MATRIX COLLECTIONS VERIFICATION ===")

    # --------------------------------------------------------------------------
    # 1. AUDIT MATRIX COLLECTIONS (engine/matrix.py)
    # --------------------------------------------------------------------------
    print("\n[Step 1] Auditing Matrix Collections...")
    # key_to_index: Must explicitly contain: '3': 27, 3: 27, '#': 27
    assert key_to_index.get("3") == 27, "key_to_index['3'] is not 27!"
    assert key_to_index.get(3) == 27, "key_to_index[3] is not 27!"
    assert key_to_index.get("#") == 27, "key_to_index['#'] is not 27!"
    assert KEY_TO_INDEX.get("3") == 27, "KEY_TO_INDEX['3'] is not 27!"

    # ordered_keys: 64-item list, ('3', 27) between ('2', 26) and ('4', 28)
    assert len(ordered_keys) == 64, f"ordered_keys length is {len(ordered_keys)}, expected 64!"
    assert ordered_keys[2] == ("2", 26), f"ordered_keys[2] is {ordered_keys[2]}, expected ('2', 26)!"
    assert ordered_keys[3] == ("3", 27), f"ordered_keys[3] is {ordered_keys[3]}, expected ('3', 27)!"
    assert ordered_keys[4] == ("4", 28), f"ordered_keys[4] is {ordered_keys[4]}, expected ('4', 28)!"

    # KEY_COORDINATES: '3': (3.0, 0.0)
    assert KEY_COORDINATES.get("3") == (3.0, 0.0), f"KEY_COORDINATES['3'] is {KEY_COORDINATES.get('3')}, expected (3.0, 0.0)!"
    assert KEY_COORDINATES.get(3) == (3.0, 0.0), f"KEY_COORDINATES[3] is {KEY_COORDINATES.get(3)}, expected (3.0, 0.0)!"

    # KeyboardMatrix class properties
    assert KeyboardMatrix.key_to_index.get("3") == 27
    assert KeyboardMatrix.ordered_keys[3] == ("3", 27)
    assert KeyboardMatrix.KEY_COORDINATES.get("3") == (3.0, 0.0)
    print("✓ Step 1 Passed: key_to_index, ordered_keys, and KEY_COORDINATES audit successful.")

    # --------------------------------------------------------------------------
    # 2. DIRECT INDEX-BASED SWITCH RENDERING (engine/lighting_engine.py)
    # --------------------------------------------------------------------------
    print("\n[Step 2] Direct Index-Based Switch Rendering & Underglow Isolation...")
    engine = LightingEngineThread()

    # Mock hardware keyboard with 147 LEDs
    dummy_kb = MagicMock()
    dummy_kb.colors = [RGBColor(0, 0, 0) for _ in range(147)]
    engine.kb = dummy_kb
    engine.running = True

    # Mock client and socket
    mock_client = MagicMock()
    mock_sock = MagicMock()
    mock_sock.fileno.return_value = 42
    mock_client.sock = mock_sock
    engine.client = mock_client

    # Verify switch_indices
    assert 27 in engine.switch_indices, "Hardware Index 27 missing from switch_indices!"
    assert 27 not in engine.edge_indices, "Hardware Index 27 must not be in edge_indices!"

    # Test static yellow render
    frame_captured = []
    ug_captured = []
    engine.frame_rendered.connect(lambda f: frame_captured.append(f))
    engine.underglow_rendered.connect(lambda u: ug_captured.append(u))

    engine.effect_name = "static"
    engine.color_a = RGBColor(255, 255, 0)  # Bright Yellow
    engine.brightness = 100  # 100%
    engine.underglow_mode = "sync"
    engine.underglow_brightness = 40

    now = time.time()
    engine._render_static_frame(now)

    # Verify target color written directly to index 27
    target_color = RGBColor(255, 255, 0)
    assert dummy_kb.colors[27] == target_color, f"Hardware LED 27 is {dummy_kb.colors[27]}, expected {target_color}!"
    assert dummy_kb.colors[112] == target_color, f"Hardware LED 112 is {dummy_kb.colors[112]}, expected {target_color}!"
    print("✓ Step 2 Passed: Switch indices direct write and assertion passed. assert 27 in switch_indices passed.")

    # --------------------------------------------------------------------------
    # 3. FIX VISUALIZER EMISSION
    # --------------------------------------------------------------------------
    print("\n[Step 3] Visualizer Emission (Strictly 64-element list with Yellow Key 3)...")
    assert len(frame_captured) > 0, "No frame was emitted!"
    latest_frame = frame_captured[-1]
    assert len(latest_frame) == 64, f"Frame must have 64 elements, got {len(latest_frame)}!"
    assert latest_frame[3] == (255, 255, 0), f"Slot 3 (Key 3) is {latest_frame[3]}, expected (255, 255, 0)!"
    assert latest_frame[58] == (255, 255, 0), f"Slot 58 (Spacebar) is {latest_frame[58]}, expected (255, 255, 0)!"
    assert all(c == (255, 255, 0) for c in latest_frame), "All keys must be yellow in static yellow mode!"
    print("✓ Step 3 Passed: Visualizer emitted 64 items, Key 3 is bright yellow (255, 255, 0).")

    print("\n=================================================================")
    print(">>> ALL MISSION AUDITS, ASSERTIONS & RENDER TESTS PASSED! <<<")
    print("=================================================================")


if __name__ == "__main__":
    test_mission_key_3_hardwire()
