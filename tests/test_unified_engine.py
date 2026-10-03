"""
Unit and Integration tests for UnifiedStegoEngine (Image + Audio Dispatcher).
"""

import os
import wave
import struct
import tempfile
import pytest
import numpy as np
from PIL import Image

from cloakpix.core.unified_engine import (
    UnifiedStegoEngine,
    UnifiedEmbeddingResult,
    UnifiedExtractionResult,
)


@pytest.fixture
def test_image():
    """Create a temporary PNG image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    img = Image.new("RGB", (100, 100), color=(120, 150, 200))
    img.save(path, "PNG")
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def test_audio():
    """Create a temporary WAV audio file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        frames = bytearray()
        for i in range(22050):
            val = int(8000 * np.sin(2 * np.pi * 440 * (i / 44100)))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(bytes(frames))
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_unified_image_flow(test_image):
    """Test unified engine embedding and extraction for images."""
    engine = UnifiedStegoEngine()
    password = "UnifiedImagePassword123!"
    secret = "Unified image secret test string."

    res = engine.embed(
        carrier_input=test_image,
        password=password,
        secret_text=secret,
        bits_per_channel=1,
        compress=True,
    )
    assert isinstance(res, UnifiedEmbeddingResult)
    assert res.carrier_type == "image"
    assert res.psnr_db is not None
    assert res.psnr_db > 50.0

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_stego:
        stego_path = f_stego.name

    try:
        UnifiedStegoEngine.save_stego_carrier(res, stego_path)
        ext = engine.extract(stego_input=stego_path, password=password)
        assert isinstance(ext, UnifiedExtractionResult)
        assert ext.carrier_type == "image"
        assert ext.text == secret
    finally:
        if os.path.exists(stego_path):
            os.remove(stego_path)


def test_unified_audio_flow(test_audio):
    """Test unified engine embedding and extraction for audio."""
    engine = UnifiedStegoEngine()
    password = "UnifiedAudioPassword456!"
    secret = "Unified audio secret test string."

    res = engine.embed(
        carrier_input=test_audio,
        password=password,
        secret_text=secret,
        bits_per_channel=1,
        compress=True,
    )
    assert isinstance(res, UnifiedEmbeddingResult)
    assert res.carrier_type == "audio"
    assert res.snr_db is not None
    assert res.snr_db > 50.0

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_stego:
        stego_path = f_stego.name

    try:
        UnifiedStegoEngine.save_stego_carrier(res, stego_path)
        ext = engine.extract(stego_input=stego_path, password=password)
        assert isinstance(ext, UnifiedExtractionResult)
        assert ext.carrier_type == "audio"
        assert ext.text == secret
    finally:
        if os.path.exists(stego_path):
            os.remove(stego_path)
