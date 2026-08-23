"""
Unit and integration tests for Steganography Engine.
Tests embedding and extraction of text, binary files, multi-bit configurations, and error handling.
"""

import numpy as np
import pytest
from PIL import Image

from securestego.core.stego_engine import StegoEngine
from securestego.core.exceptions import (
    CapacityOverflowError,
    InvalidPasswordError,
    PayloadNotFoundError,
)
from securestego.core.metrics import calculate_psnr, calculate_mse, calculate_ssim


@pytest.fixture
def sample_carrier_rgb():
    """Generates a clean synthetic 200x200 RGB test image."""
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    # Generate smooth gradient pattern
    for y in range(200):
        for x in range(200):
            arr[y, x, 0] = (x + y) % 256
            arr[y, x, 1] = (x * 2) % 256
            arr[y, x, 2] = (y * 2) % 256
    return Image.fromarray(arr, mode="RGB")


@pytest.fixture
def sample_carrier_rgba():
    """Generates a synthetic 200x200 RGBA test image with transparency."""
    arr = np.zeros((200, 200, 4), dtype=np.uint8)
    arr[:, :, :3] = 128
    arr[:, :, 3] = 200  # Semi-transparent alpha
    return Image.fromarray(arr, mode="RGBA")


def test_embed_and_extract_text(sample_carrier_rgb):
    engine = StegoEngine()
    password = "TestPassphrase2026!"
    secret_text = "Confidential Steganography Payload: Alpha-Bravo-7799. 🔒"

    # Embed
    res = engine.embed(
        carrier_input=sample_carrier_rgb,
        password=password,
        secret_text=secret_text,
        bits_per_channel=1,
    )

    assert res.stego_image is not None
    assert res.payload_type == "text"
    assert res.psnr_db > 50.0  # Visual fidelity must be extremely high
    assert res.ssim > 0.999

    # Extract
    extracted = engine.extract(res.stego_image, password=password)
    assert extracted.payload_type == "text"
    assert extracted.text == secret_text
    assert extracted.verified_authentic is True


def test_embed_and_extract_binary_file(sample_carrier_rgb, tmp_path):
    engine = StegoEngine()
    password = "FileSecretKey!99"

    # Create dummy binary file (e.g. PDF/ZIP simulated bytes)
    dummy_file_bytes = b"%PDF-1.4 " + (b"0123456789ABCDEF" * 100)
    dummy_file = tmp_path / "secret_document.pdf"
    dummy_file.write_bytes(dummy_file_bytes)

    # Embed
    res = engine.embed(
        carrier_input=sample_carrier_rgb,
        password=password,
        secret_file_path=str(dummy_file),
        bits_per_channel=1,
    )

    assert res.payload_type == "file"
    assert res.filename == "secret_document.pdf"

    # Extract
    extracted = engine.extract(res.stego_image, password=password)
    assert extracted.payload_type == "file"
    assert extracted.filename == "secret_document.pdf"
    assert extracted.data == dummy_file_bytes
    assert extracted.verified_authentic is True


def test_embed_and_extract_multibit_lsb(sample_carrier_rgb):
    """Tests 2-bit, 3-bit, and 4-bit LSB configurations."""
    secret_text = "Multi-bit LSB test payload with large capacity!"
    password = "MultiBitPassword!"

    for bpc in (2, 3, 4):
        engine = StegoEngine(default_bits_per_channel=bpc)
        res = engine.embed(
            carrier_input=sample_carrier_rgb,
            password=password,
            secret_text=secret_text,
            bits_per_channel=bpc,
        )
        assert res.bits_per_channel == bpc
        assert res.psnr_db > 35.0  # Multi-bit still preserves good quality

        # Extraction should automatically detect correct bits-per-channel
        extracted = engine.extract(res.stego_image, password=password)
        assert extracted.text == secret_text
        assert extracted.bits_per_channel == bpc


def test_embed_with_rgba_carrier(sample_carrier_rgba):
    engine = StegoEngine()
    password = "AlphaCarrierTestPassword"
    secret_text = "Stego inside RGBA image without destroying alpha channel."

    res = engine.embed(
        carrier_input=sample_carrier_rgba,
        password=password,
        secret_text=secret_text,
    )

    # Verify alpha channel was preserved
    stego_arr = np.array(res.stego_image)
    orig_arr = np.array(sample_carrier_rgba)
    assert np.array_equal(stego_arr[:, :, 3], orig_arr[:, :, 3])

    # Extract
    extracted = engine.extract(res.stego_image, password=password)
    assert extracted.text == secret_text


def test_extract_with_wrong_password_raises_error(sample_carrier_rgb):
    engine = StegoEngine()
    res = engine.embed(
        carrier_input=sample_carrier_rgb,
        password="OriginalPassword123",
        secret_text="Classified data",
    )

    with pytest.raises(InvalidPasswordError):
        engine.extract(res.stego_image, password="IncorrectPassword456")


def test_extract_on_clean_image_raises_payload_not_found(sample_carrier_rgb):
    engine = StegoEngine()
    with pytest.raises(PayloadNotFoundError):
        engine.extract(sample_carrier_rgb, password="AnyPassword")


def test_capacity_overflow_raises_error():
    """Embedding huge payload in tiny image should raise CapacityOverflowError."""
    tiny_img = Image.new("RGB", (10, 10), color=(100, 100, 100))
    engine = StegoEngine()
    huge_text = "A" * 5000  # Exceeds 10x10x3 = 300 bits = 37 bytes capacity

    with pytest.raises(CapacityOverflowError) as exc_info:
        engine.embed(tiny_img, password="Password123", secret_text=huge_text)

    assert exc_info.value.required_bytes > exc_info.value.available_bytes
