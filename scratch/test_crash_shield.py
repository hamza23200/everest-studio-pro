import os
import sys
import time
from openrgb.utils import RGBColor

# Ensure workspace root is in python path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from engine.lighting_engine import LightingEngineThread, calculate_laser_intensity
from engine.effects import EffectRenderer

def test_laser_crash_shield_and_edge_cases():
    print("=== TEST: Laser Crash Shield & Math Robustness ===")
    
    # 1. Test invalid / corrupted active_rows formats
    now = time.time()
    corrupted_active_rows = {
        "corrupted_key": (1.0,), # 1-tuple (invalid)
        2: (5.0, 2.5, now),      # valid 3-tuple
        "3": (3.0, now),         # valid 2-tuple string key
        4: ("invalid", "types"), # invalid data types
    }
    
    # Calculate intensity for key at (5.0, 2.5) -> should match Row 2 without crashing
    val = calculate_laser_intensity(5.0, 2.5, now + 0.01, corrupted_active_rows, 60.0, 0.5, 2.0)
    print(f"Intensity with corrupted active_rows: {val:.3f}")
    assert val > 0.0, "Valid Row 2 should still calculate intensity despite corrupt entries"

    # 2. Test EffectRenderer.render_laser with corrupted data
    color = EffectRenderer.render_laser(
        5.0, 2.5, now + 0.01, corrupted_active_rows, 60.0, 2.0, 0.5,
        "single", RGBColor(255, 0, 0), RGBColor(0, 0, 0), 1.0
    )
    print(f"Rendered color: RGB({color.red}, {color.green}, {color.blue})")
    assert color.red > 0, "Color should be illuminated red"

    # 3. Test LightingEngineThread render loop with active laser and keypresses
    engine = LightingEngineThread()
    engine.effect_name = "laser"
    engine.mode_type = "single"
    engine.color_a = RGBColor(255, 0, 0)
    engine.color_b = RGBColor(0, 0, 0)
    engine.laser_speed = 60.0
    engine.laser_decay = 0.5
    
    # Strike key 'G' (Index 73)
    engine.trigger_switch(73)
    
    # Execute 10 consecutive render loop steps
    frame_count = 0
    def on_frame(f):
        nonlocal frame_count
        frame_count += 1
    engine.frame_rendered.connect(on_frame)

    for i in range(10):
        engine._render_loop_step(time.time() + i * 0.02)
        
    print(f"Frames rendered successfully: {frame_count}")
    assert frame_count == 10, f"Expected 10 frames rendered, got {frame_count}"

    # 4. Inject an intentional exception into _compute_key_color to test crash shield
    original_compute = engine._compute_key_color
    def faulty_compute(*args, **kwargs):
        raise ValueError("Simulated math error for crash shield test")
    engine._compute_key_color = faulty_compute

    print("Triggering faulty render step (crash shield should catch and prevent termination)...")
    try:
        engine._render_loop_step(time.time())
        print("PASS: Crash shield successfully caught the exception without re-raising!")
    except Exception as e:
        assert False, f"Crash shield failed: exception escaped {e}"

    print("ALL CRASH SHIELD TESTS PASSED!")

if __name__ == "__main__":
    test_laser_crash_shield_and_edge_cases()
    os._exit(0)

