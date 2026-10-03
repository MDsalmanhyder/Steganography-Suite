"""
Unit and Integration Tests for Audio LSB Steganography Engine.
"""

import os
import wave
import struct
import tempfile
import pytest
import numpy as np

from cloakpix.core.audio_stego import (
    AudioStegoEngine,
    AudioEmbeddingResult,
    AudioExtractionResult,
    calculate_audio_capacity,
    calculate_audio_snr,
)
from cloakpix.core.exceptions import (
    CapacityOverflowError,
    InvalidPasswordError,
    PayloadNotFoundError,
    UnsupportedFileFormatError,
)


@pytest.fixture
def sample_wav_16bit():
    """Create a temporary 16-bit stereo WAV file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name

    sample_rate = 44100
    duration = 1.0  # 1 second
    total_frames = int(sample_rate * duration)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total_frames):
            val_l = int(10000 * np.sin(2 * np.pi * 440 * (i / sample_rate)))
            val_r = int(10000 * np.sin(2 * np.pi * 880 * (i / sample_rate)))
            frames.extend(struct.pack("<hh", val_l, val_r))
        wf.writeframes(bytes(frames))

    yield path

    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def sample_wav_8bit():
    """Create a temporary 8-bit mono WAV file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name

    sample_rate = 22050
    duration = 1.0
    total_frames = int(sample_rate * duration)

    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)  # 8-bit
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total_frames):
            val = int(128 + 50 * np.sin(2 * np.pi * 440 * (i / sample_rate)))
            frames.append(val)
        wf.writeframes(bytes(frames))

    yield path

    if os.path.exists(path):
        os.remove(path)


def test_calculate_audio_capacity(sample_wav_16bit):
    """Test audio capacity estimation."""
    cap1 = calculate_audio_capacity(sample_wav_16bit, bits_per_sample=1)
    # 44100 frames * 2 channels = 88200 samples
    assert cap1["total_samples"] == 88200
    assert cap1["raw_capacity_bytes"] == 88200 // 8
    assert cap1["channels"] == 2
    assert cap1["bits_per_sample"] == 16

    cap2 = calculate_audio_capacity(sample_wav_16bit, bits_per_sample=2)
    assert cap2["raw_capacity_bytes"] == (88200 * 2) // 8


def test_embed_and_extract_text_16bit(sample_wav_16bit):
    """Test embedding and recovering text from 16-bit stereo WAV."""
    engine = AudioStegoEngine()
    secret = "TopSecretAudioPayload-2026! Antigravity Audio Steganography."
    password = "SuperAudioPassphrase!#42"

    res = engine.embed(
        wav_path=sample_wav_16bit,
        password=password,
        secret_text=secret,
        bits_per_sample=1,
    )

    assert isinstance(res, AudioEmbeddingResult)
    assert res.payload_type == "text"
    assert res.payload_bytes == len(secret.encode("utf-8"))
    assert res.snr_db is not None
    assert res.snr_db > 60.0  # 1-bit LSB in 16-bit audio yields extremely high SNR (>70 dB)

    # Save to temp stego file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_stego:
        stego_path = f_stego.name

    try:
        AudioStegoEngine.save_audio(res.audio_samples, res.audio_params, stego_path)

        # Extract
        ext = engine.extract(wav_path=stego_path, password=password)
        assert isinstance(ext, AudioExtractionResult)
        assert ext.payload_type == "text"
        assert ext.text == secret
        assert ext.bits_per_sample == 1
    finally:
        if os.path.exists(stego_path):
            os.remove(stego_path)


def test_embed_and_extract_file_8bit(sample_wav_8bit):
    """Test embedding binary file in 8-bit mono WAV."""
    engine = AudioStegoEngine()
    payload = b"\x00\xFF\xAA\x55TestBinaryPayloadForAudioStego" * 10
    password = "EightBitPassword88!"

    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f_bin:
        f_bin.write(payload)
        bin_path = f_bin.name

    try:
        res = engine.embed(
            wav_path=sample_wav_8bit,
            password=password,
            secret_file_path=bin_path,
            bits_per_sample=2,
            compress=True,
        )
        assert res.payload_type == "file"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_stego:
            stego_path = f_stego.name

        try:
            AudioStegoEngine.save_audio(res.audio_samples, res.audio_params, stego_path)

            ext = engine.extract(wav_path=stego_path, password=password)
            assert ext.payload_type == "file"
            assert ext.data == payload
        finally:
            if os.path.exists(stego_path):
                os.remove(stego_path)
    finally:
        if os.path.exists(bin_path):
            os.remove(bin_path)


def test_audio_invalid_password(sample_wav_16bit):
    """Test that wrong password fails cryptographic authentication."""
    engine = AudioStegoEngine()
    res = engine.embed(
        wav_path=sample_wav_16bit,
        password="CorrectPassword123",
        secret_text="SecretMessage",
    )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_stego:
        stego_path = f_stego.name

    try:
        AudioStegoEngine.save_audio(res.audio_samples, res.audio_params, stego_path)

        with pytest.raises(InvalidPasswordError):
            engine.extract(wav_path=stego_path, password="WrongPassword999")
    finally:
        if os.path.exists(stego_path):
            os.remove(stego_path)


def test_audio_tamper_detection(sample_wav_16bit):
    """Test that tampering with audio samples breaks GCM authentication tag."""
    engine = AudioStegoEngine()
    res = engine.embed(
        wav_path=sample_wav_16bit,
        password="TamperProofPassword",
        secret_text="TamperTestMessage",
    )

    # Tamper with samples in the ciphertext region (sample 560 = byte 1120, past 68-byte header)
    samples_tampered = bytearray(res.audio_samples)
    samples_tampered[1120] ^= 0x01

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_stego:
        stego_path = f_stego.name

    try:
        AudioStegoEngine.save_audio(samples_tampered, res.audio_params, stego_path)

        with pytest.raises(InvalidPasswordError):
            engine.extract(wav_path=stego_path, password="TamperProofPassword")
    finally:
        if os.path.exists(stego_path):
            os.remove(stego_path)


def test_audio_capacity_overflow(sample_wav_8bit):
    """Test that oversized payload raises CapacityOverflowError."""
    engine = AudioStegoEngine()
    huge_data = "X" * 50000  # sample_wav_8bit only has 22050 samples (~2.7 KB cap)

    with pytest.raises(CapacityOverflowError):
        engine.embed(
            wav_path=sample_wav_8bit,
            password="TestPassword",
            secret_text=huge_data,
            bits_per_sample=1,
        )


def test_calculate_audio_snr():
    """Test SNR calculation math."""
    orig = np.array([100, 200, 300, 400], dtype=np.int16)
    stego = np.array([101, 199, 300, 401], dtype=np.int16)
    snr = calculate_audio_snr(orig, stego)
    assert snr > 40.0

    # Identical arrays yield infinite/high SNR
    snr_perf = calculate_audio_snr(orig, orig)
    assert snr_perf == float("inf")
