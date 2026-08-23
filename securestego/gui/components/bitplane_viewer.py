"""
Interactive Bit-Plane Viewer Component for SecureStego Forensics.
"""

from typing import Optional, Union
import numpy as np
from PIL import Image
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from securestego.core.forensics import ImageForensics


class BitPlaneViewer(QFrame):
    """
    Interactive visual slicer for inspecting individual bit planes.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_image: Optional[Image.Image] = None
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Controls Row
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(10)

        # Plane Selector (0 to 7)
        ctrl_layout.addWidget(QLabel("Bit Plane:"))
        self.bit_slider = QSlider(Qt.Orientation.Horizontal)
        self.bit_slider.setRange(0, 7)
        self.bit_slider.setValue(0)
        self.bit_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.bit_slider.setTickInterval(1)
        self.bit_slider.setFixedWidth(140)
        self.bit_slider.valueChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(self.bit_slider)

        self.bit_label = QLabel("Bit 0 (LSB)")
        self.bit_label.setStyleSheet("font-weight: bold; color: #58a6ff; min-width: 75px;")
        ctrl_layout.addWidget(self.bit_label)

        # Channel Selector
        ctrl_layout.addWidget(QLabel("Channel:"))
        self.channel_combo = QComboBox()
        self.channel_combo.addItems([
            "Combined RGB",
            "Red Channel",
            "Green Channel",
            "Blue Channel",
            "Grayscale",
        ])
        self.channel_combo.currentIndexChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(self.channel_combo)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # Scrollable image display
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet("border: 1px solid #21262d; border-radius: 6px; background-color: #0d1117;")

        self.image_label = QLabel("Load an image to inspect bit-plane slices")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        self.scroll_area.setWidget(self.image_label)

        layout.addWidget(self.scroll_area, 1)

    def set_image(self, image_input: Union[str, Image.Image]):
        if isinstance(image_input, str):
            self.current_image = Image.open(image_input)
        else:
            self.current_image = image_input
        self._update_slice()

    def _on_control_changed(self):
        bit = self.bit_slider.value()
        if bit == 0:
            self.bit_label.setText("Bit 0 (LSB)")
        elif bit == 7:
            self.bit_label.setText("Bit 7 (MSB)")
        else:
            self.bit_label.setText(f"Bit {bit}")
        self._update_slice()

    def _update_slice(self):
        if self.current_image is None:
            return

        bit = self.bit_slider.value()
        channel_map = {
            0: "combined",
            1: "r",
            2: "g",
            3: "b",
            4: "gray",
        }
        channel = channel_map.get(self.channel_combo.currentIndex(), "combined")

        try:
            slice_img = ImageForensics.extract_bit_plane(self.current_image, bit=bit, channel=channel)
            # Convert PIL Image to QPixmap
            if slice_img.mode == "RGB":
                data = slice_img.tobytes("raw", "RGB")
                qimg = QImage(data, slice_img.width, slice_img.height, slice_img.width * 3, QImage.Format.Format_RGB888)
            else:
                data = slice_img.tobytes("raw", "L")
                qimg = QImage(data, slice_img.width, slice_img.height, slice_img.width, QImage.Format.Format_Grayscale8)

            pixmap = QPixmap.fromImage(qimg)
            # Scale if larger than viewer
            scaled = pixmap.scaled(
                480, 360,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
        except Exception as e:
            self.image_label.setText(f"Error rendering bit-plane: {str(e)}")

    def clear(self):
        self.current_image = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("Load an image to inspect bit-plane slices")
