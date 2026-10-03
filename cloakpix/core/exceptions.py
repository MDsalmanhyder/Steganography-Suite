"""
Exceptions module for SecureStego.
Provides structured and descriptive domain errors.
"""


class SecureStegoError(Exception):
    """Base exception for all SecureStego errors."""
    pass


class InvalidPasswordError(SecureStegoError):
    """Raised when password authentication fails or payload cannot be decrypted."""
    pass


class IntegrityCheckFailedError(SecureStegoError):
    """Raised when cryptographic hash, GCM auth tag, or CRC header check fails."""
    pass


class CapacityOverflowError(SecureStegoError):
    """Raised when data payload exceeds carrier image capacity."""
    def __init__(self, required_bytes: int, available_bytes: int, message: str = None):
        if not message:
            message = (
                f"Data size ({required_bytes:,} bytes) exceeds carrier image capacity "
                f"({available_bytes:,} bytes)."
            )
        super().__init__(message)
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes


class CorruptedImageError(SecureStegoError):
    """Raised when carrier/stego image is corrupted or missing steganographic markers."""
    pass


class UnsupportedFormatError(SecureStegoError):
    """Raised when an unsupported image format is provided (e.g. lossy JPEG)."""
    pass


class PayloadNotFoundError(SecureStegoError):
    """Raised when no SecureStego header is detected in the image."""
    pass
