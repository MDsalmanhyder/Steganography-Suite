"""
Image Forensics and Steganalysis Module for CloakPix.
Includes visual bit-plane extraction, Chi-Square steganalysis, Shannon entropy,
metadata extraction, and PDF/JSON forensic report generation.
"""

import json
import math
import os
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image, ExifTags, PngImagePlugin
from scipy import stats

from cloakpix.core.metrics import calculate_entropy



@dataclass
class EntropyStats:
    overall: float
    red: float
    green: float
    blue: float
    grayscale: float
    lsb_plane: float


@dataclass
class ChiSquareResult:
    chi2_statistic: float
    degrees_of_freedom: int
    p_value: float
    stego_probability_pct: float
    is_stego_detected: bool
    verdict: str


@dataclass
class SamplePairResult:
    estimated_embedding_rate_pct: float
    estimated_payload_bytes: int
    confidence_level: str


@dataclass
class ImageMetadataReport:
    filename: str
    file_size_bytes: int
    format: str
    dimensions: Tuple[int, int]
    mode: str
    has_alpha: bool
    color_channels: int
    png_chunks: Dict[str, str]
    exif_data: Dict[str, str]


@dataclass
class ForensicAnalysisReport:
    timestamp: str
    target_image: str
    metadata: ImageMetadataReport
    entropy: EntropyStats
    chi_square: ChiSquareResult
    sample_pair: SamplePairResult
    stego_detection_verdict: str
    risk_level: str
    recommendations: List[str]


class ImageForensics:
    """
    Forensics and Steganalysis toolkit for analyzing images.
    """

    @staticmethod
    def _to_rgb_array(image_input: Union[str, Image.Image]) -> Tuple[Image.Image, np.ndarray]:
        """Loads image and returns (PIL Image, RGB numpy array)."""
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image not found: {image_input}")
            img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            raise TypeError("Expected file path or PIL Image.")

        rgb_img = img.convert("RGB")
        arr = np.array(rgb_img, dtype=np.uint8)
        return img, arr

    @staticmethod
    def extract_bit_plane(
        image_input: Union[str, Image.Image],
        bit: int = 0,
        channel: str = "combined",
    ) -> Image.Image:
        """
        Extracts a specific bit plane (0=LSB to 7=MSB) for visualization.
        
        Args:
            image_input: Path to image or PIL Image.
            bit: Bit plane index (0=least significant, 7=most significant).
            channel: 'r', 'g', 'b', 'gray', or 'combined'.
            
        Returns:
            PIL Image representing the visual bit plane (scaled to 0-255).
        """
        if not (0 <= bit <= 7):
            raise ValueError("Bit index must be between 0 and 7.")

        _, arr = ImageForensics._to_rgb_array(image_input)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

        channel_lower = channel.lower()
        if channel_lower == "r":
            plane = ((r >> bit) & 1) * 255
            return Image.fromarray(plane.astype(np.uint8), mode="L")
        elif channel_lower == "g":
            plane = ((g >> bit) & 1) * 255
            return Image.fromarray(plane.astype(np.uint8), mode="L")
        elif channel_lower == "b":
            plane = ((b >> bit) & 1) * 255
            return Image.fromarray(plane.astype(np.uint8), mode="L")
        elif channel_lower == "gray":
            gray = np.array(Image.fromarray(arr).convert("L"))
            plane = ((gray >> bit) & 1) * 255
            return Image.fromarray(plane.astype(np.uint8), mode="L")
        elif channel_lower == "combined":
            # Extract 3-channel RGB bit planes
            r_plane = ((r >> bit) & 1) * 255
            g_plane = ((g >> bit) & 1) * 255
            b_plane = ((b >> bit) & 1) * 255
            combined = np.dstack((r_plane, g_plane, b_plane)).astype(np.uint8)
            return Image.fromarray(combined, mode="RGB")
        else:
            raise ValueError(f"Unknown channel: {channel}. Expected 'r','g','b','gray','combined'.")

    @staticmethod
    def stegdetect_amplify(
        image_input: Union[str, Image.Image],
        num_lsb: int = 1,
        channel: str = "combined",
        num_lsbs: Optional[int] = None,
    ) -> Image.Image:
        """
        StegDetect visual LSB enhancer (inspired by and compatible with ragibson/Steganography).
        Extracts the lowest `num_lsb` bits from each pixel channel and normalizes the dynamic
        range to full [0, 255] contrast, making hidden LSB patterns immediately visible.
        
        Args:
            image_input: Image path or PIL Image.
            num_lsb: Number of LSB bits to isolate and amplify (1 to 8).
            channel: 'r', 'g', 'b', 'gray', or 'combined'.
            num_lsbs: Alias for num_lsb.
            
        Returns:
            Normalized visual PIL Image.
        """
        effective_lsb = num_lsbs if num_lsbs is not None else num_lsb
        if not (1 <= effective_lsb <= 8):
            raise ValueError("num_lsb must be between 1 and 8.")

        _, arr = ImageForensics._to_rgb_array(image_input)
        mask = (1 << effective_lsb) - 1
        scale = 255.0 / float(mask)

        channel_lower = channel.lower()
        if channel_lower in ("r", "g", "b"):
            c_idx = {"r": 0, "g": 1, "b": 2}[channel_lower]
            c_plane = ((arr[:, :, c_idx] & mask) * scale).astype(np.uint8)
            return Image.fromarray(c_plane, mode="L")
        elif channel_lower == "gray":
            gray = np.array(Image.fromarray(arr).convert("L"), dtype=np.uint8)
            gray_plane = ((gray & mask) * scale).astype(np.uint8)
            return Image.fromarray(gray_plane, mode="L")
        elif channel_lower == "combined":
            amplified_rgb = ((arr[:, :, :3] & mask) * scale).astype(np.uint8)
            return Image.fromarray(amplified_rgb, mode="RGB")
        else:
            raise ValueError(f"Unknown channel: {channel}. Expected 'r','g','b','gray','combined'.")


    @staticmethod
    def compute_entropy_statistics(image_input: Union[str, Image.Image]) -> EntropyStats:
        """
        Computes detailed Shannon entropy statistics for all channels and LSB plane.
        """
        img, arr = ImageForensics._to_rgb_array(image_input)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        gray = np.array(img.convert("L"))
        lsb_plane = arr & 1

        return EntropyStats(
            overall=round(calculate_entropy(arr), 4),
            red=round(calculate_entropy(r), 4),
            green=round(calculate_entropy(g), 4),
            blue=round(calculate_entropy(b), 4),
            grayscale=round(calculate_entropy(gray), 4),
            lsb_plane=round(calculate_entropy(lsb_plane), 4),
        )

    @staticmethod
    def chi_square_analysis(image_input: Union[str, Image.Image]) -> ChiSquareResult:
        r"""
        Performs Chi-Square ($\chi^2$) steganalysis on Pairs of Values (PoVs).
        Detects whether the LSB distribution exhibits artificial equalization.
        """
        _, arr = ImageForensics._to_rgb_array(image_input)
        # Flatten pixels across all RGB channels
        flat_pixels = arr.flatten()

        # Compute histogram of all 256 byte values
        hist = np.bincount(flat_pixels, minlength=256)

        chi2_sum = 0.0
        degrees_of_freedom = 0

        # Examine 128 Pairs of Values: (2k, 2k+1)
        for k in range(128):
            h_even = hist[2 * k]
            h_odd = hist[2 * k + 1]
            total_pair = h_even + h_odd
            if total_pair > 0:
                expected = total_pair / 2.0
                chi2_sum += ((h_even - expected) ** 2) / expected
                degrees_of_freedom += 1

        if degrees_of_freedom > 1:
            # Degrees of freedom is k - 1
            df = degrees_of_freedom - 1
            # Survival function sf = 1 - cdf
            # In LSB stego with equalized bits, chi2 is small -> p_value is high (close to 1.0)
            p_val = float(stats.chi2.sf(chi2_sum, df))
            
            # Probability that LSB data has been artificially embedded
            # When LSBs are randomized, p_value -> 1.0 (chi-square is very low relative to df)
            # In natural images with uneven PoVs, chi2 is large -> p_val is near 0.0
            stego_prob = (1.0 - p_val) if p_val < 0.5 else p_val
            # Scale to percentage
            if p_val > 0.90:
                stego_prob_pct = round(p_val * 100.0, 2)
                detected = True
                verdict = "Steganography Detected (High Statistical Confidence)"
            elif p_val > 0.60:
                stego_prob_pct = round(p_val * 100.0, 2)
                detected = True
                verdict = "Suspected Steganography (Moderate Likelihood)"
            else:
                stego_prob_pct = round((1.0 - p_val) * 30.0, 2)  # Natural baseline
                detected = False
                verdict = "Clean / Natural Image (No Anomaly Detected)"
        else:
            chi2_sum = 0.0
            df = 0
            p_val = 0.0
            stego_prob_pct = 0.0
            detected = False
            verdict = "Insufficient pixel variance for test"

        return ChiSquareResult(
            chi2_statistic=round(float(chi2_sum), 3),
            degrees_of_freedom=int(df),
            p_value=round(float(p_val), 6),
            stego_probability_pct=float(stego_prob_pct),
            is_stego_detected=detected,
            verdict=verdict,
        )

    @staticmethod
    def sample_pair_analysis(image_input: Union[str, Image.Image]) -> SamplePairResult:
        """
        Estimates embedding rate using Sample Pair Analysis (SPA).
        """
        _, arr = ImageForensics._to_rgb_array(image_input)
        flat = arr.flatten().astype(np.int32)
        total_samples = len(flat)

        if total_samples < 2:
            return SamplePairResult(0.0, 0, "Low")

        # Adjacent sample differences
        diffs = np.abs(flat[1:] - flat[:-1])
        even_diffs = np.sum((diffs % 2 == 0) & (diffs < 16))
        odd_diffs = np.sum((diffs % 2 != 0) & (diffs < 16))

        total_pairs = even_diffs + odd_diffs
        if total_pairs > 0:
            ratio = odd_diffs / total_pairs
            # In random stego, odd differences increase towards 50%
            est_rate = max(0.0, min(100.0, (ratio - 0.35) * 200.0))
        else:
            est_rate = 0.0

        est_payload_bytes = int((est_rate / 100.0) * (total_samples / 8))

        if est_rate > 50:
            confidence = "High"
        elif est_rate > 15:
            confidence = "Moderate"
        else:
            confidence = "Low"

        return SamplePairResult(
            estimated_embedding_rate_pct=round(float(est_rate), 2),
            estimated_payload_bytes=est_payload_bytes,
            confidence_level=confidence,
        )

    @staticmethod
    def extract_metadata(image_path_or_img: Union[str, Image.Image]) -> ImageMetadataReport:
        """
        Extracts EXIF and PNG chunk metadata.
        """
        if isinstance(image_path_or_img, str):
            filename = os.path.basename(image_path_or_img)
            file_size = os.path.getsize(image_path_or_img) if os.path.exists(image_path_or_img) else 0
            img = Image.open(image_path_or_img)
        else:
            filename = "Memory_Image.png"
            file_size = 0
            img = image_path_or_img

        png_chunks: Dict[str, str] = {}
        exif_dict: Dict[str, str] = {}

        # Extract PNG chunks if present
        if hasattr(img, "text") and isinstance(img.text, dict):
            for k, v in img.text.items():
                png_chunks[str(k)] = str(v)

        if hasattr(img, "info") and isinstance(img.info, dict):
            for k, v in img.info.items():
                if k not in ("exif", "icc_profile"):
                    png_chunks[str(k)] = str(v)

        # Extract EXIF tags
        try:
            exif_raw = img.getexif()
            if exif_raw:
                for tag_id, value in exif_raw.items():
                    tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                    exif_dict[tag_name] = str(value)
        except Exception:
            pass

        return ImageMetadataReport(
            filename=filename,
            file_size_bytes=file_size,
            format=img.format or "PNG",
            dimensions=img.size,
            mode=img.mode,
            has_alpha="A" in img.mode,
            color_channels=len(img.getbands()),
            png_chunks=png_chunks,
            exif_data=exif_dict,
        )

    @classmethod
    def analyze_image(cls, image_input: Union[str, Image.Image]) -> ForensicAnalysisReport:
        """
        Runs comprehensive forensic pipeline and returns structured report.
        """
        filename = (
            os.path.basename(image_input) if isinstance(image_input, str) else "In-Memory Image"
        )
        metadata = cls.extract_metadata(image_input)
        entropy = cls.compute_entropy_statistics(image_input)
        chi2 = cls.chi_square_analysis(image_input)
        sample_pair = cls.sample_pair_analysis(image_input)

        # Determine overall risk and verdict
        if chi2.is_stego_detected:
            verdict = "Steganographic Data Detected"
            risk_level = "High"
            recommendations = [
                "Extract hidden content using CloakPix Decrypt with the authorized passphrase.",
                "Review visual LSB bit planes for pixel clustering and signature patterns.",
                "Isolate image file in secure evidence vault.",
            ]
        elif entropy.lsb_plane > 0.98:
            verdict = "High LSB Entropy Anomaly (Possible Stego)"
            risk_level = "Medium"
            recommendations = [
                "Perform sample pair and frequency domain steganalysis.",
                "Compare against pristine original carrier image if available.",
            ]
        else:
            verdict = "Clean / No Hidden Data Detected"
            risk_level = "Low"
            recommendations = [
                "Image appears pristine with natural LSB noise distribution.",
                "No further forensic intervention required.",
            ]

        return ForensicAnalysisReport(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            target_image=filename,
            metadata=metadata,
            entropy=entropy,
            chi_square=chi2,
            sample_pair=sample_pair,
            stego_detection_verdict=verdict,
            risk_level=risk_level,
            recommendations=recommendations,
        )

    @classmethod
    def export_report_json(cls, report: ForensicAnalysisReport, output_path: str) -> str:
        """Exports forensic report to JSON format."""
        data = asdict(report)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return output_path

    @classmethod
    def export_report_txt(cls, report: ForensicAnalysisReport, output_path: str) -> str:
        """Exports human-readable plain text forensic report."""
        lines = [
            "=" * 70,
            "               CLOAKPIX IMAGE FORENSIC REPORT",
            "=" * 70,
            f"Timestamp:       {report.timestamp}",
            f"Target Image:    {report.target_image}",
            f"Dimensions:      {report.metadata.dimensions[0]} x {report.metadata.dimensions[1]} px",
            f"Color Mode:      {report.metadata.mode} ({report.metadata.color_channels} channels)",
            f"File Size:       {report.metadata.file_size_bytes:,} bytes",
            "-" * 70,
            "1. STEGANALYSIS VERDICT & RISK ASSESSMENT",
            f"   Verdict:      {report.stego_detection_verdict}",
            f"   Risk Level:   {report.risk_level}",
            "-" * 70,
            "2. STATISTICAL STEGANALYSIS (CHI-SQUARE & SAMPLE PAIR)",
            f"   Chi-Square Stat:    {report.chi_square.chi2_statistic}",
            f"   Degrees of Freedom: {report.chi_square.degrees_of_freedom}",
            f"   P-Value:            {report.chi_square.p_value:.6f}",
            f"   Stego Probability:  {report.chi_square.stego_probability_pct}%",
            f"   Chi-Square Verdict: {report.chi_square.verdict}",
            f"   Est. Embedding Rate:{report.sample_pair.estimated_embedding_rate_pct}%",
            f"   Est. Payload Size:  {report.sample_pair.estimated_payload_bytes:,} bytes",
            "-" * 70,
            "3. SHANNON ENTROPY DISTRIBUTION",
            f"   Overall Entropy:    {report.entropy.overall} bits/symbol",
            f"   Red Channel:        {report.entropy.red} bits/symbol",
            f"   Green Channel:      {report.entropy.green} bits/symbol",
            f"   Blue Channel:       {report.entropy.blue} bits/symbol",
            f"   Grayscale:          {report.entropy.grayscale} bits/symbol",
            f"   LSB Bit-Plane:      {report.entropy.lsb_plane} bits/symbol",
            "-" * 70,
            "4. IMAGE METADATA & PNG CHUNKS",
        ]

        if report.metadata.png_chunks:
            for k, v in report.metadata.png_chunks.items():
                lines.append(f"   [PNG Chunk] {k}: {v}")
        else:
            lines.append("   No custom PNG chunk metadata found.")

        if report.metadata.exif_data:
            for k, v in report.metadata.exif_data.items():
                lines.append(f"   [EXIF] {k}: {v}")

        lines.extend([
            "-" * 70,
            "5. FORENSIC RECOMMENDATIONS",
        ])
        for rec in report.recommendations:
            lines.append(f"   * {rec}")

        lines.append("=" * 70)
        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    @classmethod
    def export_report_pdf(cls, report: ForensicAnalysisReport, output_path: str) -> str:
        """
        Exports a high-quality PDF forensic report using ReportLab.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        except ImportError:
            # Fallback to TXT if reportlab is unavailable
            return cls.export_report_txt(report, output_path.replace(".pdf", ".txt"))

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            alignment=1,  # Center
        )
        subtitle_style = ParagraphStyle(
            "SubtitleStyle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748b"),
            alignment=1,
        )
        section_style = ParagraphStyle(
            "SectionStyle",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=10,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyStyle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )
        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=styles["Normal"],
            fontSize=11,
            leading=14,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#b91c1c") if report.risk_level == "High" else colors.HexColor("#15803d"),
        )

        elements = []

        # Header
        elements.append(Paragraph("<b>CloakPix Forensic & Steganalysis Report</b>", title_style))
        elements.append(Paragraph(f"Generated: {report.timestamp} | Target: {report.target_image}", subtitle_style))
        elements.append(Spacer(1, 14))

        # Executive Summary Table
        summary_data = [
            [Paragraph("<b>Target Image:</b>", body_style), Paragraph(report.target_image, body_style)],
            [Paragraph("<b>Dimensions:</b>", body_style), Paragraph(f"{report.metadata.dimensions[0]} × {report.metadata.dimensions[1]} px ({report.metadata.mode})", body_style)],
            [Paragraph("<b>File Size:</b>", body_style), Paragraph(f"{report.metadata.file_size_bytes:,} bytes", body_style)],
            [Paragraph("<b>Stego Verdict:</b>", body_style), Paragraph(report.stego_detection_verdict, badge_style)],
            [Paragraph("<b>Risk Assessment:</b>", body_style), Paragraph(f"<b>{report.risk_level}</b>", badge_style)],
        ]
        summary_table = Table(summary_data, colWidths=[130, 410])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 12))

        # Statistical Steganalysis Table
        elements.append(Paragraph("Statistical Steganalysis (Chi-Square & Sample Pair)", section_style))
        stego_data = [
            [Paragraph("<b>Metric</b>", body_style), Paragraph("<b>Value</b>", body_style), Paragraph("<b>Interpretation</b>", body_style)],
            [Paragraph("Chi-Square (χ²)", body_style), Paragraph(str(report.chi_square.chi2_statistic), body_style), Paragraph("PoV distribution test statistic", body_style)],
            [Paragraph("p-value", body_style), Paragraph(f"{report.chi_square.p_value:.6f}", body_style), Paragraph("Probability under null hypothesis", body_style)],
            [Paragraph("Stego Probability", body_style), Paragraph(f"<b>{report.chi_square.stego_probability_pct}%</b>", body_style), Paragraph(report.chi_square.verdict, body_style)],
            [Paragraph("Est. Embedding Rate", body_style), Paragraph(f"{report.sample_pair.estimated_embedding_rate_pct}%", body_style), Paragraph(f"Confidence: {report.sample_pair.confidence_level}", body_style)],
        ]
        stego_table = Table(stego_data, colWidths=[130, 110, 300])
        stego_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(stego_table)
        elements.append(Spacer(1, 12))

        # Shannon Entropy Table
        elements.append(Paragraph("Shannon Entropy Analysis", section_style))
        entropy_data = [
            [Paragraph("<b>Channel / Plane</b>", body_style), Paragraph("<b>Entropy (bits/symbol)</b>", body_style), Paragraph("<b>Theoretical Max (8.0)</b>", body_style)],
            [Paragraph("Overall Image", body_style), Paragraph(f"{report.entropy.overall}", body_style), Paragraph(f"{(report.entropy.overall / 8.0) * 100:.1f}% capacity", body_style)],
            [Paragraph("Red Channel", body_style), Paragraph(f"{report.entropy.red}", body_style), Paragraph(f"{(report.entropy.red / 8.0) * 100:.1f}% capacity", body_style)],
            [Paragraph("Green Channel", body_style), Paragraph(f"{report.entropy.green}", body_style), Paragraph(f"{(report.entropy.green / 8.0) * 100:.1f}% capacity", body_style)],
            [Paragraph("Blue Channel", body_style), Paragraph(f"{report.entropy.blue}", body_style), Paragraph(f"{(report.entropy.blue / 8.0) * 100:.1f}% capacity", body_style)],
            [Paragraph("LSB Bit-Plane", body_style), Paragraph(f"<b>{report.entropy.lsb_plane}</b>", body_style), Paragraph("High entropy (>0.95) indicates stego payload", body_style)],
        ]
        entropy_table = Table(entropy_data, colWidths=[150, 150, 240])
        entropy_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(entropy_table)
        elements.append(Spacer(1, 12))

        # Recommendations
        elements.append(Paragraph("Forensic Recommendations", section_style))
        for rec in report.recommendations:
            elements.append(Paragraph(f"• {rec}", body_style))

        doc.build(elements)
        return output_path
