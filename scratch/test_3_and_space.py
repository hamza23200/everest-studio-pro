import sys
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

client = OpenRGBClient()
kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("No Everest device found")
    sys.exit(1)

print(f"LED 27 Name: {kb.leds[27].name}")
print(f"LED 112 Name: {kb.leds[112].name}")

# Set entire keyboard to BLACK
for i in range(len(kb.colors)):
    kb.colors[i] = RGBColor(0, 0, 0)

# Set LED 27 to Yellow
kb.colors[27] = RGBColor(255, 255, 0)

# Set LED 112 to Yellow
kb.colors[112] = RGBColor(255, 255, 0)

kb.show(fast=True)
print("Sent Yellow to LED 27 and LED 112!")

