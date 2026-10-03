"""
Cryptographic module for SecureStego.
Implements AES-256-GCM authenticated encryption with PBKDF2 key derivation.
"""

from dataclasses import dataclass
import math
import re
from typing import Tuple

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes

from securestego.core.exceptions import (
    InvalidPasswordError,
    IntegrityCheckFailedError,
)

# Constants
KEY_SIZE_BYTES = 32          # 256-bit AES key
SALT_SIZE_BYTES = 16         # 128-bit PBKDF2 salt
NONCE_SIZE_BYTES = 12        # 96-bit standard GCM nonce
TAG_SIZE_BYTES = 16          # 128-bit GCM authentication tag
PBKDF2_ITERATIONS = 200_000  # High iteration count for resistance against brute force


@dataclass(frozen=True)
class EncryptedPayload:
    """Represents an encrypted payload with its cryptographic metadata."""
    salt: bytes
    nonce: bytes
    tag: bytes
    ciphertext: bytes

    @property
    def total_bytes(self) -> int:
        """Total byte length of the cryptographic payload."""
        return len(self.salt) + len(self.nonce) + len(self.tag) + len(self.ciphertext)


def derive_key(password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS) -> bytes:
    """
    Derives a 256-bit encryption key from a password and salt using PBKDF2-HMAC-SHA256.
    
    Args:
        password: User-provided passphrase.
        salt: Random 16-byte cryptographic salt.
        iterations: Number of PBKDF2 iterations.
        
    Returns:
        32-byte derived key.
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    if len(salt) != SALT_SIZE_BYTES:
        raise ValueError(f"Salt must be exactly {SALT_SIZE_BYTES} bytes.")

    return PBKDF2(
        password=password.encode("utf-8"),
        salt=salt,
        dkLen=KEY_SIZE_BYTES,
        count=iterations,
        hmac_hash_module=SHA256,
    )


def encrypt_payload(data: bytes, password: str, aad: bytes = b"") -> EncryptedPayload:
    """
    Encrypts raw bytes using AES-256-GCM with a PBKDF2-derived key.
    
    Args:
        data: Plaintext data bytes to encrypt.
        password: Passphrase for key derivation.
        aad: Optional additional authenticated data.
        
    Returns:
        EncryptedPayload containing salt, nonce, tag, and ciphertext.
    """
    if not data:
        raise ValueError("Cannot encrypt empty data.")

    salt = get_random_bytes(SALT_SIZE_BYTES)
    key = derive_key(password, salt)
    nonce = get_random_bytes(NONCE_SIZE_BYTES)

    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    if aad:
        cipher.update(aad)

    ciphertext, tag = cipher.encrypt_and_digest(data)

    return EncryptedPayload(
        salt=salt,
        nonce=nonce,
        tag=tag,
        ciphertext=ciphertext,
    )


def decrypt_payload(payload: EncryptedPayload, password: str, aad: bytes = b"") -> bytes:
    """
    Decrypts an EncryptedPayload using AES-256-GCM and verifies authenticity.
    
    Args:
        payload: EncryptedPayload structure.
        password: User-provided passphrase.
        aad: Additional authenticated data that was bound during encryption.
        
    Returns:
        Decrypted plaintext bytes.
        
    Raises:
        InvalidPasswordError: If the password is wrong or authentication fails.
        IntegrityCheckFailedError: If payload was tampered with.
    """
    if not password:
        raise InvalidPasswordError("Password cannot be empty.")

    key = derive_key(password, payload.salt)

    try:
        cipher = AES.new(key, AES.MODE_GCM, nonce=payload.nonce)
        if aad:
            cipher.update(aad)
        plaintext = cipher.decrypt_and_verify(payload.ciphertext, payload.tag)
        return plaintext
    except (ValueError, KeyError) as e:
        # AES-GCM raises ValueError on MAC/tag verification mismatch
        raise InvalidPasswordError(
            "Decryption failed: Invalid password or altered/corrupted data."
        ) from e


def evaluate_password_strength(password: str) -> Tuple[int, str, str]:
    """
    Evaluates password strength and returns (score_0_to_100, label, advice).
    
    Returns:
        Tuple of (score [0-100], level_label, advice_string)
    """
    if not password:
        return 0, "Empty", "Please enter a passphrase."

    length = len(password)
    has_lower = bool(re.search(r"[a-z]", password))
    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"\d", password))
    has_symbol = bool(re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", password))

    charset_size = 0
    if has_lower:
        charset_size += 26
    if has_upper:
        charset_size += 26
    if has_digit:
        charset_size += 10
    if has_symbol:
        charset_size += 33

    # Calculate Shannon/combinatorial entropy: L * log2(charset_size)
    if charset_size > 0:
        entropy = length * math.log2(charset_size)
    else:
        entropy = 0

    score = 0
    # Length score
    if length >= 16:
        score += 40
    elif length >= 12:
        score += 30
    elif length >= 8:
        score += 20
    else:
        score += 10

    # Diversity score
    types_count = sum([has_lower, has_upper, has_digit, has_symbol])
    score += types_count * 12

    # Entropy score
    if entropy >= 80:
        score += 20
    elif entropy >= 60:
        score += 15
    elif entropy >= 40:
        score += 10

    score = min(100, score)

    if score < 40:
        label = "Weak"
        advice = "Use at least 12 characters with uppercase, digits, and symbols."
    elif score < 70:
        label = "Moderate"
        advice = "Add more length and special characters to improve security."
    elif score < 90:
        label = "Strong"
        advice = "Good security level for confidential data."
    else:
        label = "Very Strong"
        advice = "Excellent passphrase entropy!"

    return score, label, advice
