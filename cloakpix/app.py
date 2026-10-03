"""
Desktop Application Entry Point for CloakPix.
"""

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from cloakpix.gui.main_window import MainWindow


def run_app():
    """Starts the PyQt6 GUI application."""
    # Ensure high DPI attributes are configured
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("CloakPix")
    app.setOrganizationName("CloakPix")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()

