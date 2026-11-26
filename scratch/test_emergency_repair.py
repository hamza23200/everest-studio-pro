"""Headless verification for the emergency render-loop / visualizer / handshake repair."""
import io
import os
import sys
import time
import contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtCore import QCoreApplication
from openrgb.utils import RGBColor

import engine.lighting_engine as le
from engine.lighting_engine import LightingEngine, calculate_laser_intensity
from engine.matrix import (
    ALL_KEY_DEFINITIONS, ORDERED_KEYS, INDEX_TO_KEY, KEY_TO_INDEX, build_key_coordinates,
)

app = QCoreApplication.instance() or QCoreApplication(sys.argv)
SLOT = {k["id"]: k["slot"] for k in ALL_KEY_DEFINITIONS}
IDX = {k["id"]: k["default_idx"] for k in ALL_KEY_DEFINITIONS}
BASE = RGBColor(0, 0, 200)
STRIKE = RGBColor(255, 0, 0)


def make_engine(effect):
    e = LightingEngine()
    e.effect_name = effect
    e.mode_type = "dual"
    e.color_a, e.color_b = STRIKE, BASE
    e.base_brightness, e.reactive_brightness = 50.0, 100.0
    e.laser_speed, e.laser_decay, e.pulse_width = 60.0, 0.5, 2.0
    e.ripple_speed, e.ripple_decay = 15.0, 0.65
    e.underglow_mode = "sync"
    return e


def run_frames(e, n=5):
    frames = []
    e.frame_rendered.connect(lambda f: frames.append(list(f)))
    t = time.time()
    for i in range(n):
        e._render_loop_step(t + 0.02 * (i + 1))
    return frames


def test_matrix_exports():
    assert len(ORDERED_KEYS) == 81 and len({n for n, _ in ORDERED_KEYS}) == 81
    assert ORDERED_KEYS[3] == ("3", 27)
    assert len(INDEX_TO_KEY) == 81 and INDEX_TO_KEY[IDX["g"]] == "g"
    assert all(0 <= i < 147 for _, i in ORDERED_KEYS)
    for dock in ("right", "left", "detached"):
        c = build_key_coordinates(dock)
        assert len(c) == (64 if dock == "detached" else 81), (dock, len(c))
    assert build_key_coordinates("left")["num_5"][0] < 0 < build_key_coordinates("right")["num_5"][0]
    assert KEY_TO_INDEX["g"] == 73
    print("PASS matrix exports (ORDERED_KEYS/KEY_TO_INDEX/INDEX_TO_KEY/KEY_COORDINATES)")


def test_effect(effect):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        e = make_engine(effect)
        assert e.kb is None, "test must run offline"
        e.trigger_switch(IDX["g"])
        e.trigger_switch(IDX["num_5"])
        frames = run_frames(e, 5)
    out = buf.getvalue()
    assert "CRASH PREVENTED" not in out and "Traceback" not in out, out
    assert len(frames) == 5, f"frame_rendered must emit EVERY frame offline, got {len(frames)}"
    last = frames[-1]
    assert len(last) == 81
    assert all(isinstance(c, tuple) and len(c) == 3 for c in last)
    a = last[SLOT["a"]]
    assert a != (0, 0, 0) and a[2] > 0, f"{effect}: base color missing on idle key 'a': {a}"
    assert any(f[SLOT["g"]][0] > 0 for f in frames), f"{effect}: no wave on 'g'"
    assert any(f[SLOT["num_5"]][0] > 0 for f in frames), f"{effect}: no wave on 'numpad 5'"
    print(f"PASS {effect}: 5 frames x 81 RGB tuples, base={a}, g_peak={max(f[SLOT['g']][0] for f in frames)}")
    return e, frames


def test_laser_row_lock():
    e, frames = test_effect("laser")
    now = time.time() + 0.05
    rows = dict(e.active_rows)
    for name in ("t", "y", "v", "b"):
        kx, ky = e.key_coords[IDX[name]]
        inten = calculate_laser_intensity(kx, ky, now, {k: v for k, v in rows.items()}, 60.0, 0.5, 2.0)
        # active_rows contains g's row; num_5 shares row 2, both on y=2.5 -> rows 1 / 3 stay dark
        assert inten == 0.0, f"row bleed on {name}: {inten}"
        for f in frames:
            assert f[SLOT[name]][0] == 0, f"laser bled red onto '{name}': {f[SLOT[name]]}"
    assert any(f[SLOT["f"]][0] > 0 or f[SLOT["h"]][0] > 0 for f in frames), "row 2 neighbours must light"
    print("PASS laser row-lock: row 1 (t,y) and row 3 (v,b) have zero wave intensity")


def test_run_loop_offline_still_animates():
    """run() must keep emitting frames when OpenRGB/USB is unavailable (the original bug)."""
    le.ensure_openrgb_server = lambda: False  # simulate no server
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        e = make_engine("laser")
        frames = []
        e.frame_rendered.connect(lambda f: frames.append(1))
        e.start()
        e.trigger_switch(IDX["g"])
        t0 = time.time()
        while time.time() - t0 < 1.5:
            app.processEvents()
            time.sleep(0.02)
        e.running = False
        e.wait(3000)
    assert len(frames) >= 20, f"render loop died offline: only {len(frames)} frames"
    assert e.is_connected is False
    print(f"PASS run() offline: {len(frames)} frames in 1.5s, badge stays honest (is_connected=False)")


if __name__ == "__main__":
    test_matrix_exports()
    test_effect("ripple")
    test_laser_row_lock()
    test_run_loop_offline_still_animates()
    print("ALL EMERGENCY REPAIR TESTS PASSED")
    sys.stdout.flush()
    os._exit(0)

