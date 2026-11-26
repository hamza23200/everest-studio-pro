"""Verification suite for Everest Studio Pro v3.0 (Phase 2): WASAPI Audio Equalizer & Screen Ambilight."""
import os
import sys
import time
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from openrgb.utils import RGBColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.audio_worker import AudioCaptureWorker
from engine.screen_worker import ScreenCaptureWorker
from engine.lighting_engine import LightingEngineThread
from engine.matrix import ALL_EDGE_INDICES, ALL_KEY_DEFINITIONS
from gui.main_window import EverestStudioWindow

app = QApplication.instance() or QApplication(sys.argv)
SLOT = {k["id"]: k["slot"] for k in ALL_KEY_DEFINITIONS}


class FakeKeyboard:
    def __init__(self, count=147):
        self.colors = [RGBColor(0, 0, 0) for _ in range(count)]

    def show(self, fast=True):
        pass


def test_audio_fft_binning():
    print("=== TEST 1: AudioCaptureWorker Logarithmic FFT Binning & Lifecycle ===")
    w = AudioCaptureWorker(num_bands=20)
    w.smoothing = 0.0  # Immediate response for deterministic bin test
    w.sensitivity = 2.0
    sr = 48000
    t = np.arange(1024, dtype=np.float32) / sr

    # 100 Hz bass sine wave -> left bands must dominate right bands
    bass_wave = 0.6 * np.sin(2.0 * np.pi * 100.0 * t)
    bass_bands = w.process_pcm_chunk(bass_wave, sample_rate=sr)
    assert len(bass_bands) == 20
    assert max(bass_bands[:5]) > 0.3, f"Expected strong bass left-band peak, got {bass_bands[:5]}"
    assert max(bass_bands[:5]) > max(bass_bands[12:]) * 3.0, f"Bass leaked to treble: {bass_bands}"

    # Reset and send 6000 Hz treble sine wave -> right bands must dominate left bands
    w._bands = [0.0] * 20
    treble_wave = 0.6 * np.sin(2.0 * np.pi * 6000.0 * t)
    treble_bands = w.process_pcm_chunk(treble_wave, sample_rate=sr)
    assert max(treble_bands[12:]) > 0.3, f"Expected strong treble right-band peak, got {treble_bands[12:]}"
    assert max(treble_bands[12:]) > max(treble_bands[:5]) * 3.0, f"Treble leaked to bass: {treble_bands}"

    # Noise floor gating on silence
    w._bands = [0.0] * 20
    silent = np.zeros(1024, dtype=np.float32)
    silent_bands = w.process_pcm_chunk(silent, sample_rate=sr)
    assert all(v == 0.0 for v in silent_bands), f"Silence did not gate to 0.0: {silent_bands}"

    # Detached board band count (15 bands)
    w.set_num_bands(15)
    bands_15 = w.process_pcm_chunk(bass_wave, sample_rate=sr)
    assert len(bands_15) == 15
    print("  -> FFT bass/treble separation, noise-floor gating, and 15/20-band scaling verified.")


def test_screen_capture_worker_mapping_and_ema():
    print("=== TEST 2: ScreenCaptureWorker Red/Blue Split & EMA Convergence ===")
    s = ScreenCaptureWorker()
    s.capture_mode = "grid"
    s.smoothing = 0.50
    s.saturation_boost = 1.0

    # Synthetic 1080p RGB image: left half pure red (255,0,0), right half pure blue (0,0,255)
    frame_a = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame_a[:, :960, 0] = 255
    frame_a[:, 960:, 2] = 255
    s.process_frame(frame_a, is_bgra=False)
    grid_a, edges_a, _ = s.get_snapshot()
    assert grid_a is not None and grid_a.shape == (5, 20, 3)

    # Left column (~col 1) should be pure red; right column (~col 18) should be pure blue
    assert grid_a[2, 1, 0] > 230 and grid_a[2, 1, 2] < 20, f"Left grid should be red: {grid_a[2, 1]}"
    assert grid_a[2, 18, 2] > 230 and grid_a[2, 18, 0] < 20, f"Right grid should be blue: {grid_a[2, 18]}"
    assert edges_a["left"][2, 0] > 230 and edges_a["right"][2, 2] > 230

    # EMA convergence: push solid green frames and verify monotonic step toward green
    frame_green = np.zeros((1080, 1920, 3), dtype=np.uint8)
    frame_green[:, :, 1] = 255
    s.process_frame(frame_green, is_bgra=False)
    grid_1, _, _ = s.get_snapshot()
    g1 = float(grid_1[2, 1, 1])
    assert 90.0 < g1 < 180.0, f"Expected ~50% EMA blend on step 1, got green={g1}"
    s.process_frame(frame_green, is_bgra=False)
    grid_2, _, _ = s.get_snapshot()
    g2 = float(grid_2[2, 1, 1])
    assert g2 > g1, f"EMA did not converge monotonically toward green: {g1} -> {g2}"
    print("  -> Left-red / right-blue mapping and monotonic EMA convergence verified.")


def test_engine_worker_lifecycle_and_rendering():
    print("=== TEST 3: Engine Auto-Lifecycle, 81-Key Output & Edge Zero-Clamp ===")
    eng = LightingEngineThread()
    fake_kb = FakeKeyboard(147)
    eng.kb = fake_kb
    eng.base_brightness = 100.0
    eng.reactive_brightness = 100.0

    # Initially on static: neither capture worker should be running
    assert not eng.audio_worker.is_running and not eng.screen_worker.is_running

    # Switch to audio_equalizer -> audio starts, screen stays off
    eng.effect_name = "audio_equalizer"
    time.sleep(0.2)
    assert eng.audio_worker.is_running, "AudioCaptureWorker must auto-start on audio_equalizer"
    assert not eng.screen_worker.is_running, "ScreenCaptureWorker must stay stopped"

    # Inject a bass sine chunk directly and verify Spectrum Bars illuminates left/bottom keys
    sr = 48000
    t = np.arange(1024, dtype=np.float32) / sr
    eng.audio_smoothing = 0.0
    eng.audio_gain = 2.0
    eng.audio_worker.smoothing = 0.0
    eng.audio_worker.sensitivity = 2.0
    eng.audio_worker.process_pcm_chunk(0.7 * np.sin(2.0 * np.pi * 100.0 * t), sr)
    frames = []
    eng.frame_rendered.connect(lambda f: frames.append(list(f)))
    eng.edge_brightness = 0
    eng._render_loop_step(time.time())
    assert len(frames[-1]) == 81
    assert frames[-1][SLOT["lctrl"]] != (0, 0, 0), f"Bass left-bottom key should light: {frames[-1][SLOT['lctrl']]}"
    for ei in ALL_EDGE_INDICES:
        c = fake_kb.colors[ei]
        assert (c.red, c.green, c.blue) == (0, 0, 0), "Edge LED leaked when edge_brightness==0"

    # Switch to screen_ambilight -> audio stops, screen starts
    eng.effect_name = "screen_ambilight"
    time.sleep(0.3)
    assert not eng.audio_worker.is_running, "AudioCaptureWorker must stop when switching away"
    assert eng.screen_worker.is_running, "ScreenCaptureWorker must auto-start on screen_ambilight"

    # Inject split frame & check key colors + edge zero clamp
    img = np.zeros((1080, 1920, 3), dtype=np.uint8)
    img[:, :960, 0] = 255
    img[:, 960:, 2] = 255
    eng.screen_smoothing = 0.0
    eng.screen_worker.smoothing = 0.0
    eng.screen_worker.process_frame(img, is_bgra=False)
    eng._render_loop_step(time.time())
    assert frames[-1][SLOT["a"]][0] > 180 and frames[-1][SLOT["a"]][2] < 30, f"Left key 'a' should be red: {frames[-1][SLOT['a']]}"
    assert frames[-1][SLOT["num_5"]][2] > 180 and frames[-1][SLOT["num_5"]][0] < 30, f"Right key 'num_5' should be blue: {frames[-1][SLOT['num_5']]}"
    for ei in ALL_EDGE_INDICES:
        c = fake_kb.colors[ei]
        assert (c.red, c.green, c.blue) == (0, 0, 0), "Edge LED leaked on screen_ambilight when edge_brightness==0"

    # Switch back to static -> both workers must stop cleanly
    eng.effect_name = "static"
    time.sleep(0.2)
    assert not eng.audio_worker.is_running and not eng.screen_worker.is_running
    print("  -> Auto-lifecycle, 81-key audio/screen rendering, and edge zero-clamp verified.")


def test_ui_phase2_controls():
    print("=== TEST 4: Phase 2 Audio & Screen UI Controls ===")
    win = EverestStudioWindow()
    win.save_settings = lambda: None

    # Switch sidebar to Audio Equalizer
    for i in range(win.effects_list.count()):
        if win.effects_list.item(i).data(Qt.ItemDataRole.UserRole) == "audio_equalizer":
            win.effects_list.setCurrentRow(i)
            break
    assert win.engine.effect_name == "audio_equalizer"
    assert not win.audio_controls_widget.isHidden()
    assert win.screen_controls_widget.isHidden()
    win.audio_bass_btn.click()
    assert win.engine.audio_style == "bass_pulse"
    win.audio_bars_btn.click()
    assert win.engine.audio_style == "bars"

    # Switch sidebar to Screen Ambilight
    for i in range(win.effects_list.count()):
        if win.effects_list.item(i).data(Qt.ItemDataRole.UserRole) == "screen_ambilight":
            win.effects_list.setCurrentRow(i)
            break
    assert win.engine.effect_name == "screen_ambilight"
    assert not win.screen_controls_widget.isHidden()
    assert win.audio_controls_widget.isHidden()
    assert win.monitor_combo.count() >= 1
    win.screen_edges_btn.click()
    assert win.engine.screen_mode == "edges"
    win.screen_grid_btn.click()
    assert win.engine.screen_mode == "grid"

    # Stop workers cleanly before exit
    win.engine.effect_name = "static"
    win.engine.stop()
    print("  -> Phase 2 Audio Equalizer & Screen Ambilight GUI controls verified.")


if __name__ == "__main__":
    test_audio_fft_binning()
    test_screen_capture_worker_mapping_and_ema()
    test_engine_worker_lifecycle_and_rendering()
    test_ui_phase2_controls()
    print("ALL V3.0 PHASE 2 SYSTEM SYNC TESTS PASSED!")
    os._exit(0)
