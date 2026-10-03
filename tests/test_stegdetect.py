"""
Unit tests for StegDetect visual contrast normalizer and bit engine benchmark.
"""

import numpy as np
from PIL import Image
import pytest

from cloakpix.core.forensics import ImageForensics
from cloakpix.core.bit_engine import (
    lsb_interleave_bytes,
    lsb_deinterleave_bytes,
    run_benchmark,
)


def test_stegdetect_amplify_dynamic_range():
    """Verify StegDetect normalizes the dynamic range across 0-255."""
    # Create an image where LSBs only have values 0 or 1
    arr = np.zeros((50, 50, 3), dtype=np.uint8)
    arr[0:25, :, 0] = 0b00000001
    arr[25:50, :, 0] = 0b00000000
    img = Image.fromarray(arr, mode="RGB")

    # Amplify 1 LSB
    amplified = ImageForensics.stegdetect_amplify(img, num_lsbs=1)
    amp_arr = np.array(amplified)

    # In amplified array, 1 * (255 / 1) = 255, 0 = 0
    assert amp_arr[0, 0, 0] == 255
    assert amp_arr[30, 0, 0] == 0


def test_stegdetect_amplify_2_lsbs():
    """Verify StegDetect normalizes 2 LSBs (max value 3 -> 255)."""
    arr = np.zeros((20, 20, 3), dtype=np.uint8)
    arr[:, :, 0] = 3  # 0b00000011
    img = Image.fromarray(arr, mode="RGB")

    amplified = ImageForensics.stegdetect_amplify(img, num_lsbs=2)
    amp_arr = np.array(amplified)
    assert amp_arr[0, 0, 0] == 255


def test_bit_engine_interleave_deinterleave():
    """Verify bit engine interleaves and restores arbitrary bit streams."""
    carrier = bytearray([0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
    payload = b"\xAB"  # 10101011

    interleaved = lsb_interleave_bytes(carrier, payload, num_lsbs=1)
    # Check that bits were embedded
    extracted = lsb_deinterleave_bytes(interleaved, num_bytes=1, num_lsbs=1)
    assert extracted == payload


def test_bit_engine_benchmark():
    """Test performance benchmark execution."""
    res = run_benchmark(carrier_size_bytes=50000, num_runs=2)
    assert "interleave_speed_mb_s" in res
    assert "deinterleave_speed_mb_s" in res
    assert res["interleave_speed_mb_s"] > 0
    assert res["deinterleave_speed_mb_s"] > 0
