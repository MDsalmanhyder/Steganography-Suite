"""
End-to-end tests for SecureStego CLI commands.
"""

import sys
from PIL import Image
import numpy as np
import pytest

from securestego.cli import build_parser, cmd_hide, cmd_extract, cmd_analyze, cmd_capacity


@pytest.fixture
def test_image_path(tmp_path):
    img_path = str(tmp_path / "carrier.png")
    arr = np.zeros((100, 100, 3), dtype=np.uint8)
    arr[:, :, 0] = 120
    arr[:, :, 1] = 150
    arr[:, :, 2] = 180
    Image.fromarray(arr).save(img_path)
    return img_path


def test_cli_hide_and_extract_text(test_image_path, tmp_path):
    parser = build_parser()
    stego_out = str(tmp_path / "stego.png")
    txt_out = str(tmp_path / "extracted.txt")

    # 1. Hide command
    args_hide = parser.parse_args([
        "hide",
        "--carrier", test_image_path,
        "--text", "Top Secret Payload CLI Test 2026",
        "--password", "CLIPassword123!",
        "--output", stego_out,
        "--bits", "1",
    ])
    cmd_hide(args_hide)
    assert (tmp_path / "stego.png").exists()

    # 2. Extract command
    args_extract = parser.parse_args([
        "extract",
        "--stego", stego_out,
        "--password", "CLIPassword123!",
        "--output-file", txt_out,
    ])
    cmd_extract(args_extract)
    assert (tmp_path / "extracted.txt").exists()
    assert (tmp_path / "extracted.txt").read_text(encoding="utf-8") == "Top Secret Payload CLI Test 2026"


def test_cli_analyze(test_image_path, tmp_path):
    parser = build_parser()
    pdf_out = str(tmp_path / "report.pdf")
    json_out = str(tmp_path / "report.json")
    slice_out = str(tmp_path / "lsb_slice.png")

    args_analyze = parser.parse_args([
        "analyze",
        "--image", test_image_path,
        "--export-pdf", pdf_out,
        "--export-json", json_out,
        "--slice-bit", "0",
        "--slice-channel", "combined",
        "--slice-out", slice_out,
    ])
    cmd_analyze(args_analyze)

    assert (tmp_path / "report.pdf").exists()
    assert (tmp_path / "report.json").exists()
    assert (tmp_path / "lsb_slice.png").exists()


def test_cli_capacity(test_image_path):
    parser = build_parser()
    args_cap = parser.parse_args([
        "capacity",
        "--image", test_image_path,
        "--bits", "1",
    ])
    cmd_capacity(args_cap)
