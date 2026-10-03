"""
Forensics and Steganalysis Lab View for SecureStego.
Provides visual bit-plane extraction, Chi-Square analysis, Shannon entropy, and PDF report export.
"""

import os
from typing import Optional
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

from securestego.core.forensics import ImageForensics, ForensicAnalysisReport
from securestego.core.file_manager import AuditLogger
from securestego.gui.components.drop_zone import DropZone
from securestego.gui.components.bitplane_viewer import BitPlaneViewer


class ForensicWorker(QThread):
    """Worker thread for running forensic computations."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, image_path: str):
        super().__init__()
        self.image_path = image_path

    def run(self):
        try:
            report = ImageForensics.analyze_image(self.image_path)
            self.finished.emit(report)
        except Exception as e:
            self.error.emit(str(e))


class ForensicsView(QWidget):
    """
    Main Steganalysis & Image Forensics Lab View.
    """

    def __init__(self, logger: Optional[AuditLogger] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logger or AuditLogger()
        self.current_image_path: Optional[str] = None
        self.last_report: Optional[ForensicAnalysisReport] = None
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

        # 1. Target Image Drop Zone
        img_group = QGroupBox("1. Select Image for Steganalysis")
        img_layout = QVBoxLayout(img_group)

        self.image_drop = DropZone(
            title="Drop Image Here for Forensic Steganalysis",
            subtitle="Analyzes bit-plane noise, Chi-Square distribution, entropy, and metadata",
            file_filters="Image Files (*.png *.bmp *.tiff *.webp *.jpg);;All Files (*.*)",
            is_image_only=True,
        )
        self.image_drop.file_selected.connect(self._on_image_selected)
        self.image_drop.file_cleared.connect(self._on_image_cleared)
        img_layout.addWidget(self.image_drop)

        # Run Analysis Button
        action_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("🔬 Run Comprehensive Forensic Analysis")
        self.analyze_btn.setObjectName("primaryButton")
        self.analyze_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.analyze_btn.clicked.connect(self._on_run_analysis_clicked)
        action_layout.addWidget(self.analyze_btn)

        self.export_pdf_btn = QPushButton("📄 Export Forensic PDF Report")
        self.export_pdf_btn.setObjectName("accentButton")
        self.export_pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_pdf_btn.clicked.connect(self._on_export_pdf_clicked)
        self.export_pdf_btn.setEnabled(False)
        action_layout.addWidget(self.export_pdf_btn)

        self.export_json_btn = QPushButton("💾 Export JSON Data")
        self.export_json_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_json_btn.clicked.connect(self._on_export_json_clicked)
        self.export_json_btn.setEnabled(False)
        action_layout.addWidget(self.export_json_btn)

        img_layout.addLayout(action_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        img_layout.addWidget(self.progress_bar)

        layout.addWidget(img_group)

        # 2. Main Forensic Splitter (Bit-Plane Viewer on Left, Statistical Analysis on Right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Bit-Plane Slicer
        bitplane_group = QGroupBox("Visual Bit-Plane Slicer & Noise Inspection")
        bp_layout = QVBoxLayout(bitplane_group)
        self.bitplane_viewer = BitPlaneViewer()
        bp_layout.addWidget(self.bitplane_viewer)
        splitter.addWidget(bitplane_group)

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

        self.verdict_detail = QLabel("Load an image and run analysis to calculate stego probabilities.")
        self.verdict_detail.setStyleSheet("font-size: 12px; color: #8b949e;")
        v_layout.addWidget(self.verdict_detail)
        stats_layout.addWidget(self.verdict_card)

        # Chi-Square & Entropy Table
        self.metrics_table = QTableWidget(7, 2)
        self.metrics_table.setHorizontalHeaderLabels(["Metric / Parameter", "Value"])
        self.metrics_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.metrics_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.metrics_table.verticalHeader().setVisible(False)
        self.metrics_table.setFixedHeight(210)
        self._init_empty_metrics_table()
        stats_layout.addWidget(self.metrics_table)

        # Metadata & PNG Chunks Table
        meta_label = QLabel("Image Metadata & Custom PNG Chunks:")
        meta_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #c9d1d9;")
        stats_layout.addWidget(meta_label)

        self.meta_table = QTableWidget(0, 2)
        self.meta_table.setHorizontalHeaderLabels(["Tag / Chunk", "Value"])
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
        for r_idx, (name, val) in enumerate(rows):
            item_name = QTableWidgetItem(name)
            item_name.setFlags(Qt.ItemFlag.ItemIsEnabled)
            item_val = QTableWidgetItem(val)
            item_val.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.metrics_table.setItem(r_idx, 0, item_name)
            self.metrics_table.setItem(r_idx, 1, item_val)

    def _on_image_selected(self, file_path: str):
        self.current_image_path = file_path
        self.bitplane_viewer.set_image(file_path)

    def _on_image_cleared(self):
        self.current_image_path = None
        self.bitplane_viewer.clear()
        self.last_report = None
        self.export_pdf_btn.setEnabled(False)
        self.export_json_btn.setEnabled(False)
        self.verdict_title.setText("Forensic Verdict: Awaiting Analysis")
        self.verdict_detail.setText("Load an image and run analysis.")
        self._init_empty_metrics_table()
        self.meta_table.setRowCount(0)

    def _on_run_analysis_clicked(self):
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            QMessageBox.warning(self, "Image Missing", "Please select an image to analyze.")
            return

        self.analyze_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = ForensicWorker(self.current_image_path)
        self.worker.finished.connect(self._on_analysis_success)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.start()

    def _on_analysis_success(self, report: ForensicAnalysisReport):
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.last_report = report
        self.export_pdf_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)

        # Update Verdict Card
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

        # Update Metrics Table
        metric_values = [
            ("Chi-Square Statistic (χ²)", str(report.chi_square.chi2_statistic)),
            ("Chi-Square p-value", f"{report.chi_square.p_value:.6f}"),
            ("Stego Detection Probability", f"{report.chi_square.stego_probability_pct}% ({report.chi_square.verdict})"),
            ("Sample Pair Embedding Rate", f"{report.sample_pair.estimated_embedding_rate_pct}% (Est. ~{report.sample_pair.estimated_payload_bytes:,} B)"),
            ("Overall Shannon Entropy", f"{report.entropy.overall} bits/symbol (R:{report.entropy.red}, G:{report.entropy.green}, B:{report.entropy.blue})"),
            ("LSB Plane Shannon Entropy", f"{report.entropy.lsb_plane} bits/symbol (>0.95 indicates randomized payload)"),
            ("Overall Risk Assessment", report.risk_level),
        ]
        for r_idx, (name, val) in enumerate(metric_values):
            self.metrics_table.setItem(r_idx, 0, QTableWidgetItem(name))
            self.metrics_table.setItem(r_idx, 1, QTableWidgetItem(val))

        # Update Metadata Table
        all_meta = []
        all_meta.append(("Dimensions", f"{report.metadata.dimensions[0]} × {report.metadata.dimensions[1]} px"))
        all_meta.append(("Color Mode", f"{report.metadata.mode} ({report.metadata.color_channels} channels)"))
        all_meta.append(("Format", report.metadata.format))
        all_meta.append(("File Size", f"{report.metadata.file_size_bytes:,} bytes"))

        for k, v in report.metadata.png_chunks.items():
            all_meta.append((f"PNG Chunk: {k}", str(v)))

        for k, v in report.metadata.exif_data.items():
            all_meta.append((f"EXIF: {k}", str(v)))

        self.meta_table.setRowCount(len(all_meta))
        for r_idx, (k, v) in enumerate(all_meta):
            self.meta_table.setItem(r_idx, 0, QTableWidgetItem(k))
            self.meta_table.setItem(r_idx, 1, QTableWidgetItem(v))

        # Log audit entry
        self.logger.log_action(
            action="ANALYZE",
            status="SUCCESS",
            target_image=self.current_image_path,
            details=f"Verdict: {report.stego_detection_verdict} (Risk: {report.risk_level}, Chi2: {report.chi_square.stego_probability_pct}%)",
            integrity_verified=not report.chi_square.is_stego_detected,
        )

        QMessageBox.information(
            self,
            "Forensic Analysis Complete",
            f"Analysis complete!\nVerdict: {report.stego_detection_verdict}\nRisk: {report.risk_level}",
        )

    def _on_analysis_error(self, error_msg: str):
        self.analyze_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Analysis Failed", f"Forensic analysis failed:\n\n{error_msg}")

    def _on_export_pdf_clicked(self):
        if not self.last_report:
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Forensic PDF Report",
            "Forensic_Report.pdf",
            "PDF Document (*.pdf)",
        )
        if save_path:
            ImageForensics.export_report_pdf(self.last_report, save_path)
            self.logger.log_action(
                action="EXPORT",
                status="SUCCESS",
                target_image=save_path,
                details="Exported Forensic PDF Report",
                integrity_verified=True,
            )
            QMessageBox.information(
                self,
                "Report Exported",
                f"Forensic PDF report successfully exported to:\n{save_path}",
            )

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
            ImageForensics.export_report_json(self.last_report, save_path)
            QMessageBox.information(
                self,
                "JSON Exported",
                f"Forensic JSON data exported to:\n{save_path}",
            )
