"""
Unit tests for forensics, steganalysis, and report generation in SecureStego.
"""

import numpy as np
import pytest
from PIL import Image

from securestego.core.forensics import ImageForensics
from securestego.core.stego_engine import StegoEngine


@pytest.fixture
def clean_image():
    """Generates a gradient image."""
    arr = np.fromfunction(lambda y, x: (x * 2 + y * 3) % 256, (150, 150), dtype=np.uint8)
    rgb = np.dstack([arr, (arr * 2) % 256, (arr * 3) % 256])
    return Image.fromarray(rgb, mode="RGB")


@pytest.fixture
def stego_image(clean_image):
    """Generates an image with embedded data."""
    engine = StegoEngine()
    res = engine.embed(
        carrier_input=clean_image,
        password="ForensicTestPassword123",
        secret_text="A" * 1500,  # Dense payload
        bits_per_channel=1,
    )
    return res.stego_image


def test_bit_plane_extraction(clean_image):
    # Test LSB and MSB extraction
    lsb_img = ImageForensics.extract_bit_plane(clean_image, bit=0, channel="combined")
    assert lsb_img.size == clean_image.size
    assert lsb_img.mode == "RGB"

    r_lsb = ImageForensics.extract_bit_plane(clean_image, bit=0, channel="r")
    assert r_lsb.size == clean_image.size
    assert r_lsb.mode == "L"

    msb_img = ImageForensics.extract_bit_plane(clean_image, bit=7, channel="gray")
    assert msb_img.size == clean_image.size


def test_entropy_computation(clean_image, stego_image):
    stats_clean = ImageForensics.compute_entropy_statistics(clean_image)
    stats_stego = ImageForensics.compute_entropy_statistics(stego_image)

    assert 0.0 <= stats_clean.overall <= 8.0
    assert 0.0 <= stats_stego.overall <= 8.0
    # LSB entropy increases when random encrypted ciphertext is embedded
    assert stats_stego.lsb_plane >= stats_clean.lsb_plane


def test_chi_square_analysis(clean_image, stego_image):
    chi_clean = ImageForensics.chi_square_analysis(clean_image)
    chi_stego = ImageForensics.chi_square_analysis(stego_image)

    assert isinstance(chi_clean.stego_probability_pct, float)
    assert isinstance(chi_stego.stego_probability_pct, float)


def test_metadata_extraction(clean_image):
    meta = ImageForensics.extract_metadata(clean_image)
    assert meta.dimensions == (150, 150)
    assert meta.mode == "RGB"
    assert meta.color_channels == 3
    assert meta.has_alpha is False


def test_generate_and_export_forensic_reports(stego_image, tmp_path):
    report = ImageForensics.analyze_image(stego_image)
    assert report.stego_detection_verdict is not None
    assert len(report.recommendations) > 0

    # JSON export
    json_path = str(tmp_path / "forensic_report.json")
    ImageForensics.export_report_json(report, json_path)
    assert (tmp_path / "forensic_report.json").exists()

    # TXT export
    txt_path = str(tmp_path / "forensic_report.txt")
    ImageForensics.export_report_txt(report, txt_path)
    assert (tmp_path / "forensic_report.txt").exists()

    # PDF export
    pdf_path = str(tmp_path / "forensic_report.pdf")
    ImageForensics.export_report_pdf(report, pdf_path)
    assert (tmp_path / "forensic_report.pdf").exists()
