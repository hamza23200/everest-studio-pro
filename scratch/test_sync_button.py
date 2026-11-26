import os
import sys
import time
import ctypes
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import engine.lighting_engine as le
from engine.lighting_engine import LightingEngineThread
from gui.main_window import EverestStudioWindow


def test_reset_everest_usb_branches():
    print("--- Subtest 1: _reset_everest_usb elevated vs non-elevated ---")
    eng = LightingEngineThread()
    expected_ps = (
        "Get-PnpDevice -PresentOnly | "
        "Where-Object { $_.InstanceId -like 'USB\\VID_3282&PID_0005&MI_*' } | "
        "ForEach-Object { pnputil /restart-device $_.InstanceId }"
    )

    # Branch A: Elevated (IsUserAnAdmin == 1)
    with patch.object(ctypes.windll.shell32, "IsUserAnAdmin", return_value=1), \
         patch.object(le.subprocess, "run") as mock_run:
        eng._reset_everest_usb()
        assert mock_run.call_count == 1, "Elevated reset must call subprocess.run once"
        cmd_args = mock_run.call_args[0][0]
        assert cmd_args[0] == "powershell.exe"
        assert "-NoProfile" in cmd_args and "-WindowStyle" in cmd_args and "Hidden" in cmd_args
        assert expected_ps in cmd_args, f"Unexpected ps_cmd: {cmd_args}"

    # Branch B: Non-Elevated (IsUserAnAdmin == 0)
    with patch.object(ctypes.windll.shell32, "IsUserAnAdmin", return_value=0), \
         patch.object(ctypes.windll.shell32, "ShellExecuteW", return_value=42) as mock_shell, \
         patch.object(le.time, "sleep") as mock_sleep:
        eng._reset_everest_usb()
        assert mock_shell.call_count == 1, "Non-elevated reset must call ShellExecuteW once"
        args = mock_shell.call_args[0]
        assert args[1] == "runas"
        assert args[2] == "powershell.exe"
        assert expected_ps in args[3]
        assert args[5] == 0
        mock_sleep.assert_any_call(2.0)

    print("  -> Elevated & non-elevated _reset_everest_usb branches verified.")


def test_force_hardware_sync_order():
    print("--- Subtest 2: force_hardware_sync strict step order ---")
    eng = LightingEngineThread()
    steps = []
    events = []
    eng.connection_changed.connect(lambda ok, msg: (events.append(ok), steps.append(("emit", ok))))

    def fake_run(cmd, **kwargs):
        if cmd and cmd[0] == "taskkill":
            steps.append("taskkill")
        return MagicMock(returncode=0)

    def fake_reset_usb():
        steps.append("reset_usb")

    def fake_spawn(wait_seconds=8.0):
        steps.append(("spawn", wait_seconds))
        return True

    def fake_connect(silent=False, attempts=6, emit_connected=True):
        steps.append(("connect", attempts, emit_connected))
        eng._is_connected = True
        eng.kb = MagicMock()
        eng.client = MagicMock()
        if emit_connected:
            eng._emit_connection_status(True, "CONNECTED")
        return True, "CONNECTED"

    def fake_push():
        steps.append("push_full_frame")

    with patch.object(le.subprocess, "run", side_effect=fake_run), \
         patch.object(eng, "_reset_everest_usb", side_effect=fake_reset_usb), \
         patch.object(le, "spawn_openrgb_server", side_effect=fake_spawn), \
         patch.object(eng, "connect_openrgb", side_effect=fake_connect), \
         patch.object(eng, "_push_full_frame", side_effect=fake_push), \
         patch.object(LightingEngineThread, "is_connected", new_callable=lambda: property(lambda self: self._is_connected)), \
         patch.object(le.time, "sleep"):

        eng.force_hardware_sync(reset_usb=True)

        assert steps[0] == ("emit", False), f"Expected emit False first, got {steps}"
        idx_taskkill = steps.index("taskkill")
        idx_reset = steps.index("reset_usb")
        idx_spawn = steps.index(("spawn", 8.0))
        idx_connect = steps.index(("connect", 3, False))
        idx_push = steps.index("push_full_frame")
        idx_emit_true = steps.index(("emit", True))

        assert idx_taskkill < idx_reset, "taskkill MUST run before _reset_everest_usb"
        assert idx_reset < idx_spawn, "_reset_everest_usb MUST run before spawn_openrgb_server"
        assert idx_spawn < idx_connect, "spawn_openrgb_server MUST run before connect_openrgb"
        assert idx_connect < idx_push, "connect_openrgb MUST run before _push_full_frame"
        assert idx_push < idx_emit_true, "_push_full_frame MUST run before connection_changed(True)"
        assert events == [False, True], f"Expected [False, True], got {events}"

        # Now test reset_usb=False skips _reset_everest_usb
        steps.clear()
        events.clear()
        eng.force_hardware_sync(reset_usb=False)
        assert "reset_usb" not in steps, f"reset_usb=False must skip _reset_everest_usb: {steps}"
        assert "taskkill" in steps and "push_full_frame" in steps

    print("  -> Strict step ordering verified for reset_usb=True and reset_usb=False.")


def test_sync_ui_button():
    print("--- Subtest 3: UI SYNC button state transitions & threading ---")
    app = QApplication.instance() or QApplication(sys.argv)
    window = EverestStudioWindow()
    engine = window.engine

    assert hasattr(window, "sync_btn"), "sync_btn must exist on EverestStudioWindow"
    assert hasattr(window, "sync_button"), "sync_button alias must exist on EverestStudioWindow"
    assert window.sync_btn.text() == "🔄 SYNC", f"Expected text '🔄 SYNC', got {window.sync_btn.text()}"

    calls = []
    in_progress_states = []

    def mock_sync(reset_usb=True):
        in_progress_states.append((window.sync_btn.isEnabled(), window.sync_btn.text()))
        calls.append(reset_usb)
        time.sleep(0.1)

    original_sync = engine.force_hardware_sync
    try:
        engine.force_hardware_sync = mock_sync
        window.sync_btn.click()

        # Immediately after click, button must be disabled with '⏳ SYNCING...'
        assert not window.sync_btn.isEnabled(), "sync_btn should be disabled while syncing"
        assert window.sync_btn.text() == "⏳ SYNCING...", f"Got text {window.sync_btn.text()}"

        deadline = time.time() + 3.0
        while time.time() < deadline and not window.sync_btn.isEnabled():
            app.processEvents()
            time.sleep(0.02)

        assert calls == [True], f"Expected force_hardware_sync(reset_usb=True), got {calls}"
        assert window.sync_btn.isEnabled(), "sync_btn should be re-enabled after completion"
        assert window.sync_btn.text() == "🔄 SYNC", f"Got text {window.sync_btn.text()}"
    finally:
        engine.force_hardware_sync = original_sync

    print("  -> UI SYNC button state transitions & background thread verified.")


if __name__ == "__main__":
    print("=== TEST: Manual Hardware Sync Button & Virtual USB Reset ===")
    test_reset_everest_usb_branches()
    test_force_hardware_sync_order()
    test_sync_ui_button()
    print("PASS: Manual Hardware Sync button verified successfully.")
    os._exit(0)
