import time
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor
from pynput import keyboard

client = OpenRGBClient()
kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("Everest 60 not found. Check OpenRGB SDK Server.")
    exit(1)

# Ensure Direct mode
for mode in kb.modes:
    if mode.name.lower() == "direct":
        try:
            kb.set_mode(mode)
        except Exception:
            pass
        break

# Print zone information
print("=" * 60)
print(f"Device: {kb.name} | Total LEDs: {len(kb.leds)} | Total Zones: {len(kb.zones)}")
for z_idx, zone in enumerate(kb.zones):
    print(f"  Zone {z_idx}: '{zone.name}' ({zone.type.name}) - {len(zone.leds)} LEDs")
print("=" * 60)

# Paint entire board purple
PURPLE = RGBColor(15, 0, 40)
for led in kb.leds:
    led.set_color(PURPLE, fast=True)
kb.show()

# Color palette for Row 4 inspection
test_leds = [
    (96, "Index 96 (Red)",     RGBColor(255, 0, 0)),
    (97, "Index 97 (Green)",   RGBColor(0, 255, 0)),
    (98, "Index 98 (Cyan)",    RGBColor(0, 255, 255)),
    (99, "Index 99 (Yellow)",  RGBColor(255, 255, 0)),
    (100, "Index 100 (Magenta)", RGBColor(255, 0, 255)),
    (101, "Index 101 (Orange)",  RGBColor(255, 128, 0)),
    (102, "Index 102 (White)",   RGBColor(255, 255, 255)),
]

print("\n--- Row 4 Physical LED Test ---")
for idx, label, col in test_leds:
    if idx < len(kb.leds):
        actual_name = kb.leds[idx].name
        kb.leds[idx].set_color(col, fast=True)
        print(f"  LED [{idx:03d}] OpenRGB Name: '{actual_name:22}' -> {label}")
kb.show()

print("\n" + "=" * 60)
print("LOOK AT YOUR KEYBOARD RIGHT NOW:")
print("Check your physical keys from '< ,', '> .', '? /', '↑', 'Shift', 'Del':")
print("  - Red (96)      -> which physical key?")
print("  - Green (97)    -> which physical key?")
print("  - Cyan (98)     -> which physical key?")
print("  - Yellow (99)   -> which physical key?")
print("  - Magenta (100) -> which physical key?")
print("  - Orange (101)  -> which physical key?")
print("  - White (102)   -> which physical key?")
print("=" * 60)

print("\n--- Key Logger Active (Press /, ?, Right Alt, or any key. Press ESC to stop) ---")

def on_press(key):
    try:
        key_name = str(key)
        char_val = getattr(key, 'char', None)
        vk_val = getattr(key, 'vk', None)
        print(f"Captured: {key_name:20} | char: {repr(char_val):6} | vk: {vk_val}")
        if key == keyboard.Key.esc:
            return False
    except Exception as e:
        print(f"Error: {e}")

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()

for led in kb.leds:
    led.set_color(PURPLE, fast=True)
kb.show()
print("Restored base purple.")

