import sys, os, time, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from PySide6.QtCore import QCoreApplication
from openrgb.utils import RGBColor
from engine.lighting_engine import LightingEngine

app = QCoreApplication(sys.argv)
e = LightingEngine()
# Configure a visible non-black base color so we confirm LEDs light immediately without any keypress
e.effect_name = "static"
e.color_a = RGBColor(0, 120, 215)
e.base_brightness = 50.0
e.underglow_mode = "sync"
e.underglow_brightness = 40

events = []
e.connection_changed.connect(lambda ok, m: events.append(ok))
print("connect:", e.connect_openrgb(), flush=True)
old_client = e.client
e.force_hardware_sync(reset_usb=False)
print("fresh client after sync:", e.client is not old_client, "| connected:", e.is_connected, "| events:", events, flush=True)
kb = e.kb
non_black = sum(1 for c in kb.colors if (c.red, c.green, c.blue) != (0, 0, 0))
print("mode:", kb.modes[kb.active_mode].name, "| LED count:", len(kb.colors), "| non-black LEDs:", non_black, flush=True)
assert e.client is not old_client, "Expected a fresh OpenRGBClient instance"
assert e.is_connected is True, "Expected connected after hard sync"
assert events == [True, False, True], f"Unexpected events: {events}"
assert kb.modes[kb.active_mode].name.lower() == "direct", "Expected Direct mode"
assert len(kb.colors) >= 147, "Expected >= 147 LEDs"
assert non_black > 0, "Expected immediate non-black LEDs pushed without any keypress"

n = subprocess.run(["tasklist", "/FI", "IMAGENAME eq OpenRGB.exe", "/NH"], capture_output=True, text=True).stdout.lower().count("openrgb.exe")
print("OpenRGB.exe instances:", n, flush=True)
assert n == 1, f"Expected exactly 1 OpenRGB.exe instance, got {n}"
print("PASS: Live hard sync & immediate frame push verified!")
os._exit(0)
