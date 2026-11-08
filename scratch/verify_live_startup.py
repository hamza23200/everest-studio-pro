"""
Verify live startup of main.py and MainWindow without blocking indefinitely.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import main

def verify_live():
    print("=== TESTING LIVE STARTUP FROM main.py ===")
    app = QApplication.instance() or QApplication(sys.argv)

    window = main.MainWindow()
    window.show()

    # Process events to allow Qt to layout and initialize
    app.processEvents()

    print(f"Active Effect: {window.engine.effect_name}")
    print(f"Color A: ({window.engine.color_a.red}, {window.engine.color_a.green}, {window.engine.color_a.blue})")
    print(f"Color B: ({window.engine.color_b.red}, {window.engine.color_b.green}, {window.engine.color_b.blue})")
    print(f"Brightness: {window.engine.brightness}")
    print(f"Canvas Switch Colors count: {len(window.canvas.switch_colors)}")
    print(f"Key 3 (slot 3) visualizer color: {window.canvas.switch_colors[3]}")
    print(f"Spacebar (slot 58) visualizer color: {window.canvas.switch_colors[58]}")

    # Render a frame
    window.engine._render_static_frame(0)
    app.processEvents()

    print(f"After static frame render -> Key 3 visualizer color: {window.canvas.switch_colors[3]}")
    print(f"After static frame render -> Spacebar visualizer color: {window.canvas.switch_colors[58]}")

    assert window.canvas.switch_colors[3] == (255, 255, 0), "Key 3 visualizer is not yellow!"
    assert window.canvas.switch_colors[58] == (255, 255, 0), "Spacebar visualizer is not yellow!"
    assert all(c == (255, 255, 0) for c in window.canvas.switch_colors), "Not all visualizer keys are yellow!"

    if window.engine.kb:
        print(f"Hardware Key 3 LED 27: ({window.engine.kb.colors[27].red}, {window.engine.kb.colors[27].green}, {window.engine.kb.colors[27].blue})")
        print(f"Hardware Spacebar LED 112: ({window.engine.kb.colors[112].red}, {window.engine.kb.colors[112].green}, {window.engine.kb.colors[112].blue})")
        assert window.engine.kb.colors[27].red == 255 and window.engine.kb.colors[27].green == 255
        assert window.engine.kb.colors[112].red == 255 and window.engine.kb.colors[112].green == 255

    print("✓ Live startup verification passed successfully!")
    window.close()

if __name__ == "__main__":
    verify_live()

