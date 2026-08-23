"""
Unit tests for file manager and audit logging.
"""

from PIL import Image
from securestego.core.file_manager import FileManager, AuditLogger


def test_audit_logger(tmp_path):
    log_dir = str(tmp_path / "logs")
    logger = AuditLogger(log_dir=log_dir)

    # Initial state
    assert len(logger.get_history()) == 0

    # Log action
    logger.log_action(
        action="ENCODE",
        status="SUCCESS",
        target_image="test_carrier.png",
        payload_type="text",
        payload_size_bytes=1024,
        details="Embedded 1024 bytes with PSNR 58.2 dB",
        integrity_verified=True,
    )

    history = logger.get_history()
    assert len(history) == 1
    assert history[0]["action"] == "ENCODE"
    assert history[0]["target_image"] == "test_carrier.png"

    # Search query
    assert len(logger.get_history(search_query="carrier")) == 1
    assert len(logger.get_history(search_query="nonexistent")) == 0

    # Clear logs
    logger.clear_logs()
    assert len(logger.get_history()) == 0


def test_save_and_export_file(tmp_path):
    img = Image.new("RGB", (50, 50), color=(255, 0, 0))
    save_path = str(tmp_path / "output_stego.png")
    saved = FileManager.save_stego_image(img, save_path)
    assert saved.endswith(".png")
    assert (tmp_path / "output_stego.png").exists()

    payload_data = b"Secret extracted binary data."
    export_dir = str(tmp_path / "exports")
    exported_path = FileManager.export_extracted_file(
        payload_data,
        export_dir,
        preferred_filename="secret_doc.pdf",
    )
    assert (tmp_path / "exports" / "secret_doc.pdf").exists()
