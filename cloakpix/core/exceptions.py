"""
Exceptions module for CloakPix.
Provides structured and descriptive domain errors.
"""


class CloakPixError(Exception):
    """Base exception for all CloakPix errors."""
    pass


# Backward compatibility alias
SecureStegoError = CloakPixError


class InvalidPasswordError(CloakPixError):
    """Raised when password authentication fails or payload cannot be decrypted."""
    pass


class IntegrityCheckFailedError(CloakPixError):
    """Raised when cryptographic hash, GCM auth tag, or CRC header check fails."""
    pass


class CapacityOverflowError(CloakPixError):
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


class CorruptedImageError(CloakPixError):
    """Raised when carrier/stego image is corrupted or missing steganographic markers."""
    pass


class UnsupportedFormatError(CloakPixError):
    """Raised when an unsupported image format is provided (e.g. lossy JPEG)."""
    pass


# Alias for naming consistency
UnsupportedFileFormatError = UnsupportedFormatError


class PayloadNotFoundError(CloakPixError):
    """Raised when no CloakPix header is detected in the image."""
    pass

