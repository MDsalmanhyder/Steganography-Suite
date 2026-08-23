"""
History and Audit Trail View for SecureStego.
Provides searchable, filterable logs of all steganographic operations.
"""

import csv
import json
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from securestego.core.file_manager import AuditLogger


class HistoryView(QWidget):
    """
    Operation History and Audit Log View.
    """

    def __init__(self, logger: Optional[AuditLogger] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = logger or AuditLogger()
        self._init_ui()
        self.refresh_logs()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Filter and Search Bar
        filter_group = QGroupBox("Audit Trail Filters")
        filter_layout = QHBoxLayout(filter_group)
        filter_layout.setSpacing(10)

        filter_layout.addWidget(QLabel("🔍 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filter by filename, details, action...")
        self.search_input.textChanged.connect(self.refresh_logs)
        filter_layout.addWidget(self.search_input, 1)

        filter_layout.addWidget(QLabel("Action:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["ALL", "ENCODE", "DECODE", "ANALYZE", "EXPORT"])
        self.action_combo.currentIndexChanged.connect(self.refresh_logs)
        filter_layout.addWidget(self.action_combo)

        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_logs)
        filter_layout.addWidget(self.refresh_btn)

        layout.addWidget(filter_group)

        # Table
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "Timestamp",
            "Action",
            "Status",
            "Target Image",
            "Payload Type",
            "Payload Size",
            "Details & Security Notes",
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table, 1)

        # Bottom Actions
        bottom_layout = QHBoxLayout()
        self.export_btn = QPushButton("💾 Export Logs (CSV / JSON)")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._on_export_clicked)
        bottom_layout.addWidget(self.export_btn)

        bottom_layout.addStretch()

        self.clear_btn = QPushButton("🗑️ Clear Audit Trail")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        bottom_layout.addWidget(self.clear_btn)

        layout.addLayout(bottom_layout)

    def refresh_logs(self):
        query = self.search_input.text()
        action_filter = self.action_combo.currentText()
        logs = self.logger.get_history(search_query=query, action_filter=action_filter)

        self.table.setRowCount(len(logs))
        for r_idx, item in enumerate(logs):
            ts = item.get("timestamp", "")
            action = item.get("action", "")
            status = item.get("status", "")
            img = item.get("target_image", "")
            ptype = item.get("payload_type", "-") or "-"
            psize = f"{item.get('payload_size_bytes', 0):,} B" if item.get("payload_size_bytes") else "-"
            details = item.get("details", "") or ""

            items = [
                QTableWidgetItem(ts),
                QTableWidgetItem(action),
                QTableWidgetItem(status),
                QTableWidgetItem(img),
                QTableWidgetItem(ptype),
                QTableWidgetItem(psize),
                QTableWidgetItem(details),
            ]

            for c_idx, table_item in enumerate(items):
                table_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(r_idx, c_idx, table_item)

    def _on_export_clicked(self):
        logs = self.logger.get_history()
        if not logs:
            QMessageBox.information(self, "No Logs", "Audit log is currently empty.")
            return

        save_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Audit Logs",
            "securestego_audit_logs.csv",
            "CSV Spreadsheet (*.csv);;JSON File (*.json)",
        )

        if not save_path:
            return

        if save_path.endswith(".json") or "JSON" in selected_filter:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)
        else:
            if not save_path.endswith(".csv"):
                save_path += ".csv"
            keys = ["id", "timestamp", "action", "status", "target_image", "payload_type", "payload_size_bytes", "details", "integrity_verified"]
            with open(save_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                for entry in logs:
                    writer.writerow({k: entry.get(k, "") for k in keys})

        QMessageBox.information(self, "Exported", f"Audit logs exported to:\n{save_path}")

    def _on_clear_clicked(self):
        reply = QMessageBox.question(
            self,
            "Clear Audit Trail",
            "Are you sure you want to permanently clear all operation audit logs?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.logger.clear_logs()
            self.refresh_logs()
            QMessageBox.information(self, "Cleared", "Audit logs have been reset.")
