import sys
import os
import subprocess
import socket
import time

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


def ensure_openrgb():
    """Silently spawns OpenRGB SDK server if not currently active."""
    if is_port_open(6742):
        return True

    base_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

    candidates = [
        os.path.join(base_dir, OPENRGB_EXE),
        os.path.join(base_dir, "dist", OPENRGB_EXE),
        os.path.join(os.getcwd(), OPENRGB_EXE),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "OpenRGB", OPENRGB_EXE),
        os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "OpenRGB", OPENRGB_EXE),
        os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "OpenRGB", OPENRGB_EXE),
        os.path.join("C:\\OpenRGB", OPENRGB_EXE),
    ]
    target = next((p for p in candidates if os.path.exists(p)), None)

    if not target:
        import shutil
        target = shutil.which(OPENRGB_EXE) or shutil.which("OpenRGB")

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
