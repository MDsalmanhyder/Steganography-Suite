"""
Decode / Data Extraction View for SecureStego.
Extracts and decrypts text or binary files from stego images with integrity verification.
"""

import os
from typing import Optional
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from securestego.core.stego_engine import StegoEngine, ExtractionResult
from securestego.core.file_manager import FileManager, AuditLogger
from securestego.core.exceptions import (
    InvalidPasswordError,
    IntegrityCheckFailedError,
    PayloadNotFoundError,
    SecureStegoError,
)
from securestego.gui.components.drop_zone import DropZone
from securestego.gui.components.password_box import PasswordBox


class ExtractionWorker(QThread):
    """Worker thread for extracting and decrypting payload."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, engine: StegoEngine, stego_path: str, password: str):
        super().__init__()
        self.engine = engine
        self.stego_path = stego_path
        self.password = password

    def run(self):
        try:
            res = self.engine.extract(
                stego_input=self.stego_path,
                password=self.password,
            )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class DecodeView(QWidget):
    """
    Main View for Extracting and Decrypting Hidden Data from Stego Images.
    """

    def __init__(self, logger: Optional[AuditLogger] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logger or AuditLogger()
        self.engine = StegoEngine()
        self.current_stego_path: Optional[str] = None
        self.last_extraction_result: Optional[ExtractionResult] = None
        self.worker: Optional[ExtractionWorker] = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(14)

        # 1. Stego Image Selection
        image_group = QGroupBox("1. Select Stego Image")
        img_layout = QVBoxLayout(image_group)

        self.stego_drop = DropZone(
            title="Drop Stego Image to Extract Data From",
            subtitle="Lossless PNG image containing hidden data",
            file_filters="Image Files (*.png *.bmp *.tiff *.webp);;All Files (*.*)",
            is_image_only=True,
        )
        self.stego_drop.file_selected.connect(self._on_stego_selected)
        self.stego_drop.file_cleared.connect(self._on_stego_cleared)
        img_layout.addWidget(self.stego_drop)

        layout.addWidget(image_group)

        # 2. Decryption Passphrase
        pwd_group = QGroupBox("2. Enter Decryption Passphrase")
        pwd_layout = QVBoxLayout(pwd_group)

        pwd_layout.addWidget(QLabel("Passphrase used during embedding:"))
        self.password_box = PasswordBox(placeholder="Enter passphrase to decrypt...")
        pwd_layout.addWidget(self.password_box)

        layout.addWidget(pwd_group)

        # 3. Extract Button & Progress
        self.extract_btn = QPushButton("🔓 Extract & Decrypt Hidden Content")
        self.extract_btn.setObjectName("primaryButton")
        self.extract_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.extract_btn.clicked.connect(self._on_extract_clicked)
        layout.addWidget(self.extract_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 4. Results Card
        self.result_card = QGroupBox("Extracted Payload & Cryptographic Verification")
        self.result_layout = QVBoxLayout(self.result_card)

        # Verification Badge
        self.badge_label = QLabel("🛡️ Authenticated & Verified (AES-256-GCM Integrity Check Passed)")
        self.badge_label.setObjectName("badgeSuccess")
        self.result_layout.addWidget(self.badge_label)

        self.info_label = QLabel("")
        self.info_label.setStyleSheet("font-size: 13px; line-height: 1.4;")
        self.result_layout.addWidget(self.info_label)

        # Text Output Container
        self.text_container = QWidget()
        text_sublayout = QVBoxLayout(self.text_container)
        text_sublayout.setContentsMargins(0, 4, 0, 0)

        self.extracted_text_edit = QPlainTextEdit()
        self.extracted_text_edit.setReadOnly(True)
        self.extracted_text_edit.setMinimumHeight(120)
        self.extracted_text_edit.setStyleSheet(
            "font-family: Consolas, 'Courier New', monospace; font-size: 13px; background-color: #0d1117;"
        )
        text_sublayout.addWidget(self.extracted_text_edit)

        text_btn_layout = QHBoxLayout()
        self.copy_btn = QPushButton("📋 Copy Text to Clipboard")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._on_copy_text_clicked)
        text_btn_layout.addWidget(self.copy_btn)

        self.save_text_btn = QPushButton("💾 Save as Text File")
        self.save_text_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_text_btn.clicked.connect(self._on_save_text_clicked)
        text_btn_layout.addWidget(self.save_text_btn)

        text_sublayout.addLayout(text_btn_layout)
        self.result_layout.addWidget(self.text_container)

        # File Output Container
        self.file_container = QWidget()
        file_sublayout = QVBoxLayout(self.file_container)
        file_sublayout.setContentsMargins(0, 4, 0, 0)

        self.file_info_label = QLabel("")
        self.file_info_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #58a6ff;")
        file_sublayout.addWidget(self.file_info_label)

        self.export_file_btn = QPushButton("💾 Export & Save Extracted File")
        self.export_file_btn.setObjectName("accentButton")
        self.export_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_file_btn.clicked.connect(self._on_export_file_clicked)
        file_sublayout.addWidget(self.export_file_btn)

        self.result_layout.addWidget(self.file_container)

        self.result_card.setVisible(False)
        layout.addWidget(self.result_card)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _on_stego_selected(self, file_path: str):
        self.current_stego_path = file_path

    def _on_stego_cleared(self):
        self.current_stego_path = None
        self.result_card.setVisible(False)

    def _on_extract_clicked(self):
        if not self.current_stego_path or not os.path.exists(self.current_stego_path):
            QMessageBox.warning(self, "Image Missing", "Please select a stego image first.")
            return

        password = self.password_box.text()
        if not password:
            QMessageBox.warning(self, "Passphrase Required", "Please enter the decryption passphrase.")
            return

        self.extract_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.result_card.setVisible(False)

        self.worker = ExtractionWorker(
            engine=self.engine,
            stego_path=self.current_stego_path,
            password=password,
        )
        self.worker.finished.connect(self._on_extract_success)
        self.worker.error.connect(self._on_extract_error)
        self.worker.start()

    def _on_extract_success(self, result: ExtractionResult):
        self.extract_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.last_extraction_result = result

        # Log audit entry
        self.logger.log_action(
            action="DECODE",
            status="SUCCESS",
            target_image=self.current_stego_path,
            payload_type=result.payload_type,
            payload_size_bytes=result.payload_size_bytes,
            details=f"Extracted {result.payload_size_bytes:,} bytes ({result.payload_type.upper()}) | Verified: AES-256-GCM Authentic",
            integrity_verified=True,
        )

        self.info_label.setText(
            f"• <b>Payload Type:</b> {result.payload_type.upper()}<br>"
            f"• <b>Payload Size:</b> {result.payload_size_bytes:,} bytes<br>"
            f"• <b>Embedding Density Detected:</b> {result.bits_per_channel} Bit(s) / Channel<br>"
            f"• <b>Cryptographic Tag:</b> Valid (Authenticity Confirmed)"
        )

        if result.payload_type == "text":
            self.text_container.setVisible(True)
            self.file_container.setVisible(False)
            self.extracted_text_edit.setPlainText(result.text or "")
        else:
            self.text_container.setVisible(False)
            self.file_container.setVisible(True)
            self.file_info_label.setText(
                f"📄 File: {result.filename} ({result.payload_size_bytes:,} bytes)"
            )

        self.result_card.setVisible(True)
        QMessageBox.information(
            self,
            "Extraction Complete",
            f"Hidden data successfully extracted and verified authentic!\nPayload Type: {result.payload_type.upper()}",
        )

    def _on_extract_error(self, error_msg: str):
        self.extract_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        self.logger.log_action(
            action="DECODE",
            status="FAILED",
            target_image=self.current_stego_path or "Unknown",
            details=error_msg,
            integrity_verified=False,
        )

        if "Invalid password" in error_msg:
            QMessageBox.critical(
                self,
                "Authentication Failed",
                "Decryption failed: Incorrect passphrase or data was altered/tampered.",
            )
        elif "No valid SecureStego data" in error_msg:
            QMessageBox.warning(
                self,
                "No Payload Detected",
                "No SecureStego header found in this image. Ensure the image has not been compressed/converted to JPEG.",
            )
        else:
            QMessageBox.critical(self, "Extraction Error", f"Failed to extract hidden data:\n\n{error_msg}")

    def _on_copy_text_clicked(self):
        text = self.extracted_text_edit.toPlainText()
        if text:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            QMessageBox.information(self, "Copied", "Secret message copied to clipboard!")

    def _on_save_text_clicked(self):
        text = self.extracted_text_edit.toPlainText()
        if not text:
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extracted Text",
            "extracted_message.txt",
            "Text Files (*.txt);;All Files (*.*)",
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(text)
            QMessageBox.information(self, "Saved", f"Extracted text saved to:\n{save_path}")

    def _on_export_file_clicked(self):
        if not self.last_extraction_result or not self.last_extraction_result.data:
            return

        preferred = self.last_extraction_result.filename or "extracted_file.bin"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extracted File",
            preferred,
            "All Files (*.*)",
        )

        if save_path:
            with open(save_path, "wb") as f:
                f.write(self.last_extraction_result.data)
            self.logger.log_action(
                action="EXPORT",
                status="SUCCESS",
                target_image=save_path,
                details=f"Exported extracted file {preferred} to {save_path}",
                integrity_verified=True,
            )
            QMessageBox.information(
                self,
                "File Exported",
                f"File successfully exported and saved to:\n{save_path}",
            )
