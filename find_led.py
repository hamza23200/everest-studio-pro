"""
Interactive LED Finder for Mountain Everest 60
Use this to find the exact hardware index of ANY stubborn or misbehaving LED (like '/ ?').

Controls:
  - Right Arrow / 'n' / Space: Advance to NEXT LED index
  - Left Arrow / 'p':           Go to PREVIOUS LED index
  - Number (e.g. '98<Enter>'):  Jump directly to index 98
  - 'q' / Esc:                  Exit
"""
import sys
from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

client = OpenRGBClient()
kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("Everest 60 not found. Check OpenRGB SDK Server.")
    sys.exit(1)

# Direct mode
for mode in kb.modes:
    if mode.name.lower() == "direct":
        try:
            kb.set_mode(mode)
        except Exception:
            pass
        break

OFF_COLOR = RGBColor(10, 0, 25)          # Faint purple for background
TARGET_COLOR = RGBColor(255, 255, 255)   # Bright white for selected LED
num_leds = len(kb.leds)

current_idx = 98

def show_index(idx):
    for i, led in enumerate(kb.leds):
        if i == idx:
            led.set_color(TARGET_COLOR, fast=True)
        else:
            led.set_color(OFF_COLOR, fast=True)
    kb.show()
    print(f"\r>>> CURRENT LED: [{idx:03d} / {num_leds-1}] Name: '{kb.leds[idx].name:25}' (Glows WHITE) <<<", end="", flush=True)

print(f"Loaded {num_leds} LEDs on {kb.name}.")
print("Starting interactive finder at index 98.")
print("Type an index number and press Enter to jump, or '+' / '-' to step, 'q' to quit:\n")

show_index(current_idx)

while True:
    try:
        cmd = input().strip().lower()
        if cmd in ('q', 'quit', 'exit'):
            break
        elif cmd in ('+', 'n', ''):
            current_idx = (current_idx + 1) % num_leds
        elif cmd in ('-', 'p'):
            current_idx = (current_idx - 1) % num_leds
        elif cmd.isdigit():
            val = int(cmd)
            if 0 <= val < num_leds:
                current_idx = val
            else:
                print(f"\nIndex out of range (0 - {num_leds - 1})")
        else:
            print("\nEnter a number, '+' (next), '-' (prev), or 'q' (quit)")
        
        show_index(current_idx)
    except (KeyboardInterrupt, EOFError):
        break

# Restore
for led in kb.leds:
    led.set_color(OFF_COLOR, fast=True)
kb.show()
print("\nDone.")

