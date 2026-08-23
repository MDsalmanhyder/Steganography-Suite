"""
Password Input Component with Strength Meter and Visibility Toggle.
"""

from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from securestego.core.crypto import evaluate_password_strength


class PasswordBox(QWidget):
    """
    Password entry widget with built-in strength meter and show/hide toggle.
    """
    text_changed = pyqtSignal(str)

    def __init__(self, placeholder: str = "Enter secret encryption passphrase...", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.is_visible = False
        self._init_ui(placeholder)

    def _init_ui(self, placeholder: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)

        self.input_field = QLineEdit()
        self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_field.setPlaceholderText(placeholder)
        self.input_field.textChanged.connect(self._on_text_changed)
        input_layout.addWidget(self.input_field)

        self.toggle_btn = QPushButton("👁")
        self.toggle_btn.setFixedSize(36, 36)
        self.toggle_btn.setToolTip("Show / Hide Passphrase")
        self.toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._toggle_visibility)
        input_layout.addWidget(self.toggle_btn)

        layout.addLayout(input_layout)

        # Strength Meter Row
        meter_layout = QHBoxLayout()
        meter_layout.setSpacing(8)

        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(False)
        self.strength_bar.setFixedHeight(6)
        meter_layout.addWidget(self.strength_bar, 1)

        self.strength_label = QLabel("Strength: Empty")
        self.strength_label.setStyleSheet("font-size: 11px; color: #8b949e;")
        meter_layout.addWidget(self.strength_label)

        layout.addLayout(meter_layout)

    def _toggle_visibility(self):
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_btn.setText("🔒")
        else:
            self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_btn.setText("👁")

    def _on_text_changed(self, text: str):
        score, label, advice = evaluate_password_strength(text)
        self.strength_bar.setValue(score)

        if score == 0:
            color = "#30363d"
            text_color = "#8b949e"
        elif score < 40:
            color = "#f85149"
            text_color = "#f85149"
        elif score < 70:
            color = "#d29922"
            text_color = "#d29922"
        elif score < 90:
            color = "#58a6ff"
            text_color = "#58a6ff"
        else:
            color = "#3fb950"
            text_color = "#3fb950"

        self.strength_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 3px;
                height: 6px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        self.strength_label.setText(f"Strength: {label}")
        self.strength_label.setStyleSheet(f"font-size: 11px; color: {text_color}; font-weight: 600;")
        self.strength_label.setToolTip(advice)
        self.text_changed.emit(text)

    def text(self) -> str:
        return self.input_field.text()

    def clear(self):
        self.input_field.clear()
