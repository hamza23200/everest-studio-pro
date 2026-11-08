"""
Everest Studio Pro - Base Camp Style Color Picker.
Includes 2D Saturation/Value gradient, vertical Hue rainbow bar,
direct HEX and R/G/B SpinBox/LineEdit inputs, and a 12-chip saved palette bar.
"""

from typing import List
from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QPainter,
    QColor,
    QBrush,
    QPen,
    QLinearGradient,
    QPainterPath,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QPushButton,
    QFrame
)


class SaturationValueBox(QWidget):
    """2D interactive Saturation (X) and Value (Y) gradient field."""
    sv_changed = Signal(float, float)  # (saturation, value) in 0.0 .. 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(165, 165)
        self.hue = 180.0  # 0.0 to 360.0
        self.sat = 1.0    # 0.0 to 1.0
        self.val = 1.0    # 0.0 to 1.0
        self.is_dragging = False

    def set_hue(self, hue: float):
        self.hue = max(0.0, min(360.0, hue))
        self.update()

    def set_sv(self, sat: float, val: float):
        self.sat = max(0.0, min(1.0, sat))
        self.val = max(0.0, min(1.0, val))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self._update_from_pos(event.position())

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self._update_from_pos(event.position())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def _update_from_pos(self, pos: QPointF):
        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        self.sat = max(0.0, min(1.0, pos.x() / w))
        self.val = max(0.0, min(1.0, 1.0 - (pos.y() / h)))
        self.sv_changed.emit(self.sat, self.val)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = self.width()
        h = self.height()
        rect = QRectF(0, 0, w, h)

        base_color = QColor.fromHsvF(min(0.999, max(0.0, self.hue / 360.0)), 1.0, 1.0)

        # Horizontal White -> Pure Hue gradient
        h_grad = QLinearGradient(0, 0, w, 0)
        h_grad.setColorAt(0.0, QColor(255, 255, 255))
        h_grad.setColorAt(1.0, base_color)
        painter.fillRect(rect, h_grad)

        # Vertical Transparent -> Black gradient
        v_grad = QLinearGradient(0, 0, 0, h)
        v_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        v_grad.setColorAt(1.0, QColor(0, 0, 0, 255))
        painter.fillRect(rect, v_grad)

        painter.setPen(QPen(QColor("#2B2F3A"), 1.0))
        painter.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))

        # Selector Reticle
        sel_x = self.sat * w
        sel_y = (1.0 - self.val) * h

        painter.setPen(QPen(QColor(0, 0, 0), 2.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(sel_x, sel_y), 5.5, 5.5)

        painter.setPen(QPen(QColor(255, 255, 255), 1.6))
        painter.drawEllipse(QPointF(sel_x, sel_y), 4.2, 4.2)


class HueBar(QWidget):
    """Vertical rainbow spectrum bar for Hue selection (0 to 360 deg)."""
    hue_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 165)
        self.hue = 180.0
        self.is_dragging = False

    def set_hue(self, hue: float):
        self.hue = max(0.0, min(360.0, hue))
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self._update_from_pos(event.position().y())

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self._update_from_pos(event.position().y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False

    def _update_from_pos(self, y: float):
        h = max(1.0, float(self.height()))
        fraction = max(0.0, min(1.0, y / h))
        self.hue = fraction * 360.0
        self.hue_changed.emit(self.hue)
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        w = self.width()
        h = self.height()
        rect = QRectF(0, 0, w, h)

        grad = QLinearGradient(0, 0, 0, h)
        stops = 12
        for i in range(stops + 1):
            pos = i / stops
            grad.setColorAt(pos, QColor.fromHsvF(min(0.999, pos), 1.0, 1.0))

        path = QPainterPath()
        path.addRoundedRect(rect, 4.0, 4.0)
        painter.fillPath(path, grad)
        painter.strokePath(path, QPen(QColor("#2B2F3A"), 1.0))

        thumb_y = (self.hue / 360.0) * h
        thumb_rect = QRectF(0, thumb_y - 2.5, w, 5.0)

        painter.setPen(QPen(QColor(0, 0, 0), 1.5))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRoundedRect(thumb_rect, 2.0, 2.0)


class BaseCampColorPicker(QWidget):
    """
    Complete Mountain Base Camp style color deck.
    Synchronizes 2D SV gradient, Hue bar, Hex text, and R/G/B SpinBoxes.
    """
    color_changed = Signal(QColor)

    def __init__(self, parent=None, initial_color=QColor("#00FFFF")):
        super().__init__(parent)
        self.current_color = initial_color
        self._updating_inputs = False

        # Saved Swatch Palette (Base Camp 12 default slots)
        self.saved_swatches: List[QColor] = [
            QColor("#00FFFF"), QColor("#0078D7"), QColor("#FF0055"), QColor("#00FF66"),
            QColor("#FFAA00"), QColor("#AA00FF"), QColor("#0F0028"), QColor("#FFFFFF"),
            QColor("#FF00FF"), QColor("#003B10"), QColor("#EAB308"), QColor("#EF4444")
        ]

        self._build_ui()
        self.load_color(self.current_color)

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(8)

        # Upper Deck: 2D Field + Hue Bar + Numeric Inputs
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.sv_box = SaturationValueBox(self)
        self.sv_box.sv_changed.connect(self._on_sv_changed)
        top_row.addWidget(self.sv_box)

        self.hue_bar = HueBar(self)
        self.hue_bar.hue_changed.connect(self._on_hue_changed)
        top_row.addWidget(self.hue_bar)

        # Numeric Inputs & Preview
        inputs_col = QVBoxLayout()
        inputs_col.setSpacing(5)

        self.preview_swatch = QFrame()
        self.preview_swatch.setFixedHeight(26)
        self.preview_swatch.setStyleSheet("border-radius: 4px; border: 1px solid #2B2F3A;")
        inputs_col.addWidget(self.preview_swatch)

        # HEX Input
        hex_row = QHBoxLayout()
        hex_lbl = QLabel("HEX:")
        hex_lbl.setStyleSheet("color: #8A8F9D; font-weight: bold; font-size: 11px;")
        self.hex_input = QLineEdit()
        self.hex_input.setMaxLength(7)
        self.hex_input.setFixedWidth(72)
        self.hex_input.setStyleSheet(
            "background-color: #181A1F; color: #FFFFFF; border: 1px solid #2B2F3A; "
            "border-radius: 4px; padding: 3px 5px; font-weight: bold; font-size: 11px;"
        )
        self.hex_input.textEdited.connect(self._on_hex_edited)
        hex_row.addWidget(hex_lbl)
        hex_row.addWidget(self.hex_input)
        inputs_col.addLayout(hex_row)

        # R, G, B SpinBoxes (0..255)
        spin_style = (
            "QSpinBox { background-color: #181A1F; color: #FFFFFF; border: 1px solid #2B2F3A; "
            "border-radius: 4px; padding: 2px 4px; font-size: 11px; font-weight: bold; }"
        )

        def make_rgb_spin(label: str):
            row = QHBoxLayout()
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet("color: #8A8F9D; font-weight: bold; font-size: 11px;")
            spin = QSpinBox()
            spin.setRange(0, 255)
            spin.setFixedWidth(72)
            spin.setStyleSheet(spin_style)
            row.addWidget(lbl)
            row.addWidget(spin)
            return row, spin

        row_r, self.r_spin = make_rgb_spin("R")
        row_g, self.g_spin = make_rgb_spin("G")
        row_b, self.b_spin = make_rgb_spin("B")

        self.r_spin.valueChanged.connect(self._on_rgb_spin_changed)
        self.g_spin.valueChanged.connect(self._on_rgb_spin_changed)
        self.b_spin.valueChanged.connect(self._on_rgb_spin_changed)

        inputs_col.addLayout(row_r)
        inputs_col.addLayout(row_g)
        inputs_col.addLayout(row_b)
        top_row.addLayout(inputs_col)

        main_layout.addLayout(top_row)

        # Saved Swatches Header + Row
        swatches_header = QLabel("SAVED COLOR")
        swatches_header.setStyleSheet("color: #8A8F9D; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        main_layout.addWidget(swatches_header)

        swatches_row = QHBoxLayout()
        swatches_row.setSpacing(4)

        self.swatch_buttons: List[QPushButton] = []
        for col in self.saved_swatches:
            btn = QPushButton()
            btn.setFixedSize(20, 20)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {col.name()}; border: 1px solid #2B2F3A; border-radius: 3px;")
            btn.clicked.connect(lambda _, c=col: self.set_color(c))
            swatches_row.addWidget(btn)
            self.swatch_buttons.append(btn)

        # Add Swatch Button (+)
        add_btn = QPushButton("+")
        add_btn.setFixedSize(20, 20)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            "background-color: #181A1F; color: #0078D7; border: 1px dashed #0078D7; "
            "border-radius: 3px; font-weight: bold; font-size: 12px;"
        )
        add_btn.clicked.connect(self._save_current_color)
        swatches_row.addWidget(add_btn)
        swatches_row.addStretch()

        main_layout.addLayout(swatches_row)

    def load_color(self, color: QColor):
        """Loads a color into the picker UI without firing color_changed."""
        self.current_color = QColor(color)
        h = self.current_color.hueF()
        if h >= 0.0:
            self.sv_box.set_hue(h * 360.0)
            self.hue_bar.set_hue(h * 360.0)
        self.sv_box.set_sv(self.current_color.saturationF(), self.current_color.valueF())
        self._update_text_inputs()

    def set_color(self, color: QColor):
        """Sets active color, updates UI, and emits color_changed."""
        self.load_color(color)
        self.color_changed.emit(self.current_color)

    def _update_text_inputs(self):
        self._updating_inputs = True
        self.preview_swatch.setStyleSheet(
            f"background-color: {self.current_color.name()}; border: 1px solid #2B2F3A; border-radius: 4px;"
        )
        self.hex_input.setText(self.current_color.name().upper())
        self.r_spin.setValue(self.current_color.red())
        self.g_spin.setValue(self.current_color.green())
        self.b_spin.setValue(self.current_color.blue())
        self._updating_inputs = False

    def _on_sv_changed(self, sat: float, val: float):
        h = min(0.999, max(0.0, self.hue_bar.hue / 360.0))
        self.current_color = QColor.fromHsvF(h, sat, val)
        self._update_text_inputs()
        self.color_changed.emit(self.current_color)

    def _on_hue_changed(self, hue: float):
        self.sv_box.set_hue(hue)
        s = self.sv_box.sat
        v = self.sv_box.val
        h = min(0.999, max(0.0, hue / 360.0))
        self.current_color = QColor.fromHsvF(h, s, v)
        self._update_text_inputs()
        self.color_changed.emit(self.current_color)

    def _on_hex_edited(self, text: str):
        if self._updating_inputs:
            return
        clean = text.strip()
        if not clean.startswith("#"):
            clean = "#" + clean
        if len(clean) == 7:
            c = QColor(clean)
            if c.isValid():
                self.current_color = c
                h = c.hueF()
                if h >= 0.0:
                    self.sv_box.set_hue(h * 360.0)
                    self.hue_bar.set_hue(h * 360.0)
                self.sv_box.set_sv(c.saturationF(), c.valueF())
                self._updating_inputs = True
                self.preview_swatch.setStyleSheet(
                    f"background-color: {c.name()}; border: 1px solid #2B2F3A; border-radius: 4px;"
                )
                self.r_spin.setValue(c.red())
                self.g_spin.setValue(c.green())
                self.b_spin.setValue(c.blue())
                self._updating_inputs = False
                self.color_changed.emit(self.current_color)

    def _on_rgb_spin_changed(self):
        if self._updating_inputs:
            return
        r = self.r_spin.value()
        g = self.g_spin.value()
        b = self.b_spin.value()
        c = QColor(r, g, b)
        self.current_color = c
        h = c.hueF()
        if h >= 0.0:
            self.sv_box.set_hue(h * 360.0)
            self.hue_bar.set_hue(h * 360.0)
        self.sv_box.set_sv(c.saturationF(), c.valueF())
        self._updating_inputs = True
        self.preview_swatch.setStyleSheet(
            f"background-color: {c.name()}; border: 1px solid #2B2F3A; border-radius: 4px;"
        )
        self.hex_input.setText(c.name().upper())
        self._updating_inputs = False
        self.color_changed.emit(self.current_color)

    def _save_current_color(self):
        """Pushes current active color to the front of saved swatches."""
        self.saved_swatches.pop()
        self.saved_swatches.insert(0, QColor(self.current_color))
        for i, btn in enumerate(self.swatch_buttons):
            c = self.saved_swatches[i]
            btn.setStyleSheet(f"background-color: {c.name()}; border: 1px solid #2B2F3A; border-radius: 3px;")
            btn.disconnect()
            btn.clicked.connect(lambda _, col=c: self.set_color(col))
