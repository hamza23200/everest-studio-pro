"""
Everest Studio Pro - Master Window (Base Camp Replica & Upgrade).
Implements context-sensitive Dynamic Parameter Deck, full 147-LED Underglow
and modular Numpad Dock controls (Detached/Left/Right), independent dual
base/reactive brightness pipeline, per-effect 5-slot profile management,
and zero-copy 35 FPS visualizer synchronization.
"""

import os
import sys
import json
from typing import Optional, Dict
import threading
from PySide6.QtCore import Qt, Signal, QSize, QTimer
from PySide6.QtGui import QColor, QAction, QFont, QBrush
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
    QApplication,
    QScrollArea,
    QComboBox,
)
from openrgb.utils import RGBColor

from engine.lighting_engine import LightingEngineThread
from engine.screen_worker import ScreenCaptureWorker
from gui.keyboard_canvas import EverestKeyboardCanvas
from gui.color_picker import BaseCampColorPicker

PROP_CLASS = "class"
CLASS_CARD_PANEL = "CardPanel"
CLASS_TOOL_BUTTON = "ToolButton"
TARGET_COLOR_A = "color_a"
TARGET_COLOR_B = "color_b"
TARGET_UNDERGLOW = "underglow"
MODE_SINGLE = "single"
MODE_DUAL = "dual"
MODE_RAINBOW = "rainbow"
DIR_RIGHT = "right"
DIR_LEFT = "left"
DIR_DETACHED = "detached"
BRUSH_PAINT = "paint"
BRUSH_ERASE = "erase"

EFFECT_CATEGORIES = [
    ("AMBIENT", [
        ("Color Wave", "wave"),
        ("Waterfall", "waterfall"),
        ("Aurora", "aurora"),
        ("Breathing & Pulse", "breathing"),
        ("Gradient Breathing", "gradient_breathing"),
        ("Cosmic Drift", "cosmic_drift"),
        ("Thunderstorm", "thunderstorm"),
        ("System Malfunction", "system_malfunction"),
    ]),
    ("DYNAMIC FX", [
        ("Tornado", "tornado"),
        ("DNA Spiral", "dna_spiral"),
        ("Row Sweep", "row_sweep"),
        ("Falling Matrix", "matrix"),
        ("Meteor Shower", "meteor_shower"),
    ]),
    ("REACTIVE", [
        ("Snappy Laser", "laser"),
        ("Expanding Ripple", "ripple"),
        ("Explosion Burst", "explosion_burst"),
        ("Crosshair", "crosshair"),
        ("Full-Board Flash", "full_board_flash"),
        ("Single-Key Punch", "punch"),
        ("Typing Heatmap", "typing_heatmap"),
    ]),
    ("SYSTEM SYNC", [
        ("Audio Equalizer", "audio_equalizer"),
        ("Screen Ambilight", "screen_ambilight"),
    ]),
    ("STATIC & CUSTOM", [
        ("Static Color", "static"),
        ("Custom Per-Key", "custom"),
        ("Lighting Off", "off"),
    ]),
]

ALL_EFFECT_KEYS = [key for _, items in EFFECT_CATEGORIES for _, key in items]


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

    sync_completed = Signal()

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
        self.resize(1260, 840)
        self.setMinimumSize(1080, 750)

        # Active color binding target ('color_a', 'color_b', or 'underglow')
        self.active_color_target = TARGET_COLOR_A
        self._suppress_slider_events = False

        # Per-Effect 5-Slot Profile Engine State
        self.active_profile_slot = 1
        self.brush_mode = BRUSH_PAINT
        self.effect_profiles: Dict[str, dict] = {}
        self.profile_buttons: Dict[int, QPushButton] = {}
        self.dock_buttons: Dict[str, QPushButton] = {}

        self._apply_qss_stylesheet()
        self._build_ui()
        self._setup_tray_icon()
        self._wire_engine_signals()

        self._sync_status_timer = QTimer(self)
        self._sync_status_timer.setInterval(500)
        self._sync_status_timer.timeout.connect(self._refresh_sync_status_hint)
        self._sync_status_timer.start()

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
                height: 30px;
                padding-left: 14px;
                border-radius: 4px;
                margin: 1px 6px;
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
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #14161B;
                width: 6px;
                margin: 2px 0;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #20232B;
                min-height: 24px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #0078D7;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
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
            QComboBox {
                background-color: #262A35;
                color: #FFFFFF;
                border: 1px solid #333947;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: bold;
                min-width: 170px;
            }
            QComboBox:hover {
                border-color: #0078D7;
            }
            QComboBox QAbstractItemView {
                background-color: #20232B;
                color: #FFFFFF;
                border: 1px solid #333947;
                selection-background-color: #0078D7;
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

        # 3. Main Stage (Top Bar + Visualizer + Numpad Dock + Underglow Strip + Parameter Deck)
        stage_widget = QWidget()
        stage_layout = QVBoxLayout(stage_widget)
        stage_layout.setContentsMargins(20, 14, 20, 16)
        stage_layout.setSpacing(10)

        stage_layout.addWidget(self._build_top_header())

        # Visualizer Canvas Container
        canvas_card = QFrame()
        canvas_card.setProperty(PROP_CLASS, CLASS_CARD_PANEL)
        canvas_card_layout = QVBoxLayout(canvas_card)
        canvas_card_layout.setContentsMargins(10, 8, 10, 8)

        self.canvas = EverestKeyboardCanvas()
        self.canvas.key_clicked.connect(self._on_canvas_key_clicked)
        canvas_card_layout.addWidget(self.canvas)
        stage_layout.addWidget(canvas_card, stretch=4)

        # Modular Numpad Dock Segmented Control
        stage_layout.addWidget(self._build_numpad_dock_panel())

        # Dedicated Underglow (44/66-LED Edge Strip) Panel
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
    # 2. EFFECTS COLUMN (Categorized Scrollable Sidebar)
    # --------------------------------------------------------------------------
    def _build_effects_column(self) -> QWidget:
        col = QWidget()
        col.setObjectName("effects_column")
        col.setFixedWidth(212)
        layout = QVBoxLayout(col)
        layout.setContentsMargins(6, 18, 6, 12)
        layout.setSpacing(6)

        header = QLabel("LIGHTING EFFECTS")
        header.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold; padding-left: 12px; letter-spacing: 1px;")
        layout.addWidget(header)

        self.effects_scroll_area = QScrollArea()
        self.effects_scroll_area.setWidgetResizable(True)
        self.effects_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.effects_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.effects_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.effects_list = QListWidget()
        self.effects_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.effects_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header_font = QFont("Segoe UI", 8)
        header_font.setBold(True)
        header_font.setPixelSize(10)
        header_fg = QBrush(QColor("#7A8294"))

        total_height = 8
        first_effect_row = None
        for cat_idx, (cat_title, entries) in enumerate(EFFECT_CATEGORIES):
            hdr_item = QListWidgetItem(f"  {cat_title}")
            hdr_item.setFlags(Qt.ItemFlag.NoItemFlags)
            hdr_item.setData(Qt.ItemDataRole.UserRole, None)
            hdr_item.setFont(header_font)
            hdr_item.setForeground(header_fg)
            hdr_height = 22 if cat_idx == 0 else 26
            hdr_item.setSizeHint(QSize(180, hdr_height))
            self.effects_list.addItem(hdr_item)
            total_height += hdr_height

            for name, key in entries:
                item = QListWidgetItem(f"  {name}")
                item.setData(Qt.ItemDataRole.UserRole, key)
                item.setSizeHint(QSize(180, 32))
                self.effects_list.addItem(item)
                if first_effect_row is None:
                    first_effect_row = self.effects_list.count() - 1
                total_height += 32

        self.effects_list.setFixedHeight(total_height + 10)
        if first_effect_row is not None:
            self.effects_list.setCurrentRow(first_effect_row)
        self.effects_list.currentItemChanged.connect(self._on_effect_changed)

        self.effects_scroll_area.setWidget(self.effects_list)
        layout.addWidget(self.effects_scroll_area)
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
        subtitle = QLabel("BASE CAMP STUDIO PRO  •  147 TOTAL LEDS  •  MODULAR NUMPAD SUPPORT")
        subtitle.setStyleSheet("font-size: 10px; font-weight: bold; color: #8A8F9D; letter-spacing: 1.2px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        layout.addLayout(title_box)

        layout.addStretch()

        self.sync_btn = QPushButton("🔄 SYNC")
        self.sync_btn.setFixedHeight(24)
        self.sync_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_btn.setToolTip("Performs virtual USB reset of Everest 60 interfaces, restarts OpenRGB server, and re-asserts Direct Mode")
        self.sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B2F3A;
                color: #FFFFFF;
                font-size: 10px;
                font-weight: bold;
                border-radius: 12px;
                padding: 2px 14px;
                border: 1px solid #3D4454;
            }
            QPushButton:hover {
                background-color: #0078D7;
                border-color: #0078D7;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: #005A9E;
                border-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #232730;
                color: #9CA3AF;
                border-color: #2E323D;
            }
        """)
        self.sync_btn.clicked.connect(self._on_sync_clicked)
        self.sync_button = self.sync_btn
        layout.addWidget(self.sync_btn)

        layout.addSpacing(8)

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
    # 4. MODULAR NUMPAD DOCK SEGMENTED CONTROL
    # --------------------------------------------------------------------------
    def _build_numpad_dock_panel(self) -> QWidget:
        panel = QFrame()
        panel.setProperty(PROP_CLASS, CLASS_CARD_PANEL)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(10)

        dock_title = QLabel("NUMPAD DOCK:")
        dock_title.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold; letter-spacing: 0.8px;")
        layout.addWidget(dock_title)

        self.dock_buttons = {}
        for pos_key, label in [("detached", "Detached (Off)"), ("left", "Left Dock"), ("right", "Right Dock")]:
            btn = QPushButton(label)
            btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
            btn.setCheckable(True)
            if pos_key == self.engine.dock_position:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, p=pos_key: self._set_dock_position(p))
            layout.addWidget(btn)
            self.dock_buttons[pos_key] = btn

        layout.addStretch()
        return panel

    def _set_dock_position(self, pos: str):
        pos_clean = pos.lower()
        if pos_clean not in (DIR_RIGHT, DIR_LEFT, DIR_DETACHED):
            pos_clean = DIR_RIGHT
        self.engine.dock_position = pos_clean
        self.canvas.dock_position = pos_clean
        if hasattr(self, "dock_buttons"):
            for p, btn in self.dock_buttons.items():
                btn.setChecked(p == pos_clean)
        if not self._suppress_slider_events:
            self.save_settings()

    # --------------------------------------------------------------------------
    # 5. DEDICATED UNDERGLOW (EDGE STRIP) PANEL
    # --------------------------------------------------------------------------
    def _build_underglow_panel(self) -> QWidget:
        panel = QFrame()
        panel.setProperty(PROP_CLASS, CLASS_CARD_PANEL)
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        ug_title = QLabel("UNDERGLOW (PERIMETER STRIP):")
        ug_title.setStyleSheet("color: #EAB308; font-size: 11px; font-weight: bold; letter-spacing: 0.8px;")
        layout.addWidget(ug_title)

        self.ug_sync_btn = QPushButton("Sync with Effect")
        self.ug_sync_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.ug_sync_btn.setCheckable(True)
        self.ug_sync_btn.setChecked(True)
        self.ug_sync_btn.clicked.connect(lambda: self._set_underglow_mode("sync"))

        self.ug_static_btn = QPushButton("Static Custom Color")
        self.ug_static_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.ug_static_btn.setCheckable(True)
        self.ug_static_btn.clicked.connect(lambda: self._set_underglow_mode("static"))

        self.ug_off_btn = QPushButton("Off")
        self.ug_off_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.ug_off_btn.setCheckable(True)
        self.ug_off_btn.clicked.connect(lambda: self._set_underglow_mode("off"))

        layout.addWidget(self.ug_sync_btn)
        layout.addWidget(self.ug_static_btn)
        layout.addWidget(self.ug_off_btn)

        layout.addSpacing(12)

        self.ug_color_chip = QPushButton("  Underglow Color  ")
        self.ug_color_chip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ug_color_chip.setFixedHeight(28)
        self.ug_color_chip.clicked.connect(lambda: self._select_color_target(TARGET_UNDERGLOW))
        layout.addWidget(self.ug_color_chip)
        self.ug_color_chip.hide()

        layout.addStretch()

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
    # 6. BOTTOM CONTEXT-SENSITIVE CONFIGURATION DECK
    # --------------------------------------------------------------------------
    def _build_bottom_deck(self) -> QWidget:
        deck = QWidget()
        deck_layout = QHBoxLayout(deck)
        deck_layout.setContentsMargins(0, 0, 0, 0)
        deck_layout.setSpacing(16)

        left_card = QFrame()
        left_card.setProperty(PROP_CLASS, CLASS_CARD_PANEL)
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

        # A. Palette Mode Row (Single / Dual / Rainbow)
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
        self.chip_a_btn.clicked.connect(lambda: self._select_color_target(TARGET_COLOR_A))

        self.chip_b_btn = QPushButton("  [Color B]  ")
        self.chip_b_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chip_b_btn.setFixedHeight(28)
        self.chip_b_btn.clicked.connect(lambda: self._select_color_target(TARGET_COLOR_B))

        chips_layout.addWidget(self.chip_a_btn)
        chips_layout.addWidget(self.chip_b_btn)
        chips_layout.addStretch()
        left_layout.addWidget(self.chips_row_widget)

        # C. Primary Speed Slider
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

        # D. Secondary Decay Duration Slider
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
        self.decay_slider.setRange(5, 50)
        self.decay_slider.setValue(16)
        self.decay_slider.valueChanged.connect(self._on_decay_slider_changed)

        decay_box.addLayout(decay_header)
        decay_box.addWidget(self.decay_slider)
        left_layout.addWidget(self.decay_widget)
        self.decay_widget.hide()

        # E. Dual Brightness Sliders (Base + Reactive)
        dual_bright_layout = QHBoxLayout()
        dual_bright_layout.setSpacing(14)

        # 1. Base Brightness
        base_bright_box = QVBoxLayout()
        base_bright_box.setSpacing(4)
        base_bright_header = QHBoxLayout()
        base_bright_lbl = QLabel("☀  BASE BRIGHTNESS")
        base_bright_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        self.base_bright_val_lbl = QLabel(f"{int(self.engine.base_brightness)}%")
        self.base_bright_val_lbl.setStyleSheet("color: #0078D7; font-size: 11px; font-weight: bold;")
        base_bright_header.addWidget(base_bright_lbl)
        base_bright_header.addStretch()
        base_bright_header.addWidget(self.base_bright_val_lbl)

        self.base_bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.base_bright_slider.setRange(0, 100)
        self.base_bright_slider.setValue(int(self.engine.base_brightness))
        self.base_bright_slider.valueChanged.connect(self._on_base_brightness_changed)
        base_bright_box.addLayout(base_bright_header)
        base_bright_box.addWidget(self.base_bright_slider)
        dual_bright_layout.addLayout(base_bright_box, stretch=1)

        # 2. Reactive Brightness
        self.react_bright_widget = QWidget()
        react_bright_box = QVBoxLayout(self.react_bright_widget)
        react_bright_box.setContentsMargins(0, 0, 0, 0)
        react_bright_box.setSpacing(4)
        react_bright_header = QHBoxLayout()
        react_bright_lbl = QLabel("⚡  REACTIVE BRIGHTNESS")
        react_bright_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        self.react_bright_val_lbl = QLabel(f"{int(self.engine.reactive_brightness)}%")
        self.react_bright_val_lbl.setStyleSheet("color: #0078D7; font-size: 11px; font-weight: bold;")
        react_bright_header.addWidget(react_bright_lbl)
        react_bright_header.addStretch()
        react_bright_header.addWidget(self.react_bright_val_lbl)

        self.react_bright_slider = QSlider(Qt.Orientation.Horizontal)
        self.react_bright_slider.setRange(0, 100)
        self.react_bright_slider.setValue(int(self.engine.reactive_brightness))
        self.react_bright_slider.valueChanged.connect(self._on_reactive_brightness_changed)
        react_bright_box.addLayout(react_bright_header)
        react_bright_box.addWidget(self.react_bright_slider)
        dual_bright_layout.addWidget(self.react_bright_widget, stretch=1)

        left_layout.addLayout(dual_bright_layout)

        # Backwards-compatibility aliases
        self.bright_slider = self.base_bright_slider
        self.bright_val_lbl = self.base_bright_val_lbl

        # F. Color Wave Directional Pad
        self.wave_dir_frame = QWidget()
        dir_layout = QHBoxLayout(self.wave_dir_frame)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_lbl = QLabel("WAVE DIRECTION:")
        dir_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        dir_layout.addWidget(dir_lbl)

        self.dir_buttons = {}
        for d_name, d_symbol in [(DIR_LEFT, "←"), (DIR_RIGHT, "→"), ("up", "↑"), ("down", "↓"), ("diagonal", "⬈")]:
            btn = QPushButton(d_symbol)
            btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
            btn.setCheckable(True)
            if d_name == DIR_RIGHT:
                btn.setChecked(True)
            btn.clicked.connect(lambda _, d=d_name: self._set_wave_direction(d))
            dir_layout.addWidget(btn)
            self.dir_buttons[d_name] = btn
        dir_layout.addStretch()
        left_layout.addWidget(self.wave_dir_frame)

        # G. Tornado Rotation Direction Pad
        self.tornado_dir_frame = QWidget()
        t_dir_layout = QHBoxLayout(self.tornado_dir_frame)
        t_dir_layout.setContentsMargins(0, 0, 0, 0)
        t_dir_lbl = QLabel("SPIN DIRECTION:")
        t_dir_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        t_dir_layout.addWidget(t_dir_lbl)

        self.tornado_cw_btn = QPushButton("↻  Clockwise")
        self.tornado_cw_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.tornado_cw_btn.setCheckable(True)
        self.tornado_cw_btn.setChecked(True)
        self.tornado_cw_btn.clicked.connect(lambda: self._set_tornado_direction(True))

        self.tornado_ccw_btn = QPushButton("↺  Counter-Clockwise")
        self.tornado_ccw_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.tornado_ccw_btn.setCheckable(True)
        self.tornado_ccw_btn.clicked.connect(lambda: self._set_tornado_direction(False))

        t_dir_layout.addWidget(self.tornado_cw_btn)
        t_dir_layout.addWidget(self.tornado_ccw_btn)
        t_dir_layout.addStretch()
        left_layout.addWidget(self.tornado_dir_frame)
        self.tornado_dir_frame.hide()

        # H. Custom Per-Key Suite (Base Color, Brush Mode Paint/Erase, Active Brush Color, Fill/Clear)
        self.custom_controls_widget = QWidget()
        custom_vbox = QVBoxLayout(self.custom_controls_widget)
        custom_vbox.setContentsMargins(0, 0, 0, 0)
        custom_vbox.setSpacing(8)

        # Row 1: Base Color + Brush Mode Segmented Control + Active Brush Color
        row1_box = QHBoxLayout()
        row1_box.setContentsMargins(0, 0, 0, 0)
        row1_box.setSpacing(10)

        base_col_lbl = QLabel("BASE COLOR:")
        base_col_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        row1_box.addWidget(base_col_lbl)

        self.custom_base_btn = QPushButton("  Base Color  ")
        self.custom_base_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.custom_base_btn.setFixedHeight(28)
        self.custom_base_btn.clicked.connect(lambda: self._select_color_target(TARGET_COLOR_B))
        row1_box.addWidget(self.custom_base_btn)

        row1_box.addSpacing(6)

        brush_mode_lbl = QLabel("BRUSH MODE:")
        brush_mode_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        row1_box.addWidget(brush_mode_lbl)

        self.brush_paint_btn = QPushButton("🖌️  Paint")
        self.brush_paint_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.brush_paint_btn.setCheckable(True)
        self.brush_paint_btn.setChecked(True)
        self.brush_paint_btn.clicked.connect(lambda: self._set_brush_mode(BRUSH_PAINT))
        row1_box.addWidget(self.brush_paint_btn)

        self.brush_erase_btn = QPushButton("🧼  Erase")
        self.brush_erase_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.brush_erase_btn.setCheckable(True)
        self.brush_erase_btn.setChecked(False)
        self.brush_erase_btn.clicked.connect(lambda: self._set_brush_mode(BRUSH_ERASE))
        row1_box.addWidget(self.brush_erase_btn)

        row1_box.addSpacing(6)

        brush_col_lbl = QLabel("ACTIVE BRUSH COLOR:")
        brush_col_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        row1_box.addWidget(brush_col_lbl)

        self.custom_brush_btn = QPushButton("  Active Brush Color  ")
        self.custom_brush_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.custom_brush_btn.setFixedHeight(28)
        self.custom_brush_btn.clicked.connect(lambda: self._select_color_target(TARGET_COLOR_A))
        row1_box.addWidget(self.custom_brush_btn)

        row1_box.addStretch()
        custom_vbox.addLayout(row1_box)

        # Row 2: Action buttons and guidance hint
        row2_box = QHBoxLayout()
        row2_box.setContentsMargins(0, 0, 0, 0)
        row2_box.setSpacing(10)

        custom_hint = QLabel("Click or drag across keys on the visualizer to paint or erase:")
        custom_hint.setStyleSheet("color: #8A8F9D; font-size: 11px;")
        row2_box.addWidget(custom_hint)
        row2_box.addStretch()

        fill_all_btn = QPushButton("🎨  Fill All Keys")
        fill_all_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        fill_all_btn.clicked.connect(self._fill_all_custom_keys)
        row2_box.addWidget(fill_all_btn)

        clear_all_btn = QPushButton("🧼  Clear / Erase All")
        clear_all_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        clear_all_btn.clicked.connect(self._clear_all_custom_keys)
        row2_box.addWidget(clear_all_btn)

        custom_vbox.addLayout(row2_box)
        left_layout.addWidget(self.custom_controls_widget)
        self.custom_controls_widget.hide()
        self.custom_actions_frame = self.custom_controls_widget

        # I. DNA Spiral Direction Pad
        self.dna_dir_frame = QWidget()
        dna_layout = QHBoxLayout(self.dna_dir_frame)
        dna_layout.setContentsMargins(0, 0, 0, 0)
        dna_lbl = QLabel("SPIRAL DIRECTION:")
        dna_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        dna_layout.addWidget(dna_lbl)

        self.dna_outward_btn = QPushButton("Outward")
        self.dna_outward_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.dna_outward_btn.setCheckable(True)
        self.dna_outward_btn.setChecked(True)
        self.dna_outward_btn.clicked.connect(lambda: self._set_dna_direction(True))

        self.dna_inward_btn = QPushButton("Inward")
        self.dna_inward_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.dna_inward_btn.setCheckable(True)
        self.dna_inward_btn.clicked.connect(lambda: self._set_dna_direction(False))

        dna_layout.addWidget(self.dna_outward_btn)
        dna_layout.addWidget(self.dna_inward_btn)
        dna_layout.addStretch()
        left_layout.addWidget(self.dna_dir_frame)
        self.dna_dir_frame.hide()

        # J. Typing Heatmap Controls (Live Decay vs Session Persistent + Reset)
        self.heatmap_controls_widget = QWidget()
        hm_layout = QHBoxLayout(self.heatmap_controls_widget)
        hm_layout.setContentsMargins(0, 0, 0, 0)
        hm_layout.setSpacing(8)
        hm_lbl = QLabel("HEATMAP MODE:")
        hm_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        hm_layout.addWidget(hm_lbl)

        self.heatmap_live_btn = QPushButton("Live Decay")
        self.heatmap_live_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.heatmap_live_btn.setCheckable(True)
        self.heatmap_live_btn.setChecked(True)
        self.heatmap_live_btn.clicked.connect(lambda: self._set_heatmap_mode("live"))

        self.heatmap_persist_btn = QPushButton("Session Persistent")
        self.heatmap_persist_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.heatmap_persist_btn.setCheckable(True)
        self.heatmap_persist_btn.clicked.connect(lambda: self._set_heatmap_mode("persistent"))

        self.heatmap_reset_btn = QPushButton("Reset Heatmap")
        self.heatmap_reset_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.heatmap_reset_btn.clicked.connect(self._on_reset_heatmap_clicked)

        hm_layout.addWidget(self.heatmap_live_btn)
        hm_layout.addWidget(self.heatmap_persist_btn)
        hm_layout.addWidget(self.heatmap_reset_btn)
        hm_layout.addStretch()
        left_layout.addWidget(self.heatmap_controls_widget)
        self.heatmap_controls_widget.hide()

        # K. Audio Equalizer Controls (Style: Spectrum Bars vs Bass Pulse)
        self.audio_controls_widget = QWidget()
        aud_layout = QHBoxLayout(self.audio_controls_widget)
        aud_layout.setContentsMargins(0, 0, 0, 0)
        aud_layout.setSpacing(8)
        aud_lbl = QLabel("AUDIO STYLE:")
        aud_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        aud_layout.addWidget(aud_lbl)

        self.audio_bars_btn = QPushButton("Spectrum Bars")
        self.audio_bars_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.audio_bars_btn.setCheckable(True)
        self.audio_bars_btn.setChecked(True)
        self.audio_bars_btn.clicked.connect(lambda: self._set_audio_style("bars"))

        self.audio_bass_btn = QPushButton("Bass Pulse")
        self.audio_bass_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.audio_bass_btn.setCheckable(True)
        self.audio_bass_btn.clicked.connect(lambda: self._set_audio_style("bass_pulse"))

        aud_layout.addWidget(self.audio_bars_btn)
        aud_layout.addWidget(self.audio_bass_btn)
        aud_layout.addStretch()
        left_layout.addWidget(self.audio_controls_widget)
        self.audio_controls_widget.hide()

        # L. Screen Ambilight Controls (Capture Mode & Monitor Selector)
        self.screen_controls_widget = QWidget()
        scr_layout = QHBoxLayout(self.screen_controls_widget)
        scr_layout.setContentsMargins(0, 0, 0, 0)
        scr_layout.setSpacing(8)
        scr_lbl = QLabel("CAPTURE MODE:")
        scr_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")
        scr_layout.addWidget(scr_lbl)

        self.screen_grid_btn = QPushButton("Full Screen Grid")
        self.screen_grid_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.screen_grid_btn.setCheckable(True)
        self.screen_grid_btn.setChecked(True)
        self.screen_grid_btn.clicked.connect(lambda: self._set_screen_mode("grid"))

        self.screen_edges_btn = QPushButton("Monitor Edges Only")
        self.screen_edges_btn.setProperty(PROP_CLASS, CLASS_TOOL_BUTTON)
        self.screen_edges_btn.setCheckable(True)
        self.screen_edges_btn.clicked.connect(lambda: self._set_screen_mode("edges"))

        mon_lbl = QLabel("MONITOR:")
        mon_lbl.setStyleSheet("color: #8A8F9D; font-size: 11px; font-weight: bold;")

        self.monitor_combo = QComboBox()
        for mon_idx, mon_label in ScreenCaptureWorker.list_monitors():
            self.monitor_combo.addItem(mon_label, mon_idx)
        self.monitor_combo.currentIndexChanged.connect(self._on_monitor_changed)

        scr_layout.addWidget(self.screen_grid_btn)
        scr_layout.addWidget(self.screen_edges_btn)
        scr_layout.addSpacing(8)
        scr_layout.addWidget(mon_lbl)
        scr_layout.addWidget(self.monitor_combo)
        scr_layout.addStretch()
        left_layout.addWidget(self.screen_controls_widget)
        self.screen_controls_widget.hide()

        # M. Live System Sync Device/Capture Status Hint
        self.sync_status_lbl = QLabel("")
        self.sync_status_lbl.setStyleSheet(
            "color: #9CA3AF; background-color: #181A1F; border: 1px solid #2B2F3A; "
            "border-radius: 6px; padding: 6px 10px; font-size: 11px;"
        )
        left_layout.addWidget(self.sync_status_lbl)
        self.sync_status_lbl.hide()

        left_layout.addStretch()
        deck_layout.addWidget(left_card, stretch=3)

        # Right Card: Base Camp Custom Color Picker
        right_card = QFrame()
        right_card.setProperty(PROP_CLASS, CLASS_CARD_PANEL)
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(14, 10, 14, 10)

        self.picker_header_lbl = QLabel("COLOR PALETTE  —  EDITING [COLOR A]")
        self.picker_header_lbl.setStyleSheet("color: #0078D7; font-size: 11px; font-weight: bold; letter-spacing: 0.8px;")
        right_layout.addWidget(self.picker_header_lbl)

        self.color_picker = BaseCampColorPicker(initial_color=QColor("#FFFF00"))
        self.color_picker.color_changed.connect(self._on_picker_color_changed)
        right_layout.addWidget(self.color_picker)

        deck_layout.addWidget(right_card, stretch=2)

        return deck

    # --------------------------------------------------------------------------
    # 7. ENGINE SIGNALS & CONTEXT-SENSITIVE LOGIC
    # --------------------------------------------------------------------------
    def _wire_engine_signals(self):
        self.engine.frame_rendered.connect(self.canvas.update_leds)
        if hasattr(self.engine, "underglow_rendered"):
            self.engine.underglow_rendered.connect(self.canvas.update_underglow)
        self.engine.key_pressed.connect(self.canvas.trigger_flare)
        self.engine.connection_changed.connect(self._on_connection_status_changed)
        self.sync_completed.connect(self._on_sync_finished)

    def _on_sync_clicked(self, *_args):
        """Runs virtual USB reset + OpenRGB restart off the GUI thread while updating button state."""
        if not self.sync_btn.isEnabled():
            return
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("⏳ SYNCING...")

        def _worker():
            try:
                self.engine.force_hardware_sync(reset_usb=True)
            finally:
                self.sync_completed.emit()

        threading.Thread(target=_worker, daemon=True).start()

    def _on_sync_finished(self):
        """Restores the SYNC button on the Qt GUI thread once sync completes."""
        self.sync_btn.setText("🔄 SYNC")
        self.sync_btn.setEnabled(True)

    def _on_status_badge_clicked(self):
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

    def _on_effect_changed(self, current: QListWidgetItem, previous: QListWidgetItem):
        if not current:
            return

        if previous:
            prev_eff = previous.data(Qt.ItemDataRole.UserRole)
            if prev_eff:
                prev_entry = self._get_or_create_effect_profile(prev_eff)
                prev_entry["slots"][str(self.active_profile_slot)] = self._capture_current_profile_dict()
                prev_entry["active_slot"] = self.active_profile_slot

        new_eff = current.data(Qt.ItemDataRole.UserRole)
        if not new_eff:
            return
        self.engine.effect_name = new_eff

        eff_entry = self._get_or_create_effect_profile(new_eff)
        active_slot = eff_entry.get("active_slot", 1)
        self.active_profile_slot = active_slot
        slot_data = eff_entry["slots"].get(str(active_slot), {})

        self._apply_profile_dict(slot_data)
        self._reconfigure_deck_for_effect(new_eff)
        self._update_profile_buttons_style()

        if not self._suppress_slider_events:
            self.save_settings()

    def _reconfigure_deck_for_effect(self, effect_key: str):
        """Dynamically reconfigures sliders, palette radios, and direction pads for the chosen effect."""
        self._suppress_slider_events = True

        self.wave_dir_frame.hide()
        self.tornado_dir_frame.hide()
        self.custom_controls_widget.hide()
        self.dna_dir_frame.hide()
        self.heatmap_controls_widget.hide()
        self.audio_controls_widget.hide()
        self.screen_controls_widget.hide()
        self.sync_status_lbl.hide()
        self.decay_widget.hide()
        self.profile_container.show()
        self.speed_widget.show()
        self.palette_row_widget.show()
        self.chips_row_widget.show()

        self.mode_single_rb.setText("Single Color")
        self.mode_dual_rb.setText("Dual Color")
        self.mode_rainbow_rb.setText("Rainbow")
        self.mode_rainbow_rb.show()
        self.mode_dual_rb.show()
        self.mode_single_rb.show()

        # Show reactive brightness slider for reactive effects, custom mode, and audio equalizer
        is_reactive = effect_key in (
            "laser", "ripple", "punch", "custom",
            "crosshair", "full_board_flash", "explosion_burst", "typing_heatmap",
            "audio_equalizer",
        )
        self.react_bright_widget.setVisible(is_reactive)

        if self._reconfigure_v3_effect(effect_key):
            pass
        elif effect_key == "wave":
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
            self.mode_rainbow_rb.hide()
            if self.mode_rainbow_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = MODE_DUAL

            self.speed_title_lbl.setText("LASER VELOCITY (KEYS / SEC)")
            self.speed_slider.setRange(5, 120)
            self.speed_slider.setValue(int(self.engine.laser_speed))
            self.speed_val_lbl.setText(f"{int(self.engine.laser_speed)} keys/s")

            self.decay_widget.show()
            self.decay_title_lbl.setText("TRAIL DECAY DURATION")
            self.decay_slider.setRange(5, 300)
            self.decay_slider.setValue(int(round(self.engine.laser_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.laser_decay:.2f} s")

            self.chip_a_btn.setText("  [Color A: Laser Beam]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")

        elif effect_key == "punch":
            self.mode_rainbow_rb.hide()
            if self.mode_rainbow_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = MODE_DUAL

            self.speed_widget.hide()
            self.decay_widget.show()
            self.decay_title_lbl.setText("KEY LINGER / FADE DURATION")
            self.decay_slider.setRange(10, 300)
            self.decay_slider.setValue(int(round(self.engine.punch_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.punch_decay:.2f} s")

            self.chip_a_btn.setText("  [Color A: Key Strike]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")

        elif effect_key == "ripple":
            self.mode_rainbow_rb.hide()
            if self.mode_rainbow_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = MODE_DUAL

            self.speed_title_lbl.setText("RIPPLE EXPANSION SPEED")
            self.speed_slider.setRange(3, 40)
            self.speed_slider.setValue(int(self.engine.ripple_speed))
            self.speed_val_lbl.setText(f"{int(self.engine.ripple_speed)} keys/s")

            self.decay_widget.show()
            self.decay_title_lbl.setText("RIPPLE LIFETIME")
            self.decay_slider.setRange(10, 300)
            self.decay_slider.setValue(int(round(self.engine.ripple_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.ripple_decay:.2f} s")

            self.chip_a_btn.setText("  [Color A: Ripple Wave]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")

        elif effect_key == "matrix":
            self.mode_single_rb.setText("Matrix Classic")
            if self.engine.mode_type not in (MODE_SINGLE, MODE_DUAL, MODE_RAINBOW):
                self.mode_single_rb.setChecked(True)
                self.engine.mode_type = MODE_SINGLE

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
            self._select_color_target(TARGET_COLOR_A)

        elif effect_key == "custom":
            self.palette_row_widget.hide()
            self.chips_row_widget.hide()
            self.speed_widget.hide()
            self.custom_controls_widget.show()
            self._select_color_target(TARGET_COLOR_A)

        elif effect_key == "off":
            self.palette_row_widget.hide()
            self.chips_row_widget.hide()
            self.speed_widget.hide()

        self._suppress_slider_events = False
        self._update_chip_visibility()
        self._refresh_color_chips()

    def _force_single_or_dual_mode(self):
        self.mode_rainbow_rb.hide()
        if self.mode_rainbow_rb.isChecked():
            self.mode_dual_rb.setChecked(True)
            self.engine.mode_type = MODE_DUAL

    def _reconfigure_v3_effect(self, effect_key: str) -> bool:
        """Configures deck sliders and controls for the v3.0 Phase 1 effects."""
        if effect_key == "row_sweep":
            self._force_single_or_dual_mode()
            self.speed_title_lbl.setText("SWEEP SPEED")
            self.speed_slider.setRange(5, 60)
            self.speed_slider.setValue(int(self.engine.sweep_speed))
            self.speed_val_lbl.setText(f"{int(self.engine.sweep_speed)} keys/s")
            self.decay_widget.show()
            self.decay_title_lbl.setText("TRAIL LENGTH")
            self.decay_slider.setRange(10, 120)
            self.decay_slider.setValue(int(round(self.engine.sweep_trail * 10)))
            self.decay_val_lbl.setText(f"{self.engine.sweep_trail:.1f} u")
            self.chip_a_btn.setText("  [Color A: Sweep Trail]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")
            return True

        if effect_key == "waterfall":
            self.mode_single_rb.hide()
            self.mode_rainbow_rb.setText("Multi-Tone Spectrum")
            if self.mode_single_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = MODE_DUAL
            self.speed_title_lbl.setText("FLOW SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.chip_a_btn.setText("  [Color A]  ")
            self.chip_b_btn.setText("  [Color B]  ")
            return True

        if effect_key == "aurora":
            self.palette_row_widget.hide()
            self.speed_title_lbl.setText("DRIFT SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.decay_widget.show()
            self.decay_title_lbl.setText("WAVE SCALE")
            self.decay_slider.setRange(5, 25)
            self.decay_slider.setValue(int(round(self.engine.aurora_scale * 10)))
            self.decay_val_lbl.setText(f"{self.engine.aurora_scale:.1f}x")
            return True

        if effect_key == "gradient_breathing":
            self.palette_row_widget.hide()
            self.speed_title_lbl.setText("BREATHING SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.decay_widget.show()
            self.decay_title_lbl.setText("MIN FLOOR BRIGHTNESS")
            self.decay_slider.setRange(0, 60)
            self.decay_slider.setValue(int(round(self.engine.breath_min_floor)))
            self.decay_val_lbl.setText(f"{int(round(self.engine.breath_min_floor))}%")
            self.chip_a_btn.setText("  [Color A]  ")
            self.chip_b_btn.setText("  [Color B]  ")
            return True

        if effect_key == "cosmic_drift":
            self.palette_row_widget.hide()
            self.speed_title_lbl.setText("DRIFT SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.decay_widget.show()
            self.decay_title_lbl.setText("STAR DENSITY")
            self.decay_slider.setRange(1, 10)
            self.decay_slider.setValue(int(round(self.engine.star_density)))
            self.decay_val_lbl.setText(str(int(round(self.engine.star_density))))
            return True

        if effect_key == "thunderstorm":
            self.palette_row_widget.hide()
            self.speed_title_lbl.setText("STORM INTENSITY")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(round(self.engine.storm_intensity)))
            self.speed_val_lbl.setText(str(int(round(self.engine.storm_intensity))))
            return True

        if effect_key == "system_malfunction":
            self.palette_row_widget.hide()
            self.speed_title_lbl.setText("GLITCH FREQUENCY")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(round(self.engine.glitch_freq)))
            self.speed_val_lbl.setText(str(int(round(self.engine.glitch_freq))))
            self.chip_a_btn.setText("  [Color A: Theme Primary]  ")
            self.chip_b_btn.setText("  [Color B: Theme Secondary]  ")
            return True

        if effect_key == "dna_spiral":
            self.palette_row_widget.hide()
            self.dna_dir_frame.show()
            self.dna_outward_btn.setChecked(self.engine.dna_outward)
            self.dna_inward_btn.setChecked(not self.engine.dna_outward)
            self.speed_title_lbl.setText("ROTATION SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.decay_widget.show()
            self.decay_title_lbl.setText("TWIST DENSITY")
            self.decay_slider.setRange(1, 10)
            self.decay_slider.setValue(int(round(self.engine.dna_twist)))
            self.decay_val_lbl.setText(str(int(round(self.engine.dna_twist))))
            self.chip_a_btn.setText("  [Color A: Strand 1]  ")
            self.chip_b_btn.setText("  [Color B: Strand 2]  ")
            return True

        if effect_key == "meteor_shower":
            self.mode_single_rb.hide()
            if self.mode_single_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = MODE_DUAL
            self.speed_title_lbl.setText("METEOR SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(self.engine.speed))
            self.speed_val_lbl.setText(str(int(self.engine.speed)))
            self.decay_widget.show()
            self.decay_title_lbl.setText("METEOR COUNT")
            self.decay_slider.setRange(4, 10)
            self.decay_slider.setValue(int(self.engine.meteor_count))
            self.decay_val_lbl.setText(str(int(self.engine.meteor_count)))
            self.chip_a_btn.setText("  [Color A: Meteor]  ")
            self.chip_b_btn.setText("  [Color B: Sky Accent]  ")
            return True

        if effect_key == "crosshair":
            self._force_single_or_dual_mode()
            self.speed_title_lbl.setText("BEAM PROPAGATION SPEED")
            self.speed_slider.setRange(10, 120)
            self.speed_slider.setValue(int(self.engine.crosshair_speed))
            self.speed_val_lbl.setText(f"{int(self.engine.crosshair_speed)} keys/s")
            self.decay_widget.show()
            self.decay_title_lbl.setText("DECAY DURATION")
            self.decay_slider.setRange(10, 300)
            self.decay_slider.setValue(int(round(self.engine.crosshair_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.crosshair_decay:.2f} s")
            self.chip_a_btn.setText("  [Color A: Beam]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")
            return True

        if effect_key == "full_board_flash":
            self._force_single_or_dual_mode()
            self.speed_widget.hide()
            self.decay_widget.show()
            self.decay_title_lbl.setText("DECAY DURATION")
            self.decay_slider.setRange(10, 300)
            self.decay_slider.setValue(int(round(self.engine.flash_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.flash_decay:.2f} s")
            self.chip_a_btn.setText("  [Color A: Flash Pulse]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")
            return True

        if effect_key == "explosion_burst":
            self._force_single_or_dual_mode()
            self.speed_title_lbl.setText("BLAST SPEED")
            self.speed_slider.setRange(8, 60)
            self.speed_slider.setValue(int(self.engine.explosion_speed))
            self.speed_val_lbl.setText(f"{int(self.engine.explosion_speed)} keys/s")
            self.decay_widget.show()
            self.decay_title_lbl.setText("DECAY LIFETIME")
            self.decay_slider.setRange(15, 300)
            self.decay_slider.setValue(int(round(self.engine.explosion_decay * 100)))
            self.decay_val_lbl.setText(f"{self.engine.explosion_decay:.2f} s")
            self.chip_a_btn.setText("  [Color A: Blast Wave]  ")
            self.chip_b_btn.setText("  [Color B: Base Idle]  ")
            return True

        if effect_key == "typing_heatmap":
            self.palette_row_widget.hide()
            self.heatmap_controls_widget.show()
            is_live = self.engine.heatmap_mode == "live"
            self.heatmap_live_btn.setChecked(is_live)
            self.heatmap_persist_btn.setChecked(not is_live)
            self.speed_widget.setVisible(is_live)
            self.speed_title_lbl.setText("COOLDOWN SPEED")
            self.speed_slider.setRange(1, 10)
            self.speed_slider.setValue(int(round(self.engine.heatmap_cooldown)))
            self.speed_val_lbl.setText(str(int(round(self.engine.heatmap_cooldown))))
            return True

        if effect_key == "audio_equalizer":
            self.mode_single_rb.hide()
            self.mode_rainbow_rb.setText("Rainbow Spectrum")
            if self.mode_single_rb.isChecked():
                self.mode_dual_rb.setChecked(True)
                self.engine.mode_type = MODE_DUAL
            self.audio_controls_widget.show()
            is_bars = self.engine.audio_style != "bass_pulse"
            self.audio_bars_btn.setChecked(is_bars)
            self.audio_bass_btn.setChecked(not is_bars)
            self.sync_status_lbl.show()
            self._refresh_sync_status_hint()
            self.speed_title_lbl.setText("SENSITIVITY / GAIN")
            self.speed_slider.setRange(5, 40)
            self.speed_slider.setValue(int(round(self.engine.audio_gain * 10)))
            self.speed_val_lbl.setText(f"{self.engine.audio_gain:.1f}x")
            self.decay_widget.show()
            self.decay_title_lbl.setText("SMOOTHING")
            self.decay_slider.setRange(0, 90)
            self.decay_slider.setValue(int(round(self.engine.audio_smoothing * 100)))
            self.decay_val_lbl.setText(f"{self.engine.audio_smoothing:.2f}")
            self.chip_a_btn.setText("  [Color A: Peak]  ")
            self.chip_b_btn.setText("  [Color B: Base / Low]  ")
            return True

        if effect_key == "screen_ambilight":
            self.palette_row_widget.hide()
            self.screen_controls_widget.show()
            is_grid = self.engine.screen_mode != "edges"
            self.screen_grid_btn.setChecked(is_grid)
            self.screen_edges_btn.setChecked(not is_grid)
            mon_idx_pos = self.monitor_combo.findData(self.engine.screen_monitor)
            if mon_idx_pos >= 0:
                self.monitor_combo.setCurrentIndex(mon_idx_pos)
            self.sync_status_lbl.show()
            self._refresh_sync_status_hint()
            self.speed_title_lbl.setText("TEMPORAL SMOOTHING")
            self.speed_slider.setRange(0, 90)
            self.speed_slider.setValue(int(round(self.engine.screen_smoothing * 100)))
            self.speed_val_lbl.setText(f"{self.engine.screen_smoothing:.2f}")
            self.decay_widget.show()
            self.decay_title_lbl.setText("SATURATION BOOST")
            self.decay_slider.setRange(10, 25)
            self.decay_slider.setValue(int(round(self.engine.screen_saturation * 10)))
            self.decay_val_lbl.setText(f"{self.engine.screen_saturation:.1f}x")
            return True

        return False

    def _on_mode_type_toggled(self):
        if self.mode_rainbow_rb.isChecked():
            self.engine.mode_type = MODE_RAINBOW
        elif self.mode_dual_rb.isChecked():
            self.engine.mode_type = MODE_DUAL
            if self.engine.effect_name == "matrix" and not self._suppress_slider_events:
                self.engine.color_a = RGBColor(0, 255, 102)
                self.engine.color_b = RGBColor(0, 59, 16)
        else:
            self.engine.mode_type = MODE_SINGLE

        self._update_chip_visibility()
        self._refresh_color_chips()
        if not self._suppress_slider_events:
            self.save_settings()

    def _update_chip_visibility(self):
        eff = self.engine.effect_name
        no_chips = (
            "off", "custom", "aurora", "cosmic_drift", "thunderstorm",
            "typing_heatmap", "screen_ambilight",
        )
        if eff in no_chips:
            self.chips_row_widget.hide()
            return

        if eff in ("gradient_breathing", "system_malfunction", "dna_spiral"):
            self.chips_row_widget.show()
            self.chip_a_btn.show()
            self.chip_b_btn.show()
            return

        if eff == "static":
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

        if self.mode_rainbow_rb.isChecked() and eff in (
            "wave", "tornado", "breathing", "waterfall", "meteor_shower", "audio_equalizer",
        ):
            self.chips_row_widget.hide()
        elif self.mode_dual_rb.isChecked():
            self.chips_row_widget.show()
            self.chip_a_btn.show()
            self.chip_b_btn.show()
        else:
            self.chips_row_widget.show()
            self.chip_a_btn.show()
            self.chip_b_btn.hide()
            if self.active_color_target == TARGET_COLOR_B:
                self._select_color_target(TARGET_COLOR_A)

    def _select_color_target(self, target: str):
        """Binds the Base Camp Color Picker to Color A, Color B, or Underglow."""
        self.active_color_target = target
        if target == TARGET_COLOR_A:
            c = self.engine.color_a
            if self.engine.effect_name == "custom":
                self.picker_header_lbl.setText("COLOR PALETTE  —  EDITING [ACTIVE BRUSH COLOR]")
            else:
                self.picker_header_lbl.setText("COLOR PALETTE  —  EDITING [COLOR A]")
        elif target == TARGET_COLOR_B:
            c = self.engine.color_b
            if self.engine.effect_name == "custom":
                self.picker_header_lbl.setText("COLOR PALETTE  —  EDITING [BASE COLOR]")
            else:
                self.picker_header_lbl.setText("COLOR PALETTE  —  EDITING [COLOR B]")
        else:
            c = self.engine.underglow_color
            self.picker_header_lbl.setText("COLOR PALETTE  —  EDITING [UNDERGLOW STRIP]")

        self.color_picker.load_color(QColor(c.red, c.green, c.blue))
        self._refresh_color_chips()

    def _refresh_color_chips(self):
        """Updates live background swatches and active highlight borders on color chips."""
        def style_chip(btn: QPushButton, rgb: RGBColor, is_active: bool):
            hex_col = f"#{rgb.red:02x}{rgb.green:02x}{rgb.blue:02x}"
            lum = 0.299 * rgb.red + 0.587 * rgb.green + 0.114 * rgb.blue
            text_col = "#000000" if lum > 140 else "#FFFFFF"
            border = "2px solid #0078D7" if is_active else "1px solid #3F4756"
            btn.setStyleSheet(
                f"background-color: {hex_col}; color: {text_col}; border: {border}; "
                f"border-radius: 5px; font-weight: bold; font-size: 11px; padding: 3px 10px;"
            )

        style_chip(self.chip_a_btn, self.engine.color_a, self.active_color_target == TARGET_COLOR_A)
        style_chip(self.chip_b_btn, self.engine.color_b, self.active_color_target == TARGET_COLOR_B)
        style_chip(self.ug_color_chip, self.engine.underglow_color, self.active_color_target == TARGET_UNDERGLOW)
        if hasattr(self, "custom_base_btn"):
            style_chip(self.custom_base_btn, self.engine.color_b, self.active_color_target == TARGET_COLOR_B)
        if hasattr(self, "custom_brush_btn"):
            style_chip(self.custom_brush_btn, self.engine.color_a, self.active_color_target == TARGET_COLOR_A)

    def _on_picker_color_changed(self, qcol: QColor):
        rgb = RGBColor(qcol.red(), qcol.green(), qcol.blue())

        if self.active_color_target == TARGET_UNDERGLOW:
            self.engine.underglow_color = rgb
        elif self.active_color_target == TARGET_COLOR_B:
            self.engine.color_b = rgb
        else:
            self.engine.color_a = rgb
            if self.engine.effect_name == "custom":
                for led_idx in self.canvas.selected_keys:
                    self.engine.paint_custom_key(led_idx, rgb)

        self._refresh_color_chips()
        if not self._suppress_slider_events:
            self.save_settings()

    def _set_brush_mode(self, mode: str):
        """Sets active painting brush mode ('paint' or 'erase')."""
        clean_mode = BRUSH_ERASE if mode == BRUSH_ERASE else BRUSH_PAINT
        self.brush_mode = clean_mode
        if hasattr(self, "brush_paint_btn"):
            self.brush_paint_btn.setChecked(clean_mode == BRUSH_PAINT)
        if hasattr(self, "brush_erase_btn"):
            self.brush_erase_btn.setChecked(clean_mode == BRUSH_ERASE)

    def _on_canvas_key_clicked(self, led_idx: int):
        """Handles keycap click and drag-over on visualizer canvas."""
        if self.engine.effect_name == "custom":
            if self.brush_mode == BRUSH_PAINT:
                self.engine.paint_custom_key(led_idx, self.engine.color_a)
            else:
                self.engine.erase_custom_key(led_idx)
            if not self._suppress_slider_events:
                self.save_settings()
        elif self.engine.effect_name in (
            "laser", "ripple", "punch", "crosshair",
            "full_board_flash", "explosion_burst", "typing_heatmap",
        ):
            self.engine.trigger_switch(led_idx)

    def _fill_all_custom_keys(self):
        """Paints all keys with the active brush color."""
        self.engine.fill_all_custom_keys(self.engine.color_a)
        if not self._suppress_slider_events:
            self.save_settings()

    def _clear_all_custom_keys(self):
        """Clears all custom painted keys, reverting every key to base color."""
        self.engine.clear_custom_keys()
        self.canvas.clear_selection()
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

    def _set_dna_direction(self, outward: bool):
        self.engine.dna_outward = bool(outward)
        if hasattr(self, "dna_outward_btn"):
            self.dna_outward_btn.setChecked(self.engine.dna_outward)
        if hasattr(self, "dna_inward_btn"):
            self.dna_inward_btn.setChecked(not self.engine.dna_outward)
        if not self._suppress_slider_events:
            self.save_settings()

    def _set_heatmap_mode(self, mode: str):
        clean_mode = "persistent" if mode == "persistent" else "live"
        self.engine.heatmap_mode = clean_mode
        is_live = clean_mode == "live"
        if hasattr(self, "heatmap_live_btn"):
            self.heatmap_live_btn.setChecked(is_live)
        if hasattr(self, "heatmap_persist_btn"):
            self.heatmap_persist_btn.setChecked(not is_live)
        if self.engine.effect_name == "typing_heatmap" and hasattr(self, "speed_widget"):
            self.speed_widget.setVisible(is_live)
        if not self._suppress_slider_events:
            self.save_settings()

    def _on_reset_heatmap_clicked(self):
        self.engine.reset_heatmap()

    def _set_audio_style(self, style: str):
        clean_style = "bass_pulse" if style == "bass_pulse" else "bars"
        self.engine.audio_style = clean_style
        if hasattr(self, "audio_bars_btn"):
            self.audio_bars_btn.setChecked(clean_style == "bars")
        if hasattr(self, "audio_bass_btn"):
            self.audio_bass_btn.setChecked(clean_style == "bass_pulse")
        if not self._suppress_slider_events:
            self.save_settings()

    def _set_screen_mode(self, mode: str):
        clean_mode = "edges" if mode == "edges" else "grid"
        self.engine.screen_mode = clean_mode
        if hasattr(self, "screen_grid_btn"):
            self.screen_grid_btn.setChecked(clean_mode == "grid")
        if hasattr(self, "screen_edges_btn"):
            self.screen_edges_btn.setChecked(clean_mode == "edges")
        if not self._suppress_slider_events:
            self.save_settings()

    def _on_monitor_changed(self, _idx: int):
        if self._suppress_slider_events or not hasattr(self, "monitor_combo"):
            return
        mon = self.monitor_combo.currentData()
        if mon is not None:
            self.engine.screen_monitor = int(mon)
            self.save_settings()

    def _refresh_sync_status_hint(self):
        """Updates inline status banner when Audio Equalizer or Screen Ambilight is active."""
        if not hasattr(self, "sync_status_lbl"):
            return
        eff = self.engine.effect_name
        if eff == "audio_equalizer":
            self.sync_status_lbl.setText(f"Audio Status: {self.engine.audio_worker.status_message}")
        elif eff == "screen_ambilight":
            self.sync_status_lbl.setText(f"Screen Status: {self.engine.screen_worker.status_message}")

    def _set_underglow_mode(self, mode: str):
        self.engine.underglow_mode = mode
        self.ug_sync_btn.setChecked(mode == "sync")
        self.ug_static_btn.setChecked(mode == "static")
        self.ug_off_btn.setChecked(mode == "off")

        if mode == "static":
            self.ug_color_chip.show()
            self._select_color_target(TARGET_UNDERGLOW)
        else:
            self.ug_color_chip.hide()
            if self.active_color_target == TARGET_UNDERGLOW:
                self._select_color_target(TARGET_COLOR_A)

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
        elif eff == "row_sweep":
            self.engine.sweep_speed = float(val)
            self.speed_val_lbl.setText(f"{val} keys/s")
        elif eff == "thunderstorm":
            self.engine.storm_intensity = float(val)
            self.speed_val_lbl.setText(str(val))
        elif eff == "system_malfunction":
            self.engine.glitch_freq = float(val)
            self.speed_val_lbl.setText(str(val))
        elif eff == "crosshair":
            self.engine.crosshair_speed = float(val)
            self.speed_val_lbl.setText(f"{val} keys/s")
        elif eff == "explosion_burst":
            self.engine.explosion_speed = float(val)
            self.speed_val_lbl.setText(f"{val} keys/s")
        elif eff == "typing_heatmap":
            self.engine.heatmap_cooldown = float(val)
            self.speed_val_lbl.setText(str(val))
        elif eff == "audio_equalizer":
            gain = val / 10.0
            self.engine.audio_gain = gain
            self.speed_val_lbl.setText(f"{gain:.1f}x")
        elif eff == "screen_ambilight":
            smooth = val / 100.0
            self.engine.screen_smoothing = smooth
            self.speed_val_lbl.setText(f"{smooth:.2f}")
        else:
            self.engine.speed = float(val)
            self.speed_val_lbl.setText(str(val))
        self.save_settings()

    def _on_decay_slider_changed(self, val: int):
        if self._suppress_slider_events:
            return
        eff = self.engine.effect_name
        if eff == "row_sweep":
            trail = val / 10.0
            self.engine.sweep_trail = trail
            self.decay_val_lbl.setText(f"{trail:.1f} u")
        elif eff == "aurora":
            scale = val / 10.0
            self.engine.aurora_scale = scale
            self.decay_val_lbl.setText(f"{scale:.1f}x")
        elif eff == "gradient_breathing":
            self.engine.breath_min_floor = float(val)
            self.decay_val_lbl.setText(f"{val}%")
        elif eff == "cosmic_drift":
            self.engine.star_density = float(val)
            self.decay_val_lbl.setText(str(val))
        elif eff == "dna_spiral":
            self.engine.dna_twist = float(val)
            self.decay_val_lbl.setText(str(val))
        elif eff == "meteor_shower":
            self.engine.meteor_count = int(val)
            self.decay_val_lbl.setText(str(val))
        elif eff == "audio_equalizer":
            smooth = val / 100.0
            self.engine.audio_smoothing = smooth
            self.decay_val_lbl.setText(f"{smooth:.2f}")
        elif eff == "screen_ambilight":
            sat = val / 10.0
            self.engine.screen_saturation = sat
            self.decay_val_lbl.setText(f"{sat:.1f}x")
        else:
            seconds = val / 100.0
            if eff == "laser":
                self.engine.laser_decay = seconds
            elif eff == "punch":
                self.engine.punch_decay = seconds
            elif eff == "ripple":
                self.engine.ripple_decay = seconds
            elif eff == "crosshair":
                self.engine.crosshair_decay = seconds
            elif eff == "full_board_flash":
                self.engine.flash_decay = seconds
            elif eff == "explosion_burst":
                self.engine.explosion_decay = seconds
            self.decay_val_lbl.setText(f"{seconds:.2f} s")
        self.save_settings()

    def _on_base_brightness_changed(self, val: int):
        self.base_bright_val_lbl.setText(f"{val}%")
        self.engine.base_brightness = float(val)
        if not self._suppress_slider_events:
            self.save_settings()

    def _on_reactive_brightness_changed(self, val: int):
        self.react_bright_val_lbl.setText(f"{val}%")
        self.engine.reactive_brightness = float(val)
        if not self._suppress_slider_events:
            self.save_settings()

    def _on_brightness_changed(self, val: int):
        self._on_base_brightness_changed(val)

    def _on_edge_brightness_changed(self, val: int):
        self.engine.underglow_brightness = val
        self.edge_bright_val.setText(f"{val}%")
        if not self._suppress_slider_events:
            self.save_settings()

    # --------------------------------------------------------------------------
    # 8. PER-EFFECT 5-SLOT PROFILES & PERSISTENCE
    # --------------------------------------------------------------------------
    def _update_profile_buttons_style(self):
        """Highlights active profile button and dims inactive slots."""
        for slot, btn in self.profile_buttons.items():
            if slot == self.active_profile_slot:
                btn.setStyleSheet(self.PROFILE_BTN_ACTIVE_STYLE)
            else:
                btn.setStyleSheet(self.PROFILE_BTN_INACTIVE_STYLE)

    def _get_default_slots_for_effect(self, eff: str) -> Dict[str, dict]:
        """Returns 5 distinct factory default presets for the given effect."""
        base_defaults = {
            "1": {
                "color_a": "#FFFF00",
                "color_b": "#0000FF",
                "base_color": "#0000FF",
                "react_color": "#FFFF00",
                "palette_mode": MODE_DUAL,
                "color_mode": MODE_DUAL,
                "speed": 5,
                "base_brightness": 20,
                "reactive_brightness": 100,
                "decay": 0.16,
                "laser_speed": 60,
                "laser_decay": 0.16,
                "punch_decay": 0.35,
                "ripple_speed": 15,
                "ripple_decay": 0.65,
                "matrix_speed": 6,
                "underglow_mode": "sync",
                "underglow_color": "#0078D7",
                "underglow_brightness": 35,
                "direction": DIR_RIGHT,
                "tornado_cw": True,
            },
            "2": {
                "color_a": "#00FFFF",
                "color_b": "#FF007F",
                "base_color": "#FF007F",
                "react_color": "#00FFFF",
                "palette_mode": MODE_DUAL,
                "color_mode": MODE_DUAL,
                "speed": 6,
                "base_brightness": 25,
                "reactive_brightness": 100,
                "decay": 0.14,
                "laser_speed": 75,
                "laser_decay": 0.14,
                "punch_decay": 0.30,
                "ripple_speed": 20,
                "ripple_decay": 0.50,
                "matrix_speed": 7,
                "underglow_mode": "sync",
                "underglow_color": "#00FFFF",
                "underglow_brightness": 40,
                "direction": "diagonal",
                "tornado_cw": False,
            },
            "3": {
                "color_a": "#00FF66",
                "color_b": "#1A0033",
                "base_color": "#1A0033",
                "react_color": "#00FF66",
                "palette_mode": MODE_DUAL,
                "color_mode": MODE_DUAL,
                "speed": 7,
                "base_brightness": 15,
                "reactive_brightness": 100,
                "decay": 0.18,
                "laser_speed": 85,
                "laser_decay": 0.18,
                "punch_decay": 0.40,
                "ripple_speed": 18,
                "ripple_decay": 0.60,
                "matrix_speed": 8,
                "underglow_mode": "static",
                "underglow_color": "#00FF66",
                "underglow_brightness": 30,
                "direction": DIR_LEFT,
                "tornado_cw": True,
            },
            "4": {
                "color_a": "#FF3300",
                "color_b": "#001122",
                "base_color": "#001122",
                "react_color": "#FF3300",
                "palette_mode": MODE_DUAL,
                "color_mode": MODE_DUAL,
                "speed": 4,
                "base_brightness": 30,
                "reactive_brightness": 100,
                "decay": 0.20,
                "laser_speed": 50,
                "laser_decay": 0.20,
                "punch_decay": 0.50,
                "ripple_speed": 12,
                "ripple_decay": 0.75,
                "matrix_speed": 5,
                "underglow_mode": "sync",
                "underglow_color": "#FF3300",
                "underglow_brightness": 35,
                "direction": "up",
                "tornado_cw": False,
            },
            "5": {
                "color_a": "#FFFFFF",
                "color_b": "#000000",
                "base_color": "#000000",
                "react_color": "#FFFFFF",
                "palette_mode": MODE_SINGLE,
                "color_mode": MODE_SINGLE,
                "speed": 8,
                "base_brightness": 0,
                "reactive_brightness": 100,
                "decay": 0.12,
                "laser_speed": 95,
                "laser_decay": 0.12,
                "punch_decay": 0.25,
                "ripple_speed": 22,
                "ripple_decay": 0.45,
                "matrix_speed": 9,
                "underglow_mode": "off",
                "underglow_color": "#000000",
                "underglow_brightness": 0,
                "direction": "down",
                "tornado_cw": True,
            },
        }

        if eff in ("wave", "tornado", "breathing", "waterfall", "meteor_shower", "audio_equalizer"):
            base_defaults["1"]["palette_mode"] = MODE_RAINBOW
            base_defaults["1"]["color_mode"] = MODE_RAINBOW
            for k in base_defaults:
                base_defaults[k]["base_brightness"] = 100
            if eff == "audio_equalizer":
                base_defaults["1"]["base_brightness"] = 10
                base_defaults["1"]["reactive_brightness"] = 100
                base_defaults["1"]["color_a"] = "#FF007F"
                base_defaults["1"]["color_b"] = "#001840"
        elif eff in ("aurora", "cosmic_drift", "thunderstorm", "row_sweep", "gradient_breathing", "system_malfunction", "dna_spiral"):
            for k in base_defaults:
                base_defaults[k]["base_brightness"] = 100
            if eff == "system_malfunction":
                base_defaults["1"]["color_a"] = "#B026FF"
                base_defaults["1"]["color_b"] = "#FF007F"
            elif eff == "dna_spiral":
                base_defaults["1"]["color_a"] = "#00F0FF"
                base_defaults["1"]["color_b"] = "#FF007F"
            elif eff == "gradient_breathing":
                base_defaults["1"]["color_a"] = "#00D4FF"
                base_defaults["1"]["color_b"] = "#8A2BE2"
        elif eff == "matrix":
            base_defaults["1"]["palette_mode"] = "matrix_classic"
            base_defaults["1"]["color_mode"] = "matrix_classic"
            for k in base_defaults:
                base_defaults[k]["base_brightness"] = 100
        elif eff in ("static", "custom", "audio_equalizer", "screen_ambilight"):
            for k in base_defaults:
                base_defaults[k]["base_brightness"] = 100

        for slot_k in base_defaults:
            base_defaults[slot_k]["mode"] = eff
            base_defaults[slot_k]["brightness"] = base_defaults[slot_k]["base_brightness"]
            base_defaults[slot_k].setdefault("sweep_speed", 25)
            base_defaults[slot_k].setdefault("sweep_trail", 4.0)
            base_defaults[slot_k].setdefault("aurora_scale", 1.0)
            base_defaults[slot_k].setdefault("breath_min_floor", 10)
            base_defaults[slot_k].setdefault("star_density", 5)
            base_defaults[slot_k].setdefault("storm_intensity", 5)
            base_defaults[slot_k].setdefault("glitch_freq", 5)
            base_defaults[slot_k].setdefault("dna_twist", 5)
            base_defaults[slot_k].setdefault("dna_outward", True)
            base_defaults[slot_k].setdefault("meteor_count", 6)
            base_defaults[slot_k].setdefault("crosshair_speed", 50)
            base_defaults[slot_k].setdefault("crosshair_decay", 0.45)
            base_defaults[slot_k].setdefault("flash_decay", 0.40)
            base_defaults[slot_k].setdefault("explosion_speed", 28)
            base_defaults[slot_k].setdefault("explosion_decay", 0.65)
            base_defaults[slot_k].setdefault("heatmap_mode", "live")
            base_defaults[slot_k].setdefault("heatmap_cooldown", 5)
            base_defaults[slot_k].setdefault("audio_style", "bars")
            base_defaults[slot_k].setdefault("audio_gain", 1.5)
            base_defaults[slot_k].setdefault("audio_smoothing", 0.50)
            base_defaults[slot_k].setdefault("screen_mode", "grid")
            base_defaults[slot_k].setdefault("screen_smoothing", 0.55)
            base_defaults[slot_k].setdefault("screen_saturation", 1.5)
            base_defaults[slot_k].setdefault("screen_monitor", 1)

        return base_defaults

    def _get_or_create_effect_profile(self, eff: str) -> dict:
        if eff not in self.effect_profiles or not isinstance(self.effect_profiles[eff], dict):
            self.effect_profiles[eff] = {
                "active_slot": 1,
                "slots": self._get_default_slots_for_effect(eff)
            }
        slots_dict = self.effect_profiles[eff].setdefault("slots", {})
        defaults = self._get_default_slots_for_effect(eff)
        for s in range(1, 6):
            s_str = str(s)
            if s_str not in slots_dict or not isinstance(slots_dict[s_str], dict):
                slots_dict[s_str] = defaults.get(s_str, {})
        return self.effect_profiles[eff]

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
            "base_brightness": int(round(self.engine.base_brightness)),
            "reactive_brightness": int(round(self.engine.reactive_brightness)),
            "brightness": int(round(self.engine.base_brightness)),
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
            "sweep_speed": int(self.engine.sweep_speed),
            "sweep_trail": round(self.engine.sweep_trail, 1),
            "aurora_scale": round(self.engine.aurora_scale, 1),
            "breath_min_floor": int(round(self.engine.breath_min_floor)),
            "star_density": int(round(self.engine.star_density)),
            "storm_intensity": int(round(self.engine.storm_intensity)),
            "glitch_freq": int(round(self.engine.glitch_freq)),
            "dna_twist": int(round(self.engine.dna_twist)),
            "dna_outward": bool(self.engine.dna_outward),
            "meteor_count": int(self.engine.meteor_count),
            "crosshair_speed": int(self.engine.crosshair_speed),
            "crosshair_decay": round(self.engine.crosshair_decay, 2),
            "flash_decay": round(self.engine.flash_decay, 2),
            "explosion_speed": int(self.engine.explosion_speed),
            "explosion_decay": round(self.engine.explosion_decay, 2),
            "heatmap_mode": self.engine.heatmap_mode,
            "heatmap_cooldown": int(round(self.engine.heatmap_cooldown)),
            "audio_style": self.engine.audio_style,
            "audio_gain": round(self.engine.audio_gain, 1),
            "audio_smoothing": round(self.engine.audio_smoothing, 2),
            "screen_mode": self.engine.screen_mode,
            "screen_smoothing": round(self.engine.screen_smoothing, 2),
            "screen_saturation": round(self.engine.screen_saturation, 1),
            "screen_monitor": int(self.engine.screen_monitor),
        }
        if self.engine.effect_name == "custom":
            d["custom_colors"] = {
                str(k): rgb_to_hex(v) for k, v in self.engine.custom_key_colors.items()
            }
            d["brush_mode"] = self.brush_mode
        return d

    def _on_profile_clicked(self, slot: int):
        """Switches active profile slot for the CURRENT effect only."""
        eff = self.engine.effect_name
        if slot == self.active_profile_slot:
            return

        eff_entry = self._get_or_create_effect_profile(eff)
        # 1. Save outgoing profile parameters to in-memory slot dictionary
        eff_entry["slots"][str(self.active_profile_slot)] = self._capture_current_profile_dict()

        # 2. Update active slot
        self.active_profile_slot = slot
        eff_entry["active_slot"] = slot

        # 3. Apply incoming slot configuration
        slot_data = eff_entry["slots"].get(str(slot))
        if not slot_data:
            slot_data = self._capture_current_profile_dict()
            eff_entry["slots"][str(slot)] = slot_data

        self._apply_profile_dict(slot_data)
        self._update_profile_buttons_style()
        self.engine.mark_dirty()
        self.save_settings()

    def _apply_profile_dict(self, cfg: dict):
        """Applies configuration dictionary to self.engine and updates UI controls."""
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

            # 2. Dual Brightness Sliders
            base_b = cfg.get("base_brightness", cfg.get("brightness", 20))
            base_b_val = max(0, min(100, int(base_b)))
            self.engine.base_brightness = float(base_b_val)
            if hasattr(self, "base_bright_slider"):
                self.base_bright_slider.setValue(base_b_val)
            if hasattr(self, "base_bright_val_lbl"):
                self.base_bright_val_lbl.setText(f"{base_b_val}%")

            react_b = cfg.get("reactive_brightness", 100)
            react_b_val = max(0, min(100, int(react_b)))
            self.engine.reactive_brightness = float(react_b_val)
            if hasattr(self, "react_bright_slider"):
                self.react_bright_slider.setValue(react_b_val)
            if hasattr(self, "react_bright_val_lbl"):
                self.react_bright_val_lbl.setText(f"{react_b_val}%")

            # 3. Underglow Brightness Slider
            if "underglow_brightness" in cfg:
                ug_val = max(0, min(100, int(cfg["underglow_brightness"])))
                self.engine.underglow_brightness = ug_val
                if hasattr(self, "edge_bright_slider"):
                    self.edge_bright_slider.setValue(ug_val)
                if hasattr(self, "edge_bright_val"):
                    self.edge_bright_val.setText(f"{ug_val}%")

            # 4. Velocities & Durations
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
            if "sweep_speed" in cfg:
                self.engine.sweep_speed = float(cfg["sweep_speed"])
            if "sweep_trail" in cfg:
                self.engine.sweep_trail = float(cfg["sweep_trail"])
            if "aurora_scale" in cfg:
                self.engine.aurora_scale = float(cfg["aurora_scale"])
            if "breath_min_floor" in cfg:
                self.engine.breath_min_floor = float(cfg["breath_min_floor"])
            if "star_density" in cfg:
                self.engine.star_density = float(cfg["star_density"])
            if "storm_intensity" in cfg:
                self.engine.storm_intensity = float(cfg["storm_intensity"])
            if "glitch_freq" in cfg:
                self.engine.glitch_freq = float(cfg["glitch_freq"])
            if "dna_twist" in cfg:
                self.engine.dna_twist = float(cfg["dna_twist"])
            if "dna_outward" in cfg:
                self._set_dna_direction(bool(cfg["dna_outward"]))
            if "meteor_count" in cfg:
                self.engine.meteor_count = int(cfg["meteor_count"])
            if "crosshair_speed" in cfg:
                self.engine.crosshair_speed = float(cfg["crosshair_speed"])
            if "crosshair_decay" in cfg:
                self.engine.crosshair_decay = float(cfg["crosshair_decay"])
            if "flash_decay" in cfg:
                self.engine.flash_decay = float(cfg["flash_decay"])
            if "explosion_speed" in cfg:
                self.engine.explosion_speed = float(cfg["explosion_speed"])
            if "explosion_decay" in cfg:
                self.engine.explosion_decay = float(cfg["explosion_decay"])
            if "heatmap_mode" in cfg:
                self._set_heatmap_mode(cfg["heatmap_mode"])
            if "heatmap_cooldown" in cfg:
                self.engine.heatmap_cooldown = float(cfg["heatmap_cooldown"])
            if "audio_style" in cfg:
                self._set_audio_style(cfg["audio_style"])
            if "audio_gain" in cfg:
                self.engine.audio_gain = float(cfg["audio_gain"])
            if "audio_smoothing" in cfg:
                self.engine.audio_smoothing = float(cfg["audio_smoothing"])
            if "screen_mode" in cfg:
                self._set_screen_mode(cfg["screen_mode"])
            if "screen_smoothing" in cfg:
                self.engine.screen_smoothing = float(cfg["screen_smoothing"])
            if "screen_saturation" in cfg:
                self.engine.screen_saturation = float(cfg["screen_saturation"])
            if "screen_monitor" in cfg:
                self.engine.screen_monitor = max(1, int(cfg["screen_monitor"]))

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

            # 5. Custom Keys
            if "custom_colors" in cfg and isinstance(cfg["custom_colors"], dict):
                self.engine.custom_key_colors.clear()
                for k_str, hex_val in cfg["custom_colors"].items():
                    try:
                        k_idx = int(k_str)
                        self.engine.custom_key_colors[k_idx] = hex_to_rgb(hex_val, RGBColor(0, 120, 215))
                    except Exception:
                        pass
            elif self.engine.effect_name == "custom":
                self.engine.custom_key_colors.clear()

            if "brush_mode" in cfg:
                self._set_brush_mode(cfg["brush_mode"])

            # 6. Palette / Color Mode
            col_mode = cfg.get("color_mode", cfg.get("palette_mode", MODE_RAINBOW))
            self.engine.mode_type = col_mode
            if hasattr(self, "mode_single_rb") and hasattr(self, "mode_dual_rb") and hasattr(self, "mode_rainbow_rb"):
                if col_mode == MODE_SINGLE:
                    self.mode_single_rb.setChecked(True)
                elif col_mode == MODE_DUAL:
                    self.mode_dual_rb.setChecked(True)
                else:
                    self.mode_rainbow_rb.setChecked(True)

            # 7. Underglow Mode
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
        """Serializes current engine, per-effect profiles, and UI state to config.json."""
        try:
            eff = self.engine.effect_name
            eff_entry = self._get_or_create_effect_profile(eff)
            current_dict = self._capture_current_profile_dict()
            eff_entry["slots"][str(self.active_profile_slot)] = current_dict
            eff_entry["active_slot"] = self.active_profile_slot

            config_data = {
                "active_effect": eff,
                "dock_position": self.engine.dock_position,
                "effect_profiles": self.effect_profiles,
                # Backward compatibility root keys:
                "mode": eff,
                "active_profile": self.active_profile_slot,
                "profiles": {s: eff_entry["slots"].get(s, {}) for s in ("1", "2", "3", "4", "5")},
            }
            config_data.update(current_dict)

            cfg_path = self._get_config_path()
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Failed to save settings to config.json: {e}")

    def load_settings(self):
        """Loads persisted state from config.json and configures engine and UI controls."""
        cfg_path = self._get_config_path()

        if not os.path.exists(cfg_path):
            self.effect_profiles = {}
            for eff in ALL_EFFECT_KEYS:
                self.effect_profiles[eff] = {
                    "active_slot": 1,
                    "slots": self._get_default_slots_for_effect(eff)
                }
            self.active_profile_slot = 1
            self._set_dock_position(DIR_RIGHT)
            self._update_profile_buttons_style()
            return

        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to read config.json: {e}")
            cfg = {}

        # 1. Dock Position
        dock_pos = cfg.get("dock_position", DIR_RIGHT)
        self._set_dock_position(dock_pos)

        # 2. Per-Effect Profiles (backward-compatible auto-init for new v3.0 effects)
        raw_eff_profiles = cfg.get("effect_profiles")
        if isinstance(raw_eff_profiles, dict) and raw_eff_profiles:
            self.effect_profiles = raw_eff_profiles
            for eff in ALL_EFFECT_KEYS:
                self._get_or_create_effect_profile(eff)
        else:
            self.effect_profiles = {}
            for eff in ALL_EFFECT_KEYS:
                self.effect_profiles[eff] = {
                    "active_slot": 1,
                    "slots": self._get_default_slots_for_effect(eff)
                }
            legacy_profiles = cfg.get("profiles", {})
            legacy_mode = cfg.get("mode", "static")
            if legacy_mode in self.effect_profiles and isinstance(legacy_profiles, dict):
                for s in range(1, 6):
                    s_str = str(s)
                    if s_str in legacy_profiles:
                        self.effect_profiles[legacy_mode]["slots"][s_str] = legacy_profiles[s_str]

        # 3. Active Effect & Active Slot
        target_effect = cfg.get("active_effect", cfg.get("mode", "static"))
        eff_entry = self._get_or_create_effect_profile(target_effect)
        active_slot = eff_entry.get("active_slot", cfg.get("active_profile", 1))
        try:
            active_slot = int(active_slot)
            if active_slot not in range(1, 6):
                active_slot = 1
        except Exception:
            active_slot = 1
        self.active_profile_slot = active_slot
        eff_entry["active_slot"] = active_slot

        # Select in effects list
        if hasattr(self, "effects_list"):
            for i in range(self.effects_list.count()):
                item = self.effects_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == target_effect:
                    self.effects_list.setCurrentRow(i)
                    break

        slot_data = eff_entry["slots"].get(str(active_slot), {})
        self._apply_profile_dict(slot_data)
        self._reconfigure_deck_for_effect(target_effect)
        self._update_profile_buttons_style()

    # --------------------------------------------------------------------------
    # 9. SYSTEM TRAY DAEMON INTEGRATION
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
