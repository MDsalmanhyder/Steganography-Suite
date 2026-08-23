"""
Main Application Window for SecureStego.
Combines tabs, menus, status bar, and modern styling.
"""

import os
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PIL import Image
import numpy as np

from securestego import __version__
from securestego.core.file_manager import AuditLogger
from securestego.core.metrics import calculate_image_capacity
from securestego.gui.styles import DARK_THEME_QSS
from securestego.gui.views.encode_view import EncodeView
from securestego.gui.views.decode_view import DecodeView
from securestego.gui.views.forensics_view import ForensicsView
from securestego.gui.views.history_view import HistoryView


class CapacityCalculatorDialog(QDialog):
    """Utility modal dialog for calculating image capacity."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Carrier Capacity Calculator")
        self.setFixedSize(380, 240)
        self.setStyleSheet(DARK_THEME_QSS)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.width_spin = QSpinBox()
        self.width_spin.setRange(10, 10000)
        self.width_spin.setValue(1920)
        self.width_spin.valueChanged.connect(self._recalc)
        form.addRow("Image Width (px):", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(10, 10000)
        self.height_spin.setValue(1080)
        self.height_spin.valueChanged.connect(self._recalc)
        form.addRow("Image Height (px):", self.height_spin)

        self.bpc_spin = QSpinBox()
        self.bpc_spin.setRange(1, 4)
        self.bpc_spin.setValue(1)
        self.bpc_spin.valueChanged.connect(self._recalc)
        form.addRow("LSB Bits / Channel:", self.bpc_spin)

        layout.addLayout(form)

        self.result_label = QLabel()
        self.result_label.setStyleSheet("font-size: 13px; color: #58a6ff; font-weight: bold; padding: 10px; background: #161b22; border-radius: 6px;")
        layout.addWidget(self.result_label)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self._recalc()

    def _recalc(self):
        w = self.width_spin.value()
        h = self.height_spin.value()
        bpc = self.bpc_spin.value()
        info = calculate_image_capacity(w, h, channels=3, bits_per_channel=bpc)
        raw_kb = info["raw_capacity_bytes"] / 1024.0
        raw_mb = raw_kb / 1024.0
        self.result_label.setText(
            f"Total Raw Capacity: {info['raw_capacity_bytes']:,} bytes\n"
            f"≈ {raw_kb:.1f} KB ({raw_mb:.2f} MB)\n"
            f"Usable Payload: ~{info['usable_capacity_bytes']:,} bytes"
        )


class MainWindow(QMainWindow):
    """
    Primary desktop interface window for SecureStego.
    """

    def __init__(self):
        super().__init__()
        self.logger = AuditLogger()
        self.setWindowTitle(f"SecureStego – Secure Image Steganography & Forensics v{__version__}")
        self.resize(1100, 780)
        self.setMinimumSize(920, 640)

        # Apply Global Dark Stylesheet
        self.setStyleSheet(DARK_THEME_QSS)

        self._init_menu()
        self._init_ui()
        self._init_status_bar()

    def _init_menu(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("📁 File")
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools Menu
        tools_menu = menubar.addMenu("🛠️ Tools")

        calc_action = QAction("Capacity Calculator...", self)
        calc_action.triggered.connect(self._open_capacity_calculator)
        tools_menu.addAction(calc_action)

        gen_carrier_action = QAction("Generate Synthetic Test Carrier Image...", self)
        gen_carrier_action.triggered.connect(self._generate_synthetic_carrier)
        tools_menu.addAction(gen_carrier_action)

        # Help Menu
        help_menu = menubar.addMenu("❓ Help")

        crypto_action = QAction("Cryptographic Specifications", self)
        crypto_action.triggered.connect(self._show_crypto_info)
        help_menu.addAction(crypto_action)

        about_action = QAction("About SecureStego", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _init_ui(self):
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # 1. Encode View
        self.encode_view = EncodeView(logger=self.logger)
        self.tabs.addTab(self.encode_view, "🔏 Hide Secret Data (Encode)")

        # 2. Decode View
        self.decode_view = DecodeView(logger=self.logger)
        self.tabs.addTab(self.decode_view, "🔓 Extract Hidden Data (Decode)")

        # 3. Forensics View
        self.forensics_view = ForensicsView(logger=self.logger)
        self.tabs.addTab(self.forensics_view, "🔬 Forensics & Steganalysis Lab")

        # 4. Audit History View
        self.history_view = HistoryView(logger=self.logger)
        self.tabs.addTab(self.history_view, "📋 Audit Trail & History")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self.tabs)

    def _init_status_bar(self):
        self.status = QStatusBar()
        self.status.showMessage("Ready | Crypto Engine: AES-256-GCM + PBKDF2-HMAC-SHA256 (200k iterations)")
        self.setStatusBar(self.status)

    def _on_tab_changed(self, index: int):
        if index == 3:
            # Refresh history tab whenever user switches to it
            self.history_view.refresh_logs()

    def _open_capacity_calculator(self):
        dialog = CapacityCalculatorDialog(self)
        dialog.exec()

    def _generate_synthetic_carrier(self):
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Synthetic Test Carrier Image",
            "synthetic_carrier_1080p.png",
            "PNG Image (*.png)",
        )
        if save_path:
            # Create a 1920x1080 synthetic gradient image
            w, h = 1920, 1080
            arr = np.zeros((h, w, 3), dtype=np.uint8)
            # Plasma gradient
            x = np.linspace(0, 10, w)
            y = np.linspace(0, 10, h)
            xx, yy = np.meshgrid(x, y)
            arr[:, :, 0] = ((np.sin(xx) + 1.0) * 127.5).astype(np.uint8)
            arr[:, :, 1] = ((np.cos(yy) + 1.0) * 127.5).astype(np.uint8)
            arr[:, :, 2] = ((np.sin(xx + yy) + 1.0) * 127.5).astype(np.uint8)
            img = Image.fromarray(arr, mode="RGB")
            img.save(save_path, "PNG")

            QMessageBox.information(
                self,
                "Carrier Generated",
                f"Synthetic 1080p carrier image generated successfully at:\n{save_path}\n"
                f"Raw Capacity: 777,600 bytes (~759 KB)",
            )

    def _show_crypto_info(self):
        QMessageBox.information(
            self,
            "Cryptographic Security Model",
            "SecureStego Cryptographic Architecture:\n\n"
            "• Encryption Cipher: AES-256-GCM (Galois/Counter Mode)\n"
            "• Key Derivation: PBKDF2-HMAC-SHA256 with 200,000 iterations\n"
            "• Salt: 128-bit (16-byte) cryptographically secure pseudorandom salt\n"
            "• Initialization Vector: 96-bit (12-byte) random nonce per operation\n"
            "• Authenticated Tag: 128-bit (16-byte) GCM GMAC tag\n"
            "• Header Checksum: CRC32 integrity verification\n\n"
            "Guarantees:\n"
            "Confidentiality, ciphertext authenticity, and tamper detection.",
        )

    def _show_about_dialog(self):
        QMessageBox.about(
            self,
            "About SecureStego",
            f"<b>SecureStego v{__version__}</b><br><br>"
            "An enterprise-grade cross-platform steganography and image forensics suite.<br><br>"
            "<b>Features:</b><br>"
            "• AES-256-GCM encrypted LSB data embedding (Text & Arbitrary Files)<br>"
            "• Multi-bit LSB density configuration (1 to 4 bits/channel)<br>"
            "• Visual bit-plane slicer & Chi-Square steganalysis lab<br>"
            "• Shannon entropy statistics & PDF forensic reports<br>"
            "• Persistent audit logging & capacity calculations<br><br>"
            "Built with Python 3.12, PyQt6, PyCryptodome, Pillow, and NumPy.",
        )
