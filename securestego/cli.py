"""
Command-Line Interface (CLI) for SecureStego.
Enables headless scripting, automated workflows, and batch steganography & forensics.
"""

import argparse
import getpass
import os
import sys
from PIL import Image

from securestego import __version__
from securestego.core.stego_engine import StegoEngine
from securestego.core.forensics import ImageForensics
from securestego.core.file_manager import FileManager, AuditLogger
from securestego.core.metrics import calculate_image_capacity
from securestego.core.exceptions import SecureStegoError


def get_password(provided_password: str = None) -> str:
    if provided_password:
        return provided_password
    pwd = getpass.getpass("Enter secret passphrase: ")
    if not pwd:
        print("Error: Passphrase cannot be empty.", file=sys.stderr)
        sys.exit(1)
    return pwd


def cmd_hide(args):
    engine = StegoEngine(default_bits_per_channel=args.bits)
    password = get_password(args.password)

    if not os.path.exists(args.carrier):
        print(f"Error: Carrier image not found: {args.carrier}", file=sys.stderr)
        sys.exit(1)

    if not args.text and not args.file:
        print("Error: Must provide either --text <msg> or --file <path>.", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Encrypting and embedding data into: {args.carrier}")
    print(f"[*] Embedding density: {args.bits} bit(s) per channel")

    try:
        res = engine.embed(
            carrier_input=args.carrier,
            password=password,
            secret_text=args.text,
            secret_file_path=args.file,
            bits_per_channel=args.bits,
        )

        out_path = FileManager.save_stego_image(res.stego_image, args.output)

        print("\n[+] Embedding Successful!")
        print(f"    • Output Stego Image: {out_path}")
        print(f"    • Payload Type:       {res.payload_type.upper()}")
        print(f"    • Payload Size:       {res.payload_bytes:,} bytes")
        print(f"    • Total Stream:       {res.total_embedded_bytes:,} bytes ({res.capacity_used_pct}% of image capacity)")
        print(f"    • PSNR Fidelity:      {res.psnr_db} dB")
        print(f"    • MSE:                {res.mse}")
        print(f"    • SSIM:               {res.ssim}")
    except SecureStegoError as e:
        print(f"[-] Error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_extract(args):
    engine = StegoEngine()
    password = get_password(args.password)

    if not os.path.exists(args.stego):
        print(f"Error: Stego image not found: {args.stego}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Extracting and verifying hidden payload from: {args.stego}")

    try:
        res = engine.extract(args.stego, password=password)

        print("\n[+] Extraction Successful & Authenticated (AES-256-GCM Verified)!")
        print(f"    • Payload Type:       {res.payload_type.upper()}")
        print(f"    • Payload Size:       {res.payload_size_bytes:,} bytes")
        print(f"    • Bits / Channel:     {res.bits_per_channel}")

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
    except SecureStegoError as e:
        print(f"[-] Decryption/Extraction Failed: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_analyze(args):
    if not os.path.exists(args.image):
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Running forensic steganalysis pipeline on: {args.image}")
    report = ImageForensics.analyze_image(args.image)

    # Print summary to console
    print("\n" + "=" * 60)
    print("             SECURESTEGO FORENSIC REPORT")
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
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    with Image.open(args.image) as img:
        w, h = img.size
        channels = len(img.getbands())

    info = calculate_image_capacity(w, h, channels=3, bits_per_channel=args.bits)
    raw_kb = info["raw_capacity_bytes"] / 1024.0
    usable_kb = info["usable_capacity_bytes"] / 1024.0

    print(f"\nCapacity Analysis for: {args.image}")
    print(f"• Dimensions:        {w} × {h} px")
    print(f"• Channels Used:     3 (RGB)")
    print(f"• Embedding Density: {args.bits} bit(s) / channel")
    print(f"• Raw Capacity:      {info['raw_capacity_bytes']:,} bytes ({raw_kb:.2f} KB)")
    print(f"• Usable Capacity:   ~{info['usable_capacity_bytes']:,} bytes ({usable_kb:.2f} KB)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="securestego",
        description=f"SecureStego v{__version__} – Secure Image Steganography & Forensics Suite",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: hide
    hide_p = subparsers.add_parser("hide", help="Embed encrypted secret text or file into carrier image")
    hide_p.add_argument("--carrier", "-c", required=True, help="Path to input carrier image (PNG recommended)")
    hide_p.add_argument("--text", "-t", help="Secret text message to embed")
    hide_p.add_argument("--file", "-f", help="Path to secret binary file to embed")
    hide_p.add_argument("--password", "-p", help="Encryption passphrase (will prompt securely if omitted)")
    hide_p.add_argument("--output", "-o", required=True, help="Output stego image path (.png)")
    hide_p.add_argument("--bits", "-b", type=int, default=1, choices=[1, 2, 3, 4], help="LSB bits per channel (1 to 4)")

    # Command: extract
    extract_p = subparsers.add_parser("extract", help="Extract and decrypt hidden payload from stego image")
    extract_p.add_argument("--stego", "-s", required=True, help="Path to stego image")
    extract_p.add_argument("--password", "-p", help="Decryption passphrase (will prompt securely if omitted)")
    extract_p.add_argument("--output-dir", "-d", help="Directory to save extracted file")
    extract_p.add_argument("--output-file", "-o", help="File name/path for extracted text or file")

    # Command: analyze
    analyze_p = subparsers.add_parser("analyze", help="Run forensic steganalysis on an image")
    analyze_p.add_argument("--image", "-i", required=True, help="Path to image to analyze")
    analyze_p.add_argument("--export-pdf", help="Save forensic report as PDF")
    analyze_p.add_argument("--export-json", help="Save forensic report as JSON")
    analyze_p.add_argument("--export-txt", help="Save forensic report as plain text")
    analyze_p.add_argument("--slice-bit", type=int, default=0, choices=range(8), help="Bit plane index (0-7)")
    analyze_p.add_argument("--slice-channel", default="combined", choices=["r", "g", "b", "gray", "combined"], help="Channel for bit-plane extraction")
    analyze_p.add_argument("--slice-out", help="Save extracted bit-plane slice image")

    # Command: capacity
    cap_p = subparsers.add_parser("capacity", help="Calculate image data hiding capacity")
    cap_p.add_argument("--image", "-i", required=True, help="Path to image")
    cap_p.add_argument("--bits", "-b", type=int, default=1, choices=[1, 2, 3, 4], help="LSB bits per channel (1 to 4)")

    # Command: gui
    subparsers.add_parser("gui", help="Launch the Desktop GUI Application")

    return parser


def main():
    parser = build_parser()
    if len(sys.argv) == 1:
        # Launch GUI if no args provided
        from securestego.app import run_app
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
    elif args.command == "gui":
        from securestego.app import run_app
        run_app()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
