"""
Audio Forensics and Steganalysis Module for CloakPix.
Analyzes WAV audio files for LSB steganography, sample entropy anomalies,
dynamic range, RMS energy, and generates comprehensive forensic audit reports.
"""

import json
import math
import os
import time
import wave
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from scipy import stats

from cloakpix.core.exceptions import UnsupportedFormatError


@dataclass
class AudioEntropyStats:
    overall_sample_entropy: float
    lsb_plane_entropy: float
    lsb2_plane_entropy: float
    theoretical_max: float


@dataclass
class AudioMetadataReport:
    filename: str
    file_size_bytes: int
    duration_seconds: float
    channels: int
    sample_rate_hz: int
    bit_depth: int
    total_samples: int
    rms_amplitude: float
    dc_offset: float


@dataclass
class AudioForensicReport:
    timestamp: str
    target_audio: str
    metadata: AudioMetadataReport
    entropy: AudioEntropyStats
    stego_detection_verdict: str
    stego_probability_pct: float
    risk_level: str
    recommendations: List[str]

    @property
    def sample_rate(self) -> int:
        return self.metadata.sample_rate_hz

    @property
    def bits_per_sample(self) -> int:
        return self.metadata.bit_depth

    @property
    def channels(self) -> int:
        return self.metadata.channels

    @property
    def total_samples(self) -> int:
        return self.metadata.total_samples

    @property
    def duration_seconds(self) -> float:
        return self.metadata.duration_seconds

    @property
    def rms_energy(self) -> float:
        return self.metadata.rms_amplitude

    @property
    def dc_bias(self) -> float:
        return self.metadata.dc_offset

    @property
    def verdict(self) -> str:
        return self.stego_detection_verdict

    @property
    def file_size_bytes(self) -> int:
        return self.metadata.file_size_bytes

    @property
    def bitplane_entropy(self) -> Dict[int, float]:
        return {
            0: self.entropy.lsb_plane_entropy,
            1: self.entropy.lsb2_plane_entropy,
        }


class AudioForensics:
    """
    Forensics and steganalysis suite for uncompressed audio signals.
    """

    @staticmethod
    def calculate_bit_entropy(bits: np.ndarray) -> float:
        """Calculates Shannon entropy of a binary bit stream (0 to 1 bit/symbol)."""
        if len(bits) == 0:
            return 0.0
        p1 = float(np.mean(bits))
        p0 = 1.0 - p1
        if p0 <= 0 or p1 <= 0:
            return 0.0
        return float(-p0 * math.log2(p0) - p1 * math.log2(p1))

    @classmethod
    def analyze_audio(cls, wav_path: str) -> AudioForensicReport:
        """
        Runs comprehensive forensic steganalysis on a WAV audio file.
        """
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"Audio file not found: {wav_path}")

        filename = os.path.basename(wav_path)
        file_size = os.path.getsize(wav_path)

        with wave.open(wav_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            comptype = wf.getcomptype()
            raw_frames = wf.readframes(n_frames)

        if comptype != "NONE":
            raise UnsupportedFormatError(f"Compressed audio ({comptype}) is not supported for forensic analysis.")

        bit_depth = sampwidth * 8
        if sampwidth == 1:
            samples = np.frombuffer(raw_frames, dtype=np.uint8)
        elif sampwidth == 2:
            samples = np.frombuffer(raw_frames, dtype=np.int16)
        elif sampwidth == 4:
            samples = np.frombuffer(raw_frames, dtype=np.int32)
        else:
            raise UnsupportedFormatError(f"Unsupported sample width: {sampwidth} bytes.")

        total_samples = len(samples)
        duration = n_frames / float(framerate) if framerate > 0 else 0.0

        # Physical signal properties
        float_samples = samples.astype(np.float64)
        rms = float(np.sqrt(np.mean(float_samples ** 2))) if total_samples > 0 else 0.0
        dc_offset = float(np.mean(float_samples)) if total_samples > 0 else 0.0

        # Entropy calculations
        # Sample histogram entropy
        hist, _ = np.histogram(samples, bins=min(256, max(16, len(np.unique(samples)))))
        probs = hist[hist > 0] / float(total_samples)
        overall_entropy = float(-np.sum(probs * np.log2(probs))) if len(probs) > 0 else 0.0

        # LSB plane (bit 0) entropy
        lsb0 = (samples & 1).astype(np.uint8)
        lsb0_entropy = cls.calculate_bit_entropy(lsb0)

        # LSB 1 plane (bit 1) entropy
        lsb1 = ((samples >> 1) & 1).astype(np.uint8)
        lsb1_entropy = cls.calculate_bit_entropy(lsb1)

        # Forensic Steganalysis Verdict
        # Natural audio LSB entropy is usually 0.70 - 0.92. Encrypted payload drives it to > 0.99.
        if lsb0_entropy > 0.985:
            stego_prob = min(99.9, round(lsb0_entropy * 100.0, 1))
            verdict = "Steganographic Audio Payload Detected"
            risk_level = "High"
            recs = [
                "Extract hidden content using CloakPix Decrypt with the authorized passphrase.",
                "High LSB randomness (>98.5% entropy) strongly indicates cryptographically concealed payload.",
                "Preserve WAV file hash in chain of custody evidence vault.",
            ]
        elif lsb0_entropy > 0.95:
            stego_prob = round(65.0 + (lsb0_entropy - 0.95) * 500.0, 1)
            verdict = "Suspicious LSB Audio Entropy Anomaly"
            risk_level = "Medium"
            recs = [
                "Elevated LSB entropy detected. Inspect audio frequency domain spectrogram.",
                "Compare against pristine studio master recording if accessible.",
            ]
        else:
            stego_prob = max(0.5, round((lsb0_entropy / 0.95) * 20.0, 1))
            verdict = "Clean / Pristine Audio Signal"
            risk_level = "Low"
            recs = [
                "Audio signal exhibits natural acoustic noise distribution in least significant bits.",
                "No steganographic anomalies detected.",
            ]

        meta = AudioMetadataReport(
            filename=filename,
            file_size_bytes=file_size,
            duration_seconds=round(duration, 2),
            channels=n_channels,
            sample_rate_hz=framerate,
            bit_depth=bit_depth,
            total_samples=total_samples,
            rms_amplitude=round(rms, 2),
            dc_offset=round(dc_offset, 4),
        )

        entropy_stats = AudioEntropyStats(
            overall_sample_entropy=round(overall_entropy, 3),
            lsb_plane_entropy=round(lsb0_entropy, 4),
            lsb2_plane_entropy=round(lsb1_entropy, 4),
            theoretical_max=round(float(bit_depth), 1),
        )

        return AudioForensicReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            target_audio=filename,
            metadata=meta,
            entropy=entropy_stats,
            stego_detection_verdict=verdict,
            stego_probability_pct=stego_prob,
            risk_level=risk_level,
            recommendations=recs,
        )

    @classmethod
    def export_report_txt(cls, report: AudioForensicReport, output_path: str) -> str:
        """Exports human-readable plain text report for audio."""
        lines = [
            "=" * 70,
            "               CLOAKPIX AUDIO FORENSIC REPORT",
            "=" * 70,
            f"Timestamp:          {report.timestamp}",
            f"Target Audio:       {report.target_audio}",
            f"File Size:          {report.metadata.file_size_bytes:,} bytes",
            f"Duration:           {report.metadata.duration_seconds} seconds",
            f"Channels:           {report.metadata.channels} ({'Stereo' if report.metadata.channels == 2 else 'Mono'})",
            f"Sample Rate:        {report.metadata.sample_rate_hz:,} Hz",
            f"Bit Depth:          {report.metadata.bit_depth}-bit PCM",
            f"Total Samples:      {report.metadata.total_samples:,}",
            f"RMS Energy:         {report.metadata.rms_amplitude}",
            f"DC Bias / Offset:   {report.metadata.dc_offset}",
            "-" * 70,
            "STATISTICAL STEGANALYSIS & ENTROPY",
            f"• Overall Entropy:  {report.entropy.overall_sample_entropy} bits/symbol",
            f"• LSB (Bit 0):      {report.entropy.lsb_plane_entropy} (Randomness Index)",
            f"• LSB (Bit 1):      {report.entropy.lsb2_plane_entropy}",
            "-" * 70,
            "FORENSIC VERDICT",
            f"• Result:           {report.stego_detection_verdict}",
            f"• Stego Likelihood: {report.stego_probability_pct}%",
            f"• Risk Level:       {report.risk_level}",
            "-" * 70,
            "RECOMMENDATIONS",
        ]
        for r in report.recommendations:
            lines.append(f"• {r}")
        lines.append("=" * 70)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return output_path

    @classmethod
    def export_report_json(cls, report: AudioForensicReport, output_path: str) -> str:
        """Exports audio forensic report to JSON."""
        data = asdict(report)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return output_path
