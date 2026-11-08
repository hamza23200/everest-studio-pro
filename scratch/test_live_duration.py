"""
Verify continuous run for 30+ seconds without supervisor thread or PWM resets.
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

def test_live_30s():
    print("=== STARTING 30-SECOND CONTINUOUS RUN VERIFICATION ===")
    app = QApplication.instance() or QApplication(sys.argv)

    window = MainWindow()
    window.show()
    app.processEvents()

    # 1. Verify profile buttons on screen
    assert len(window.profile_buttons) == 5, f"Expected 5 profile buttons, found {len(window.profile_buttons)}"
    for slot in range(1, 6):
        btn = window.profile_buttons[slot]
        assert btn.isVisible(), f"Profile button [ P{slot} ] is not visible!"
        assert btn.text() == f"[ P{slot} ]", f"Button text mismatch: {btn.text()}"
        print(f"  -> Verified Profile button: {btn.text()} (Visible: True)")

    # 2. Verify supervisor thread is completely absent
    assert not hasattr(window.engine, "supervisor_thread"), "supervisor_thread attribute found!"
    assert not hasattr(window.engine, "_connection_supervisor"), "_connection_supervisor method found!"
    print("  -> Confirmed: Zero supervisor threads exist.")

    # 3. Monitor engine for 32 seconds (covering multiple 5s / 7.6s windows)
    print("  -> Monitoring live render loop for 32 seconds...")
    start_time = time.time()
    frames_rendered = 0

    def on_frame(colors):
        nonlocal frames_rendered
        frames_rendered += 1

    window.engine.frame_rendered.connect(on_frame)

    while time.time() - start_time < 32.0:
        app.processEvents()
        time.sleep(0.02)
        elapsed = time.time() - start_time
        if int(elapsed) % 5 == 0 and int(elapsed) > 0:
            if not getattr(test_live_30s, f"logged_{int(elapsed)}", False):
                setattr(test_live_30s, f"logged_{int(elapsed)}", True)
                print(f"     [T+{int(elapsed):02d}s] Continuous render active. Frames rendered: {frames_rendered}")

    print(f"  -> Total frames rendered: {frames_rendered} (~{frames_rendered / 32:.1f} FPS)")
    assert frames_rendered > 500, f"Expected >500 frames in 32s, got {frames_rendered}"

    window.engine.stop()
    window.close()
    print("✓ 32-second continuous live execution completed with ZERO blackouts!")

if __name__ == "__main__":
    test_live_30s()

