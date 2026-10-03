"""
Encode / Data Hiding View for CloakPix.
Provides rich interface for embedding encrypted text or files into images and WAV audio.
"""

import os
from typing import Optional
from PIL import Image
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from cloakpix.core.unified_engine import UnifiedStegoEngine, UnifiedEmbeddingResult
from cloakpix.core.audio_stego import calculate_audio_capacity
from cloakpix.core.file_manager import FileManager, AuditLogger
from cloakpix.core.metrics import calculate_image_capacity
from cloakpix.core.exceptions import CapacityOverflowError, CloakPixError
from cloakpix.gui.components.drop_zone import DropZone
from cloakpix.gui.components.capacity_bar import CapacityBar
from cloakpix.gui.components.password_box import PasswordBox


class EmbeddingWorker(QThread):
    """Background worker for embedding without freezing the GUI."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        engine: UnifiedStegoEngine,
        carrier_path: str,
        password: str,
        secret_text: Optional[str] = None,
        secret_file_path: Optional[str] = None,
        bits_per_channel: int = 1,
        compress: bool = True,
    ):
        super().__init__()
        self.engine = engine
        self.carrier_path = carrier_path
        self.password = password
        self.secret_text = secret_text
        self.secret_file_path = secret_file_path
        self.bits_per_channel = bits_per_channel
        self.compress = compress

    def run(self):
        try:
            res = self.engine.embed(
                carrier_input=self.carrier_path,
                password=self.password,
                secret_text=self.secret_text,
                secret_file_path=self.secret_file_path,
                bits_per_channel=self.bits_per_channel,
                compress=self.compress,
            )
            self.finished.emit(res)
        except Exception as e:
            self.error.emit(str(e))


class EncodeView(QWidget):
    """
    Main View for Hiding Data (Text / Files) in Carrier Images or Audio.
    """

    def __init__(self, logger: Optional[AuditLogger] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logger or AuditLogger()
        self.engine = UnifiedStegoEngine()
        self.current_carrier_path: Optional[str] = None
        self.current_secret_file_path: Optional[str] = None
        self.last_embedding_result: Optional[UnifiedEmbeddingResult] = None
        self.worker: Optional[EmbeddingWorker] = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(14)

        # 1. Carrier Media Section
        carrier_group = QGroupBox("1. Select Carrier Media (Image or Audio)")
        carrier_layout = QVBoxLayout(carrier_group)

        self.carrier_drop = DropZone(
            title="Drop Cover Carrier (Image or WAV Audio) Here",
            subtitle="Supports PNG, BMP, TIFF, WEBP, and WAV Audio",
            file_filters="Supported Carriers (*.png *.bmp *.tiff *.webp *.wav);;Images (*.png *.bmp *.tiff *.webp);;Audio Files (*.wav);;All Files (*.*)",
            is_image_only=False,
        )
        self.carrier_drop.file_selected.connect(self._on_carrier_selected)
        self.carrier_drop.file_cleared.connect(self._on_carrier_cleared)
        carrier_layout.addWidget(self.carrier_drop)

        self.capacity_bar = CapacityBar()
        carrier_layout.addWidget(self.capacity_bar)

        layout.addWidget(carrier_group)

        # 2. Secret Payload Section
        payload_group = QGroupBox("2. Secret Payload Data")
        payload_layout = QVBoxLayout(payload_group)

        # Payload Mode Switch
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup(self)

        self.text_radio = QRadioButton("📝 Hide Secret Text Message")
        self.text_radio.setChecked(True)
        self.mode_group.addButton(self.text_radio)
        mode_layout.addWidget(self.text_radio)

        self.file_radio = QRadioButton("📁 Hide Secret File (PDF, DOCX, ZIP, Image, etc.)")
        self.mode_group.addButton(self.file_radio)
        mode_layout.addWidget(self.file_radio)

        self.text_radio.toggled.connect(self._on_mode_toggled)
        payload_layout.addLayout(mode_layout)

        # Text Input Area
        self.text_container = QWidget()
        text_layout = QVBoxLayout(self.text_container)
        text_layout.setContentsMargins(0, 4, 0, 0)
        self.text_edit = QPlainTextEdit()
        self.text_edit.setPlaceholderText("Type or paste your secret message here...")
        self.text_edit.setMinimumHeight(100)
        self.text_edit.textChanged.connect(self._recalc_capacity)
        text_layout.addWidget(self.text_edit)

        self.char_count_label = QLabel("0 characters | 0 bytes")
        self.char_count_label.setStyleSheet("font-size: 11px; color: #8b949e; font-family: monospace;")
        text_layout.addWidget(self.char_count_label)
        payload_layout.addWidget(self.text_container)

        # File Input Area
        self.file_container = QWidget()
        file_layout = QVBoxLayout(self.file_container)
        file_layout.setContentsMargins(0, 4, 0, 0)
        self.secret_file_drop = DropZone(
            title="Drop Secret File to Hide",
            subtitle="Any file type: PDF, DOCX, ZIP, TXT, PNG, etc.",
            file_filters="All Files (*.*)",
            is_image_only=False,
        )
        self.secret_file_drop.file_selected.connect(self._on_secret_file_selected)
        self.secret_file_drop.file_cleared.connect(self._on_secret_file_cleared)
        file_layout.addWidget(self.secret_file_drop)
        self.file_container.setVisible(False)
        payload_layout.addWidget(self.file_container)

        layout.addWidget(payload_group)

        # 3. Security & Advanced Configuration
        config_group = QGroupBox("3. Security & Stego Configuration")
        config_layout = QVBoxLayout(config_group)

        # Password Box
        config_layout.addWidget(QLabel("Encryption Passphrase (AES-256-GCM + PBKDF2):"))
        self.password_box = PasswordBox()
        config_layout.addWidget(self.password_box)

        # Compression Checkbox
        self.compress_cb = QCheckBox("🗜️ Pre-compress payload before encryption (Deflate/zlib)")
        self.compress_cb.setChecked(True)
        self.compress_cb.setStyleSheet("color: #58a6ff; font-weight: bold; margin: 4px 0;")
        config_layout.addWidget(self.compress_cb)

        # LSB Slider Row
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("LSB Embedding Density:"))

        self.lsb_slider = QSlider(Qt.Orientation.Horizontal)
        self.lsb_slider.setRange(1, 4)
        self.lsb_slider.setValue(1)
        self.lsb_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.lsb_slider.setTickInterval(1)
        self.lsb_slider.setFixedWidth(160)
        self.lsb_slider.valueChanged.connect(self._on_lsb_slider_changed)
        slider_layout.addWidget(self.lsb_slider)

        self.lsb_label = QLabel("1 Bit / Channel (Max Visual/Acoustic Fidelity)")
        self.lsb_label.setStyleSheet("color: #58a6ff; font-weight: bold;")
        slider_layout.addWidget(self.lsb_label)

        slider_layout.addStretch()
        config_layout.addLayout(slider_layout)

        layout.addWidget(config_group)

        # 4. Action Button & Progress
        self.embed_btn = QPushButton("🔒 Encrypt & Embed Data")
        self.embed_btn.setObjectName("primaryButton")
        self.embed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.embed_btn.clicked.connect(self._on_embed_clicked)
        layout.addWidget(self.embed_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate animation
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 5. Results & Metrics Card
        self.result_card = QGroupBox("Embedding Results & Quality Analysis")
        result_layout = QVBoxLayout(self.result_card)

        self.metrics_label = QLabel("Ready to embed.")
        self.metrics_label.setStyleSheet("font-size: 13px; line-height: 1.4;")
        result_layout.addWidget(self.metrics_label)

        self.save_btn = QPushButton("💾 Save Stego Carrier")
        self.save_btn.setObjectName("accentButton")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.save_btn.setVisible(False)
        result_layout.addWidget(self.save_btn)

        self.result_card.setVisible(False)
        layout.addWidget(self.result_card)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _on_carrier_selected(self, file_path: str):
        self.current_carrier_path = file_path
        self._recalc_capacity()

    def _on_carrier_cleared(self):
        self.current_carrier_path = None
        self.capacity_bar.reset()

    def _on_secret_file_selected(self, file_path: str):
        self.current_secret_file_path = file_path
        self._recalc_capacity()

    def _on_secret_file_cleared(self):
        self.current_secret_file_path = None
        self._recalc_capacity()

    def _on_mode_toggled(self):
        is_text = self.text_radio.isChecked()
        self.text_container.setVisible(is_text)
        self.file_container.setVisible(not is_text)
        self._recalc_capacity()

    def _on_lsb_slider_changed(self, value: int):
        labels = {
            1: "1 Bit / Channel (Max Fidelity, PSNR > 50 dB / SNR > 60 dB)",
            2: "2 Bits / Channel (Balanced Capacity, High Quality)",
            3: "3 Bits / Channel (High Capacity)",
            4: "4 Bits / Channel (Maximum Capacity)",
        }
        self.lsb_label.setText(labels.get(value, f"{value} Bits"))
        self._recalc_capacity()

    def _recalc_capacity(self):
        bpc = self.lsb_slider.value()

        # Calculate payload size
        if self.text_radio.isChecked():
            text = self.text_edit.toPlainText()
            raw_bytes = len(text.encode("utf-8"))
            self.char_count_label.setText(f"{len(text):,} characters | {raw_bytes:,} bytes")
        else:
            if self.current_secret_file_path and os.path.exists(self.current_secret_file_path):
                raw_bytes = os.path.getsize(self.current_secret_file_path)
            else:
                raw_bytes = 0

        # Estimated total stream bytes (header + tag + nonce + ciphertext)
        estimated_stream = raw_bytes + 128 if raw_bytes > 0 else 0

        if self.current_carrier_path and os.path.exists(self.current_carrier_path):
            ext = os.path.splitext(self.current_carrier_path)[1].lower()
            if ext == ".wav":
                try:
                    cap_info = calculate_audio_capacity(self.current_carrier_path, bpc)
                    max_bytes = cap_info["raw_capacity_bytes"]
                    self.capacity_bar.update_capacity(estimated_stream, max_bytes)
                except Exception:
                    self.capacity_bar.reset()
            else:
                try:
                    with Image.open(self.current_carrier_path) as img:
                        w, h = img.size
                        channels = 4 if img.mode == "RGBA" else 3
                        cap_info = calculate_image_capacity(w, h, channels=channels, bits_per_channel=bpc)
                        max_bytes = cap_info["raw_capacity_bytes"]
                        self.capacity_bar.update_capacity(estimated_stream, max_bytes)
                except Exception:
                    self.capacity_bar.reset()
        else:
            self.capacity_bar.reset()

    def _on_embed_clicked(self):
        if not self.current_carrier_path or not os.path.exists(self.current_carrier_path):
            QMessageBox.warning(self, "Carrier Missing", "Please select a carrier image or audio file first.")
            return

        password = self.password_box.text()
        if not password:
            QMessageBox.warning(self, "Passphrase Required", "Please enter an encryption passphrase.")
            return

        secret_text = None
        secret_file_path = None

        if self.text_radio.isChecked():
            secret_text = self.text_edit.toPlainText()
            if not secret_text:
                QMessageBox.warning(self, "Empty Message", "Please enter a secret message to hide.")
                return
        else:
            if not self.current_secret_file_path or not os.path.exists(self.current_secret_file_path):
                QMessageBox.warning(self, "File Missing", "Please select a secret file to hide.")
                return
            secret_file_path = self.current_secret_file_path

        bpc = self.lsb_slider.value()
        compress = self.compress_cb.isChecked()

        # Start embedding in background worker
        self.embed_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = EmbeddingWorker(
            engine=self.engine,
            carrier_path=self.current_carrier_path,
            password=password,
            secret_text=secret_text,
            secret_file_path=secret_file_path,
            bits_per_channel=bpc,
            compress=compress,
        )
        self.worker.finished.connect(self._on_embed_success)
        self.worker.error.connect(self._on_embed_error)
        self.worker.start()

    def _on_embed_success(self, result: UnifiedEmbeddingResult):
        self.embed_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.last_embedding_result = result

        # Log audit entry
        self.logger.log_action(
            action="ENCODE",
            status="SUCCESS",
            target_image=self.current_carrier_path,
            payload_type=result.payload_type,
            payload_size_bytes=result.payload_bytes,
            details=f"Embedded {result.total_embedded_bytes:,} bytes ({result.capacity_used_pct}% cap) into {result.carrier_type.upper()}",
            integrity_verified=True,
        )

        comp_badge = "Enabled (zlib Deflate)" if self.compress_cb.isChecked() else "Disabled"

        if result.carrier_type == "audio":
            snr_badge = "🟢 Imperceptible Acoustic Noise" if (result.snr_db or 0.0) >= 60.0 else "🟡 Good Audio Quality"
            self.metrics_label.setText(
                f"✅ <b>Data Successfully Encrypted & Embedded into Audio!</b><br><br>"
                f"• <b>Carrier Type:</b> WAV Audio (PCM)<br>"
                f"• <b>Payload Size:</b> {result.payload_bytes:,} bytes ({result.payload_type.upper()})<br>"
                f"• <b>Pre-Compression:</b> {comp_badge}<br>"
                f"• <b>Total Embedded Stream:</b> {result.total_embedded_bytes:,} bytes ({result.capacity_used_pct}% of audio capacity)<br>"
                f"• <b>Signal-to-Noise Ratio (SNR):</b> <b>{result.snr_db:.2f} dB</b> ({snr_badge})<br>"
                f"• <b>Encryption:</b> AES-256-GCM (PBKDF2 200k rounds)"
            )
            self.save_btn.setText("💾 Save Stego Audio (Lossless WAV)")
        else:
            quality_badge = "🟢 Excellent Fidelity (Imperceptible)" if (result.psnr_db or 0.0) >= 48.0 else "🟡 Good Quality"
            self.metrics_label.setText(
                f"✅ <b>Data Successfully Encrypted & Embedded into Image!</b><br><br>"
                f"• <b>Carrier Type:</b> Image ({result.carrier_format or 'PNG'})<br>"
                f"• <b>Payload Size:</b> {result.payload_bytes:,} bytes ({result.payload_type.upper()})<br>"
                f"• <b>Pre-Compression:</b> {comp_badge}<br>"
                f"• <b>Total Embedded Stream:</b> {result.total_embedded_bytes:,} bytes ({result.capacity_used_pct}% of image capacity)<br>"
                f"• <b>Peak Signal-to-Noise Ratio (PSNR):</b> <b>{result.psnr_db} dB</b> ({quality_badge})<br>"
                f"• <b>Mean Squared Error (MSE):</b> {result.mse}<br>"
                f"• <b>Structural Similarity (SSIM):</b> {result.ssim}<br>"
                f"• <b>Encryption:</b> AES-256-GCM (PBKDF2 200k rounds)"
            )
            self.save_btn.setText("💾 Save Stego Image (Lossless PNG/BMP/TIFF/WEBP)")

        self.save_btn.setVisible(True)
        self.result_card.setVisible(True)

        metric_str = f"SNR: {result.snr_db:.2f} dB" if result.carrier_type == "audio" else f"PSNR: {result.psnr_db} dB"
        QMessageBox.information(
            self,
            "Embedding Complete",
            f"Data successfully encrypted and embedded into {result.carrier_type.upper()}!\n{metric_str}",
        )

    def _on_embed_error(self, error_msg: str):
        self.embed_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        self.logger.log_action(
            action="ENCODE",
            status="FAILED",
            target_image=self.current_carrier_path or "Unknown",
            details=error_msg,
            integrity_verified=False,
        )

        QMessageBox.critical(self, "Embedding Error", f"Failed to embed data:\n\n{error_msg}")

    def _on_save_clicked(self):
        if not self.last_embedding_result:
            return

        res = self.last_embedding_result
        if res.carrier_type == "audio":
            default_name = "stego_audio.wav"
            if self.current_carrier_path:
                base = os.path.splitext(os.path.basename(self.current_carrier_path))[0]
                default_name = f"{base}_stego.wav"

            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Stego Audio File",
                default_name,
                "WAV Audio (*.wav)",
            )
            if save_path:
                UnifiedStegoEngine.save_stego_carrier(res, save_path)
                self.logger.log_action(
                    action="EXPORT",
                    status="SUCCESS",
                    target_image=save_path,
                    details=f"Saved stego audio to {save_path}",
                    integrity_verified=True,
                )
                QMessageBox.information(
                    self,
                    "Saved Successfully",
                    f"Stego audio successfully saved in lossless WAV format to:\n{save_path}",
                )
        else:
            default_name = "stego_output.png"
            if self.current_carrier_path:
                base = os.path.splitext(os.path.basename(self.current_carrier_path))[0]
                default_name = f"{base}_stego.png"

            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Stego Image",
                default_name,
                "Lossless PNG (*.png);;Bitmap Image (*.bmp);;TIFF Image (*.tiff);;Lossless WEBP (*.webp)",
            )

            if save_path:
                UnifiedStegoEngine.save_stego_carrier(res, save_path)
                self.logger.log_action(
                    action="EXPORT",
                    status="SUCCESS",
                    target_image=save_path,
                    details=f"Saved stego image to {save_path}",
                    integrity_verified=True,
                )
                QMessageBox.information(
                    self,
                    "Saved Successfully",
                    f"Stego image successfully saved in lossless format to:\n{save_path}",
                )
