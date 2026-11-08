import sys
import time
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

client = OpenRGBClient()
kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("Everest keyboard not found!")
    sys.exit(1)

# Set all 147 LEDs to BLACK first
for i in range(len(kb.colors)):
    kb.colors[i] = RGBColor(0, 0, 0)
kb.show(fast=True)
time.sleep(0.5)

print("Checking indices 24 to 37 (Row 0: ESC through BACKSPACE)...")
# Let's light up keys ESC, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0, -, =, BACKSPACE in RED
for idx in range(24, 38):
    kb.colors[idx] = RGBColor(255, 0, 0)
kb.show(fast=True)
time.sleep(2.0)

print("Checking indices 46 to 59 (Row 1: TAB through BACKSLASH)...")
# Let's light up Row 1 in GREEN
for idx in range(46, 60):
    kb.colors[idx] = RGBColor(0, 255, 0)
kb.show(fast=True)
time.sleep(2.0)

# Reset to black
for i in range(len(kb.colors)):
    kb.colors[i] = RGBColor(0, 0, 0)
kb.show(fast=True)
print("Done!")

