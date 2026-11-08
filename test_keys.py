import time
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
from pynput import keyboard

client = OpenRGBClient()
kb = next((d for d in client.devices if "everest" in d.name.lower()), None)

if not kb:
    print("Everest 60 not found. Is OpenRGB SDK Server running?")
    exit(1)

# Ensure device is in Direct mode
for mode in kb.modes:
    if mode.name.lower() == "direct":
        try:
            kb.set_mode(mode)
        except Exception:
            pass
        break

# 1. Force ALL LEDs to purple base
PURPLE = RGBColor(15, 0, 40)
CYAN   = RGBColor(0, 255, 255)
YELLOW = RGBColor(255, 255, 0)
GREEN  = RGBColor(0, 255, 0)
RED    = RGBColor(255, 0, 0)

for led in kb.leds:
    led.set_color(PURPLE, fast=True)
kb.show()
print(f"Reset all {len(kb.leds)} LEDs to purple.")

# 2. Map LED names to indices
name_to_index = {led.name.lower(): idx for idx, led in enumerate(kb.leds)}

idx_slash  = name_to_index.get("key: /")
idx_rshift = name_to_index.get("key: right shift")
idx_ralt   = name_to_index.get("key: right alt")

print(f"\n--- Looked up by name ---")
print(f"  'key: right alt'   -> Index: {idx_ralt}")
print(f"  'key: /'           -> Index: {idx_slash}")
print(f"  'key: right shift' -> Index: {idx_rshift}")

# Check what LEDs 98 and 99 actually are
print(f"\n--- Checking LED 98 & 99 in OpenRGB's LED list ---")
if 98 < len(kb.leds):
    print(f"  LED 98 Name: '{kb.leds[98].name}' -> Setting to CYAN")
    kb.leds[98].set_color(CYAN, fast=True)
if 99 < len(kb.leds):
    print(f"  LED 99 Name: '{kb.leds[99].name}' -> Setting to YELLOW")
    kb.leds[99].set_color(YELLOW, fast=True)

# Also check neighboring LEDs for context
print("\n--- Neighborhood around 95-102 ---")
for i in range(max(0, 95), min(len(kb.leds), 103)):
    print(f"  [{i:03d}]: '{kb.leds[i].name}'")

# Push colors to keyboard
kb.show()

print("\n" + "=" * 60)
print(" PHYSICAL HARDWARE CHECK:")
print(" - Which physical key is glowing CYAN   (LED 98)?")
print(" - Which physical key is glowing YELLOW (LED 99)?")
print("=" * 60)
print("\n--- Interactive Key Capture (Type keys, press ESC to stop) ---")

def on_press(key):
    info = []
    if hasattr(key, 'char') and key.char:
        info.append(f"char='{key.char}' (ord={ord(key.char)})")
    if hasattr(key, 'vk') and key.vk:
        info.append(f"vk={key.vk}")
    
    print(f"Captured: {key:25} | {', '.join(info)}")

    if key == keyboard.Key.esc:
        return False

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()

# Restore purple on exit
for led in kb.leds:
    led.set_color(PURPLE, fast=True)
kb.show()
print("\nRestored all LEDs to purple.")

