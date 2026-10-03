"""
Desktop Application Entry Point for SecureStego.
"""

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from securestego.gui.main_window import MainWindow


def run_app():
    """Starts the PyQt6 GUI application."""
    # Ensure high DPI attributes are configured
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("SecureStego")
    app.setOrganizationName("SecureStego")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
