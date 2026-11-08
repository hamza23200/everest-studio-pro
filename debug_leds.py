"""
Helper script to inspect the Mountain Everest 60's LED names and indices in OpenRGB.
Make sure OpenRGB is running with the SDK Server enabled (Settings -> Start Server).
"""
import sys
from openrgb import OpenRGBClient

def main():
    try:
        client = OpenRGBClient()
    except Exception as e:
        print(f"Error connecting to OpenRGB SDK: {e}")
        print("Please verify that OpenRGB is running and the SDK Server is enabled.")
        sys.exit(1)

    kb = None
    for device in client.devices:
        if "Mountain Everest" in device.name or "Everest 60" in device.name:
            kb = device
            break

    if not kb:
        print("Mountain Everest 60 not found! Detected devices:")
        for idx, dev in enumerate(client.devices):
            print(f"  [{idx}] {dev.name} ({dev.type})")
        sys.exit(1)

    print(f"Found Device: {kb.name} (Type: {kb.type})")
    print(f"Total LEDs: {len(kb.leds)}")
    print("=" * 50)
    for i, led in enumerate(kb.leds):
        print(f"  LED {i:02d}: '{led.name}'")
    print("=" * 50)

if __name__ == "__main__":
    main()

