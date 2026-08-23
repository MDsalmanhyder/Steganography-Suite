"""
Unit tests for PyQt6 GUI components and views.
"""

import sys
import pytest
from PyQt6.QtWidgets import QApplication
from securestego.gui.main_window import MainWindow, CapacityCalculatorDialog
from securestego.gui.components.password_box import PasswordBox
from securestego.gui.components.capacity_bar import CapacityBar


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_password_box_widget(qapp):
    box = PasswordBox()
    box.input_field.setText("StrongPassword!2026")
    assert box.text() == "StrongPassword!2026"
    assert box.strength_bar.value() > 70

    box._toggle_visibility()
    assert box.is_visible is True
    box._toggle_visibility()
    assert box.is_visible is False


def test_capacity_bar_widget(qapp):
    bar = CapacityBar()
    bar.update_capacity(500, 1000)
    assert bar.used_bytes == 500
    assert bar.total_bytes == 1000
    assert bar.progress.value() == 500


def test_capacity_calculator_dialog(qapp):
    dialog = CapacityCalculatorDialog()
    assert dialog.width_spin.value() == 1920
    assert dialog.height_spin.value() == 1080


def test_main_window_instantiation(qapp):
    window = MainWindow()
    assert window.tabs.count() == 4
    assert window.windowTitle().startswith("SecureStego")
