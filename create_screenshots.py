"""
Script to capture high-resolution demonstration screenshots of SecureStego GUI.
"""

import os
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from securestego.gui.main_window import MainWindow

# Disable blocking dialogs during automated capture
QMessageBox.information = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.warning = lambda *args, **kwargs: QMessageBox.StandardButton.Ok
QMessageBox.critical = lambda *args, **kwargs: QMessageBox.StandardButton.Ok


def capture_screenshots():
    os.makedirs("docs/screenshots", exist_ok=True)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.resize(1100, 780)
    window.show()
    app.processEvents()

    # 1. Capture Tab 0: Encode View
    carrier_path = os.path.abspath("demo_assets/carrier_cyber_landscape.png")
    if os.path.exists(carrier_path):
        window.encode_view.carrier_drop.set_file(carrier_path)
        window.encode_view.text_edit.setPlainText(
            "[TOP SECRET] Tactical grid coordinates alpha-74.\nPayload authentic AES-256-GCM encrypted."
        )
        window.encode_view.password_box.input_field.setText("CipherShield#2026!SecureKey")
        app.processEvents()

    pix = window.grab()
    pix.save("docs/screenshots/01_encode_view.png", "PNG")
    print("Saved docs/screenshots/01_encode_view.png")

    # 2. Perform embedding to show result state
    window.encode_view._on_embed_clicked()
    # Wait for worker thread
    if window.encode_view.worker:
        window.encode_view.worker.wait()
    app.processEvents()

    pix = window.grab()
    pix.save("docs/screenshots/02_embed_result.png", "PNG")
    print("Saved docs/screenshots/02_embed_result.png")

    # 3. Capture Tab 1: Decode View
    window.tabs.setCurrentIndex(1)
    app.processEvents()
    # Save a temporary stego image to decode
    if window.encode_view.last_embedding_result:
        temp_stego = "demo_assets/stego_demo.png"
        window.encode_view.last_embedding_result.stego_image.save(temp_stego, "PNG")
        window.decode_view.stego_drop.set_file(os.path.abspath(temp_stego))
        window.decode_view.password_box.input_field.setText("CipherShield#2026!SecureKey")
        window.decode_view._on_extract_clicked()
        if window.decode_view.worker:
            window.decode_view.worker.wait()
        app.processEvents()

    pix = window.grab()
    pix.save("docs/screenshots/03_decode_view.png", "PNG")
    print("Saved docs/screenshots/03_decode_view.png")

    # 4. Capture Tab 2: Forensics Lab View
    window.tabs.setCurrentIndex(2)
    app.processEvents()
    if os.path.exists("demo_assets/stego_demo.png"):
        window.forensics_view.image_drop.set_file(os.path.abspath("demo_assets/stego_demo.png"))
        window.forensics_view._on_run_analysis_clicked()
        if window.forensics_view.worker:
            window.forensics_view.worker.wait()
        app.processEvents()

    pix = window.grab()
    pix.save("docs/screenshots/04_forensics_lab.png", "PNG")
    print("Saved docs/screenshots/04_forensics_lab.png")

    # 5. Capture Tab 3: History & Audit Log
    window.tabs.setCurrentIndex(3)
    window.history_view.refresh_logs()
    app.processEvents()

    pix = window.grab()
    pix.save("docs/screenshots/05_audit_history.png", "PNG")
    print("Saved docs/screenshots/05_audit_history.png")

    print("\nAll demonstration screenshots captured successfully!")


if __name__ == "__main__":
    capture_screenshots()
