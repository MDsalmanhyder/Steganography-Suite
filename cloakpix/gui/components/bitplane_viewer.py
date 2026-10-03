"""
Interactive Bit-Plane Viewer Component for CloakPix Forensics.
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
from cloakpix.core.forensics import ImageForensics


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

        # Mode Selector
        ctrl_layout.addWidget(QLabel("Inspection Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Individual Bit-Plane",
            "StegDetect Dynamic Range Normalizer",
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        ctrl_layout.addWidget(self.mode_combo)

        # Plane / LSB Selector
        self.slider_title = QLabel("Bit Plane:")
        ctrl_layout.addWidget(self.slider_title)
        self.bit_slider = QSlider(Qt.Orientation.Horizontal)
        self.bit_slider.setRange(0, 7)
        self.bit_slider.setValue(0)
        self.bit_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.bit_slider.setTickInterval(1)
        self.bit_slider.setFixedWidth(130)
        self.bit_slider.valueChanged.connect(self._on_control_changed)
        ctrl_layout.addWidget(self.bit_slider)

        self.bit_label = QLabel("Bit 0 (LSB)")
        self.bit_label.setStyleSheet("font-weight: bold; color: #58a6ff; min-width: 85px;")
        ctrl_layout.addWidget(self.bit_label)

        # Channel Selector
        self.channel_label = QLabel("Channel:")
        ctrl_layout.addWidget(self.channel_label)
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

        self.image_label = QLabel("Load an image to inspect bit-plane slices or StegDetect contrast")
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

    def _on_mode_changed(self):
        is_stegdetect = self.mode_combo.currentIndex() == 1
        if is_stegdetect:
            self.slider_title.setText("LSBs to Amplify:")
            self.bit_slider.blockSignals(True)
            self.bit_slider.setRange(1, 8)
            self.bit_slider.setValue(2)
            self.bit_slider.blockSignals(False)
            self.bit_label.setText("2 LSBs (0-255)")
            self.channel_combo.setEnabled(False)
            self.channel_label.setEnabled(False)
        else:
            self.slider_title.setText("Bit Plane:")
            self.bit_slider.blockSignals(True)
            self.bit_slider.setRange(0, 7)
            self.bit_slider.setValue(0)
            self.bit_slider.blockSignals(False)
            self.bit_label.setText("Bit 0 (LSB)")
            self.channel_combo.setEnabled(True)
            self.channel_label.setEnabled(True)
        self._update_slice()

    def _on_control_changed(self):
        is_stegdetect = self.mode_combo.currentIndex() == 1
        val = self.bit_slider.value()

        if is_stegdetect:
            self.bit_label.setText(f"{val} LSB{'s' if val > 1 else ''} (0-255)")
        else:
            if val == 0:
                self.bit_label.setText("Bit 0 (LSB)")
            elif val == 7:
                self.bit_label.setText("Bit 7 (MSB)")
            else:
                self.bit_label.setText(f"Bit {val}")
        self._update_slice()

    def _update_slice(self):
        if self.current_image is None:
            return

        is_stegdetect = self.mode_combo.currentIndex() == 1
        val = self.bit_slider.value()

        try:
            if is_stegdetect:
                slice_img = ImageForensics.stegdetect_amplify(self.current_image, num_lsbs=val)
            else:
                channel_map = {
                    0: "combined",
                    1: "r",
                    2: "g",
                    3: "b",
                    4: "gray",
                }
                channel = channel_map.get(self.channel_combo.currentIndex(), "combined")
                slice_img = ImageForensics.extract_bit_plane(self.current_image, bit=val, channel=channel)

            # Convert PIL Image to QPixmap
            if slice_img.mode == "RGB":
                data = slice_img.tobytes("raw", "RGB")
                qimg = QImage(data, slice_img.width, slice_img.height, slice_img.width * 3, QImage.Format.Format_RGB888)
            elif slice_img.mode == "RGBA":
                rgb_img = slice_img.convert("RGB")
                data = rgb_img.tobytes("raw", "RGB")
                qimg = QImage(data, rgb_img.width, rgb_img.height, rgb_img.width * 3, QImage.Format.Format_RGB888)
            else:
                data = slice_img.tobytes("raw", "L")
                qimg = QImage(data, slice_img.width, slice_img.height, slice_img.width, QImage.Format.Format_Grayscale8)

            pixmap = QPixmap.fromImage(qimg)
            # Scale if larger than viewer
            scaled = pixmap.scaled(
                500, 380,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
        except Exception as e:
            self.image_label.setText(f"Error rendering visual: {str(e)}")

    def clear(self):
        self.current_image = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("Load an image to inspect bit-plane slices")
