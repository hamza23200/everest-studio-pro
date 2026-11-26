import sys
import os
import shutil
import subprocess
import socket
import time
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QLockFile, QDir, QPointF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPainterPath

from engine.lighting_engine import LightingEngine
from engine.matrix import KeyboardMatrix
from gui.main_window import MainWindow


OPENRGB_EXE = "OpenRGB.exe"


def is_port_open(port=6742):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(('127.0.0.1', port)) == 0


def is_openrgb_running() -> bool:
    """True if OpenRGB.exe is already in the process list (prevents duplicate instances)."""
    if os.name != 'nt':
        return False
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {OPENRGB_EXE}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).stdout
        return OPENRGB_EXE.lower() in out.lower()
    except Exception:
        return False


def ensure_openrgb():
    """Spawns the OpenRGB SDK server only if neither the port nor the process already exists."""
    if is_port_open(6742):
        return True

    if is_openrgb_running():
        # Already running (possibly still starting its server): wait, never spawn a second one.
        for _ in range(15):
            time.sleep(0.4)
            if is_port_open(6742):
                return True
        print("[WARN] OpenRGB.exe is running but SDK port 6742 is closed; not spawning a duplicate.")
        return False

    is_frozen = getattr(sys, 'frozen', False)
    app_dir = (
        Path(sys.executable).resolve().parent
        if is_frozen
        else Path(__file__).resolve().parent
    )

    candidates = [
        app_dir / "OpenRGB" / OPENRGB_EXE,
        app_dir / OPENRGB_EXE,
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "OpenRGB" / OPENRGB_EXE,
        Path(os.environ.get("LOCALAPPDATA", "")) / "OpenRGB" / OPENRGB_EXE,
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "OpenRGB" / OPENRGB_EXE,
    ]
    target = next((str(p) for p in candidates if p.is_file()), None)

    if not target:
        target = shutil.which(OPENRGB_EXE) or shutil.which("OpenRGB")
    if not target and not is_frozen:
        dev_dist = app_dir / "dist" / OPENRGB_EXE
        if dev_dist.is_file():
            target = str(dev_dist)

    if target:
        info = subprocess.STARTUPINFO()
        info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        info.wShowWindow = subprocess.SW_HIDE
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        try:
            subprocess.Popen(
                [target, "--server", "--startminimized"],
                startupinfo=info,
                creationflags=creationflags
            )
            for _ in range(15):
                time.sleep(0.4)
                if is_port_open(6742):
                    return True
        except Exception as e:
            print(f"[WARN] Failed to spawn OpenRGB: {e}")
    return False


def create_app_icon():
    """Generates a sleek procedural app/tray icon for Everest Studio."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Base rounded tile
    path = QPainterPath()
    path.addRoundedRect(4.0, 4.0, 56.0, 56.0, 14.0, 14.0)
    painter.fillPath(path, QColor("#181A1F"))

    # Mountain Blue accent shape
    accent_path = QPainterPath()
    accent_path.moveTo(QPointF(16.0, 46.0))
    accent_path.lineTo(QPointF(32.0, 18.0))
    accent_path.lineTo(QPointF(48.0, 46.0))
    accent_path.lineTo(QPointF(38.0, 46.0))
    accent_path.lineTo(QPointF(32.0, 32.0))
    accent_path.lineTo(QPointF(26.0, 46.0))
    accent_path.closeSubpath()

    painter.fillPath(accent_path, QColor("#0078D7"))
    painter.end()

    return QIcon(pixmap)


def main():
    # Single instance check
    lock_path = os.path.join(QDir.tempPath(), "everest_studio_pro.lock")
    lock_file = QLockFile(lock_path)
    if not lock_file.tryLock(100):
        print("[INFO] Everest Studio is already running.")
        sys.exit(0)

    # Auto-spawn OpenRGB SDK server if needed
    ensure_openrgb()

    app = QApplication(sys.argv)
    app.setApplicationName("Everest Studio Pro")
    app.setQuitOnLastWindowClosed(False)

    app_icon = create_app_icon()
    app.setWindowIcon(app_icon)

    window = MainWindow()
    window.show()

    exit_code = app.exec()
    lock_file.unlock()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
