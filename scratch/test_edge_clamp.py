"""
Comprehensive Automated Verification for Underglow Hard-Lock,
Edge Decoupling, and Ghost Event Filtering.
"""

import sys
import os
import time
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openrgb.utils import RGBColor
from pynput import keyboard

from engine.lighting_engine import LightingEngineThread
from engine.matrix import KEY_DEFINITIONS, EDGE_INDICES, SWITCH_INDICES


class DummyKey:
    def __init__(self, char=None, name=None, vk=None):
        if char is not None:
            self.char = char
        if name is not None:
            self.name = name
        if vk is not None:
            self.vk = vk


def run_tests():
    print("=== STARTING UNDERGLOW & EDGE CLAMP TESTS ===")
    engine = LightingEngineThread()

    # Mock OpenRGB hardware device with 147 LEDs
    dummy_kb = MagicMock()
    dummy_kb.colors = [RGBColor(255, 255, 255) for _ in range(147)]
    engine.kb = dummy_kb
    engine.running = True

    # ---------------------------------------------------------
    # TEST 1: Ghost Polling Filter in _is_reactive_trigger
    # ---------------------------------------------------------
    print("\n[Test 1] Ghost Polling & Modifier Filter...")
    # Modifiers by name
    for mod in ["shift", "shift_l", "shift_r", "ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r", "alt_gr", "caps_lock", "cmd", "cmd_l", "cmd_r", "menu"]:
        assert not engine._is_reactive_trigger(DummyKey(name=mod)), f"Failed to reject modifier name: {mod}"

    # Modifiers by VK
    for vk in [16, 17, 18, 20, 91, 92, 93, 160, 161, 162, 163, 164, 165, 229]:
        assert not engine._is_reactive_trigger(DummyKey(vk=vk)), f"Failed to reject modifier VK: {vk}"

    # Valid keys
    assert engine._is_reactive_trigger(DummyKey(char="a")), "Failed to accept char 'a'"
    assert engine._is_reactive_trigger(DummyKey(char="1")), "Failed to accept char '1'"
    assert engine._is_reactive_trigger(DummyKey(char=" ")), "Failed to accept space char"
    assert engine._is_reactive_trigger(DummyKey(name="space")), "Failed to accept space name"
    assert engine._is_reactive_trigger(DummyKey(name="enter")), "Failed to accept enter"
    assert engine._is_reactive_trigger(DummyKey(name="backspace")), "Failed to accept backspace"
    assert engine._is_reactive_trigger(keyboard.Key.space), "Failed to accept keyboard.Key.space"
    assert engine._is_reactive_trigger(keyboard.Key.enter), "Failed to accept keyboard.Key.enter"
    print("✓ Test 1 Passed: All ghost modifiers rejected, valid keys accepted.")

    # ---------------------------------------------------------
    # TEST 2: Dynamic 64 Switches & 83 Edge Indices Detection
    # ---------------------------------------------------------
    print("\n[Test 2] Dynamic 64 Switches & 83 Edge Diffusers Detection...")
    assert len(engine.switch_indices) == 64, f"Expected 64 switch indices, got {len(engine.switch_indices)}"
    assert len(engine.edge_indices) == 83, f"Expected 83 edge indices, got {len(engine.edge_indices)}"
    assert len(engine.switch_indices) + len(engine.edge_indices) == 147, "Sum of switches + edge must equal 147"
    assert engine.switch_indices.isdisjoint(set(engine.edge_indices)), "Switch and edge indices must not overlap!"

    # Verify index 0 is in edge_indices
    assert 0 in engine.edge_indices, "LED 0 is not in edge_indices!"
    assert 0 not in engine.switch_indices, "LED 0 should not be in switch_indices!"

    # Unmapped keys / missing lookups must return None, NEVER 0
    dummy_unknown = DummyKey(name="f24_unknown_key")
    res = engine._resolve_key(dummy_unknown)
    assert res is None, f"_resolve_key should return None for unknown, got: {res}"

    # Triggering switch 0 or any edge index must be completely ignored
    engine.active_rows.clear()
    engine.active_punches.clear()
    engine.active_ripples.clear()

    engine.trigger_switch(0)
    assert len(engine.active_rows) == 0, "Triggering LED 0 created active row!"
    assert len(engine.active_punches) == 0, "Triggering LED 0 created active punch!"
    assert len(engine.active_ripples) == 0, "Triggering LED 0 created active ripple!"

    for e_idx in engine.edge_indices:
        engine.trigger_switch(e_idx)
    assert len(engine.active_rows) == 0, "Triggering edge indices created active row!"
    assert len(engine.active_punches) == 0, "Triggering edge indices created active punch!"
    assert len(engine.active_ripples) == 0, "Triggering edge indices created active ripple!"
    print("✓ Test 2 Passed: Dynamic 64 switches & 83 edge indices verified. Edge indices cannot be triggered.")

    # ---------------------------------------------------------
    # TEST 3: Hard-Lock at 0% Edge Brightness
    # ---------------------------------------------------------
    print("\n[Test 3] Hard-Lock at 0% Edge Brightness (Pure Darkness)...")
    frame_output = []
    ug_output = []
    engine.frame_rendered.connect(lambda f: frame_output.append(f))
    engine.underglow_rendered.connect(lambda u: ug_output.append(u))

    engine.underglow_brightness = 0
    now = time.time()

    for eff in ["static", "wave", "breathing", "tornado", "laser", "punch", "ripple", "matrix"]:
        engine.effect_name = eff
        engine.underglow_mode = "sync"
        engine._render_loop_step(now)

        assert len(frame_output[-1]) == 64, f"Frame must contain exactly 64 keys, got {len(frame_output[-1])}"
        # Underglow signal must be (0, 0, 0)
        assert ug_output[-1] == (0, 0, 0), f"Underglow not (0,0,0) in {eff} mode at 0% brightness!"

        # All edge LEDs in hardware buffer must be RGBColor(0, 0, 0)
        for e_idx in engine.edge_indices:
            c = dummy_kb.colors[e_idx]
            assert c.red == 0 and c.green == 0 and c.blue == 0, f"Edge LED {e_idx} not pure black in {eff} mode!"

    print("✓ Test 3 Passed: 0% brightness locks all 83 perimeter LEDs to complete black.")

    # ---------------------------------------------------------
    # TEST 4: Underglow Mode 'off'
    # ---------------------------------------------------------
    print("\n[Test 4] Underglow Mode 'off'...")
    engine.underglow_brightness = 100
    engine.underglow_mode = "off"
    engine.effect_name = "wave"
    engine._render_loop_step(time.time())
    assert ug_output[-1] == (0, 0, 0), "Underglow not (0,0,0) when underglow_mode is 'off'"
    for e_idx in engine.edge_indices:
        c = dummy_kb.colors[e_idx]
        assert c.red == 0 and c.green == 0 and c.blue == 0, f"Edge LED {e_idx} not black when mode is 'off'"
    print("✓ Test 4 Passed: Underglow 'off' mode forces pure black on all perimeter LEDs.")

    # ---------------------------------------------------------
    # TEST 5: Decoupled Reactive Underglow in 'sync' Mode
    # ---------------------------------------------------------
    print("\n[Test 5] Reactive Keystroke Flare Decoupling in 'sync' Mode...")
    engine.underglow_brightness = 50
    engine.underglow_mode = "sync"
    engine.mode_type = "dual"
    engine.color_a = RGBColor(255, 0, 0)     # Strike color (Red)
    engine.color_b = RGBColor(0, 0, 200)     # Ambient Base (Blue)
    expected_edge_blue = int(200 * 0.5)      # 100

    for eff in ["laser", "punch", "ripple"]:
        engine.effect_name = eff
        now = time.time()

        # Simulate heavy typing on switch 24 (ESC switch)
        engine.trigger_switch(24)
        engine._render_loop_step(now)

        # Underglow must be (0, 0, 100), strictly base color scaled by 50%
        # It must NOT have any red (strike color) from the punch/laser/ripple!
        ug_color = ug_output[-1]
        assert ug_color[0] == 0, f"Underglow contaminated with red in {eff} mode: {ug_color}"
        assert ug_color[2] == expected_edge_blue, f"Underglow blue expected {expected_edge_blue}, got: {ug_color[2]}"

        # Perimeter LEDs on hardware buffer
        for e_idx in engine.edge_indices:
            c = dummy_kb.colors[e_idx]
            assert c.red == 0, f"Perimeter LED {e_idx} flared red in {eff} mode!"
            assert c.blue == expected_edge_blue, f"Perimeter LED {e_idx} blue mismatch: {c.blue}"

    print("✓ Test 5 Passed: Underglow remains strictly ambient base; keystrokes never flare edges.")

    # ---------------------------------------------------------
    # TEST 6: Single-Color Reactive Mode with Underglow
    # ---------------------------------------------------------
    print("\n[Test 6] Single-Color Reactive Mode...")
    engine.mode_type = "single"
    for eff in ["laser", "punch", "ripple"]:
        engine.effect_name = eff
        engine.underglow_mode = "off"
        engine.trigger_switch(25)  # Key '1'
        engine._render_loop_step(time.time())
        assert ug_output[-1] == (0, 0, 0), f"Underglow not black in single-color {eff}"
        for e_idx in engine.edge_indices:
            c = dummy_kb.colors[e_idx]
            assert c.red == 0 and c.green == 0 and c.blue == 0, f"Perimeter LED {e_idx} not black in single {eff}"
    print("✓ Test 6 Passed: Single-color reactive underglow remains pure black.")

    print("\n==========================================")
    print(">>> ALL 6 VERIFICATION TEST SUITES PASSED! <<<")
    print("==========================================")


if __name__ == "__main__":
    run_tests()
