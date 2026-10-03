"""
Capacity Bar Component for CloakPix.
Visualizes payload size relative to carrier image embedding capacity.
"""

from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class CapacityBar(QFrame):
    """
    Capacity usage indicator with dynamic color styling and statistics.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.used_bytes = 0
        self.total_bytes = 0
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # Header Row
        header_layout = QHBoxLayout()
        self.title_label = QLabel("📊 Carrier Capacity Usage")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #c9d1d9;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.stats_label = QLabel("0 B / 0 B (0.0%)")
        self.stats_label.setStyleSheet("font-size: 12px; color: #8b949e; font-family: monospace;")
        header_layout.addWidget(self.stats_label)

        layout.addLayout(header_layout)

        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(10)
        self._apply_progress_style("#238636", "#2ea043")
        layout.addWidget(self.progress)

    def _apply_progress_style(self, color1: str, color2: str):
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 5px;
                height: 10px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {color1}, stop:1 {color2});
                border-radius: 4px;
            }}
        """)

    @staticmethod
    def _format_bytes(num_bytes: int) -> str:
        if num_bytes < 1024:
            return f"{num_bytes} B"
        elif num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024.0:.1f} KB"
        else:
            return f"{num_bytes / (1024.0 * 1024.0):.2f} MB"

    def update_capacity(self, used_bytes: int, total_bytes: int):
        self.used_bytes = max(0, used_bytes)
        self.total_bytes = max(0, total_bytes)

        if self.total_bytes == 0:
            pct = 0.0
            val = 0
            self._apply_progress_style("#238636", "#2ea043")
        else:
            pct = (self.used_bytes / self.total_bytes) * 100.0
            val = int(min(1000, (self.used_bytes / self.total_bytes) * 1000))

            if pct > 100.0:
                self._apply_progress_style("#da3633", "#f85149")
            elif pct > 80.0:
                self._apply_progress_style("#9e6a03", "#d29922")
            else:
                self._apply_progress_style("#1f6feb", "#238636")

        self.progress.setValue(val)
        used_str = self._format_bytes(self.used_bytes)
        total_str = self._format_bytes(self.total_bytes)
        self.stats_label.setText(f"{used_str} / {total_str} ({pct:.1f}%)")

        if pct > 100.0:
            self.stats_label.setStyleSheet("font-size: 12px; color: #f85149; font-weight: bold; font-family: monospace;")
        else:
            self.stats_label.setStyleSheet("font-size: 12px; color: #8b949e; font-family: monospace;")

    def reset(self):
        self.update_capacity(0, 0)
