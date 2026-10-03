"""
Forensics and Steganalysis Lab View for CloakPix.
Provides visual bit-plane extraction, StegDetect contrast normalization, Chi-Square analysis,
Shannon entropy, and multi-media (Image + Audio) forensic reporting.
"""

import os
import json
from typing import Optional, Union
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cloakpix.core.forensics import ImageForensics, ForensicAnalysisReport
from cloakpix.core.audio_forensics import AudioForensics, AudioForensicReport
from cloakpix.core.file_manager import AuditLogger
from cloakpix.gui.components.drop_zone import DropZone
from cloakpix.gui.components.bitplane_viewer import BitPlaneViewer


class ForensicWorker(QThread):
    """Worker thread for running forensic computations on image or audio carriers."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, target_path: str):
        super().__init__()
        self.target_path = target_path

    def run(self):
        try:
            ext = os.path.splitext(self.target_path)[1].lower()
            if ext == ".wav":
                report = AudioForensics.analyze_audio(self.target_path)
            else:
                report = ImageForensics.analyze_image(self.target_path)
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))


class ForensicsView(QWidget):
    """
    Main Steganalysis & Multi-Media Forensics Lab View.
    """

    def __init__(self, logger: Optional[AuditLogger] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logger or AuditLogger()
        self.current_target_path: Optional[str] = None
        self.last_report: Optional[Union[ForensicAnalysisReport, AudioForensicReport]] = None
        self.worker: Optional[ForensicWorker] = None

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(14)

        # 1. Target Carrier Drop Zone
        carrier_group = QGroupBox("1. Select Carrier for Forensic Steganalysis")
        carrier_layout = QVBoxLayout(carrier_group)

        self.carrier_drop = DropZone(
            title="Drop Image or WAV Audio Here for Steganalysis",
            subtitle="Bit-Plane noise, StegDetect contrast normalization, Chi-Square, and audio entropy",
            file_filters="Supported Media (*.png *.bmp *.tiff *.webp *.wav);;Images (*.png *.bmp *.tiff *.webp);;Audio (*.wav);;All Files (*.*)",
            is_image_only=False,
        )
        self.carrier_drop.file_selected.connect(self._on_carrier_selected)
        self.carrier_drop.file_cleared.connect(self._on_carrier_cleared)
        self.image_drop = self.carrier_drop  # Alias for backward compatibility
        carrier_layout.addWidget(self.carrier_drop)

        # Run Analysis Button
        action_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("🔬 Run Comprehensive Forensic Analysis")
        self.analyze_btn.setObjectName("primaryButton")
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._on_run_analysis_clicked)
        action_layout.addWidget(self.analyze_btn)

        self.export_report_btn = QPushButton("📄 Export Forensic Report")
        self.export_report_btn.setObjectName("accentButton")
        self.export_report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_report_btn.clicked.connect(self._on_export_report_clicked)
        self.export_report_btn.setEnabled(False)
        action_layout.addWidget(self.export_report_btn)

        self.export_json_btn = QPushButton("💾 Export JSON Data")
        self.export_json_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_json_btn.clicked.connect(self._on_export_json_clicked)
        self.export_json_btn.setEnabled(False)
        action_layout.addWidget(self.export_json_btn)

        carrier_layout.addLayout(action_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        carrier_layout.addWidget(self.progress_bar)

        layout.addWidget(carrier_group)

        # 2. Main Forensic Splitter (Bit-Plane/StegDetect on Left, Statistical Analysis on Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Bit-Plane & StegDetect Slicer
        self.bitplane_group = QGroupBox("Visual Bit-Plane Slicer & StegDetect Dynamic Normalizer")
        bp_layout = QVBoxLayout(self.bitplane_group)
        self.bitplane_viewer = BitPlaneViewer()
        bp_layout.addWidget(self.bitplane_viewer)
        splitter.addWidget(self.bitplane_group)

        # Right: Statistical Steganalysis & Metadata
        stats_group = QGroupBox("Steganalysis Metrics & Metadata Inspector")
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setSpacing(12)

        # Verdict Badge Card
        self.verdict_card = QFrame()
        self.verdict_card.setStyleSheet("background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 10px;")
        v_layout = QVBoxLayout(self.verdict_card)
        self.verdict_title = QLabel("Forensic Verdict: Awaiting Analysis")
        self.verdict_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
        v_layout.addWidget(self.verdict_title)

        self.verdict_detail = QLabel("Load an image or WAV file and run analysis to calculate stego probabilities.")
        self.verdict_detail.setStyleSheet("font-size: 12px; color: #8b949e;")
        v_layout.addWidget(self.verdict_detail)
        stats_layout.addWidget(self.verdict_card)

        # Metrics Table
        self.metrics_table = QTableWidget(7, 2)
        self.metrics_table.setHorizontalHeaderLabels(["Metric / Parameter", "Value"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.metrics_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.setFixedHeight(210)
        self._init_empty_metrics_table()
        stats_layout.addWidget(self.metrics_table)

        # Metadata Table
        meta_label = QLabel("Media Metadata & Structure:")
        meta_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #c9d1d9;")
        stats_layout.addWidget(meta_label)

        self.meta_table = QTableWidget(0, 2)
        self.meta_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.meta_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.meta_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.meta_table.verticalHeader().setVisible(False)
        self.meta_table.setFixedHeight(140)
        stats_layout.addWidget(self.meta_table)

        splitter.addWidget(stats_group)
        layout.addWidget(splitter)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def _init_empty_metrics_table(self):
        rows = [
            ("Chi-Square Statistic (χ²)", "--"),
            ("Chi-Square p-value", "--"),
            ("Stego Detection Probability", "--"),
            ("Sample Pair Embedding Rate", "--"),
            ("Overall Shannon Entropy", "--"),
            ("LSB Plane Shannon Entropy", "--"),
            ("Overall Risk Level", "--"),
        ]
        self.metrics_table.setRowCount(len(rows))
        for r_idx, (name, val) in enumerate(rows):
            item_name = QTableWidgetItem(name)
            item_name.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_val = QTableWidgetItem(val)
            item_val.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.metrics_table.setItem(r_idx, 0, item_name)
            self.metrics_table.setItem(r_idx, 1, item_val)

    def _on_carrier_selected(self, file_path: str):
        self.current_target_path = file_path
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".wav":
            self.bitplane_viewer.clear()
            self.bitplane_viewer.image_label.setText("🎵 Audio File Selected: Bitplane visualization applies to images.\nRun forensic analysis for audio bitplane entropy & statistical metrics.")
        else:
            self.bitplane_viewer.set_image(file_path)

    def _on_carrier_cleared(self):
        self.current_target_path = None
        self.bitplane_viewer.clear()
        self.last_report = None
        self.export_report_btn.setEnabled(False)
        self.export_json_btn.setEnabled(False)
        self.verdict_title.setText("Forensic Verdict: Awaiting Analysis")
        self.verdict_detail.setText("Load a carrier and run analysis.")
        self._init_empty_metrics_table()
        self.meta_table.setRowCount(0)

    def _on_run_analysis_clicked(self):
        if not self.current_target_path or not os.path.exists(self.current_target_path):
            QMessageBox.warning(self, "Carrier Missing", "Please select an image or audio file to analyze.")
            return

        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = ForensicWorker(self.current_target_path)
        self.worker.finished.connect(self._on_analysis_success)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.start()

    def _on_analysis_success(self, report: Union[ForensicAnalysisReport, AudioForensicReport]):
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.last_report = report
        self.export_report_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)

        if isinstance(report, AudioForensicReport):
            # Audio Report
            if report.risk_level == "High":
                self.verdict_card.setStyleSheet("background-color: #261214; border: 1px solid #da3633; border-radius: 8px; padding: 10px;")
                self.verdict_title.setText(f"🚨 Audio Verdict: {report.verdict}")
                self.verdict_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f85149;")
            elif report.risk_level == "Medium":
                self.verdict_card.setStyleSheet("background-color: #241d13; border: 1px solid #9e6a03; border-radius: 8px; padding: 10px;")
                self.verdict_title.setText(f"⚠️ Audio Verdict: {report.verdict}")
                self.verdict_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #d29922;")
            else:
                self.verdict_card.setStyleSheet("background-color: #102117; border: 1px solid #238636; border-radius: 8px; padding: 10px;")
                self.verdict_title.setText(f"✅ Audio Verdict: {report.verdict}")
                self.verdict_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #3fb950;")

            lsb_ent = report.bitplane_entropy.get(0, 0.0)
            self.verdict_detail.setText(
                f"Risk: {report.risk_level} | LSB Entropy: {lsb_ent:.4f} bits/symbol | "
                f"RMS: {report.rms_energy:.4f} | DC Bias: {report.dc_bias:.6f}"
            )

            metric_values = [
                ("Audio Sample Rate", f"{report.sample_rate:,} Hz"),
                ("Sample Bit Depth", f"{report.bits_per_sample}-bit PCM ({'Mono' if report.channels == 1 else 'Stereo'})"),
                ("Total Audio Samples", f"{report.total_samples:,} samples ({report.duration_seconds:.2f} s)"),
                ("Root Mean Square (RMS) Energy", f"{report.rms_energy:.5f}"),
                ("DC Bias Offset", f"{report.dc_bias:.6f}"),
                ("LSB (Bit 0) Shannon Entropy", f"{lsb_ent:.4f} bits/symbol (>0.95 indicates randomized payload)"),
                ("Overall Audio Risk Assessment", report.risk_level),
            ]
            self.metrics_table.setRowCount(len(metric_values))
            for r_idx, (name, val) in enumerate(metric_values):
                self.metrics_table.setItem(r_idx, 0, QTableWidgetItem(name))
                self.metrics_table.setItem(r_idx, 1, QTableWidgetItem(val))

            meta_items = [
                ("Format", "Uncompressed PCM WAV"),
                ("File Size", f"{report.file_size_bytes:,} bytes"),
                ("Channels", str(report.channels)),
                ("Duration", f"{report.duration_seconds:.3f} s"),
                ("Theoretical Capacity (1-bit LSB)", f"{(report.total_samples // 8):,} bytes"),
            ]
            for bit_idx, ent in sorted(report.bitplane_entropy.items()):
                meta_items.append((f"Bitplane {bit_idx} Entropy", f"{ent:.4f} bits/symbol"))

            self.meta_table.setRowCount(len(meta_items))
            for r_idx, (k, v) in enumerate(meta_items):
                self.meta_table.setItem(r_idx, 0, QTableWidgetItem(k))
                self.meta_table.setItem(r_idx, 1, QTableWidgetItem(v))

            self.export_report_btn.setText("📄 Export Forensic TXT Report")

        else:
            # Image Report
            if report.risk_level == "High":
                self.verdict_card.setStyleSheet("background-color: #261214; border: 1px solid #da3633; border-radius: 8px; padding: 10px;")
                self.verdict_title.setText(f"🚨 Verdict: {report.stego_detection_verdict}")
                self.verdict_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f85149;")
            elif report.risk_level == "Medium":
                self.verdict_card.setStyleSheet("background-color: #241d13; border: 1px solid #9e6a03; border-radius: 8px; padding: 10px;")
                self.verdict_title.setText(f"⚠️ Verdict: {report.stego_detection_verdict}")
                self.verdict_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #d29922;")
            else:
                self.verdict_card.setStyleSheet("background-color: #102117; border: 1px solid #238636; border-radius: 8px; padding: 10px;")
                self.verdict_title.setText(f"✅ Verdict: {report.stego_detection_verdict}")
                self.verdict_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #3fb950;")

            self.verdict_detail.setText(
                f"Risk Level: {report.risk_level} | Chi-Square Probability: {report.chi_square.stego_probability_pct}% | "
                f"LSB Entropy: {report.entropy.lsb_plane} bits/symbol"
            )

            metric_values = [
                ("Chi-Square Statistic (χ²)", str(report.chi_square.chi2_statistic)),
                ("Chi-Square p-value", f"{report.chi_square.p_value:.6f}"),
                ("Stego Detection Probability", f"{report.chi_square.stego_probability_pct}% ({report.chi_square.verdict})"),
                ("Sample Pair Embedding Rate", f"{report.sample_pair.estimated_embedding_rate_pct}% (Est. ~{report.sample_pair.estimated_payload_bytes:,} B)"),
                ("Overall Shannon Entropy", f"{report.entropy.overall} bits/symbol (R:{report.entropy.red}, G:{report.entropy.green}, B:{report.entropy.blue})"),
                ("LSB Plane Shannon Entropy", f"{report.entropy.lsb_plane} bits/symbol (>0.95 indicates randomized payload)"),
                ("Overall Risk Assessment", report.risk_level),
            ]
            self.metrics_table.setRowCount(len(metric_values))
            for r_idx, (name, val) in enumerate(metric_values):
                self.metrics_table.setItem(r_idx, 0, QTableWidgetItem(name))
                self.metrics_table.setItem(r_idx, 1, QTableWidgetItem(val))

            all_meta = [
                ("Dimensions", f"{report.metadata.dimensions[0]} × {report.metadata.dimensions[1]} px"),
                ("Color Mode", f"{report.metadata.mode} ({report.metadata.color_channels} channels)"),
                ("Format", report.metadata.format),
                ("File Size", f"{report.metadata.file_size_bytes:,} bytes"),
            ]
            for k, v in report.metadata.png_chunks.items():
                all_meta.append((f"PNG Chunk: {k}", str(v)))
            for k, v in report.metadata.exif_data.items():
                all_meta.append((f"EXIF: {k}", str(v)))

            self.meta_table.setRowCount(len(all_meta))
            for r_idx, (k, v) in enumerate(all_meta):
                self.meta_table.setItem(r_idx, 0, QTableWidgetItem(k))
                self.meta_table.setItem(r_idx, 1, QTableWidgetItem(v))

            self.export_report_btn.setText("📄 Export Forensic PDF Report")

        # Log audit
        verdict = report.verdict if isinstance(report, AudioForensicReport) else report.stego_detection_verdict
        self.logger.log_action(
            action="ANALYZE",
            status="SUCCESS",
            target_image=self.current_target_path,
            details=f"Verdict: {verdict} (Risk: {report.risk_level})",
            integrity_verified=(report.risk_level == "Low"),
        )

        QMessageBox.information(
            self,
            "Forensic Analysis Complete",
            f"Analysis complete!\nVerdict: {verdict}\nRisk: {report.risk_level}",
        )

    def _on_analysis_error(self, error_msg: str):
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Analysis Failed", f"Forensic analysis failed:\n\n{error_msg}")

    def _on_export_report_clicked(self):
        if not self.last_report:
            return

        if isinstance(self.last_report, AudioForensicReport):
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Audio Forensic Report",
                "Audio_Forensic_Report.txt",
                "Text Documents (*.txt);;All Files (*.*)",
            )
            if save_path:
                AudioForensics.export_report_txt(self.last_report, save_path)
                QMessageBox.information(self, "Report Exported", f"Audio forensic report exported to:\n{save_path}")
        else:
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Forensic PDF Report",
                "Forensic_Report.pdf",
                "PDF Document (*.pdf)",
            )
            if save_path:
                ImageForensics.export_report_pdf(self.last_report, save_path)
                QMessageBox.information(self, "Report Exported", f"Forensic PDF report exported to:\n{save_path}")

    def _on_export_json_clicked(self):
        if not self.last_report:
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Forensic JSON Data",
            "Forensic_Report.json",
            "JSON Data (*.json)",
        )
        if save_path:
            if isinstance(self.last_report, AudioForensicReport):
                AudioForensics.export_report_json(self.last_report, save_path)
            else:
                ImageForensics.export_report_json(self.last_report, save_path)
            QMessageBox.information(self, "JSON Exported", f"Forensic JSON data exported to:\n{save_path}")
