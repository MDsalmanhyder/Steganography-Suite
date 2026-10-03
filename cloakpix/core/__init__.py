"""
Core module exports for CloakPix.
"""

from cloakpix.core.exceptions import (
    CloakPixError,
    SecureStegoError,
    InvalidPasswordError,
    IntegrityCheckFailedError,
    CapacityOverflowError,
    CorruptedImageError,
    UnsupportedFormatError,
    PayloadNotFoundError,
)
from cloakpix.core.crypto import (
    EncryptedPayload,
    derive_key,
    encrypt_payload,
    decrypt_payload,
    evaluate_password_strength,
)
from cloakpix.core.metrics import (
    calculate_mse,
    calculate_psnr,
    calculate_ssim,
    calculate_entropy,
    calculate_image_capacity,
)
from cloakpix.core.stego_engine import (
    StegoEngine,
    EmbeddingResult,
    ExtractionResult,
    StegoMetadata,
)
from cloakpix.core.forensics import (
    ImageForensics,
    EntropyStats,
    ChiSquareResult,
    SamplePairResult,
    ImageMetadataReport,
    ForensicAnalysisReport,
)
from cloakpix.core.file_manager import (
    FileManager,
    AuditLogger,
    AuditLogEntry,
)
from cloakpix.core.audio_stego import (
    AudioStegoEngine,
    AudioEmbeddingResult,
    AudioExtractionResult,
    calculate_audio_capacity,
    calculate_audio_snr,
)
from cloakpix.core.audio_forensics import (
    AudioForensics,
    AudioForensicReport,
    AudioEntropyStats,
    AudioMetadataReport,
)
from cloakpix.core.unified_engine import (
    UnifiedStegoEngine,
    UnifiedResult,
)
from cloakpix.core.bit_engine import (
    lsb_interleave_bytes,
    lsb_deinterleave_bytes,
    run_benchmark,
)

__all__ = [
    "CloakPixError",
    "SecureStegoError",
    "InvalidPasswordError",
    "IntegrityCheckFailedError",
    "CapacityOverflowError",
    "CorruptedImageError",
    "UnsupportedFormatError",
    "PayloadNotFoundError",
    "EncryptedPayload",
    "derive_key",
    "encrypt_payload",
    "decrypt_payload",
    "evaluate_password_strength",
    "calculate_mse",
    "calculate_psnr",
    "calculate_ssim",
    "calculate_entropy",
    "calculate_image_capacity",
    "StegoEngine",
    "EmbeddingResult",
    "ExtractionResult",
    "StegoMetadata",
    "ImageForensics",
    "EntropyStats",
    "ChiSquareResult",
    "SamplePairResult",
    "ImageMetadataReport",
    "ForensicAnalysisReport",
    "FileManager",
    "AuditLogger",
    "AuditLogEntry",
    "AudioStegoEngine",
    "AudioEmbeddingResult",
    "AudioExtractionResult",
    "calculate_audio_capacity",
    "calculate_audio_snr",
    "AudioForensics",
    "AudioForensicReport",
    "AudioEntropyStats",
    "AudioMetadataReport",
    "UnifiedStegoEngine",
    "UnifiedResult",
    "lsb_interleave_bytes",
    "lsb_deinterleave_bytes",
    "run_benchmark",
]

