# Everest Studio Pro

[![Release](https://img.shields.io/github/v/release/hamza23200/everest-studio-pro?color=blue)](https://github.com/hamza23200/everest-studio-pro/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue?logo=windows)](https://github.com/hamza23200/everest-studio-pro)
[![License](https://img.shields.io/badge/License-GPLv3-green)](LICENSE)

**Production-Grade Base Camp Replacement & Lighting Suite for Mountain Everest 60**

Built with **PySide6**, **openrgb-python**, and **pynput**. Faithfully replicates Mountain's official Base Camp dark slate aesthetic while providing high-performance, lag-free reactive and continuous lighting animations.

<img width="1843" height="1258" alt="image" src="https://github.com/user-attachments/assets/d61164a5-709f-400a-90dd-82c3adebd6e0" />


---

## Architecture Overview

```
Mountain Everest 60 Project Root
├── engine/
│   ├── matrix.py             # 2D physical coordinates (15x5u) & full Windows OEM VK maps
│   ├── effects.py            # Mathematical lighting algorithms (Wave, Tornado, Rain, Laser, etc.)
│   └── lighting_engine.py    # Dedicated 35 FPS QThread, socket manager, and pynput hooks
├── gui/
│   ├── keyboard_canvas.py    # QPainter 2D hardware-accelerated keyboard visualizer
│   ├── color_picker.py       # Base Camp custom color deck (2D SV, Hue, HEX, RGB, Swatches)
│   └── main_window.py        # Master window (Rail, Effects list, Stage, Sliders, Tray)
├── main.py                   # PySide6 lifecycle, single-instance lock, auto-daemon spawn
├── requirements.txt          # PySide6, openrgb-python, pynput, pyinstaller
└── build_exe.bat             # One-click standalone executable builder
```

---

## Hardware & Driver Specifications

- **Target Hardware**: Mountain Everest 60 (VID: `0x3282`, PID: `0x0005`).
- **LED Channels**: 147 Total LEDs (64 keyboard switches, 44 perimeter underglow diffusers, 39 modular numpad virtual headers).
- **Driver**: OpenRGB SDK Server (`127.0.0.1:6742`) running in Direct Mode.
- **Critical Verified Matrix Overrides**:
  - `/ ?` (Forward Slash / Question Mark): OpenRGB Index `99` (`key: /`) & Virtual Key Code `191` (`OEM_2`).
  - `Right Shift`: Index `98` (`key: right shift`, 1.0u key).
  - `Delete`: Index `100` (`key: delete`, dedicated 60% nav key).
  - `Up Arrow`: Index `101` (`key: up arrow`).
  - `Right Alt`: Index `113` (`key: right alt`, captured on Windows as `Key.alt_gr` / `Key.alt_r`).
  - `Perimeter Edge Diffusers`: 44 zone LEDs around the chassis perimeter.

---

## Lighting Effects

1. **Color Wave (Continuous)**:
   - 2D vector projection: Right, Left, Down, Up, Diagonal.
   - Modes: Rainbow, Dual Color, Single Color.
2. **Tornado (Rotating Spiral Wave)**:
   - Polar spiral mathematics centered on keyboard middle ($cx=7.25, cy=2.0$).
   - Clockwise and counter-clockwise options.
3. **Breathing & Pulse**:
   - Sinusoidal wave with quadratic decay curve ($intensity = factor^{1.8}$) for natural LED fade.
4. **Snappy Aula Laser**:
   - 5-channel row overwrite state machine (`active_rows[row] = (origin_x, t0)`).
   - $v = 75.0$ keys/sec with defined soft crest and exponential afterglow. Zero multi-tap stacking lag.
5. **Falling Matrix Code (Rain)**:
   - 15 independent randomized column streams with bright neon green/white sparks and dark matrix green tails.
6. **Expanding Ripple**:
   - Concentric circular wavefronts expanding outward from keypress location.
7. **Single-Key Reactive (Punch)**:
   - Instant 100% flare on key strike with linear decay.
8. **Custom Per-Key**:
   - Interactive visualizer selection: click individual keys or "Select All" to paint custom palettes.
9. **Static & Off**:
   - Pure color with master brightness scaling, or instant dark mode.

---

## Installation & Running

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 2. Launch Everest Studio Pro
```powershell
python main.py
```
*Note: If OpenRGB is not running, Everest Studio Pro will automatically attempt to launch `OpenRGB.exe --server --headless` in the background with no console window.*

---

## Building Standalone `.exe`

Run the included batch script:
```powershell
.\build_exe.bat
```
Or execute PyInstaller directly:
```powershell
pyinstaller --noconsole --onefile --name "EverestStudio" --clean main.py
```
The resulting executable will be generated at `dist/EverestStudio.exe`.
