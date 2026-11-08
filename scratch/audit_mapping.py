import os
import sys
from openrgb import OpenRGBClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.matrix import KEY_DEFINITIONS, build_matrix_coords

client = OpenRGBClient()
kb = next((d for d in client.devices if "everest" in d.name.lower()), None)
if not kb:
    print("Everest keyboard not found via OpenRGB!")
    sys.exit(1)

name_to_index = {led.name.lower(): idx for idx, led in enumerate(kb.leds)}

coords, idx_to_slot = build_matrix_coords(name_to_index)

print(f"Total kb.leds: {len(kb.leds)}")
print(f"Total KEY_DEFINITIONS: {len(KEY_DEFINITIONS)}")
print(f"Total coords mapped: {len(coords)}")
print(f"Total idx_to_slot mapped: {len(idx_to_slot)}")

resolved_indices = []
for k in KEY_DEFINITIONS:
    idx = k.get("resolved_idx")
    name = k["name"]
    resolved_indices.append(idx)
    if k["slot"] < 28: # Row 0 and Row 1
        print(f"Slot {k['slot']:02d}: label='{k['label']}', name='{name}', resolved_idx={idx}, default_idx={k['default_idx']}, in name_to_index={'yes' if name.lower() in name_to_index else 'NO'}")

# Check for duplicates or missing in resolved_indices
from collections import Counter
counts = Counter(resolved_indices)
duplicates = {k: v for k, v in counts.items() if v > 1}
print(f"\nDuplicates in resolved_indices: {duplicates}")

switch_indices = set(resolved_indices)
print(f"Number of unique switch indices: {len(switch_indices)}")

# Check non-switch indices
all_indices = set(range(len(kb.leds)))
edge_indices = sorted(list(all_indices - switch_indices))
print(f"Number of non-switch (edge) indices: {len(edge_indices)}")

# Check LEDs 24 to 60 specifically (Row 0 and Row 1 area)
print("\n--- Physical LEDs 24 to 60 in OpenRGB ---")
for i in range(24, 60):
    is_switch = i in switch_indices
    print(f"LED {i:03d}: '{kb.leds[i].name}' -> {'SWITCH' if is_switch else 'EDGE/ACCENT'}")

