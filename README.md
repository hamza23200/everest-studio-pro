# Everest Studio Pro

[![Release](https://img.shields.io/badge/Release-v3.0-blue)](https://github.com/hamza23200/everest-studio-pro/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20(x64)-blue?logo=windows)](https://github.com/hamza23200/everest-studio-pro)
[![License](https://img.shields.io/badge/License-GPL--3.0-green)](LICENSE)

**Production-Grade Base Camp Replacement & Lighting Suite for the Mountain Everest 60 (147 LEDs)**

Built with **PySide6**, **openrgb-python**, **pynput**, **NumPy**, **PyAudioWPatch**, and **mss**. Replicates Mountain's dark slate Base Camp aesthetic with a 35 FPS single-thread OpenRGB hardware clock, modular numpad dock geometry, decoupled WASAPI Audio Equalizer and Screen Ambilight capture threads, per-effect 5-slot profiles, and one-click virtual USB recovery.

![Everest Studio Pro v3.0](assets/everest_v3_preview.png)

---

## Quick Start

### Option A — Standalone Windows `.exe` (Recommended, No Python Needed)

1. Download `EverestStudio-v3.0-win64.zip` from the [GitHub Releases](https://github.com/hamza23200/everest-studio-pro/releases/latest) page and extract it anywhere.
2. Download the Windows 64-bit portable `.zip` of **OpenRGB** from [https://openrgb.org/releases.html](https://openrgb.org/releases.html) and extract it into an `OpenRGB/` folder right next to `EverestStudio.exe`.
3. **First-time OpenRGB setup (Important):** Launch `OpenRGB\OpenRGB.exe` once, check **"Do not show this message again"** on the PawnIO/I2C warning dialog (if shown), verify `Initial Detection Delay` is set to `0` in Settings, and close OpenRGB.
4. Exit Mountain **Base Camp** completely (right-click its system tray icon → **Exit**, and disable it in Task Manager → **Startup apps**).
5. Run `EverestStudio.exe`. It will automatically launch OpenRGB silently in the background, generate a default `config.json` next to `EverestStudio.exe`, and switch the keyboard into Direct Mode.

### Option B — Run from Source (Python 3.11+)

```powershell
git clone https://github.com/hamza23200/everest-studio-pro.git
cd everest-studio-pro
pip install -r requirements.txt
```

Place the extracted portable `OpenRGB/` folder inside the project root (or install OpenRGB on your system `PATH`), then launch:

```powershell
python main.py
```

---

## Architecture Overview

```text
everest-studio-pro/
├── engine/
│   ├── matrix.py           # 147-LED mapping, 81 ordered switches, & Right/Left/Detached coords
│   ├── effects.py          # 25 procedural, reactive, audio FFT, & screen ambilight shaders
│   ├── audio_worker.py     # Decoupled Windows WASAPI loopback RFFT thread (15/20 bands)
│   ├── screen_worker.py    # Decoupled mss multi-monitor capture & EMA color smoother
│   └── lighting_engine.py  # 35 FPS QThread, Direct Mode USB recovery, & debounced pynput hook
├── gui/
│   ├── keyboard_canvas.py  # QPainter 2D 81-key visualizer + 66-diffuser underglow halo
│   ├── color_picker.py     # Base Camp color deck (SV plane, Hue slider, RGB/HEX, swatches)
│   └── main_window.py      # Categorized scrollable sidebar, sliders, profiles P1-P5, & tray
├── assets/                 # Preview imagery
├── main.py                 # Single-instance lock, portable OpenRGB bootstrap, & Qt entry
├── requirements.txt        # PySide6, openrgb-python, pynput, numpy, pyaudiowpatch, mss, pyinstaller
├── EverestStudio.spec      # PyInstaller spec bundling pyaudiowpatch, mss, and numpy DLLs
└── build_exe.bat           # One-click standalone executable builder
```

---

## Hardware & Driver Specifications

- **Target Hardware:** Mountain Everest 60 (`VID: 0x3282`, `PID: 0x0005`).
- **LED Topology (147 Total LEDs):**
  - **81 Mechanical Switches:** `64` main 60% switches + `17` modular numpad switches (dynamically supporting **Right Dock**, **Left Dock**, and **Detached** layouts).
  - **66 Perimeter Underglow Diffusers:** Independently driven with `Sync with Effect` (0.4 anti-burst dampening), `Static Custom Color`, `Off`, and strict `RGB(0, 0, 0)` clamping at `0%` edge brightness.
- **SDK Transport:** OpenRGB SDK Server (`127.0.0.1:6742`) in `Direct` mode on a single synchronized thread.
- **Verified Key Overrides:** `3` (Index `27`), `Spacebar` (Index `112`), `/ ?` (Index `99`), `Right Shift` (Index `98`), `Delete` (Index `100`), `Up Arrow` (Index `101`), `Right Alt` / `AltGr` (Index `113`), plus all 17 numpad virtual keycodes.

---

## 25 Lighting Effects

Every effect supports 5 independent preset slots (`[ P1 ]` – `[ P5 ]`) persisted in `config.json`.

### Ambient
1. **Color Wave** — 2D directional wave (`Right`, `Left`, `Down`, `Up`, `Diagonal`) in Rainbow, Dual, or Single mode.
2. **Waterfall** — Continuous downward liquid cascade with horizontal shimmer (`Dual Color` or `Multi-Tone Spectrum`).
3. **Aurora** — Northern Lights rendered with 3 overlapping low-frequency 2D sine waves.
4. **Breathing & Pulse** — Smooth global breathing using an ocular quadratic curve (`factor ** 1.8`).
5. **Gradient Breathing** — Dual-color horizontal gradient breathing down to a configurable minimum brightness floor.
6. **Cosmic Drift** — Slowly drifting deep nebula gradient with twinkling white star particles.
7. **Thunderstorm** — Stormy midnight-blue base with localized flickering lightning clusters and perimeter-synced thunderclaps.
8. **System Malfunction** — Cyberpunk dual-color theme with brief randomized horizontal row glitch flickers.

### Dynamic FX
9. **Tornado** — Aspect-normalized polar spiral centered on the active dock midpoint (`Clockwise` / `Counter-Clockwise`).
10. **DNA Spiral** — 180°-offset double-helix arms radiating `Outward` or `Inward`.
11. **Row Sweep** — Serpentine left-to-right glowing head sweeping sequentially down Rows `0..4`.
12. **Falling Matrix** — Per-column falling rain streams (`Matrix Classic`, `Dual Color`, or `Rainbow`).
13. **Meteor Shower** — Pool of `4–10` independent angled meteors with bright heads and decaying tails.

### Reactive *(Modifier-Filtered & 80ms Debounced)*
14. **Snappy Laser** — Row-locked horizontal laser beam firing across only the struck key's row.
15. **Expanding Ripple** — Concentric circular cosine-bell wavefronts radiating from keystrokes.
16. **Explosion Burst** — White-hot core flash (`< 80ms`), radial shockwave, and flickering ember sparks.
17. **Crosshair** — Simultaneous horizontal row and vertical column propagating beams.
18. **Full-Board Flash** — Unified board-wide envelope pulse that smoothly re-energizes on rapid typing.
19. **Single-Key Punch** — Instant key-strike flare with linear decay back to base brightness.
20. **Typing Heatmap** — Per-key thermal gradient (`Blue -> Cyan -> Yellow -> Red -> White`) with **Live Decay**, **Session Persistent**, and **Reset Heatmap** controls.

### System Sync *(Auto-Lifecycle Daemon Threads — 0% Idle CPU When Inactive)*
21. **Audio Equalizer** — Live Windows WASAPI loopback capture via `pyaudiowpatch` + Hann-windowed NumPy `rfft` binned into `15` (detached) or `20` (docked) logarithmic bands. Includes `Spectrum Bars` and `Bass Pulse` modes, **Sensitivity / Gain**, **Smoothing**, and auto-recovery on audio device switch.
22. **Screen Ambilight** — Real-time `mss` monitor capture (~22 FPS) downsampled via strided NumPy slicing into a `5x20` key grid and 4 monitor-edge perimeter strips, with **Full Screen Grid** / **Monitor Edges Only**, **Monitor** selector, **Temporal Smoothing**, and **Saturation Boost**.

### Static & Custom
23. **Static Color** — Clean uniform color with independent edge diffuser control.
24. **Custom Per-Key** — Interactive paint/erase brush directly on the 2D visualizer (`Fill All` / `Clear All`).
25. **Lighting Off** — Instant blackout across all switches and underglow LEDs.

---

## Troubleshooting & Cold-Boot Sync

- **Conflicts with Mountain Base Camp:** Base Camp and OpenRGB cannot share the Everest 60 HID endpoint (`VID 0x3282`, `PID 0x0005`). Fully quit Base Camp and disable its startup entry before running Everest Studio Pro.
- **Cold-Boot Hardware Sleep & `[ 🔄 SYNC ]` Button:** If Windows leaves the Everest 60 asleep after a cold boot or sleep cycle, click **`🔄 SYNC`** in the top-right header. It kills `OpenRGB.exe`, performs a virtual USB interface restart (`pnputil /restart-device` on `USB\VID_3282&PID_0005&MI_*`), respawns OpenRGB cleanly, re-asserts Direct Mode, and pushes a full 147-LED frame.
  - Because `pnputil` requires administrator privileges, running as a standard user prompts UAC once when clicking **`🔄 SYNC`**.
  - For completely hands-free cold boots with zero UAC prompts, launch `EverestStudio.exe` at logon via a **Windows Task Scheduler** task configured with **"Run with highest privileges"**.
- **OpenRGB Not Found / Offline Mode:** Ensure `OpenRGB.exe` resides in `<app_dir>\OpenRGB\OpenRGB.exe` (or `<app_dir>\OpenRGB.exe` or `PATH`). While disconnected, the 2D on-screen visualizer continues animating at 35 FPS and the status badge accurately shows `OFFLINE / SIMULATOR`.

---

## Building Standalone `.exe`

Run the included build script from the repository root:

```powershell
.\build_exe.bat
```

Or invoke PyInstaller directly with the tracked `.spec` file (required so `pyaudiowpatch`, `mss`, and `numpy` DLLs are bundled):

```powershell
pyinstaller EverestStudio.spec --noconfirm --clean
```

The standalone executable is generated at `dist\EverestStudio.exe`.
