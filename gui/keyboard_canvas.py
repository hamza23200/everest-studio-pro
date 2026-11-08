"""
Everest Studio Pro - High-Performance 2D Keyboard Visualizer.
Renders real-time hardware LED backlighting, keycap legends, underglow,
and supports interactive per-key lighting painting using QPainter and @Slot(object).
"""

import time
from typing import Dict, List, Tuple, Set, Optional
from PySide6.QtCore import Qt, QRectF, QPointF, Signal, Slot
from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QFont,
    QLinearGradient,
    QRadialGradient,
    QPainterPath
)
from PySide6.QtWidgets import QWidget

from engine.matrix import KEY_DEFINITIONS


class EverestKeyboardCanvas(QWidget):
    """
    Hardware-accelerated 2D visualizer widget replicating the Mountain Everest 60
    chassis, keycap legends, switch backlights, and perimeter underglow.
    """
    key_clicked = Signal(int)        # Emits hardware LED index when a keycap is clicked/painted
    selection_changed = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(680, 235)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setMouseTracking(True)

        # Current frame RGB tuples [(r, g, b), ...] for slots 0..63 + slot 64 (underglow)
        self.switch_colors: List[Tuple[int, int, int]] = [(15, 0, 40)] * 64
        self.underglow_rgb: Tuple[int, int, int] = (0, 120, 215)

        # Selected hardware LED indices for Custom Per-Key mode
        self.selected_keys: Set[int] = set()
        # Active key strikes for visual pop animation {slot_idx: timestamp}
        self.key_strikes: Dict[int, float] = {}

        # Pre-calculated geometry mapping for fast hit-testing {slot_idx: QRectF}
        self.slot_screen_rects: Dict[int, QRectF] = {}
        self.hovered_slot: Optional[int] = None
        self.is_painting_drag = False

    @Slot(object)
    def update_frame(self, colors_list: object):
        """
        Zero-copy slot receiving lightweight list of RGB tuples from LightingEngineThread.
        Eliminates Shiboken dict-marshalling overhead.
        """
        if isinstance(colors_list, list) and len(colors_list) >= 64:
            self.switch_colors = colors_list[:64]
            if len(colors_list) >= 65:
                self.underglow_rgb = colors_list[64]
            self.update()

    @Slot(object)
    def update_underglow(self, ug_tuple: object):
        """Updates the diffused perimeter chassis underglow halo."""
        if isinstance(ug_tuple, (tuple, list)) and len(ug_tuple) == 3:
            self.underglow_rgb = (int(ug_tuple[0]), int(ug_tuple[1]), int(ug_tuple[2]))
            self.update()

    @Slot(int)
    def flash_key(self, slot_idx: int):
        """Slot called when a physical key strike occurs (0..63)."""
        self.key_strikes[slot_idx] = time.time()
        self.update()

    def select_all_keys(self):
        """Selects all 64 keys for batch operations in Custom Mode."""
        self.selected_keys = {
            k.get("resolved_idx", k["default_idx"]) for k in KEY_DEFINITIONS
        }
        self.selection_changed.emit(self.selected_keys)
        self.update()

    def clear_selection(self):
        """Deselects all keys."""
        self.selected_keys.clear()
        self.selection_changed.emit(self.selected_keys)
        self.update()

    def _slot_at_pos(self, pos: QPointF) -> Optional[int]:
        for slot_idx, rect in self.slot_screen_rects.items():
            if rect.contains(pos):
                return slot_idx
        return None

    def mousePressEvent(self, event):
        """Interactive key selection and live painting for Custom Per-Key Lighting."""
        if event.button() == Qt.MouseButton.LeftButton:
            slot_idx = self._slot_at_pos(event.position())
            if slot_idx is not None:
                self.is_painting_drag = True
                k = KEY_DEFINITIONS[slot_idx]
                led_idx = k.get("resolved_idx", k["default_idx"])

                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    if led_idx in self.selected_keys:
                        self.selected_keys.remove(led_idx)
                    else:
                        self.selected_keys.add(led_idx)
                else:
                    self.selected_keys = {led_idx}

                self.key_strikes[slot_idx] = time.time()
                self.key_clicked.emit(led_idx)
                self.selection_changed.emit(self.selected_keys)
                self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()
        slot_idx = self._slot_at_pos(pos)
        if slot_idx != self.hovered_slot:
            self.hovered_slot = slot_idx
            self.update()

        if self.is_painting_drag and slot_idx is not None:
            k = KEY_DEFINITIONS[slot_idx]
            led_idx = k.get("resolved_idx", k["default_idx"])
            self.selected_keys.add(led_idx)
            self.key_clicked.emit(led_idx)
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_painting_drag = False

    def paintEvent(self, _event):
        """Draws the aluminum chassis, diffused underglow, and all 64 switch keycaps."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w = float(self.width())
        h = float(self.height())

        margin_x = 28.0
        margin_y = 18.0
        avail_w = w - (margin_x * 2.0)
        avail_h = h - (margin_y * 2.0)

        unit = min(avail_w / 15.2, avail_h / 5.2)
        total_kb_w = unit * 15.0
        total_kb_h = unit * 5.0

        offset_x = (w - total_kb_w) / 2.0
        offset_y = (h - total_kb_h) / 2.0
        gap = unit * 0.055

        # ----------------------------------------------------------------------
        # 1. PERIMETER UNDERGLOW HALO & CHASSIS
        # ----------------------------------------------------------------------
        bezel_pad = unit * 0.34
        case_rect = QRectF(
            offset_x - bezel_pad,
            offset_y - bezel_pad,
            total_kb_w + (bezel_pad * 2.0),
            total_kb_h + (bezel_pad * 2.0)
        )

        ur, ug, ub = self.underglow_rgb
        edge_qcolor = QColor(ur, ug, ub)

        if edge_qcolor.value() > 8:
            # Outer soft diffused underglow bloom
            for expand, alpha in [(12.0, 28), (7.0, 55), (3.0, 95)]:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(
                    case_rect.adjusted(-expand, -expand, expand, expand),
                    12.0 + expand * 0.4,
                    12.0 + expand * 0.4
                )
                painter.fillPath(glow_path, QColor(ur, ug, ub, alpha))

        # Gunmetal aluminum top plate
        case_path = QPainterPath()
        case_path.addRoundedRect(case_rect, 10.0, 10.0)

        case_grad = QLinearGradient(case_rect.topLeft(), case_rect.bottomLeft())
        case_grad.setColorAt(0.0, QColor("#1D2027"))
        case_grad.setColorAt(0.5, QColor("#15171D"))
        case_grad.setColorAt(1.0, QColor("#0F1115"))

        painter.fillPath(case_path, case_grad)

        # Perimeter accent rim reflecting active underglow
        rim_color = QColor(ur, ug, ub, 160) if edge_qcolor.value() > 15 else QColor("#2B2F3A")
        painter.strokePath(case_path, QPen(rim_color, 1.8))

        # ----------------------------------------------------------------------
        # 2. DRAW ALL 64 SWITCHES
        # ----------------------------------------------------------------------
        now = time.time()
        self.slot_screen_rects.clear()

        font_label = QFont("Segoe UI", max(7, int(unit * 0.25)), QFont.Weight.Bold)
        font_sublabel = QFont("Segoe UI", max(6, int(unit * 0.19)), QFont.Weight.DemiBold)

        for slot_idx, k in enumerate(KEY_DEFINITIONS):
            led_idx = k.get("resolved_idx", k["default_idx"])
            kx = offset_x + (k["x"] * unit)
            ky = offset_y + (k["y"] * unit)
            kw = (k["w"] * unit) - (gap * 2.0)
            kh = (k["h"] * unit) - (gap * 2.0)

            key_rect = QRectF(kx + gap, ky + gap, kw, kh)
            self.slot_screen_rects[slot_idx] = key_rect

            r, g, b = self.switch_colors[slot_idx] if slot_idx < len(self.switch_colors) else (0, 0, 0)
            led_color = QColor(r, g, b)

            # Check for visual strike pop
            is_struck = False
            if slot_idx in self.key_strikes:
                if (now - self.key_strikes[slot_idx]) < 0.20:
                    is_struck = True
                else:
                    del self.key_strikes[slot_idx]

            # Under-switch diffused LED backglow
            if led_color.value() > 8 or is_struck:
                backlight_rect = key_rect.adjusted(-3.0, -3.0, 3.0, 3.0)
                rad_grad = QRadialGradient(backlight_rect.center(), max(kw, kh) * 0.72)
                rad_grad.setColorAt(0.0, QColor(r, g, b, 210 if is_struck else 165))
                rad_grad.setColorAt(0.65, QColor(r, g, b, 90))
                rad_grad.setColorAt(1.0, QColor(r, g, b, 0))
                painter.fillRect(backlight_rect, rad_grad)

            # Keycap Body (#262A35)
            cap_path = QPainterPath()
            cap_radius = unit * 0.12
            cap_path.addRoundedRect(key_rect, cap_radius, cap_radius)

            cap_grad = QLinearGradient(key_rect.topLeft(), key_rect.bottomLeft())
            if is_struck:
                cap_grad.setColorAt(0.0, QColor("#383E4E"))
                cap_grad.setColorAt(1.0, QColor("#282C38"))
            else:
                cap_grad.setColorAt(0.0, QColor("#2A2F3B"))
                cap_grad.setColorAt(0.5, QColor("#262A35"))
                cap_grad.setColorAt(1.0, QColor("#1E212B"))

            painter.fillPath(cap_path, cap_grad)

            # Live LED color illumination on keycap surface (vivid illumination matching hardware)
            if led_color.value() > 10:
                val_norm = led_color.value() / 255.0
                alpha = int(140 + 75 * val_norm)
                painter.fillPath(cap_path, QColor(r, g, b, alpha))

            # Keycap Border (Selection / Hover / Standard Bevel)
            if led_idx in self.selected_keys:
                painter.strokePath(cap_path, QPen(QColor("#0078D7"), 2.2))
            elif slot_idx == self.hovered_slot:
                painter.strokePath(cap_path, QPen(QColor("#60A5FA"), 1.5))
            elif led_color.value() > 25:
                painter.strokePath(cap_path, QPen(QColor(r, g, b, 240), 1.4))
            else:
                painter.strokePath(cap_path, QPen(QColor("#343946"), 1.0))

            # Key Legends (Illuminated with smart contrast)
            label_text = k["label"]
            sublabel_text = k["sublabel"]

            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum > 130:
                text_color = QColor(15, 17, 22, 245)
            elif led_color.value() > 40:
                text_color = QColor(255, 255, 255, 240)
            else:
                text_color = QColor(210, 215, 225, 220)

            painter.setPen(text_color)

            if sublabel_text:
                half_h = key_rect.height() / 2.0
                top_rect = QRectF(key_rect.left(), key_rect.top() + 1.0, key_rect.width(), half_h)
                bot_rect = QRectF(key_rect.left(), key_rect.top() + half_h * 0.82, key_rect.width(), half_h)

                painter.setFont(font_sublabel)
                painter.drawText(top_rect, Qt.AlignmentFlag.AlignCenter, sublabel_text)

                painter.setFont(font_label)
                painter.drawText(bot_rect, Qt.AlignmentFlag.AlignCenter, label_text)
            else:
                painter.setFont(font_label)
                painter.drawText(key_rect, Qt.AlignmentFlag.AlignCenter, label_text)
