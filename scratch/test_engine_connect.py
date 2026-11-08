import os
import sys
from PySide6.QtCore import QCoreApplication

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.lighting_engine import LightingEngineThread

app = QCoreApplication(sys.argv)
engine = LightingEngineThread()
connected, msg = engine.connect_openrgb()
print(f"Connection result: {connected}, {msg}")
print(f"switch_indices count: {len(engine.switch_indices)}")
print(f"edge_indices count: {len(engine.edge_indices)}")

