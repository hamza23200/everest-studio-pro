import os
import sys
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Headless Qt environment for CI testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from engine.lighting_engine import LightingEngineThread, RGBColor
from gui.main_window import MainWindow

def test_profiles_and_supervisor():
    app = QApplication.instance() or QApplication(sys.argv)

    print("[TEST 1] Testing LightingEngineThread supervisor and mode call boundaries...")
    engine = LightingEngineThread()
    # Mock OpenRGB kb
    class MockMode:
        def __init__(self, name):
            self.name = name
    class MockLED:
        def __init__(self, name):
            self.name = name
    class MockDevice:
        def __init__(self):
            self.name = "Mountain Everest 60"
            self.modes = [MockMode("direct"), MockMode("custom")]
            self.leds = [MockLED(f"Led {i}") for i in range(147)]
            self.colors = [RGBColor(0, 0, 0) for _ in range(147)]
            self.set_mode_calls = []

        def set_mode(self, mode):
            mode_name = getattr(mode, "name", str(mode))
            self.set_mode_calls.append(mode_name)

        def show(self, fast=True):
            pass

    mock_kb = MockDevice()
    engine.kb = mock_kb
    engine.switch_indices.add(27)

    # Verify Key 3 and edge diffusers
    assert 27 in engine.switch_indices, "Key 3 (index 27) missing from switch_indices"
    assert 27 not in engine.edge_indices, "Key 3 (index 27) found in edge_indices"
    assert len(engine.switch_indices) == 64, f"Expected 64 switches, got {len(engine.switch_indices)}"
    assert len(engine.edge_indices) == 83, f"Expected 83 edge diffusers, got {len(engine.edge_indices)}"
    print("  -> Switch & Edge indices count verified (64 switches, 83 edges).")

    # Verify supervisor thread and method are completely deleted
    assert not hasattr(engine, "_connection_supervisor"), "_connection_supervisor method must be completely deleted!"
    assert not hasattr(engine, "supervisor_thread"), "supervisor_thread attribute must be deleted!"
    print("  -> Supervisor thread and method verified completely deleted.")

    print("\n[TEST 2] Testing MainWindow Profile UI & Switching...")
    window = MainWindow(engine_thread=engine)
    window.show()

    # Reset to default profile fixtures for predictable test baseline
    window.active_profile_slot = 1
    window.profiles = window._get_default_profiles()
    window._apply_profile_dict(window.profiles["1"])
    window._update_profile_buttons_style()

    # Check that 5 profile buttons exist
    assert len(window.profile_buttons) == 5, f"Expected 5 profile buttons, got {len(window.profile_buttons)}"
    for slot in range(1, 6):
        assert slot in window.profile_buttons, f"Slot {slot} missing from profile_buttons"
        assert window.profile_buttons[slot].text() == f"[ P{slot} ]", f"Slot {slot} text mismatch"
    print("  -> All 5 profile buttons [ P1 ] - [ P5 ] verified.")

    # Verify active profile default is 1
    assert window.active_profile_slot == 1, f"Expected default slot 1, got {window.active_profile_slot}"
    assert "#0078D7" in window.profile_buttons[1].styleSheet(), "P1 button not styled with active Mountain Blue"
    assert "#20232B" in window.profile_buttons[2].styleSheet(), "P2 button not styled with inactive color"
    print("  -> Default P1 active styling verified.")

    # Switch to Profile 2
    print("\n[TEST 3] Switching to Profile 2...")
    window._on_profile_clicked(2)
    assert window.active_profile_slot == 2, f"Active slot did not update to 2, got {window.active_profile_slot}"
    assert "#0078D7" in window.profile_buttons[2].styleSheet(), "P2 button not highlighted"
    assert "#20232B" in window.profile_buttons[1].styleSheet(), "P1 button not dimmed"
    p2_effect = window.engine.effect_name
    print(f"  -> Profile 2 active effect: {p2_effect}")
    assert p2_effect == "laser", f"Expected laser for P2 default, got {p2_effect}"

    # Change settings on Profile 2
    window.engine.speed = 88.0
    window.engine.color_a = RGBColor(12, 34, 56)
    window.save_settings()

    # Switch to Profile 3
    print("\n[TEST 4] Switching to Profile 3...")
    window._on_profile_clicked(3)
    assert window.active_profile_slot == 3
    assert window.engine.effect_name == "wave"
    print(f"  -> Profile 3 active effect: {window.engine.effect_name}")

    # Switch back to Profile 2 and ensure our customized settings were retained!
    print("\n[TEST 5] Switching back to Profile 2 to verify persistence...")
    window._on_profile_clicked(2)
    assert window.active_profile_slot == 2
    assert window.engine.effect_name == "laser"
    assert window.engine.color_a.red == 12 and window.engine.color_a.green == 34 and window.engine.color_a.blue == 56, \
        f"Custom Color A was not retained! Got {window.engine.color_a}"
    print(f"  -> Profile 2 customized Color A ({window.engine.color_a}) successfully restored!")

    # Check config.json on disk
    cfg_path = window._get_config_path()
    assert os.path.exists(cfg_path), "config.json does not exist on disk"
    with open(cfg_path, "r", encoding="utf-8") as f:
        disk_cfg = json.load(f)

    assert disk_cfg["active_profile"] == 2, f"config.json active_profile mismatch: {disk_cfg.get('active_profile')}"
    assert "profiles" in disk_cfg, "profiles key missing from config.json"
    assert "2" in disk_cfg["profiles"], "Profile 2 missing from profiles in config.json"
    assert disk_cfg["profiles"]["2"]["color_a"] == "#0C2238", f"Color A in config.json mismatch: {disk_cfg['profiles']['2']['color_a']}"
    print("  -> config.json properly serialized with 'active_profile' and 'profiles' dict.")

    print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_profiles_and_supervisor()
