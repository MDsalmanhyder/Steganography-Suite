"""
Modern Dark Theme QSS Stylesheet and Color Palette for SecureStego.
"""

DARK_THEME_QSS = """
/* Global Window & Typography */
QWidget {
    background-color: #0d1117;
    color: #e6edf3;
    font-family: 'Segoe UI', 'SF Pro Text', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
    font-size: 13px;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

/* Main Window */
QMainWindow {
    background-color: #0d1117;
}

/* Scroll Area */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* Tab Bar & Tab Widget */
QTabWidget::pane {
    border: 1px solid #30363d;
    background-color: #161b22;
    border-radius: 10px;
    top: -1px;
}

QTabBar::tab {
    background-color: #161b22;
    color: #8b949e;
    padding: 10px 22px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    border: 1px solid #30363d;
    border-bottom: none;
    font-weight: 600;
    font-size: 13px;
}

QTabBar::tab:selected {
    background-color: #21262d;
    color: #58a6ff;
    border: 1px solid #58a6ff;
    border-bottom: 2px solid #21262d;
}

QTabBar::tab:hover:!selected {
    background-color: #1f242c;
    color: #c9d1d9;
}

/* Group Box / Card Container */
QGroupBox {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    margin-top: 18px;
    padding: 16px 14px 14px 14px;
    font-weight: bold;
    font-size: 13px;
    color: #f0f6fc;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    background-color: #21262d;
    border: 1px solid #30363d;
    border-radius: 5px;
    color: #58a6ff;
}

/* Push Buttons */
QPushButton {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #30363d;
    color: #ffffff;
    border-color: #8b949e;
}

QPushButton:pressed {
    background-color: #161b22;
}

QPushButton:disabled {
    background-color: #161b22;
    color: #484f58;
    border-color: #21262d;
}

/* Primary Action Button (Green / Blue) */
QPushButton#primaryButton {
    background-color: #238636;
    color: #ffffff;
    border: 1px solid #2ea043;
    font-size: 14px;
    padding: 10px 20px;
    border-radius: 8px;
}

QPushButton#primaryButton:hover {
    background-color: #2ea043;
    border-color: #3fb950;
}

QPushButton#primaryButton:pressed {
    background-color: #1b6528;
}

QPushButton#accentButton {
    background-color: #1f6feb;
    color: #ffffff;
    border: 1px solid #388bfd;
    font-size: 14px;
    padding: 10px 20px;
    border-radius: 8px;
}

QPushButton#accentButton:hover {
    background-color: #388bfd;
    border-color: #58a6ff;
}

/* Text Inputs and Editors */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #58a6ff;
    background-color: #0d1117;
}

/* Progress Bar */
QProgressBar {
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    font-size: 12px;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1f6feb, stop:1 #238636);
    border-radius: 5px;
}

/* Slider */
QSlider::groove:horizontal {
    border: 1px solid #30363d;
    height: 6px;
    background: #21262d;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #58a6ff;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #58a6ff;
    border: 2px solid #ffffff;
    width: 16px;
    margin-top: -6px;
    margin-bottom: -6px;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #79c0ff;
}

/* Combo Box */
QComboBox {
    background-color: #21262d;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
}

QComboBox:hover {
    border-color: #58a6ff;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left: none;
}

QComboBox QAbstractItemView {
    background-color: #161b22;
    color: #c9d1d9;
    selection-background-color: #1f6feb;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 4px;
}

/* Table Widget */
QTableWidget {
    background-color: #0d1117;
    color: #c9d1d9;
    border: 1px solid #30363d;
    border-radius: 8px;
    gridline-color: #21262d;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #161b22;
    color: #8b949e;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #30363d;
    font-weight: 600;
    font-size: 12px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0d1117;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #30363d;
    min-height: 25px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #8b949e;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Status Bar */
QStatusBar {
    background-color: #161b22;
    color: #8b949e;
    border-top: 1px solid #30363d;
    font-size: 12px;
}

/* Labels */
QLabel {
    color: #c9d1d9;
}

QLabel#headingLabel {
    font-size: 16px;
    font-weight: bold;
    color: #f0f6fc;
}

QLabel#subheadingLabel {
    font-size: 12px;
    color: #8b949e;
}

QLabel#badgeSuccess {
    background-color: rgba(46, 160, 67, 0.2);
    color: #3fb950;
    border: 1px solid #238636;
    border-radius: 6px;
    padding: 4px 8px;
    font-weight: bold;
    font-size: 12px;
}

QLabel#badgeWarning {
    background-color: rgba(210, 153, 34, 0.2);
    color: #d29922;
    border: 1px solid #9e6a03;
    border-radius: 6px;
    padding: 4px 8px;
    font-weight: bold;
    font-size: 12px;
}

QLabel#badgeDanger {
    background-color: rgba(248, 81, 73, 0.2);
    color: #f85149;
    border: 1px solid #da3633;
    border-radius: 6px;
    padding: 4px 8px;
    font-weight: bold;
    font-size: 12px;
}

/* Radio Buttons & Checkboxes */
QRadioButton, QCheckBox {
    color: #c9d1d9;
    spacing: 8px;
}

QRadioButton::indicator, QCheckBox::indicator {
    width: 16px;
    height: 16px;
    background-color: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
}

QCheckBox::indicator {
    border-radius: 4px;
}

QRadioButton::indicator:checked {
    background-color: #58a6ff;
    border: 3px solid #0d1117;
}

QCheckBox::indicator:checked {
    background-color: #58a6ff;
    border: 1px solid #58a6ff;
}
"""
