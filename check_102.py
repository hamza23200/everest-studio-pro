from openrgb import OpenRGBClient
from openrgb.utils import RGBColor

client = OpenRGBClient()
kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("Everest 60 not found. Check OpenRGB SDK Server.")
    exit(1)

# Ensure Direct mode so hardware respects SDK colors
for mode in kb.modes:
    if mode.name.lower() == "direct":
        try:
            kb.set_mode(mode)
        except Exception:
            pass
        break

# Paint entire board dim purple
BASE_COLOR = RGBColor(15, 0, 40)
for led in kb.leds:
    led.set_color(BASE_COLOR, fast=True)

# Target candidates around the cluster
kb.leds[98].set_color(RGBColor(0, 255, 255), fast=True)   # Cyan
kb.leds[99].set_color(RGBColor(255, 255, 0), fast=True)   # Yellow
kb.leds[100].set_color(RGBColor(255, 0, 255), fast=True)  # Magenta
kb.leds[101].set_color(RGBColor(255, 128, 0), fast=True)  # Orange
kb.leds[102].set_color(RGBColor(0, 255, 0), fast=True)    # NEON GREEN
kb.show()

print("\n" + "=" * 60)
print(" PHYSICAL INSPECTION RESULTS:")
print(f"  [98]  Name: '{kb.leds[98].name:20}' -> Cyan")
print(f"  [99]  Name: '{kb.leds[99].name:20}' -> Yellow")
print(f"  [100] Name: '{kb.leds[100].name:20}' -> Magenta")
print(f"  [101] Name: '{kb.leds[101].name:20}' -> Orange")
print(f"  [102] Name: '{kb.leds[102].name:20}' -> NEON GREEN")
print("=" * 60)
print("Look at your physical '/ ?' key:")
print("  - If it is NEON GREEN:  Index 102 is the physical '/ ?' key.")
print("  - If it is YELLOW:      Index 99 is the physical '/ ?' key.")
print("  - If it is CYAN:        Index 98 is the physical '/ ?' key.")
print("  - If it is MAGENTA:     Index 100 is the physical '/ ?' key.")
print("  - If it is ORANGE:      Index 101 is the physical '/ ?' key.")
print("  - If it is STILL PURPLE or OFF: The key is at a different index.")
print("=" * 60 + "\n")

