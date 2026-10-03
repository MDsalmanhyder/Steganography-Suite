"""
Unit tests for Audio Forensics & Steganalysis module.
"""

import os
import json
import wave
import struct
import tempfile
import pytest
import numpy as np

from cloakpix.core.audio_forensics import AudioForensics, AudioForensicReport
from cloakpix.core.audio_stego import AudioStegoEngine


@pytest.fixture
def wav_pair():
    """Create a clean WAV and a stego WAV."""
    sample_rate = 44100
    duration = 0.5  # 0.5s = 22050 frames
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_clean:
        clean_path = f_clean.name
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f_stego:
        stego_path = f_stego.name

    with wave.open(clean_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(int(sample_rate * duration)):
            val = int(8000 * np.sin(2 * np.pi * 440 * (i / sample_rate)))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(bytes(frames))

    # Embed random stego data into stego_path
    engine = AudioStegoEngine()
    res = engine.embed(
        wav_path=clean_path,
        password="ForensicTestPassword",
        secret_text="A" * 500,
        bits_per_sample=1,
    )
    AudioStegoEngine.save_audio(res.audio_samples, res.audio_params, stego_path)

    yield clean_path, stego_path

    if os.path.exists(clean_path):
        os.remove(clean_path)
    if os.path.exists(stego_path):
        os.remove(stego_path)


def test_analyze_clean_and_stego_audio(wav_pair):
    """Test forensic analysis on clean vs stego audio carriers."""
    clean_path, stego_path = wav_pair

    clean_rep = AudioForensics.analyze_audio(clean_path)
    assert isinstance(clean_rep, AudioForensicReport)
    assert clean_rep.sample_rate == 44100
    assert clean_rep.bits_per_sample == 16
    assert clean_rep.channels == 1
    assert clean_rep.total_samples == 22050
    assert clean_rep.duration_seconds == 0.5
    assert 0 in clean_rep.bitplane_entropy

    stego_rep = AudioForensics.analyze_audio(stego_path)
    assert isinstance(stego_rep, AudioForensicReport)
    # LSB entropy should be elevated in the stego file due to encrypted pseudorandom payload
    assert stego_rep.bitplane_entropy[0] > clean_rep.bitplane_entropy[0]


def test_audio_forensics_export(wav_pair):
    """Test exporting audio forensic reports to TXT and JSON."""
    clean_path, _ = wav_pair
    report = AudioForensics.analyze_audio(clean_path)

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f_txt:
        txt_path = f_txt.name
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f_json:
        json_path = f_json.name

    try:
        AudioForensics.export_report_txt(report, txt_path)
        assert os.path.exists(txt_path)
        with open(txt_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "CLOAKPIX AUDIO FORENSIC" in content
        assert "STATISTICAL STEGANALYSIS & ENTROPY" in content

        AudioForensics.export_report_json(report, json_path)
        assert os.path.exists(json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["metadata"]["sample_rate_hz"] == 44100
        assert "entropy" in data
    finally:
        if os.path.exists(txt_path):
            os.remove(txt_path)
        if os.path.exists(json_path):
            os.remove(json_path)
