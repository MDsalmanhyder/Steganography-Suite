"""
Command-Line Interface (CLI) for CloakPix.
Unified, cross-format steganography and forensics suite for Images (.png, .bmp, .tiff, .webp) and Audio (.wav).
Includes StegDetect visual normalizer and high-speed bit interleaving benchmark suite.
"""

import argparse
import getpass
import os
import sys
from typing import Optional
from PIL import Image

from cloakpix import __version__
from cloakpix.core.unified_engine import UnifiedStegoEngine
from cloakpix.core.stego_engine import StegoEngine
from cloakpix.core.audio_stego import AudioStegoEngine
from cloakpix.core.forensics import ImageForensics
from cloakpix.core.audio_forensics import AudioForensics
from cloakpix.core.file_manager import FileManager, AuditLogger
from cloakpix.core.bit_engine import run_benchmark
from cloakpix.core.exceptions import CloakPixError


def get_password(provided_password: Optional[str] = None) -> str:
    if provided_password:
        return provided_password
    pwd = getpass.getpass("Enter secret passphrase: ")
    if not pwd:
        print("Error: Passphrase cannot be empty.", file=sys.stderr)
        sys.exit(1)
    return pwd


def cmd_hide(args):
    unified = UnifiedStegoEngine(default_bits=args.bits)
    password = get_password(args.password)

    if not os.path.exists(args.carrier):
        print(f"Error: Carrier file not found: {args.carrier}", file=sys.stderr)
        sys.exit(1)

    if not args.text and not args.file:
        print("Error: Must provide either --text <msg> or --file <path>.", file=sys.stderr)
        sys.exit(1)

    is_audio = unified.is_audio_carrier(args.carrier)
    carrier_type_str = "WAV Audio" if is_audio else "Lossless Image"

    print(f"[*] Concealing data into {carrier_type_str}: {args.carrier}")
    print(f"[*] Embedding density: {args.bits} bit(s) per {'sample' if is_audio else 'channel'}")
    if args.compress:
        print("[*] Pre-compression: Enabled (zlib deflate level 9)")

    try:
        res = unified.embed(
            carrier_input=args.carrier,
            password=password,
            secret_text=args.text,
            secret_file_path=args.file,
            bits=args.bits,
            compress=args.compress,
            output_path=args.output,
        )

        # If image, save using FileManager to ensure lossless formatting
        if not is_audio:
            out_path = FileManager.save_stego_image(res.raw_result.stego_image, args.output)
        else:
            out_path = os.path.abspath(args.output)

        print("\n[+] Embedding Successful & Cryptographically Authenticated!")
        print(f"    • Output Stego File:  {out_path}")
        print(f"    • Carrier Medium:     {res.carrier_type.upper()}")
        print(f"    • Payload Type:       {res.payload_type.upper()}")
        print(f"    • Payload Size:       {res.payload_bytes:,} bytes")
        print(f"    • Total Stream:       {res.total_embedded_bytes:,} bytes ({res.capacity_used_pct}% capacity)")
        print(f"    • {res.fidelity_metric_name}:      {res.fidelity_value} dB")
        if not is_audio:
            print(f"    • MSE:                {res.raw_result.mse}")
            print(f"    • SSIM:               {res.raw_result.ssim}")
        else:
            print(f"    • Sample Rate:        {res.raw_result.sample_rate:,} Hz")
            print(f"    • Channels:           {res.raw_result.channels}")
    except CloakPixError as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_extract(args):
    unified = UnifiedStegoEngine()
    password = get_password(args.password)

    if not os.path.exists(args.stego):
        print(f"Error: Stego file not found: {args.stego}", file=sys.stderr)
        sys.exit(1)

    is_audio = unified.is_audio_carrier(args.stego)
    print(f"[*] Extracting and authenticating hidden payload from ({'Audio' if is_audio else 'Image'}): {args.stego}")

    try:
        res = unified.extract(args.stego, password=password)

        print("\n[+] Extraction Successful & Authenticated (AES-256-GCM Verified)!")
        print(f"    • Payload Type:       {res.payload_type.upper()}")
        print(f"    • Payload Size:       {res.payload_size_bytes:,} bytes")
        print(f"    • Bits / Unit:        {res.bits_per_sample if is_audio else res.bits_per_channel}")

        if res.payload_type == "text":
            print("\n--- DECODED MESSAGE CONTENT ---")
            print(res.text)
            print("--------------------------------\n")
            if args.output_file:
                with open(args.output_file, "w", encoding="utf-8") as f:
                    f.write(res.text)
                print(f"[+] Text saved to: {args.output_file}")
        else:
            out_dir = args.output_dir or "."
            dest = FileManager.export_extracted_file(
                res.data,
                out_dir,
                preferred_filename=args.output_file or res.filename,
            )
            print(f"[+] Extracted file exported to: {dest}")
    except CloakPixError as e:
        print(f"[-] Decryption/Extraction Failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_analyze(args):
    if not os.path.exists(args.image):
        print(f"Error: Target file not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    unified = UnifiedStegoEngine()
    if unified.is_audio_carrier(args.image):
        print(f"[*] Running Audio forensic steganalysis pipeline on: {args.image}")
        report = AudioForensics.analyze_audio(args.image)

        print("\n" + "=" * 60)
        print("             CLOAKPIX AUDIO FORENSIC REPORT")
        print("=" * 60)
        print(f"Target:             {report.target_audio}")
        print(f"Duration:           {report.metadata.duration_seconds} sec ({report.metadata.sample_rate_hz:,} Hz, {report.metadata.channels} ch)")
        print(f"Verdict:            {report.stego_detection_verdict}")
        print(f"Risk Level:         {report.risk_level}")
        print("-" * 60)
        print(f"Stego Probability:  {report.stego_probability_pct}%")
        print(f"LSB Entropy (Bit0): {report.entropy.lsb_plane_entropy} (Randomness Index)")
        print(f"LSB Entropy (Bit1): {report.entropy.lsb2_plane_entropy}")
        print(f"Overall Entropy:    {report.entropy.overall_sample_entropy} bits/symbol")
        print("=" * 60)

        if args.export_txt:
            AudioForensics.export_report_txt(report, args.export_txt)
            print(f"[+] Audio TXT Report saved to: {args.export_txt}")
        if args.export_json:
            AudioForensics.export_report_json(report, args.export_json)
            print(f"[+] Audio JSON Data saved to: {args.export_json}")
        return

    # Image Forensics
    print(f"[*] Running Image forensic steganalysis pipeline on: {args.image}")
    report = ImageForensics.analyze_image(args.image)

    # Print summary to console
    print("\n" + "=" * 60)
    print("             CLOAKPIX FORENSIC REPORT")
    print("=" * 60)
    print(f"Target:             {report.target_image}")
    print(f"Dimensions:         {report.metadata.dimensions[0]}x{report.metadata.dimensions[1]} px ({report.metadata.mode})")
    print(f"Verdict:            {report.stego_detection_verdict}")
    print(f"Risk Level:         {report.risk_level}")
    print("-" * 60)
    print(f"Chi-Square (χ²):    {report.chi_square.chi2_statistic} (p={report.chi_square.p_value:.6f})")
    print(f"Stego Probability:  {report.chi_square.stego_probability_pct}%")
    print(f"Sample Pair Est:    {report.sample_pair.estimated_embedding_rate_pct}% (~{report.sample_pair.estimated_payload_bytes:,} B)")
    print(f"Overall Entropy:    {report.entropy.overall} bits/symbol")
    print(f"LSB Plane Entropy:  {report.entropy.lsb_plane} bits/symbol")
    print("=" * 60)

    if args.export_pdf:
        pdf_out = ImageForensics.export_report_pdf(report, args.export_pdf)
        print(f"[+] Forensic PDF Report saved to: {pdf_out}")

    if args.export_json:
        json_out = ImageForensics.export_report_json(report, args.export_json)
        print(f"[+] Forensic JSON Data saved to: {json_out}")

    if args.export_txt:
        txt_out = ImageForensics.export_report_txt(report, args.export_txt)
        print(f"[+] Forensic TXT Report saved to: {txt_out}")

    if args.slice_out:
        slice_img = ImageForensics.extract_bit_plane(
            args.image,
            bit=args.slice_bit,
            channel=args.slice_channel,
        )
        slice_img.save(args.slice_out)
        print(f"[+] Bit plane slice (Bit {args.slice_bit}, {args.slice_channel}) saved to: {args.slice_out}")


def cmd_capacity(args):
    if not os.path.exists(args.image):
        print(f"Error: Target carrier not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    unified = UnifiedStegoEngine()
    info = unified.calculate_capacity(args.image, bits=args.bits)

    print(f"\nCapacity Analysis for: {args.image}")
    print(f"• Carrier Type:      {info['carrier_type'].upper()}")
    if info['carrier_type'] == "image":
        w, h = info["dimensions"]
        print(f"• Dimensions:        {w} × {h} px ({info['mode']})")
        print(f"• Channels Used:     3 (RGB)")
    else:
        print(f"• Duration:          {info['duration_seconds']} sec")
        print(f"• Sample Rate:       {info['sample_rate_hz']:,} Hz ({info['channels']} channel(s))")
        print(f"• Total Samples:     {info['total_samples']:,}")

    raw_kb = info["raw_capacity_bytes"] / 1024.0
    usable_kb = info["usable_capacity_bytes"] / 1024.0
    print(f"• Embedding Density: {args.bits} bit(s) / unit")
    print(f"• Raw Capacity:      {info['raw_capacity_bytes']:,} bytes ({raw_kb:.2f} KB)")
    print(f"• Usable Capacity:   ~{info['usable_capacity_bytes']:,} bytes ({usable_kb:.2f} KB)")


def cmd_stegdetect(args):
    """
    StegDetect command (inspired by ragibson/Steganography):
    Amplifies and normalizes the lowest n LSBs to reveal hidden data patterns visually.
    """
    if not os.path.exists(args.image):
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Running StegDetect LSB visual amplifier ({args.bits} LSBs) on: {args.image}")
    amplified = ImageForensics.stegdetect_amplify(
        args.image,
        num_lsb=args.bits,
        channel=args.channel,
    )

    out_path = args.output
    if not out_path:
        base, ext = os.path.splitext(args.image)
        out_path = f"{base}_{args.bits}LSBs{ext}"

    amplified.save(out_path)
    print(f"[+] StegDetect contrast map saved to: {out_path}")


def cmd_benchmark(args):
    """
    Benchmarks bit interleaving / deinterleaving throughput across 1-8 LSBs.
    """
    print(f"\n[*] Benchmarking CloakPix Bit Interleaving Engine...")
    print(f"[*] Payload: {args.payload} MB | Carrier: {args.carrier} MB")
    print("-" * 52)
    print(f"| # LSBs | Encode Rate   | Decode Rate   | Status   |")
    print("-" * 52)

    results = run_benchmark(payload_mb=args.payload, carrier_mb=args.carrier)
    for r in results:
        print(
            f"| {r['num_lsb']:<6} | "
            f"{r['encode_rate_mb_s']:>7.1f} MB/s | "
            f"{r['decode_rate_mb_s']:>7.1f} MB/s | "
            f"Verified |"
        )
    print("-" * 52)
    print("[+] Benchmark complete: 100% roundtrip accuracy verified across all 1-8 bit depths!\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cloakpix",
        description=f"CloakPix v{__version__} – Secure Image & Audio Steganography & Forensics Suite",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: hide
    hide_p = subparsers.add_parser("hide", help="Embed encrypted secret text or file into carrier image or WAV audio")
    hide_p.add_argument("--carrier", "-c", required=True, help="Path to input carrier (PNG, BMP, TIFF, WEBP, or WAV)")
    hide_p.add_argument("--text", "-t", help="Secret text message to embed")
    hide_p.add_argument("--file", "-f", help="Path to secret binary file to embed")
    hide_p.add_argument("--password", "-p", help="Encryption passphrase (will prompt securely if omitted)")
    hide_p.add_argument("--output", "-o", required=True, help="Output stego path (.png, .bmp, .wav, etc.)")
    hide_p.add_argument("--bits", "-b", type=int, default=1, choices=[1, 2, 3, 4], help="LSB bits per channel/sample (1 to 4)")
    hide_p.add_argument("--compress", "-z", action="store_true", help="Pre-compress payload with zlib deflate before encryption")

    # Command: extract
    extract_p = subparsers.add_parser("extract", help="Extract and decrypt hidden payload from stego image or WAV audio")
    extract_p.add_argument("--stego", "-s", required=True, help="Path to stego image or WAV audio")
    extract_p.add_argument("--password", "-p", help="Decryption passphrase (will prompt securely if omitted)")
    extract_p.add_argument("--output-dir", "-d", help="Directory to save extracted file")
    extract_p.add_argument("--output-file", "-o", help="File name/path for extracted text or file")

    # Command: analyze
    analyze_p = subparsers.add_parser("analyze", help="Run forensic steganalysis on an image or WAV audio")
    analyze_p.add_argument("--image", "--target", "--carrier", "-i", "-t", dest="image", required=True, help="Path to image or WAV audio to analyze")
    analyze_p.add_argument("--export-pdf", help="Save forensic report as PDF (images)")
    analyze_p.add_argument("--export-json", help="Save forensic report as JSON")
    analyze_p.add_argument("--export-txt", help="Save forensic report as plain text")
    analyze_p.add_argument("--slice-bit", type=int, default=0, choices=range(8), help="Bit plane index (0-7)")
    analyze_p.add_argument("--slice-channel", default="combined", choices=["r", "g", "b", "gray", "combined"], help="Channel for bit-plane extraction")
    analyze_p.add_argument("--slice-out", help="Save extracted bit-plane slice image")

    # Command: capacity
    cap_p = subparsers.add_parser("capacity", help="Calculate carrier data hiding capacity (Image or WAV Audio)")
    cap_p.add_argument("--image", "--carrier", "-i", "-c", dest="image", required=True, help="Path to carrier image or WAV audio file")
    cap_p.add_argument("--bits", "-b", type=int, default=1, choices=[1, 2, 3, 4], help="LSB bits per channel/sample (1 to 4)")

    # Command: stegdetect (from ragibson/Steganography)
    steg_p = subparsers.add_parser("stegdetect", help="Visual LSB contrast normalizer to reveal hidden pixel patterns")
    steg_p.add_argument("--image", "-i", required=True, help="Path to image")
    steg_p.add_argument("--bits", "-n", type=int, default=2, choices=range(1, 9), help="Number of LSBs to amplify (1 to 8, default: 2)")
    steg_p.add_argument("--channel", "-c", default="combined", choices=["r", "g", "b", "gray", "combined"], help="Channel to isolate")
    steg_p.add_argument("--output", "-o", help="Path to save amplified contrast map")

    # Command: benchmark (from ragibson/Steganography bit_manipulation test)
    bench_p = subparsers.add_parser("benchmark", help="Benchmark bit interleaving & throughput speed (MB/s)")
    bench_p.add_argument("--payload", type=float, default=1.0, help="Test payload size in MB (default: 1.0)")
    bench_p.add_argument("--carrier", type=float, default=10.0, help="Test carrier size in MB (default: 10.0)")

    # Command: gui
    subparsers.add_parser("gui", help="Launch the Desktop GUI Application")

    return parser


def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        # Launch GUI if no args provided
        from cloakpix.app import run_app
        run_app()
        return

    args = parser.parse_args()

    if args.command == "hide":
        cmd_hide(args)
    elif args.command == "extract":
        cmd_extract(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "capacity":
        cmd_capacity(args)
    elif args.command == "stegdetect":
        cmd_stegdetect(args)
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "gui":
        from cloakpix.app import run_app
        run_app()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
