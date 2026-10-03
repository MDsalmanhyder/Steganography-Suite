"""
Unified Steganography Engine for CloakPix.
Automatically detects whether carrier is Image (.png, .bmp, .tiff, .webp) or Audio (.wav),
dispatching to the appropriate engine with consistent AES-256-GCM encryption.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
from PIL import Image

from cloakpix.core.stego_engine import StegoEngine, EmbeddingResult, ExtractionResult
from cloakpix.core.audio_stego import (
    AudioStegoEngine,
    AudioEmbeddingResult,
    AudioExtractionResult,
    calculate_audio_capacity,
)
from cloakpix.core.file_manager import FileManager
from cloakpix.core.metrics import calculate_image_capacity
from cloakpix.core.exceptions import UnsupportedFormatError


AUDIO_EXTENSIONS = {".wav"}
IMAGE_EXTENSIONS = {".png", ".bmp", ".tiff", ".tif", ".webp"}


@dataclass
class UnifiedEmbeddingResult:
    carrier_type: str  # "image" or "audio"
    payload_type: str  # "text" or "file"
    payload_bytes: int
    total_embedded_bytes: int
    capacity_used_pct: float
    bits_per_channel: int
    psnr_db: Optional[float] = None
    mse: Optional[float] = None
    ssim: Optional[float] = None
    snr_db: Optional[float] = None
    stego_image: Optional[Image.Image] = None
    audio_samples: Optional[bytes] = None
    audio_params: Optional[Any] = None
    carrier_format: Optional[str] = None
    raw_result: Optional[Any] = None

    @property
    def fidelity_metric_name(self) -> str:
        return "Audio SNR" if self.carrier_type == "audio" else "Image PSNR"

    @property
    def fidelity_value(self) -> float:
        return self.snr_db if self.carrier_type == "audio" else (self.psnr_db or 0.0)


@dataclass
class UnifiedExtractionResult:
    carrier_type: str  # "image" or "audio"
    payload_type: str  # "text" or "file"
    data: bytes
    text: Optional[str] = None
    filename: Optional[str] = None
    payload_size_bytes: int = 0
    bits_per_channel: int = 1
    carrier_format: Optional[str] = None
    raw_result: Optional[Any] = None

    @property
    def bits_per_sample(self) -> int:
        return self.bits_per_channel


# Alias for backward compatibility
UnifiedResult = UnifiedEmbeddingResult


class UnifiedStegoEngine:
    """
    Intelligent high-level dispatcher for both Image and Audio steganography.
    """

    def __init__(self, default_bits: int = 1):
        self.image_engine = StegoEngine(default_bits_per_channel=default_bits)
        self.audio_engine = AudioStegoEngine(default_bits_per_sample=default_bits)

    @staticmethod
    def is_audio_carrier(carrier_path_or_obj: Union[str, Any]) -> bool:
        """Determines if the carrier is a WAV audio file."""
        if isinstance(carrier_path_or_obj, str):
            ext = os.path.splitext(carrier_path_or_obj)[1].lower()
            return ext in AUDIO_EXTENSIONS
        return False

    @staticmethod
    def is_image_carrier(carrier_path_or_obj: Union[str, Any]) -> bool:
        """Determines if the carrier is a supported image file or PIL Image."""
        if isinstance(carrier_path_or_obj, Image.Image):
            return True
        if isinstance(carrier_path_or_obj, str):
            ext = os.path.splitext(carrier_path_or_obj)[1].lower()
            return ext in IMAGE_EXTENSIONS
        return False

    def calculate_capacity(
        self,
        carrier_input: Union[str, Image.Image],
        bits: int = 1,
    ) -> Dict[str, Any]:
        """Calculates hiding capacity for either Image or Audio carrier."""
        if self.is_audio_carrier(carrier_input):
            info = calculate_audio_capacity(carrier_input, bits_per_sample=bits)
            info["carrier_type"] = "audio"
            return info
        elif self.is_image_carrier(carrier_input):
            if isinstance(carrier_input, str):
                img = Image.open(carrier_input)
            else:
                img = carrier_input
            w, h = img.size
            channels = len(img.getbands())
            channels_used = 4 if img.mode == "RGBA" else 3 if channels >= 3 else 1
            info = calculate_image_capacity(w, h, channels=channels_used, bits_per_channel=bits)
            info["carrier_type"] = "image"
            info["dimensions"] = (w, h)
            info["mode"] = img.mode
            return info
        else:
            raise UnsupportedFormatError(
                f"Unsupported carrier format. Supported carriers: Image ({', '.join(IMAGE_EXTENSIONS)}) "
                f"and Audio ({', '.join(AUDIO_EXTENSIONS)})."
            )

    def embed(
        self,
        carrier_input: Union[str, Image.Image],
        password: str,
        secret_text: Optional[str] = None,
        secret_file_path: Optional[str] = None,
        secret_bytes: Optional[bytes] = None,
        secret_filename: Optional[str] = None,
        bits_per_channel: int = 1,
        bits: Optional[int] = None,
        compress: bool = False,
        output_path: Optional[str] = None,
    ) -> UnifiedEmbeddingResult:
        """Embeds data into either Image or Audio carrier."""
        bpc = bits if bits is not None else bits_per_channel

        if self.is_audio_carrier(carrier_input):
            res: AudioEmbeddingResult = self.audio_engine.embed(
                carrier_input=carrier_input,
                password=password,
                secret_text=secret_text,
                secret_file_path=secret_file_path,
                secret_bytes=secret_bytes,
                secret_filename=secret_filename,
                bits_per_sample=bpc,
                output_path=output_path,
                compress=compress,
            )
            return UnifiedEmbeddingResult(
                carrier_type="audio",
                payload_type=res.payload_type,
                payload_bytes=res.payload_bytes,
                total_embedded_bytes=res.total_embedded_bytes,
                capacity_used_pct=res.capacity_used_pct,
                bits_per_channel=res.bits_per_sample,
                snr_db=res.snr_db,
                audio_samples=res.audio_samples,
                audio_params=res.audio_params,
                carrier_format="WAV",
                raw_result=res,
            )
        elif self.is_image_carrier(carrier_input):
            res: EmbeddingResult = self.image_engine.embed(
                carrier_input=carrier_input,
                password=password,
                secret_text=secret_text,
                secret_file_path=secret_file_path,
                secret_file_bytes=secret_bytes,
                secret_filename=secret_filename,
                bits_per_channel=bpc,
                compress=compress,
            )
            return UnifiedEmbeddingResult(
                carrier_type="image",
                payload_type=res.payload_type,
                payload_bytes=res.payload_bytes,
                total_embedded_bytes=res.total_embedded_bytes,
                capacity_used_pct=res.capacity_used_pct,
                bits_per_channel=res.bits_per_channel,
                psnr_db=res.psnr_db,
                mse=res.mse,
                ssim=res.ssim,
                stego_image=res.stego_image,
                carrier_format=getattr(res, "carrier_format", "PNG"),
                raw_result=res,
            )
        else:
            raise UnsupportedFormatError(
                f"Unsupported carrier format. Please select an image ({', '.join(IMAGE_EXTENSIONS)}) "
                f"or WAV audio ({', '.join(AUDIO_EXTENSIONS)})."
            )

    def extract(
        self,
        stego_input: Union[str, Image.Image],
        password: str,
    ) -> UnifiedExtractionResult:
        """Extracts and verifies payload from Image or Audio stego carrier."""
        if self.is_audio_carrier(stego_input):
            res: AudioExtractionResult = self.audio_engine.extract(stego_input, password=password)
            return UnifiedExtractionResult(
                carrier_type="audio",
                payload_type=res.payload_type,
                data=res.data,
                text=res.text,
                filename=res.filename,
                payload_size_bytes=res.payload_size_bytes,
                bits_per_channel=res.bits_per_sample,
                carrier_format="WAV",
                raw_result=res,
            )
        else:
            res: ExtractionResult = self.image_engine.extract(stego_input, password=password)
            return UnifiedExtractionResult(
                carrier_type="image",
                payload_type=res.payload_type,
                data=res.data,
                text=res.text,
                filename=res.filename,
                payload_size_bytes=res.payload_size_bytes,
                bits_per_channel=res.bits_per_channel,
                carrier_format="Image",
                raw_result=res,
            )

    @staticmethod
    def save_stego_carrier(result: UnifiedEmbeddingResult, output_path: str) -> None:
        """Saves embedding result to either audio WAV or image file format."""
        if result.carrier_type == "audio":
            if result.audio_samples is not None and result.audio_params is not None:
                FileManager.save_stego_audio(result.audio_samples, result.audio_params, output_path)
            else:
                raise ValueError("No audio sample data available in result.")
        else:
            if result.stego_image is not None:
                FileManager.save_stego_image(result.stego_image, output_path)
            else:
                raise ValueError("No stego image available in result.")
