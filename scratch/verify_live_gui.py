import sys, time, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

app = QApplication(sys.argv)
w = MainWindow()
w.show()
w.engine.effect_name = "laser"
t = time.time()
while time.time() - t < 6.0:
    app.processEvents()
    time.sleep(0.02)
    if int((time.time() - t) * 10) == 30:
        w.engine.trigger_switch(73)
sc = w.canvas.switch_colors
print("canvas len", len(sc), "nonblack", sum(1 for c in sc if c != (0, 0, 0)),
      "stuck-default", sum(1 for c in sc if c == (15, 0, 40)), "sample", sc[0], sc[40], flush=True)
print("badge:", w.status_badge.text().strip(), "| engine.is_connected:", w.engine.is_connected, flush=True)
os._exit(0)

