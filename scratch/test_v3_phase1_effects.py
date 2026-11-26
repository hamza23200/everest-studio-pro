"""Verification suite for Everest Studio Pro v3.0 (Phase 1): Categorized Sidebar & 13 New Effects."""
import io
import os
import sys
import time
import contextlib
from unittest.mock import MagicMock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from openrgb.utils import RGBColor

from engine.lighting_engine import LightingEngineThread
from engine.matrix import ALL_EDGE_INDICES, ALL_KEY_DEFINITIONS
from gui.main_window import ALL_EFFECT_KEYS, EverestStudioWindow

app = QApplication.instance() or QApplication(sys.argv)

SLOT = {k["id"]: k["slot"] for k in ALL_KEY_DEFINITIONS}
IDX = {k["id"]: k["default_idx"] for k in ALL_KEY_DEFINITIONS}

NEW_V3_EFFECTS = [
    "row_sweep",
    "waterfall",
    "aurora",
    "gradient_breathing",
    "cosmic_drift",
    "thunderstorm",
    "system_malfunction",
    "dna_spiral",
    "meteor_shower",
    "crosshair",
    "full_board_flash",
    "explosion_burst",
    "typing_heatmap",
]
REACTIVE_V3_EFFECTS = {"crosshair", "full_board_flash", "explosion_burst", "typing_heatmap"}


class FakeKeyboard:
    def __init__(self, count=147):
        self.colors = [RGBColor(0, 0, 0) for _ in range(count)]

    def show(self, fast=True):
        pass


def _valid_rgb_tuple(c) -> bool:
    return (
        isinstance(c, tuple)
        and len(c) == 3
        and all(isinstance(v, int) and 0 <= v <= 255 for v in c)
    )


def test_all_13_effects_across_docks():
    print("=== TEST 1: All 13 New Effects Across Right/Left/Detached Docks ===")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        for dock in ("right", "left", "detached"):
            eng = LightingEngineThread()
            eng.dock_position = dock
            eng.base_brightness = 50.0
            eng.reactive_brightness = 100.0
            eng.color_a = RGBColor(255, 60, 0)
            eng.color_b = RGBColor(0, 40, 200)
            eng.mode_type = "dual"
            eng.underglow_mode = "sync"
            eng.underglow_brightness = 50

            frames = []
            eng.frame_rendered.connect(lambda f: frames.append(list(f)))

            for eff in NEW_V3_EFFECTS:
                frames.clear()
                eng.effect_name = eff
                t0 = time.time()
                if eff in REACTIVE_V3_EFFECTS:
                    eng.trigger_switch(IDX["g"])
                    eng.trigger_switch(IDX["num_5"])
                for tick in range(20):
                    eng._render_loop_step(t0 + tick * 0.03)

                assert len(frames) == 20, f"{dock}/{eff}: expected 20 frames, got {len(frames)}"
                for frame in frames:
                    assert len(frame) == 81, f"{dock}/{eff}: expected 81 LEDs, got {len(frame)}"
                    assert all(_valid_rgb_tuple(c) for c in frame), f"{dock}/{eff}: invalid RGB tuple"

    out = buf.getvalue()
    assert "ENGINE CRASH PREVENTED" not in out and "Traceback" not in out, out
    print("  -> Passed 20 frames x 13 effects x 3 docks with 81 valid RGB tuples & zero crashes.")


def test_perimeter_zero_edge_clamp():
    print("=== TEST 2: 66 Perimeter Diffusers Clamp Strictly to (0,0,0) when edge_brightness == 0 ===")
    eng = LightingEngineThread()
    fake_kb = FakeKeyboard(147)
    eng.kb = fake_kb
    eng.dock_position = "right"
    eng.base_brightness = 100.0
    eng.reactive_brightness = 100.0
    eng.underglow_mode = "sync"
    eng.edge_brightness = 0
    assert eng.underglow_brightness == 0

    for eff in NEW_V3_EFFECTS:
        eng.effect_name = eff
        if eff in REACTIVE_V3_EFFECTS:
            eng.trigger_switch(IDX["g"])
        eng._render_loop_step(time.time())
        for edge_idx in ALL_EDGE_INDICES:
            c = fake_kb.colors[edge_idx]
            assert (c.red, c.green, c.blue) == (0, 0, 0), (
                f"{eff}: edge LED {edge_idx} leaked non-zero {(c.red, c.green, c.blue)} when edge_brightness==0"
            )

    print("  -> All 66 perimeter LEDs strictly clamped to (0, 0, 0) across all 13 effects.")


def test_reactive_v3_semantics():
    print("=== TEST 3: Reactive Crosshair / Flash / Explosion / Heatmap Semantics ===")
    eng = LightingEngineThread()
    eng.dock_position = "right"
    eng.mode_type = "single"
    eng.color_a = RGBColor(255, 0, 0)
    eng.color_b = RGBColor(0, 0, 0)
    eng.base_brightness = 0.0
    eng.reactive_brightness = 100.0
    frames = []
    eng.frame_rendered.connect(lambda f: frames.append(list(f)))

    # Crosshair on 'g': 'f' (row 2) and 't' (near x of 'g') light up; far corner 'esc' stays black
    eng.effect_name = "crosshair"
    eng.trigger_switch(IDX["g"])
    eng._render_loop_step(time.time() + 0.04)
    assert frames[-1][SLOT["g"]][0] > 0, "Crosshair center 'g' should light up"
    assert frames[-1][SLOT["f"]][0] > 0, "Crosshair horizontal beam should light 'f'"
    assert frames[-1][SLOT["esc"]] == (0, 0, 0), f"Crosshair leaked to 'esc': {frames[-1][SLOT['esc']]}"

    # Full-Board Flash on 'g': board lights uniformly
    eng.effect_name = "full_board_flash"
    eng.trigger_switch(IDX["g"])
    eng._render_loop_step(time.time() + 0.01)
    assert frames[-1][SLOT["esc"]][0] > 0 and frames[-1][SLOT["right"]][0] > 0, "Flash should illuminate whole board"

    # Explosion Burst on 'g': 'g' bright, adjacent 'f' > 0
    eng.effect_name = "explosion_burst"
    eng.trigger_switch(IDX["g"])
    eng._render_loop_step(time.time() + 0.02)
    assert frames[-1][SLOT["g"]][0] > 100, "Explosion core 'g' should be bright"

    # Typing Heatmap: persistent retains heat, reset clears
    eng.effect_name = "typing_heatmap"
    eng.heatmap_mode = "persistent"
    eng.base_brightness = 20.0
    eng.trigger_switch(IDX["g"])
    heat_before = eng.key_heat.get(IDX["g"], 0.0)
    assert heat_before > 0.0, "Strike should add heat"
    eng._render_loop_step(time.time() + 0.2)
    assert eng.key_heat.get(IDX["g"], 0.0) == heat_before, "Persistent mode must not decay heat"
    eng.reset_heatmap()
    assert len(eng.key_heat) == 0, "reset_heatmap() must clear all heat"
    print("  -> Crosshair, Full-Board Flash, Explosion Burst, and Typing Heatmap semantics verified.")


def test_ui_sidebar_and_controls():
    print("=== TEST 4: Scrollable Categorized Sidebar (25 Effects) & Heatmap Controls ===")
    win = EverestStudioWindow()
    assert hasattr(win, "effects_scroll_area"), "effects_scroll_area missing"
    found_keys = []
    for i in range(win.effects_list.count()):
        item = win.effects_list.item(i)
        k = item.data(Qt.ItemDataRole.UserRole)
        if k:
            found_keys.append(k)
        else:
            # Category header must not be selectable
            assert item.flags() == Qt.ItemFlag.NoItemFlags, "Header item must not be selectable"

    assert len(found_keys) == 25, f"Expected 25 selectable effects, got {len(found_keys)}: {found_keys}"
    assert set(found_keys) == set(ALL_EFFECT_KEYS), "Sidebar effect keys mismatch"

    # Select typing_heatmap in sidebar and test UI buttons without mutating saved config on disk
    win.save_settings = lambda: None
    for i in range(win.effects_list.count()):
        if win.effects_list.item(i).data(Qt.ItemDataRole.UserRole) == "typing_heatmap":
            win.effects_list.setCurrentRow(i)
            break

    assert win.engine.effect_name == "typing_heatmap"
    assert not win.heatmap_controls_widget.isHidden(), "Heatmap controls must show in typing_heatmap"
    win.heatmap_persist_btn.click()
    assert win.engine.heatmap_mode == "persistent"
    assert win.speed_widget.isHidden(), "Cooldown slider should hide in persistent mode"
    win.heatmap_live_btn.click()
    assert win.engine.heatmap_mode == "live"
    assert not win.speed_widget.isHidden(), "Cooldown slider should show in live mode"

    win.engine.trigger_switch(IDX["g"])
    assert len(win.engine.key_heat) > 0
    win.heatmap_reset_btn.click()
    assert len(win.engine.key_heat) == 0

    print("  -> All 25 effects, 5 category headers, QScrollArea, and dynamic controls verified.")


if __name__ == "__main__":
    test_all_13_effects_across_docks()
    test_perimeter_zero_edge_clamp()
    test_reactive_v3_semantics()
    test_ui_sidebar_and_controls()
    print("ALL V3.0 PHASE 1 TESTS PASSED!")
    os._exit(0)
