"""
Drag and Drop Zone Widget for CloakPix.
"""

import os
import wave
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PIL import Image


class DropZone(QFrame):
    """
    Interactive drag-and-drop zone with image thumbnail and audio file preview.
    """
    file_selected = pyqtSignal(str)
    file_cleared = pyqtSignal()

    def __init__(
        self,
        title: str = "Drag & Drop Carrier (Image or WAV Audio) Here",
        subtitle: str = "Supports PNG, BMP, TIFF, WEBP, and WAV Audio",
        file_filters: str = "Supported Carriers (*.png *.bmp *.tiff *.webp *.wav);;Images (*.png *.bmp *.tiff *.webp);;Audio Files (*.wav);;All Files (*.*)",
        is_image_only: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.title_text = title
        self.subtitle_text = subtitle
        self.file_filters = file_filters
        self.is_image_only = is_image_only
        self.current_file_path: Optional[str] = None

        self.setAcceptDrops(True)
        self.setObjectName("dropZone")
        self._init_ui()
        self._set_default_style()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(8)

        # Icon / Preview Label
        self.icon_label = QLabel("🖼️" if self.is_image_only else "📁")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("font-size: 36px; background: transparent;")
        self.layout.addWidget(self.icon_label)

        # Title Label
        self.title_label = QLabel(self.title_text)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff; background: transparent;")
        self.layout.addWidget(self.title_label)

        # Subtitle Label
        self.subtitle_label = QLabel(self.subtitle_text)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("font-size: 11px; color: #8b949e; background: transparent;")
        self.layout.addWidget(self.subtitle_label)

        # Action Buttons Container
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.browse_btn = QPushButton("📁 Browse...")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        btn_layout.addWidget(self.browse_btn)

        self.clear_btn = QPushButton("✕ Clear")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear)
        self.clear_btn.setVisible(False)
        btn_layout.addWidget(self.clear_btn)

        self.layout.addLayout(btn_layout)

    def _set_default_style(self):
        self.setStyleSheet("""
            QFrame#dropZone {
                background-color: #161b22;
                border: 2px dashed #30363d;
                border-radius: 12px;
                min-height: 140px;
            }
        """)

    def _set_drag_active_style(self):
        self.setStyleSheet("""
            QFrame#dropZone {
                background-color: #1f293d;
                border: 2px dashed #58a6ff;
                border-radius: 12px;
                min-height: 140px;
            }
        """)

    def _set_loaded_style(self):
        self.setStyleSheet("""
            QFrame#dropZone {
                background-color: #161b22;
                border: 2px solid #238636;
                border-radius: 12px;
                min-height: 140px;
            }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._set_drag_active_style()

    def dragLeaveEvent(self, event):
        if self.current_file_path:
            self._set_loaded_style()
        else:
            self._set_default_style()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            if os.path.exists(file_path):
                self.set_file(file_path)
        event.acceptProposedAction()

    def _on_browse_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            self.file_filters,
        )
        if file_path:
            self.set_file(file_path)

    def set_file(self, file_path: str):
        self.current_file_path = file_path
        filename = os.path.basename(file_path)
        size_kb = os.path.getsize(file_path) / 1024.0
        ext = os.path.splitext(filename)[1].lower()

        if ext == ".wav":
            try:
                with wave.open(file_path, "rb") as wf:
                    frames = wf.getnframes()
                    rate = wf.getframerate()
                    duration = frames / float(rate) if rate > 0 else 0.0
                    channels = wf.getnchannels()
                    sampwidth = wf.getsampwidth() * 8
                self.icon_label.setPixmap(QPixmap())
                self.icon_label.setText("🎵")
                self.icon_label.setStyleSheet("font-size: 40px; background: transparent;")
                ch_str = "Mono" if channels == 1 else "Stereo" if channels == 2 else f"{channels}ch"
                self.title_label.setText(f"{filename} ({duration:.2f}s, {ch_str})")
                self.subtitle_label.setText(f"{rate:,} Hz | {sampwidth}-bit PCM | {size_kb:.1f} KB")
            except Exception:
                self.icon_label.setPixmap(QPixmap())
                self.icon_label.setText("🎵")
                self.title_label.setText(filename)
                self.subtitle_label.setText(f"WAV Audio | Size: {size_kb:.1f} KB")
        elif ext in [".png", ".bmp", ".tiff", ".tif", ".webp", ".jpg", ".jpeg"] or self.is_image_only:
            try:
                # Load image and make thumbnail
                pixmap = QPixmap(file_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        100, 100,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self.icon_label.setPixmap(scaled_pixmap)
                    self.icon_label.setStyleSheet("background: transparent; border-radius: 6px;")
                else:
                    self.icon_label.setText("🖼️")
            except Exception:
                self.icon_label.setText("🖼️")

            # Get dimensions
            try:
                with Image.open(file_path) as img:
                    w, h = img.size
                    mode = img.mode
                self.title_label.setText(f"{filename} ({w}×{h} px)")
                self.subtitle_label.setText(f"Mode: {mode} | Size: {size_kb:.1f} KB")
            except Exception:
                self.title_label.setText(filename)
                self.subtitle_label.setText(f"Size: {size_kb:.1f} KB")
        else:
            self.icon_label.setPixmap(QPixmap())
            self.icon_label.setText("📄")
            self.title_label.setText(filename)
            self.subtitle_label.setText(f"Type: {ext.upper()} | Size: {size_kb:.1f} KB")

        self.clear_btn.setVisible(True)
        self._set_loaded_style()
        self.file_selected.emit(file_path)

    def clear(self):
        self.current_file_path = None
        self.icon_label.setPixmap(QPixmap())
        self.icon_label.setText("🖼️" if self.is_image_only else "📁")
        self.icon_label.setStyleSheet("font-size: 36px; background: transparent;")
        self.title_label.setText(self.title_text)
        self.subtitle_label.setText(self.subtitle_text)
        self.clear_btn.setVisible(False)
        self._set_default_style()
        self.file_cleared.emit()

    def get_file_path(self) -> Optional[str]:
        return self.current_file_path
