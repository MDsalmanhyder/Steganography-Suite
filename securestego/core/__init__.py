"""
Core module exports for SecureStego.
"""

from securestego.core.exceptions import (
    SecureStegoError,
    InvalidPasswordError,
    IntegrityCheckFailedError,
    CapacityOverflowError,
    CorruptedImageError,
    UnsupportedFormatError,
    PayloadNotFoundError,
)
from securestego.core.crypto import (
    EncryptedPayload,
    derive_key,
    encrypt_payload,
    decrypt_payload,
    evaluate_password_strength,
)
from securestego.core.metrics import (
    calculate_mse,
    calculate_psnr,
    calculate_ssim,
    calculate_entropy,
    calculate_image_capacity,
)
from securestego.core.stego_engine import (
    StegoEngine,
    EmbeddingResult,
    ExtractionResult,
    StegoMetadata,
)
from securestego.core.forensics import (
    ImageForensics,
    EntropyStats,
    ChiSquareResult,
    SamplePairResult,
    ImageMetadataReport,
    ForensicAnalysisReport,
)
from securestego.core.file_manager import (
    FileManager,
    AuditLogger,
    AuditLogEntry,
)

__all__ = [
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
]
