"""
Everest Studio Pro - Master Window (Base Camp Replica & Upgrade).
Implements context-sensitive Dynamic Parameter Deck, full 44-LED Underglow
controls, Color A / Color B / Underglow active chip toggles, and zero-copy
35 FPS visualizer synchronization.
"""

import os
import sys
import json
from typing import Optional, Dict
import threading
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QFrame,
    QListWidget,
    QListWidgetItem,
    QButtonGroup,
    QRadioButton,
    QSystemTrayIcon,
    QMenu,
    QApplication
)
from openrgb.utils import RGBColor

from engine.lighting_engine import LightingEngineThread
from gui.keyboard_canvas import EverestKeyboardCanvas
from gui.color_picker import BaseCampColorPicker


def rgb_to_hex(c: RGBColor) -> str:
    """Formats OpenRGB RGBColor as uppercase 6-character hex string."""
    return f"#{c.red:02X}{c.green:02X}{c.blue:02X}"


def hex_to_rgb(hex_str: str, default: RGBColor) -> RGBColor:
    """Parses a hex color string (e.g. '#00FFFF' or '00FFFF') into an RGBColor."""
    try:
        s = hex_str.strip().lstrip("#")
        if len(s) == 6:
            r = int(s[0:2], 16)
            g = int(s[2:4], 16)
            b = int(s[4:6], 16)
            return RGBColor(r, g, b)
    except Exception:
        pass
    return default


class EverestStudioWindow(QMainWindow):
    """Mountain Base Camp Production Replica & Upgrade Suite."""

    PROFILE_BTN_INACTIVE_STYLE = (
        "QPushButton {"
        "  background-color: #20232B;"
        "  color: #E0E0E0;"
        "  border: 1px solid #2E323D;"
        "  border-radius: 4px;"
        "  font-size: 11px;"
        "  font-weight: bold;"
        "  padding: 4px 6px;"
        "}"
        "QPushButton:hover {"
        "  background-color: #282C37;"
        "  color: #FFFFFF;"
        "  border-color: #3D424E;"
        "}"
    )

    PROFILE_BTN_ACTIVE_STYLE = (
        "QPushButton {"
        "  background-color: #0078D7;"
        "  color: #FFFFFF;"
        "  border: 1px solid #0078D7;"
        "  border-radius: 4px;"
        "  font-size: 11px;"
        "  font-weight: bold;"
        "  padding: 4px 6px;"
        "}"
        "QPushButton:hover {"
        "  background-color: #1084E3;"
        "}"
    )

    def __init__(self, engine_thread: Optional[LightingEngineThread] = None):
        super().__init__()
        start_engine_after = False
        if engine_thread is None:
            self.engine = LightingEngineThread()
            start_engine_after = True
        else:
            self.engine = engine_thread

        self.setWindowTitle("Everest Studio Pro - Mountain Everest 60")
        self.resize(1220, 810)
        self.setMinimumSize(1060, 740)

        # Active color binding target ('color_a', 'color_b', or 'underglow')
        self.active_color_target = "color_a"
        self._suppress_slider_events = False
        self.active_profile_slot = 1
        self.profiles: Dict[str, dict] = {}
        self.profile_buttons: Dict[int, QPushButton] = {}

        self._apply_qss_stylesheet()
        self._build_ui()
        self._setup_tray_icon()
        self._wire_engine_signals()

        # Load persisted settings from config.json before starting lighting thread
        self.load_settings()

        # Trigger initial UI configuration for active effect
        self._reconfigure_deck_for_effect(self.engine.effect_name)
        self._refresh_color_chips()

        if start_engine_after:
            self.engine.start()

    def _apply_qss_stylesheet(self):
        """High-fidelity Mountain Base Camp Dark Slate stylesheet."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #181A1F;
            }
            QWidget {
                color: #FFFFFF;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            #left_rail {
                background-color: #131417;
                border-right: 1px solid #232731;
            }
            #effects_column {
                background-color: #181A1F;
                border-right: 1px solid #232731;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                height: 38px;
                padding-left: 14px;
                border-radius: 4px;
                margin: 2px 8px;
                color: #8A8F9D;
                font-size: 12px;
                font-weight: 500;
            }
            QListWidget::item:hover {
                background-color: #20232B;
                color: #FFFFFF;
            }
            QListWidget::item:selected {
                background-color: #20232B;
                color: #0078D7;
                font-weight: bold;
                border-left: 3px solid #0078D7;
            }
            .CardPanel {
                background-color: #20232B;
                border: 1px solid #2B2F3A;
                border-radius: 8px;
            }
            QSlider::groove:horizontal {
                height: 5px;
                background: #2B2F3A;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #0078D7;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
                background: #FFFFFF;
                border: 2px solid #0078D7;
            }
            QSlider::handle:horizontal:hover {
                background: #0078D7;
            }
            QRadioButton {
                color: #8A8F9D;
                font-size: 12px;
                font-weight: 600;
                spacing: 6px;
            }
            QRadioButton:checked {
                color: #FFFFFF;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 1px solid #3F4756;
                background-color: #181A1F;
            }
            QRadioButton::indicator:checked {
                background-color: #0078D7;
                border: 2px solid #FFFFFF;
            }
            QPushButton.ToolButton {
                background-color: #262A35;
                color: #D1D5DB;
                border: 1px solid #333947;
                border-radius: 4px;
                padding: 5px 12px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton.ToolButton:hover {
                background-color: #2D3342;
                border-color: #0078D7;
                color: #FFFFFF;
            }
            QPushButton.ToolButton:checked {
                background-color: #0078D7;
                border-color: #0078D7;
                color: #FFFFFF;
            }
        """)

    def _build_ui(self):
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root_layout = QHBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Navigation Rail (64px)
        root_layout.addWidget(self._build_left_rail())

        # 2. Effect Selection Column (195px)
        root_layout.addWidget(self._build_effects_column())

        # 3. Main Stage (Top Bar + Visualizer + Underglow Strip + Parameter Deck)
        stage_widget = QWidget()
        stage_layout = QVBoxLayout(stage_widget)
        stage_layout.setContentsMargins(20, 14, 20, 16)
        stage_layout.setSpacing(12)

        stage_layout.addWidget(self._build_top_header())

        # Visualizer Canvas Container
        canvas_card = QFrame()
        canvas_card.setProperty("class", "CardPanel")
        canvas_card_layout = QVBoxLayout(canvas_card)
        canvas_card_layout.setContentsMargins(10, 8, 10, 8)

        self.canvas = EverestKeyboardCanvas()
        self.canvas.key_clicked.connect(self._on_canvas_key_clicked)
        canvas_card_layout.addWidget(self.canvas)
        stage_layout.addWidget(canvas_card, stretch=4)

        # Dedicated Underglow (44-LED Edge Strip) Panel
        stage_layout.addWidget(self._build_underglow_panel())

        # Bottom Context-Sensitive Configuration Deck
        stage_layout.addWidget(self._build_bottom_deck(), stretch=3)

        root_layout.addWidget(stage_widget, stretch=1)

    # --------------------------------------------------------------------------
    # 1. LEFT RAIL
    # --------------------------------------------------------------------------
    def _build_left_rail(self) -> QWidget:
        rail = QWidget()
        rail.setObjectName("left_rail")
        rail.setFixedWidth(64)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(12)

        brand_mark = QLabel("▲")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setStyleSheet("color: #0078D7; font-size: 22px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(brand_mark)

        nav_items = [
            ("👤", "Profiles", False),
            ("💡", "Lighting", True),
            ("⌨", "Key Binding", False),
            ("⚡", "Macro", False),
            ("⚙", "Settings", False),
        ]
        for icon_text, tooltip, is_active in nav_items:
            btn = QPushButton(icon_text)
            btn.setFixedSize(64, 46)
            btn.setToolTip(tooltip)
            style = "font-size: 16px; border: none; background: transparent; "
            if is_active:
                style += "color: #0078D7; border-left: 3px solid #0078D7; background-color: #181A1F;"
            else:
                style += "color: #555A68;"
            btn.setStyleSheet(style)
            layout.addWidget(btn)

        layout.addStretch()
        return rail

    # --------------------------------------------------------------------------
    # 2. EFFECTS COLUMN
    # --------------------------------------------------------------------------
    def _build_effects_column(self) -> QWidget:
        col = QWidget()
        col.setObjectName("effects_column")
        col.setFixedWidth(195)
        layout = QVBoxLayout(col)
        layout.setContentsMargins(8, 20, 8, 16)
        layout.setSpacing(8)

        header = QLabel("LIGHTING EFFECTS")
        header.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold; padding-left: 14px; letter-spacing: 1px;")
        layout.addWidget(header)

        self.effects_list = QListWidget()
        effects = [
            ("Color Wave", "wave"),
            ("Tornado", "tornado"),
            ("Breathing & Pulse", "breathing"),
            ("Snappy Laser", "laser"),
            ("Falling Matrix", "matrix"),
            ("Expanding Ripple", "ripple"),
            ("Single-Key Punch", "punch"),
            ("Static Color", "static"),
            ("Custom Per-Key", "custom"),
            ("Lighting Off", "off")
        ]
        for name, key in effects:
            item = QListWidgetItem(f"  {name}")
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.effects_list.addItem(item)

        self.effects_list.setCurrentRow(0)
        self.effects_list.currentItemChanged.connect(self._on_effect_changed)

        layout.addWidget(self.effects_list)
        return col

    # --------------------------------------------------------------------------
    # 3. TOP HEADER
    # --------------------------------------------------------------------------
    def _build_top_header(self) -> QWidget:
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("MOUNTAIN EVEREST 60")
        title.setStyleSheet("font-size: 18px; font-weight: bold; letter-spacing: 1px; color: #FFFFFF;")
        subtitle = QLabel("BASE CAMP STUDIO PRO  •  64-KEY + 44-LED PERIMETER DIFFUSER")
        subtitle.setStyleSheet("font-size: 10px; font-weight: bold; color: #8A8F9D; letter-spacing: 1.2px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        layout.addStretch()

        self.status_badge = QPushButton(" CONNECTED ")
        self.status_badge.setFixedHeight(24)
        self.status_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_badge.setStyleSheet(
            "background-color: #22C55E; color: #FFFFFF; font-size: 10px; "
            "font-weight: bold; border-radius: 12px; padding: 2px 14px; border: none;"
        )
        self.status_badge.clicked.connect(self._on_status_badge_clicked)
        layout.addWidget(self.status_badge)

        return header

    # --------------------------------------------------------------------------
    # 4. DEDICATED 44-LED UNDERGLOW (EDGE STRIP) PANEL
    # --------------------------------------------------------------------------
    def _build_underglow_panel(self) -> QWidget:
        panel = QFrame()
        panel.setProperty("class", "CardPanel")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        ug_title = QLabel("UNDERGLOW (44-LED EDGE STRIP):")
        ug_title.setStyleSheet("color: #EAB308; font-size: 11px; font-weight: bold; letter-spacing: 0.8px;")
        layout.addWidget(ug_title)

        self.ug_sync_btn = QPushButton("Sync with Effect")
        self.ug_sync_btn.setProperty("class", "ToolButton")
        self.ug_sync_btn.setCheckable(True)
        self.ug_sync_btn.setChecked(True)
        self.ug_sync_btn.clicked.connect(lambda: self._set_underglow_mode("sync"))

        self.ug_static_btn = QPushButton("Static Custom Color")
        self.ug_static_btn.setProperty("class", "ToolButton")
        self.ug_static_btn.setCheckable(True)
        self.ug_static_btn.clicked.connect(lambda: self._set_underglow_mode("static"))

        self.ug_off_btn = QPushButton("Off")
        self.ug_off_btn.setProperty("class", "ToolButton")
        self.ug_off_btn.setCheckable(True)
        self.ug_off_btn.clicked.connect(lambda: self._set_underglow_mode("off"))

        layout.addWidget(self.ug_sync_btn)
        layout.addWidget(self.ug_static_btn)
        layout.addWidget(self.ug_off_btn)

        layout.addSpacing(12)

        # Independent Underglow Swatch Chip
        self.ug_color_chip = QPushButton("  Underglow Color  ")
        self.ug_color_chip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ug_color_chip.setFixedHeight(28)
        self.ug_color_chip.clicked.connect(lambda: self._select_color_target("underglow"))
        layout.addWidget(self.ug_color_chip)
        self.ug_color_chip.hide()

        layout.addStretch()

        # Dedicated Edge Brightness Slider
        edge_bright_lbl = QLabel("EDGE BRIGHTNESS:")
        edge_bright_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        layout.addWidget(edge_bright_lbl)

        self.edge_bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.edge_bright_slider.setRange(0, 100)
        self.edge_bright_slider.setValue(self.engine.underglow_brightness)
        self.edge_bright_slider.setFixedWidth(130)
        self.edge_bright_slider.valueChanged.connect(self._on_edge_brightness_changed)
        layout.addWidget(self.edge_bright_slider)

        self.edge_bright_val = QLabel(f"{self.engine.underglow_brightness}%")
        self.edge_bright_val.setStyleSheet("color: #0078D7; font-size: 11px; font-weight: bold; min-width: 34px;")
        layout.addWidget(self.edge_bright_val)

        return panel

    # --------------------------------------------------------------------------
    # 5. BOTTOM CONTEXT-SENSITIVE CONFIGURATION DECK
    # --------------------------------------------------------------------------
    def _build_bottom_deck(self) -> QWidget:
        deck = QWidget()
        deck_layout = QHBoxLayout(deck)
        deck_layout.setContentsMargins(0, 0, 0, 0)
        deck_layout.setSpacing(16)

        # Left Card: Context-Sensitive Controls
        left_card = QFrame()
        left_card.setProperty("class", "CardPanel")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(18, 14, 18, 14)
        left_layout.setSpacing(10)

        # Profile Preset Row ([ P1 ] - [ P5 ])
        self.profile_container = QWidget()
        prof_box = QHBoxLayout(self.profile_container)
        prof_box.setContentsMargins(0, 0, 0, 0)
        prof_box.setSpacing(8)

        prof_lbl = QLabel("PROFILES:")
        prof_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold; letter-spacing: 0.8px;")
        prof_box.addWidget(prof_lbl)

        self.profile_buttons = {}
        for slot in range(1, 6):
            btn = QPushButton(f"[ P{slot} ]")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setFixedWidth(54)
            btn.setStyleSheet(self.PROFILE_BTN_INACTIVE_STYLE)
            btn.clicked.connect(lambda _, s=slot: self._on_profile_clicked(s))
            prof_box.addWidget(btn)
            self.profile_buttons[slot] = btn

        prof_box.addStretch()
        left_layout.addWidget(self.profile_container)

        # A. Palette Mode Row (Single / Dual / Rainbow / Matrix Classic)
        self.palette_row_widget = QWidget()
        mode_box = QHBoxLayout(self.palette_row_widget)
        mode_box.setContentsMargins(0, 0, 0, 0)
        mode_lbl = QLabel("COLOR MODE:")
        mode_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        mode_box.addWidget(mode_lbl)

        self.mode_single_rb = QRadioButton("Single Color")
        self.mode_dual_rb = QRadioButton("Dual Color")
        self.mode_rainbow_rb = QRadioButton("Rainbow")
        self.mode_rainbow_rb.setChecked(True)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.mode_single_rb)
        self.mode_group.addButton(self.mode_dual_rb)
        self.mode_group.addButton(self.mode_rainbow_rb)
        self.mode_single_rb.toggled.connect(self._on_mode_type_toggled)
        self.mode_dual_rb.toggled.connect(self._on_mode_type_toggled)
        self.mode_rainbow_rb.toggled.connect(self._on_mode_type_toggled)

        mode_box.addWidget(self.mode_single_rb)
        mode_box.addWidget(self.mode_dual_rb)
        mode_box.addWidget(self.mode_rainbow_rb)
        mode_box.addStretch()
        left_layout.addWidget(self.palette_row_widget)

        # B. Active Color Chip Selector ([Color A] / [Color B])
        self.chips_row_widget = QWidget()
        chips_layout = QHBoxLayout(self.chips_row_widget)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(10)

        chips_lbl = QLabel("ACTIVE SWATCH:")
        chips_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        chips_layout.addWidget(chips_lbl)

        self.chip_a_btn = QPushButton("  [Color A]  ")
        self.chip_a_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chip_a_btn.setFixedHeight(28)
        self.chip_a_btn.clicked.connect(lambda: self._select_color_target("color_a"))

        self.chip_b_btn = QPushButton("  [Color B]  ")
        self.chip_b_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chip_b_btn.setFixedHeight(28)
        self.chip_b_btn.clicked.connect(lambda: self._select_color_target("color_b"))

        chips_layout.addWidget(self.chip_a_btn)
        chips_layout.addWidget(self.chip_b_btn)
        chips_layout.addStretch()
        left_layout.addWidget(self.chips_row_widget)

        # C. Primary Speed Slider (Dynamic range per effect)
        self.speed_widget = QWidget()
        speed_box = QVBoxLayout(self.speed_widget)
        speed_box.setContentsMargins(0, 0, 0, 0)
        speed_box.setSpacing(4)
        speed_header = QHBoxLayout()
        self.speed_title_lbl = QLabel("SPEED")
        self.speed_title_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        self.speed_val_lbl = QLabel("5")
        self.speed_val_lbl.setStyleSheet("color: #0078D7; font-size: 11px; font-weight: bold;")
        speed_header.addWidget(self.speed_title_lbl)
        speed_header.addStretch()
        speed_header.addWidget(self.speed_val_lbl)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.valueChanged.connect(self._on_speed_slider_changed)

        speed_box.addLayout(speed_header)
        speed_box.addWidget(self.speed_slider)
        left_layout.addWidget(self.speed_widget)

        # D. Secondary Decay / Linger Duration Slider (For Laser, Punch, Ripple)
        self.decay_widget = QWidget()
        decay_box = QVBoxLayout(self.decay_widget)
        decay_box.setContentsMargins(0, 0, 0, 0)
        decay_box.setSpacing(4)
        decay_header = QHBoxLayout()
        self.decay_title_lbl = QLabel("TRAIL DECAY DURATION")
        self.decay_title_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        self.decay_val_lbl = QLabel("0.16 s")
        self.decay_val_lbl.setStyleSheet("color: #0078D7; font-size: 11px; font-weight: bold;")
        decay_header.addWidget(self.decay_title_lbl)
        decay_header.addStretch()
        decay_header.addWidget(self.decay_val_lbl)

        self.decay_slider = QSlider(Qt.Orientation.Horizontal)
        self.decay_slider.setRange(5, 50)  # 0.05s to 0.50s
        self.decay_slider.setValue(16)
        self.decay_slider.valueChanged.connect(self._on_decay_slider_changed)

        decay_box.addLayout(decay_header)
        decay_box.addWidget(self.decay_slider)
        left_layout.addWidget(self.decay_widget)
        self.decay_widget.hide()

        # E. Brightness Slider (0% to 100% with sun icons)
        bright_box = QVBoxLayout()
        bright_box.setSpacing(4)
        bright_header = QHBoxLayout()
        bright_lbl = QLabel("☀  BRIGHTNESS")
        bright_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        self.bright_val_lbl = QLabel("100%")
        self.bright_val_lbl.setStyleSheet("color: #0078D7; font-size: 11px; font-weight: bold;")
        bright_header.addWidget(bright_lbl)
        bright_header.addStretch()
        bright_header.addWidget(self.bright_val_lbl)

        self.bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.bright_slider.setRange(0, 100)
        self.bright_slider.setValue(100)
        self.bright_slider.valueChanged.connect(self._on_brightness_changed)

        bright_box.addLayout(bright_header)
        bright_box.addWidget(self.bright_slider)
        left_layout.addLayout(bright_box)

        # F. Color Wave Directional Pad (← → ↑ ↓ ⬈)
        self.wave_dir_frame = QWidget()
        dir_layout = QHBoxLayout(self.wave_dir_frame)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_lbl = QLabel("WAVE DIRECTION:")
        dir_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        dir_layout.addWidget(dir_lbl)

        self.dir_buttons = {}
        for d_name, d_symbol in [("left", "←"), ("right", "→"), ("up", "↑"), ("down", "↓"), ("diagonal", "⬈")]:
            btn = QPushButton(d_symbol)
            btn.setProperty("class", "ToolButton")
            btn.setCheckable(True)
            if d_name == "right":
                btn.setChecked(True)
            btn.clicked.connect(lambda _, d=d_name: self._set_wave_direction(d))
            dir_layout.addWidget(btn)
            self.dir_buttons[d_name] = btn
        dir_layout.addStretch()
        left_layout.addWidget(self.wave_dir_frame)

        # G. Tornado Rotation Direction Pad (↻ Clockwise / ↺ Counter-Clockwise)
        self.tornado_dir_frame = QWidget()
        t_dir_layout = QHBoxLayout(self.tornado_dir_frame)
        t_dir_layout.setContentsMargins(0, 0, 0, 0)
        t_dir_lbl = QLabel("SPIN DIRECTION:")
        t_dir_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        t_dir_layout.addWidget(t_dir_lbl)

        self.tornado_cw_btn = QPushButton("↻  Clockwise")
        self.tornado_cw_btn.setProperty("class", "ToolButton")
        self.tornado_cw_btn.setCheckable(True)
        self.tornado_cw_btn.setChecked(True)
        self.tornado_cw_btn.clicked.connect(lambda: self._set_tornado_direction(True))

        self.tornado_ccw_btn = QPushButton("↺  Counter-Clockwise")
        self.tornado_ccw_btn.setProperty("class", "ToolButton")
        self.tornado_ccw_btn.setCheckable(True)
        self.tornado_ccw_btn.clicked.connect(lambda: self._set_tornado_direction(False))

        t_dir_layout.addWidget(self.tornado_cw_btn)
        t_dir_layout.addWidget(self.tornado_ccw_btn)
        t_dir_layout.addStretch()
        left_layout.addWidget(self.tornado_dir_frame)
        self.tornado_dir_frame.hide()

        # H. Custom Per-Key Actions Bar
        self.custom_actions_frame = QWidget()
        custom_act_layout = QHBoxLayout(self.custom_actions_frame)
        custom_act_layout.setContentsMargins(0, 0, 0, 0)
        custom_hint = QLabel("Click or drag across keys on the 2D visualizer above to paint:")
        custom_hint.setStyleSheet("color: #8A8F9D; font-size: 11px;")
        fill_all_btn = QPushButton("Fill All 64 Keys")
        fill_all_btn.setProperty("class", "ToolButton")
        fill_all_btn.clicked.connect(self._fill_all_custom_keys)
        clr_sel_btn = QPushButton("Clear Selection")
        clr_sel_btn.setProperty("class", "ToolButton")
        clr_sel_btn.clicked.connect(lambda: self.canvas.clear_selection())
        custom_act_layout.addWidget(custom_hint)
        custom_act_layout.addStretch()
        custom_act_layout.addWidget(fill_all_btn)
        custom_act_layout.addWidget(clr_sel_btn)
        left_layout.addWidget(self.custom_actions_frame)
        self.custom_actions_frame.hide()

        left_layout.addStretch()
        deck_layout.addWidget(left_card, stretch=3)

        # Right Card: Base Camp Custom Color Picker
        right_card = QFrame()
        right_card.setProperty("class", "CardPanel")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 10, 14, 10)

        self.picker_header_lbl = QLabel("COLOR PALETTE  —  EDITING [COLOR A]")
        self.picker_header_lbl.setStyleSheet("color: #0078D7; font-size: 11px; font-weight: bold; letter-spacing: 0.8px;")
        right_layout.addWidget(self.picker_header_lbl)

        self.color_picker = BaseCampColorPicker(initial_color=QColor("#00FFFF"))
        self.color_picker.color_changed.connect(self._on_picker_color_changed)
        right_layout.addWidget(self.color_picker)

        deck_layout.addWidget(right_card, stretch=2)

        return deck

    # --------------------------------------------------------------------------
    # 6. ENGINE SIGNALS & CONTEXT-SENSITIVE LOGIC
    # --------------------------------------------------------------------------
    def _wire_engine_signals(self):
        self.engine.frame_rendered.connect(self.canvas.update_frame)
        if hasattr(self.engine, "underglow_rendered"):
            self.engine.underglow_rendered.connect(self.canvas.update_underglow)
        self.engine.key_struck.connect(self.canvas.flash_key)
        self.engine.connection_changed.connect(self._on_connection_status_changed)

    def _on_status_badge_clicked(self):
        """Triggers manual connection attempt when the status badge button is clicked."""
        self.status_badge.setText(" CONNECTING... ")
        self.status_badge.setStyleSheet(
            "background-color: #EAB308; color: #FFFFFF; font-size: 10px; "
            "font-weight: bold; border-radius: 12px; padding: 2px 14px; border: none;"
        )
        threading.Thread(target=self.engine.connect, daemon=True).start()

    def _on_connection_status_changed(self, connected: bool, message: str):
        if connected:
            self.status_badge.setText(" CONNECTED ")
            self.status_badge.setStyleSheet(
                "background-color: #22C55E; color: #FFFFFF; font-size: 10px; "
                "font-weight: bold; border-radius: 12px; padding: 2px 14px; border: none;"
            )
            self.status_badge.setToolTip("OpenRGB connected to Mountain Everest 60")
        else:
            self.status_badge.setText(" OFFLINE / SIMULATOR (CLICK TO RETRY) ")
            self.status_badge.setStyleSheet(
                "background-color: #F59E0B; color: #FFFFFF; font-size: 10px; "
                "font-weight: bold; border-radius: 12px; padding: 2px 14px; border: none;"
            )
            self.status_badge.setToolTip(f"{message}\nClick to attempt manual reconnection.")

    def _on_effect_changed(self, current: QListWidgetItem, _previous: QListWidgetItem):
        if not current:
            return
        effect_key = current.data(Qt.ItemDataRole.UserRole)
        self.engine.effect_name = effect_key
        self._reconfigure_deck_for_effect(effect_key)
        if not self._suppress_slider_events:
            self.save_settings()

    def _reconfigure_deck_for_effect(self, effect_key: str):
        """Dynamically reconfigures sliders, palette radios, and direction pads for the chosen effect."""
        self._suppress_slider_events = True

        # Hide context-specific sub-panels first
        self.wave_dir_frame.hide()
        self.tornado_dir_frame.hide()
        self.custom_actions_frame.hide()
        self.decay_widget.hide()
        self.profile_container.show()
        self.speed_widget.show()
        self.palette_row_widget.show()
        self.chips_row_widget.show()

        # Reset radio button labels
        self.mode_single_rb.setText("Single Color")
        self.mode_dual_rb.setText("Dual Color")
        self.mode_rainbow_rb.setText("Rainbow")
        self.mode_rainbow_rb.show()
        self.mode_dual_rb.show()
        self.mode_single_rb.show()

        if effect_key == "wave":
            self.wave_dir_frame.show()
            self.speed_title_lbl.setText("WAVE SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.chip_a_btn.setText("  [Color A]  ")
            self.chip_b_btn.setText("  [Color B]  ")

        elif effect_key == "tornado":
            self.tornado_dir_frame.show()
            self.speed_title_lbl.setText("ROTATION SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.chip_a_btn.setText("  [Color A]  ")
            self.chip_b_btn.setText("  [Color B]  ")

        elif effect_key == "breathing":
            self.speed_title_lbl.setText("PULSE SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.chip_a_btn.setText("  [Color A]  ")
            self.chip_b_btn.setText("  [Color B]  ")

        elif effect_key == "laser":
            # Snappy Laser: Single Color (Black Base + Laser) or Dual Color (Base + Laser)
            self.mode_rainbow_rb.hide()
            if self.mode_rainbow_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = "dual"

            self.speed_title_lbl.setText("LASER VELOCITY (KEYS / SEC)")
            self.speed_slider.setRange(15, 120)
            self.speed_slider.setValue(int(self.engine.laser_speed))
            self.speed_val_lbl.setText(f"{int(self.engine.laser_speed)} keys/s")

            self.decay_widget.show()
            self.decay_title_lbl.setText("TRAIL DECAY DURATION")
            self.decay_slider.setRange(5, 50)
            self.decay_slider.setValue(int(round(self.engine.laser_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.laser_decay:.2f} s")

            self.chip_a_btn.setText("  [Color A: Laser Beam]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")

        elif effect_key == "punch":
            # Single-Key Punch: Single Color or Dual Color + Linger Slider (0.10 to 2.50s)
            self.mode_rainbow_rb.hide()
            if self.mode_rainbow_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = "dual"

            self.speed_widget.hide()
            self.decay_widget.show()
            self.decay_title_lbl.setText("KEY LINGER / FADE DURATION")
            self.decay_slider.setRange(10, 250)  # 0.10s to 2.50s
            self.decay_slider.setValue(int(round(self.engine.punch_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.punch_decay:.2f} s")

            self.chip_a_btn.setText("  [Color A: Key Strike]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")

        elif effect_key == "ripple":
            self.mode_rainbow_rb.hide()
            if self.mode_rainbow_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = "dual"

            self.speed_title_lbl.setText("RIPPLE EXPANSION SPEED")
            self.speed_slider.setRange(5, 40)
            self.speed_slider.setValue(int(self.engine.ripple_speed))
            self.speed_val_lbl.setText(f"{int(self.engine.ripple_speed)} keys/s")

            self.decay_widget.show()
            self.decay_title_lbl.setText("RIPPLE LIFETIME")
            self.decay_slider.setRange(20, 150)
            self.decay_slider.setValue(int(round(self.engine.ripple_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.ripple_decay:.2f} s")

            self.chip_a_btn.setText("  [Color A: Ripple Wave]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")

        elif effect_key == "matrix":
            # Falling Matrix: Matrix Classic, Dual Color (Head + Tail), Rainbow
            self.mode_single_rb.setText("Matrix Classic")
            if self.engine.mode_type not in ("single", "dual", "rainbow"):
                self.mode_single_rb.setChecked(True)
                self.engine.mode_type = "single"

            self.speed_title_lbl.setText("FALLING RAIN VELOCITY (ROWS / SEC)")
            self.speed_slider.setRange(2, 15)
            self.speed_slider.setValue(int(self.engine.matrix_speed))
            self.speed_val_lbl.setText(f"{int(self.engine.matrix_speed)} rows/s")

            self.chip_a_btn.setText("  [Color A: Spark Head]  ")
            self.chip_b_btn.setText("  [Color B: Trail Stream]  ")

        elif effect_key == "static":
            self.palette_row_widget.hide()
            self.speed_widget.hide()
            self.chip_a_btn.setText("  [Static Switch Color]  ")
            self._select_color_target("color_a")

        elif effect_key == "custom":
            self.palette_row_widget.hide()
            self.speed_widget.hide()
            self.custom_actions_frame.show()
            self.chip_a_btn.setText("  [Paint Brush Color]  ")
            self._select_color_target("color_a")

        elif effect_key == "off":
            self.palette_row_widget.hide()
            self.chips_row_widget.hide()
            self.speed_widget.hide()

        self._suppress_slider_events = False
        self._update_chip_visibility()
        self._refresh_color_chips()

    def _on_mode_type_toggled(self):
        if self.mode_rainbow_rb.isChecked():
            self.engine.mode_type = "rainbow"
        elif self.mode_dual_rb.isChecked():
            self.engine.mode_type = "dual"
            if self.engine.effect_name == "matrix" and not self._suppress_slider_events:
                # Default Matrix Dual Colors if not customized
                self.engine.color_a = RGBColor(0, 255, 102)
                self.engine.color_b = RGBColor(0, 59, 16)
        else:
            self.engine.mode_type = "single"

        self._update_chip_visibility()
        self._refresh_color_chips()
        if not self._suppress_slider_events:
            self.save_settings()

    def _update_chip_visibility(self):
        eff = self.engine.effect_name
        if eff == "off":
            self.chips_row_widget.hide()
            return

        if eff in ("static", "custom"):
            self.chips_row_widget.show()
            self.chip_a_btn.show()
            self.chip_b_btn.hide()
            return

        if eff == "matrix":
            if self.mode_dual_rb.isChecked():
                self.chips_row_widget.show()
                self.chip_a_btn.show()
                self.chip_b_btn.show()
            else:
                self.chips_row_widget.hide()
            return

        if self.mode_rainbow_rb.isChecked() and eff in ("wave", "tornado", "breathing"):
            self.chips_row_widget.hide()
        elif self.mode_dual_rb.isChecked():
            self.chips_row_widget.show()
            self.chip_a_btn.show()
            self.chip_b_btn.show()
        else:
            self.chips_row_widget.show()
            self.chip_a_btn.show()
            self.chip_b_btn.hide()
            if self.active_color_target == "color_b":
                self._select_color_target("color_a")

    def _select_color_target(self, target: str):
        """Binds the Base Camp Color Picker to Color A, Color B, or Underglow."""
        self.active_color_target = target
        if target == "color_a":
            c = self.engine.color_a
            self.picker_header_lbl.setText("COLOR PALETTE  —  EDITING [COLOR A]")
        elif target == "color_b":
            c = self.engine.color_b
            self.picker_header_lbl.setText("COLOR PALETTE  —  EDITING [COLOR B]")
        else:
            c = self.engine.underglow_color
            self.picker_header_lbl.setText("COLOR PALETTE  —  EDITING [UNDERGLOW STRIP]")

        self.color_picker.load_color(QColor(c.red, c.green, c.blue))
        self._refresh_color_chips()

    def _refresh_color_chips(self):
        """Updates live background swatches and active highlight borders on Color A, Color B, and Underglow chips."""
        def style_chip(btn: QPushButton, rgb: RGBColor, is_active: bool):
            hex_col = f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}"
            lum = 0.299 * rgb.red + 0.587 * rgb.green + 0.114 * rgb.blue
            text_col = "#000000" if lum > 140 else "#FFFFFF"
            border = "2px solid #0078D7" if is_active else "1px solid #3F4756"
            btn.setStyleSheet(
                f"background-color: {hex_col}; color: {text_col}; border: {border}; "
                f"border-radius: 5px; font-weight: bold; font-size: 11px; padding: 3px 10px;"
            )

        style_chip(self.chip_a_btn, self.engine.color_a, self.active_color_target == "color_a")
        style_chip(self.chip_b_btn, self.engine.color_b, self.active_color_target == "color_b")
        style_chip(self.ug_color_chip, self.engine.underglow_color, self.active_color_target == "underglow")

    def _on_picker_color_changed(self, qcol: QColor):
        rgb = RGBColor(qcol.red(), qcol.green(), qcol.blue())

        if self.active_color_target == "underglow":
            self.engine.underglow_color = rgb
        elif self.active_color_target == "color_b":
            self.engine.color_b = rgb
        else:
            self.engine.color_a = rgb
            if self.engine.effect_name == "custom":
                for led_idx in self.canvas.selected_keys:
                    self.engine.set_custom_key_color(led_idx, rgb)

        self._refresh_color_chips()
        if not self._suppress_slider_events:
            self.save_settings()

    def _on_canvas_key_clicked(self, led_idx: int):
        """
        In Custom Per-Key mode: immediately paints clicked switch with active color.
        In Reactive modes: triggers a test pulse on the clicked switch!
        """
        if self.engine.effect_name == "custom":
            qc = self.color_picker.current_color
            rgb = RGBColor(qc.red(), qc.green(), qc.blue())
            self.engine.set_custom_key_color(led_idx, rgb)
            if not self._suppress_slider_events:
                self.save_settings()
        elif self.engine.effect_name in ("laser", "ripple", "punch"):
            self.engine.trigger_switch(led_idx)

    def _fill_all_custom_keys(self):
        qc = self.color_picker.current_color
        rgb = RGBColor(qc.red(), qc.green(), qc.blue())
        self.engine.fill_all_custom_keys(rgb)
        if not self._suppress_slider_events:
            self.save_settings()

    def _set_wave_direction(self, direction: str):
        self.engine.direction = direction
        for d, btn in self.dir_buttons.items():
            btn.setChecked(d == direction)
        if not self._suppress_slider_events:
            self.save_settings()

    def _set_tornado_direction(self, clockwise: bool):
        self.engine.tornado_cw = clockwise
        self.tornado_cw_btn.setChecked(clockwise)
        self.tornado_ccw_btn.setChecked(not clockwise)
        if not self._suppress_slider_events:
            self.save_settings()

    def _set_underglow_mode(self, mode: str):
        self.engine.underglow_mode = mode
        self.ug_sync_btn.setChecked(mode == "sync")
        self.ug_static_btn.setChecked(mode == "static")
        self.ug_off_btn.setChecked(mode == "off")

        if mode == "static":
            self.ug_color_chip.show()
            self._select_color_target("underglow")
        else:
            self.ug_color_chip.hide()
            if self.active_color_target == "underglow":
                self._select_color_target("color_a")

        if not self._suppress_slider_events:
            self.save_settings()

    def _on_speed_slider_changed(self, val: int):
        if self._suppress_slider_events:
            return
        eff = self.engine.effect_name
        if eff == "laser":
            self.engine.laser_speed = float(val)
            self.speed_val_lbl.setText(f"{val} keys/s")
        elif eff == "matrix":
            self.engine.matrix_speed = float(val)
            self.speed_val_lbl.setText(f"{val} rows/s")
        elif eff == "ripple":
            self.engine.ripple_speed = float(val)
            self.speed_val_lbl.setText(f"{val} keys/s")
        else:
            self.engine.speed = float(val)
            self.speed_val_lbl.setText(str(val))
        self.save_settings()

    def _on_decay_slider_changed(self, val: int):
        if self._suppress_slider_events:
            return
        seconds = val / 100.0
        eff = self.engine.effect_name
        if eff == "laser":
            self.engine.laser_decay = seconds
        elif eff == "punch":
            self.engine.punch_decay = seconds
        elif eff == "ripple":
            self.engine.ripple_decay = seconds
        self.decay_val_lbl.setText(f"{seconds:.2f} s")
        self.save_settings()

    def _on_brightness_changed(self, val: int):
        self.bright_val_lbl.setText(f"{val}%")
        self.engine.brightness = val / 100.0
        if not self._suppress_slider_events:
            self.save_settings()

    def _on_edge_brightness_changed(self, val: int):
        self.engine.underglow_brightness = val
        self.edge_bright_val.setText(f"{val}%")
        if not self._suppress_slider_events:
            self.save_settings()

    # --------------------------------------------------------------------------
    # 7. PROFILES & PERSISTENCE (config.json)
    # --------------------------------------------------------------------------
    def _update_profile_buttons_style(self):
        """Highlights active profile button and dims inactive slots."""
        for slot, btn in self.profile_buttons.items():
            if slot == self.active_profile_slot:
                btn.setStyleSheet(self.PROFILE_BTN_ACTIVE_STYLE)
            else:
                btn.setStyleSheet(self.PROFILE_BTN_INACTIVE_STYLE)

    def _get_default_profiles(self) -> Dict[str, dict]:
        """Returns 5 distinct factory default presets for slots P1 to P5."""
        return {
            "1": {
                "mode": "ripple",
                "color_mode": "dual",
                "palette_mode": "dual",
                "color_a": "#FFFF00",
                "color_b": "#0000FF",
                "base_color": "#0000FF",
                "react_color": "#FFFF00",
                "speed": 5,
                "brightness": 100,
                "decay": 0.16,
                "laser_speed": 60,
                "laser_decay": 0.16,
                "punch_decay": 0.35,
                "ripple_speed": 15,
                "ripple_decay": 0.65,
                "matrix_speed": 6,
                "underglow_mode": "static",
                "underglow_color": "#A01C1C",
                "underglow_brightness": 25,
                "direction": "right",
                "tornado_cw": True,
            },
            "2": {
                "mode": "laser",
                "color_mode": "dual",
                "palette_mode": "dual",
                "color_a": "#00FFFF",
                "color_b": "#FF007F",
                "base_color": "#FF007F",
                "react_color": "#00FFFF",
                "speed": 5,
                "brightness": 100,
                "decay": 0.14,
                "laser_speed": 75,
                "laser_decay": 0.14,
                "punch_decay": 0.35,
                "ripple_speed": 15,
                "ripple_decay": 0.65,
                "matrix_speed": 6,
                "underglow_mode": "sync",
                "underglow_color": "#00FFFF",
                "underglow_brightness": 35,
                "direction": "right",
                "tornado_cw": True,
            },
            "3": {
                "mode": "wave",
                "color_mode": "rainbow",
                "palette_mode": "rainbow",
                "color_a": "#00FF00",
                "color_b": "#0000FF",
                "base_color": "#0000FF",
                "react_color": "#00FF00",
                "speed": 6,
                "brightness": 100,
                "decay": 0.16,
                "laser_speed": 60,
                "laser_decay": 0.16,
                "punch_decay": 0.35,
                "ripple_speed": 15,
                "ripple_decay": 0.65,
                "matrix_speed": 6,
                "underglow_mode": "sync",
                "underglow_color": "#00FFCC",
                "underglow_brightness": 40,
                "direction": "right",
                "tornado_cw": True,
            },
            "4": {
                "mode": "matrix",
                "color_mode": "matrix_classic",
                "palette_mode": "matrix_classic",
                "color_a": "#00FF44",
                "color_b": "#000000",
                "base_color": "#000000",
                "react_color": "#00FF44",
                "speed": 6,
                "brightness": 100,
                "decay": 0.16,
                "laser_speed": 60,
                "laser_decay": 0.16,
                "punch_decay": 0.35,
                "ripple_speed": 15,
                "ripple_decay": 0.65,
                "matrix_speed": 7,
                "underglow_mode": "off",
                "underglow_color": "#000000",
                "underglow_brightness": 0,
                "direction": "down",
                "tornado_cw": True,
            },
            "5": {
                "mode": "static",
                "color_mode": "single",
                "palette_mode": "single",
                "color_a": "#0078D7",
                "color_b": "#0078D7",
                "base_color": "#0078D7",
                "react_color": "#0078D7",
                "speed": 5,
                "brightness": 100,
                "decay": 0.16,
                "laser_speed": 60,
                "laser_decay": 0.16,
                "punch_decay": 0.35,
                "ripple_speed": 15,
                "ripple_decay": 0.65,
                "matrix_speed": 6,
                "underglow_mode": "sync",
                "underglow_color": "#0078D7",
                "underglow_brightness": 40,
                "direction": "right",
                "tornado_cw": True,
            },
        }

    def _capture_current_profile_dict(self) -> dict:
        """Captures active UI and lighting parameters into a dictionary."""
        d = {
            "mode": self.engine.effect_name,
            "color_mode": self.engine.mode_type,
            "palette_mode": self.engine.mode_type,
            "color_a": rgb_to_hex(self.engine.color_a),
            "color_b": rgb_to_hex(self.engine.color_b),
            "base_color": rgb_to_hex(self.engine.color_b),
            "react_color": rgb_to_hex(self.engine.color_a),
            "speed": int(self.engine.speed),
            "brightness": int(round(self.engine.brightness * 100)),
            "decay": round(self.engine.laser_decay, 2),
            "laser_speed": int(self.engine.laser_speed),
            "laser_decay": round(self.engine.laser_decay, 2),
            "punch_decay": round(self.engine.punch_decay, 2),
            "ripple_speed": int(self.engine.ripple_speed),
            "ripple_decay": round(self.engine.ripple_decay, 2),
            "matrix_speed": int(self.engine.matrix_speed),
            "underglow_mode": self.engine.underglow_mode,
            "underglow_color": rgb_to_hex(self.engine.underglow_color),
            "underglow_brightness": int(self.engine.underglow_brightness),
            "direction": self.engine.direction,
            "tornado_cw": self.engine.tornado_cw,
        }
        if self.engine.effect_name == "custom":
            d["custom_colors"] = {
                str(k): rgb_to_hex(v) for k, v in self.engine.custom_key_colors.items()
            }
        return d

    def _on_profile_clicked(self, slot: int):
        """Switches active profile slot, persisting current state and applying new slot configuration."""
        if slot == self.active_profile_slot:
            return

        # 1. Save outgoing profile parameters to in-memory profile dictionary
        self.profiles[str(self.active_profile_slot)] = self._capture_current_profile_dict()

        # 2. Update active profile slot
        self.active_profile_slot = slot

        # 3. Retrieve target incoming profile settings
        slot_key = str(slot)
        if slot_key not in self.profiles:
            defaults = self._get_default_profiles()
            self.profiles[slot_key] = defaults.get(slot_key, self._capture_current_profile_dict())

        prof_data = self.profiles[slot_key]

        # 4. Apply incoming settings to engine and UI
        self._apply_profile_dict(prof_data)

        # 5. Update profile button styles
        self._update_profile_buttons_style()

        # 6. Mark engine dirty & save to config.json
        self.engine.mark_dirty()
        self.save_settings()

    def _apply_profile_dict(self, cfg: dict):
        """Applies configuration dictionary to self.engine and updates all UI controls."""
        self._suppress_slider_events = True
        try:
            # 1. Colors
            if "color_a" in cfg:
                self.engine.color_a = hex_to_rgb(cfg["color_a"], self.engine.color_a)
            elif "react_color" in cfg:
                self.engine.color_a = hex_to_rgb(cfg["react_color"], self.engine.color_a)

            if "color_b" in cfg:
                self.engine.color_b = hex_to_rgb(cfg["color_b"], self.engine.color_b)
            elif "base_color" in cfg:
                self.engine.color_b = hex_to_rgb(cfg["base_color"], self.engine.color_b)

            if "underglow_color" in cfg:
                self.engine.underglow_color = hex_to_rgb(cfg["underglow_color"], self.engine.underglow_color)

            # 2. Sliders & Brightness
            if "brightness" in cfg:
                b_val = max(0, min(100, int(cfg["brightness"])))
                self.engine.brightness = b_val / 100.0
                if hasattr(self, "bright_slider"):
                    self.bright_slider.setValue(b_val)
                if hasattr(self, "bright_val_lbl"):
                    self.bright_val_lbl.setText(f"{b_val}%")

            if "underglow_brightness" in cfg:
                ug_val = max(0, min(100, int(cfg["underglow_brightness"])))
                self.engine.underglow_brightness = ug_val
                if hasattr(self, "edge_bright_slider"):
                    self.edge_bright_slider.setValue(ug_val)
                if hasattr(self, "edge_bright_val"):
                    self.edge_bright_val.setText(f"{ug_val}%")

            if "speed" in cfg:
                self.engine.speed = float(cfg["speed"])
                if hasattr(self, "speed_slider"):
                    self.speed_slider.setValue(int(self.engine.speed))
                if hasattr(self, "speed_val_lbl"):
                    self.speed_val_lbl.setText(str(int(self.engine.speed)))

            if "laser_speed" in cfg:
                self.engine.laser_speed = float(cfg["laser_speed"])
            if "laser_decay" in cfg:
                self.engine.laser_decay = float(cfg["laser_decay"])
            elif "decay" in cfg:
                self.engine.laser_decay = float(cfg["decay"])
            if "punch_decay" in cfg:
                self.engine.punch_decay = float(cfg["punch_decay"])
            if "ripple_speed" in cfg:
                self.engine.ripple_speed = float(cfg["ripple_speed"])
            if "ripple_decay" in cfg:
                self.engine.ripple_decay = float(cfg["ripple_decay"])
            if "matrix_speed" in cfg:
                self.engine.matrix_speed = float(cfg["matrix_speed"])

            if "direction" in cfg:
                self.engine.direction = cfg["direction"]
                if hasattr(self, "dir_buttons"):
                    for d, btn in self.dir_buttons.items():
                        btn.setChecked(d == self.engine.direction)

            if "tornado_cw" in cfg:
                self.engine.tornado_cw = bool(cfg["tornado_cw"])
                if hasattr(self, "tornado_cw_btn"):
                    self.tornado_cw_btn.setChecked(self.engine.tornado_cw)
                if hasattr(self, "tornado_ccw_btn"):
                    self.tornado_ccw_btn.setChecked(not self.engine.tornado_cw)

            # 3. Custom Keys if saved
            if "custom_colors" in cfg and isinstance(cfg["custom_colors"], dict):
                for k_str, hex_val in cfg["custom_colors"].items():
                    try:
                        k_idx = int(k_str)
                        self.engine.custom_key_colors[k_idx] = hex_to_rgb(hex_val, RGBColor(0, 120, 215))
                    except Exception:
                        pass

            # 4. Palette / Color Mode
            col_mode = cfg.get("color_mode", cfg.get("palette_mode", "rainbow"))
            self.engine.mode_type = col_mode
            if hasattr(self, "mode_single_rb") and hasattr(self, "mode_dual_rb") and hasattr(self, "mode_rainbow_rb"):
                if col_mode == "single":
                    self.mode_single_rb.setChecked(True)
                elif col_mode == "dual":
                    self.mode_dual_rb.setChecked(True)
                else:
                    self.mode_rainbow_rb.setChecked(True)

            # 5. Underglow Mode
            if "underglow_mode" in cfg:
                ug_mode = cfg["underglow_mode"]
                self.engine.underglow_mode = ug_mode
                if hasattr(self, "ug_sync_btn"):
                    self.ug_sync_btn.setChecked(ug_mode == "sync")
                if hasattr(self, "ug_static_btn"):
                    self.ug_static_btn.setChecked(ug_mode == "static")
                if hasattr(self, "ug_off_btn"):
                    self.ug_off_btn.setChecked(ug_mode == "off")
                if hasattr(self, "ug_color_chip"):
                    if ug_mode == "static":
                        self.ug_color_chip.show()
                    else:
                        self.ug_color_chip.hide()

            # 6. Active Effect Selection
            target_effect = cfg.get("mode", self.engine.effect_name)
            self.engine.effect_name = target_effect
            if hasattr(self, "effects_list"):
                for i in range(self.effects_list.count()):
                    item = self.effects_list.item(i)
                    if item.data(Qt.ItemDataRole.UserRole) == target_effect:
                        self.effects_list.setCurrentRow(i)
                        break

            # 7. Reconfigure dynamic parameter deck and refresh color chips
            self._reconfigure_deck_for_effect(target_effect)
            self._select_color_target(self.active_color_target)
            self._refresh_color_chips()
            self.engine.mark_dirty()

        except Exception as e:
            print(f"[WARN] Error applying profile settings: {e}")
        finally:
            self._suppress_slider_events = False

    def _get_config_path(self) -> str:
        """Determines config.json path adjacent to the executable or project root."""
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "config.json")

    def save_settings(self):
        """Serializes current engine, profiles, and UI state to config.json."""
        try:
            current_dict = self._capture_current_profile_dict()
            if not hasattr(self, "profiles") or not isinstance(self.profiles, dict):
                self.profiles = {}
            self.profiles[str(self.active_profile_slot)] = current_dict

            config_data = dict(current_dict)
            config_data["active_profile"] = self.active_profile_slot
            config_data["profiles"] = self.profiles

            cfg_path = self._get_config_path()
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save settings to config.json: {e}")

    def load_settings(self):
        """Loads persisted state from config.json and configures self.engine and UI controls."""
        cfg_path = self._get_config_path()
        defaults = self._get_default_profiles()

        if not os.path.exists(cfg_path):
            self.profiles = defaults
            self.active_profile_slot = 1
            self._update_profile_buttons_style()
            return

        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to read config.json: {e}")
            self.profiles = defaults
            self.active_profile_slot = 1
            self._update_profile_buttons_style()
            return

        raw_profiles = cfg.get("profiles", {})
        self.profiles = {}
        for s in range(1, 6):
            s_key = str(s)
            if s_key in raw_profiles and isinstance(raw_profiles[s_key], dict):
                self.profiles[s_key] = raw_profiles[s_key]
            elif s == 1 and ("mode" in cfg or "color_a" in cfg):
                # Backwards compatibility: seed slot 1 with legacy flat root keys
                self.profiles[s_key] = {k: v for k, v in cfg.items() if k not in ("profiles", "active_profile")}
            else:
                self.profiles[s_key] = defaults.get(s_key, {})

        active_slot = cfg.get("active_profile", 1)
        try:
            active_slot = int(active_slot)
            if active_slot not in range(1, 6):
                active_slot = 1
        except Exception:
            active_slot = 1
        self.active_profile_slot = active_slot

        # Apply settings for active profile
        active_prof_data = self.profiles.get(str(self.active_profile_slot), self.profiles.get("1", {}))
        self._apply_profile_dict(active_prof_data)
        self._update_profile_buttons_style()

    # --------------------------------------------------------------------------
    # 8. SYSTEM TRAY DAEMON INTEGRATION
    # --------------------------------------------------------------------------
    def _setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Everest Studio Pro - Mountain Everest 60")

        menu = QMenu(self)
        show_action = QAction("Open Everest Studio", self)
        show_action.triggered.connect(self.restore_from_tray)
        menu.addAction(show_action)

        hide_action = QAction("Minimize to Tray", self)
        hide_action.triggered.connect(self.hide)
        menu.addAction(hide_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close_application)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)

        icon = self.windowIcon()
        if not icon.isNull():
            self.tray_icon.setIcon(icon)
        self.tray_icon.show()

    def restore_from_tray(self):
        """Restores and activates the main dashboard window."""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self.restore_from_tray()

    def changeEvent(self, event):
        if event.type() == event.Type.WindowStateChange:
            if self.isMinimized():
                self.hide()
                if hasattr(self, "tray_icon") and self.tray_icon:
                    self.tray_icon.showMessage(
                        "Everest Studio Pro",
                        "Lighting engine continues running at 35 FPS in the background.",
                        QSystemTrayIcon.MessageIcon.Information,
                        1500
                    )
        super().changeEvent(event)

    def close_application(self):
        """Flushes configuration to disk, halts lighting engine, and cleanly quits."""
        self.save_settings()
        self.engine.stop()
        if hasattr(self, "tray_icon") and self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        """Intercepts window close: hides to system tray instead of stopping the daemon."""
        if hasattr(self, "tray_icon") and self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.showMessage(
                "Everest Studio Pro",
                "Minimized to system tray. Lighting engine continues running.",
                QSystemTrayIcon.MessageIcon.Information,
                1500,
            )
            event.ignore()
        else:
            self.close_application()
            event.accept()


# Alias for clean importing
MainWindow = EverestStudioWindow
