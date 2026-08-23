"""
Steganography Engine for SecureStego.
High-performance LSB embedding and extraction powered by NumPy and Pillow.
Supports text and arbitrary binary files with AES-256-GCM encryption.
"""

import io
import os
import struct
import zlib
from dataclasses import dataclass
from typing import Optional, Tuple, Union
import numpy as np
from PIL import Image

from securestego.core.crypto import (
    EncryptedPayload,
    encrypt_payload,
    decrypt_payload,
    SALT_SIZE_BYTES,
    NONCE_SIZE_BYTES,
    TAG_SIZE_BYTES,
)
from securestego.core.exceptions import (
    CapacityOverflowError,
    CorruptedImageError,
    InvalidPasswordError,
    IntegrityCheckFailedError,
    PayloadNotFoundError,
    UnsupportedFormatError,
)
from securestego.core.metrics import (
    calculate_psnr,
    calculate_mse,
    calculate_ssim,
    calculate_image_capacity,
)

# Steganography Protocol Constants
MAGIC_HEADER = b"SECSTEG"  # 7 bytes
PROTOCOL_VERSION = 1       # 1 byte
TYPE_TEXT = 1              # Payload is UTF-8 text string
TYPE_FILE = 2              # Payload is binary file (PDF, DOCX, ZIP, etc.)


@dataclass
class StegoMetadata:
    """Metadata embedded in stego header."""
    version: int
    payload_type: int
    bits_per_channel: int
    filename: str
    payload_length: int
    salt: bytes
    nonce: bytes
    tag: bytes


@dataclass
class EmbeddingResult:
    """Result returned after successfully embedding data."""
    stego_image: Image.Image
    payload_bytes: int
    total_embedded_bytes: int
    capacity_used_pct: float
    psnr_db: float
    mse: float
    ssim: float
    bits_per_channel: int
    payload_type: str
    filename: Optional[str] = None


@dataclass
class ExtractionResult:
    """Result returned after successfully extracting and decrypting data."""
    payload_type: str  # "text" or "file"
    data: bytes
    text: Optional[str]
    filename: Optional[str]
    payload_size_bytes: int
    bits_per_channel: int
    verified_authentic: bool


class StegoEngine:
    """
    Core engine handling LSB embedding, extraction, and cryptographic binding.
    """

    def __init__(self, default_bits_per_channel: int = 1):
        if not (1 <= default_bits_per_channel <= 4):
            raise ValueError("bits_per_channel must be between 1 and 4.")
        self.default_bits_per_channel = default_bits_per_channel

    @staticmethod
    def _validate_image(image_input: Union[str, Image.Image]) -> Image.Image:
        """Validates and loads image as RGB or RGBA."""
        if isinstance(image_input, str):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Carrier image not found: {image_input}")
            img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            raise TypeError("Image input must be file path or PIL Image.")

        # Ensure image is in RGB or RGBA mode
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        return img

    @staticmethod
    def _bytes_to_bits(data: bytes, bits_per_chunk: int = 1) -> np.ndarray:
        """Converts bytes to numpy array of integer chunks (e.g. 1-bit or 2-bit values)."""
        byte_arr = np.frombuffer(data, dtype=np.uint8)
        # Unpack each byte into 8 bits (MSB to LSB)
        bits = np.unpackbits(byte_arr)
        
        if bits_per_chunk == 1:
            return bits

        # Group bits into chunks of bits_per_chunk
        pad_len = (bits_per_chunk - (len(bits) % bits_per_chunk)) % bits_per_chunk
        if pad_len > 0:
            bits = np.pad(bits, (0, pad_len), "constant")

        reshaped = bits.reshape(-1, bits_per_chunk)
        # Convert bit chunks to integer values
        weights = 1 << np.arange(bits_per_chunk - 1, -1, -1, dtype=np.uint8)
        chunks = np.dot(reshaped, weights).astype(np.uint8)
        return chunks

    @staticmethod
    def _bits_to_bytes(chunks: np.ndarray, bits_per_chunk: int = 1, num_bytes: Optional[int] = None) -> bytes:
        """Reconstructs byte sequence from chunks."""
        if bits_per_chunk == 1:
            packed = np.packbits(chunks)
            if num_bytes is not None:
                return packed[:num_bytes].tobytes()
            return packed.tobytes()

        # Convert chunk integers back to bits
        bit_matrix = []
        for i in range(bits_per_chunk - 1, -1, -1):
            bit_matrix.append((chunks >> i) & 1)
        bits = np.column_stack(bit_matrix).flatten()
        packed = np.packbits(bits)
        if num_bytes is not None:
            return packed[:num_bytes].tobytes()
        return packed.tobytes()

    def build_header(
        self,
        payload_type: int,
        bits_per_channel: int,
        filename: str,
        encrypted_payload: EncryptedPayload,
    ) -> bytes:
        """Constructs binary protocol header with CRC32 integrity check."""
        fn_bytes = filename.encode("utf-8") if filename else b""
        fn_len = len(fn_bytes)

        # Header payload without CRC:
        # MAGIC (7) + VERSION (1) + TYPE (1) + BPC (1) + FN_LEN (2) + FN_BYTES (N) +
        # PAYLOAD_LEN (8) + SALT (16) + NONCE (12) + TAG (16)
        raw_header = struct.pack(
            f">7sBBB H{fn_len}s Q",
            MAGIC_HEADER,
            PROTOCOL_VERSION,
            payload_type,
            bits_per_channel,
            fn_len,
            fn_bytes,
            len(encrypted_payload.ciphertext),
        ) + encrypted_payload.salt + encrypted_payload.nonce + encrypted_payload.tag

        crc = zlib.crc32(raw_header) & 0xFFFFFFFF
        full_header = raw_header + struct.pack(">I", crc)
        return full_header

    def parse_header_from_bytes(self, header_bytes: bytes) -> Tuple[StegoMetadata, int]:
        """
        Parses stego metadata from extracted header bytes.
        Returns (StegoMetadata, total_header_length_in_bytes).
        """
        if len(header_bytes) < 70:
            raise PayloadNotFoundError("Header is too short to contain valid stego metadata.")

        # Fixed pre-filename length: MAGIC(7) + VER(1) + TYPE(1) + BPC(1) + FN_LEN(2) = 12 bytes
        magic, version, ptype, bpc, fn_len = struct.unpack(">7sBBB H", header_bytes[:12])
        if magic != MAGIC_HEADER:
            raise PayloadNotFoundError("No SecureStego header detected in carrier image.")

        if version != PROTOCOL_VERSION:
            raise CorruptedImageError(f"Unsupported stego protocol version: {version}")

        idx = 12
        filename = ""
        if fn_len > 0:
            if len(header_bytes) < idx + fn_len:
                raise CorruptedImageError("Incomplete header: filename truncated.")
            filename = header_bytes[idx : idx + fn_len].decode("utf-8", errors="replace")
            idx += fn_len

        # Next fixed fields: PAYLOAD_LEN (8) + SALT(16) + NONCE(12) + TAG(16) + CRC(4) = 56 bytes
        fixed_trailer_len = 8 + SALT_SIZE_BYTES + NONCE_SIZE_BYTES + TAG_SIZE_BYTES + 4
        if len(header_bytes) < idx + fixed_trailer_len:
            raise CorruptedImageError("Incomplete header: metadata fields truncated.")

        payload_len = struct.unpack(">Q", header_bytes[idx : idx + 8])[0]
        idx += 8

        salt = header_bytes[idx : idx + SALT_SIZE_BYTES]
        idx += SALT_SIZE_BYTES

        nonce = header_bytes[idx : idx + NONCE_SIZE_BYTES]
        idx += NONCE_SIZE_BYTES

        tag = header_bytes[idx : idx + TAG_SIZE_BYTES]
        idx += TAG_SIZE_BYTES

        stored_crc = struct.unpack(">I", header_bytes[idx : idx + 4])[0]
        idx += 4
        total_header_bytes = idx

        # Verify CRC32
        computed_crc = zlib.crc32(header_bytes[: idx - 4]) & 0xFFFFFFFF
        if stored_crc != computed_crc:
            raise IntegrityCheckFailedError(
                "Stego header CRC32 check failed! The image data has been modified or corrupted."
            )

        metadata = StegoMetadata(
            version=version,
            payload_type=ptype,
            bits_per_channel=bpc,
            filename=filename,
            payload_length=payload_len,
            salt=salt,
            nonce=nonce,
            tag=tag,
        )
        return metadata, total_header_bytes

    def embed(
        self,
        carrier_input: Union[str, Image.Image],
        password: str,
        secret_text: Optional[str] = None,
        secret_file_path: Optional[str] = None,
        secret_file_bytes: Optional[bytes] = None,
        secret_filename: Optional[str] = None,
        bits_per_channel: Optional[int] = None,
    ) -> EmbeddingResult:
        """
        Embeds encrypted secret text or binary file into carrier image using LSB.
        
        Args:
            carrier_input: File path or PIL Image.
            password: User encryption passphrase.
            secret_text: Text string to hide.
            secret_file_path: Path to binary file to hide.
            secret_file_bytes: Raw bytes of binary file to hide.
            secret_filename: Optional name for binary file.
            bits_per_channel: 1, 2, 3, or 4 LSB bits per channel.
            
        Returns:
            EmbeddingResult containing modified image and quality metrics.
        """
        if not password:
            raise InvalidPasswordError("A passphrase is required to encrypt the secret payload.")

        # Determine payload type and prepare raw data
        if secret_text is not None:
            payload_type = TYPE_TEXT
            raw_data = secret_text.encode("utf-8")
            filename = ""
            payload_type_str = "text"
        elif secret_file_path is not None:
            payload_type = TYPE_FILE
            if not os.path.exists(secret_file_path):
                raise FileNotFoundError(f"Secret file not found: {secret_file_path}")
            with open(secret_file_path, "rb") as f:
                raw_data = f.read()
            filename = os.path.basename(secret_file_path)
            payload_type_str = "file"
        elif secret_file_bytes is not None:
            payload_type = TYPE_FILE
            raw_data = secret_file_bytes
            filename = secret_filename or "hidden_file.bin"
            payload_type_str = "file"
        else:
            raise ValueError("Must provide either secret_text, secret_file_path, or secret_file_bytes.")

        if len(raw_data) == 0:
            raise ValueError("Secret payload cannot be empty.")

        bpc = bits_per_channel or self.default_bits_per_channel
        if not (1 <= bpc <= 4):
            raise ValueError("bits_per_channel must be between 1 and 4.")

        # Encrypt payload with AES-256-GCM
        encrypted_payload = encrypt_payload(raw_data, password)

        # Build protocol header
        header = self.build_header(
            payload_type=payload_type,
            bits_per_channel=bpc,
            filename=filename,
            encrypted_payload=encrypted_payload,
        )

        full_stream = header + encrypted_payload.ciphertext
        total_stream_bytes = len(full_stream)

        # Prepare carrier image
        original_img = self._validate_image(carrier_input)
        img_arr = np.array(original_img, dtype=np.uint8)
        orig_shape = img_arr.shape

        # We embed across RGB channels (ignoring Alpha channel if RGBA to preserve transparency)
        if len(orig_shape) == 3 and orig_shape[2] == 4:
            # RGBA: embed in RGB (first 3 channels)
            channels_to_embed = 3
            carrier_rgb = img_arr[:, :, :3]
            alpha_channel = img_arr[:, :, 3]
            is_rgba = True
        elif len(orig_shape) == 3 and orig_shape[2] == 3:
            # RGB
            channels_to_embed = 3
            carrier_rgb = img_arr
            is_rgba = False
        else:
            # Grayscale or other
            img_arr = np.array(original_img.convert("RGB"), dtype=np.uint8)
            channels_to_embed = 3
            carrier_rgb = img_arr
            is_rgba = False

        height, width, _ = carrier_rgb.shape
        capacity_info = calculate_image_capacity(width, height, channels=3, bits_per_channel=bpc)
        max_bytes = capacity_info["raw_capacity_bytes"]

        if total_stream_bytes > max_bytes:
            raise CapacityOverflowError(
                required_bytes=total_stream_bytes,
                available_bytes=max_bytes,
            )

        # Flatten RGB channels to 1D array
        flat_carrier = carrier_rgb.reshape(-1)
        
        # Convert byte stream to bit chunks for embedding
        chunks_to_embed = self._bytes_to_bits(full_stream, bits_per_chunk=bpc)
        num_chunks = len(chunks_to_embed)

        # Embed into LSBs using vectorized numpy operations
        mask = (1 << bpc) - 1
        inv_mask = np.uint8((~mask) & 0xFF)

        # Modify only the required slice of pixels
        modified_carrier = flat_carrier.copy()
        carrier_slice = modified_carrier[:num_chunks]
        modified_slice = (carrier_slice & inv_mask) | chunks_to_embed
        modified_carrier[:num_chunks] = modified_slice

        # Reshape back to image dimensions
        modified_rgb = modified_carrier.reshape((height, width, 3))

        if is_rgba:
            stego_arr = np.dstack((modified_rgb, alpha_channel))
            stego_image = Image.fromarray(stego_arr, mode="RGBA")
        else:
            stego_arr = modified_rgb
            stego_image = Image.fromarray(stego_arr, mode="RGB")

        # Calculate metrics
        psnr_val = calculate_psnr(original_img, stego_image)
        mse_val = calculate_mse(original_img, stego_image)
        ssim_val = calculate_ssim(original_img, stego_image)
        capacity_used_pct = (total_stream_bytes / max_bytes) * 100.0

        return EmbeddingResult(
            stego_image=stego_image,
            payload_bytes=len(raw_data),
            total_embedded_bytes=total_stream_bytes,
            capacity_used_pct=round(capacity_used_pct, 2),
            psnr_db=round(psnr_val, 2),
            mse=round(mse_val, 4),
            ssim=round(ssim_val, 6),
            bits_per_channel=bpc,
            payload_type=payload_type_str,
            filename=filename if payload_type == TYPE_FILE else None,
        )

    def extract(
        self,
        stego_input: Union[str, Image.Image],
        password: str,
    ) -> ExtractionResult:
        """
        Extracts and decrypts hidden payload from stego image.
        Automatically probes bits-per-channel configurations (1-4 LSBs).
        
        Args:
            stego_input: Path to stego image or PIL Image object.
            password: Passphrase used during embedding.
            
        Returns:
            ExtractionResult containing decrypted data, text, filename, and verification status.
        """
        if not password:
            raise InvalidPasswordError("A passphrase is required to decrypt the hidden data.")

        img = self._validate_image(stego_input)
        img_arr = np.array(img, dtype=np.uint8)

        if len(img_arr.shape) == 3 and img_arr.shape[2] >= 3:
            carrier_rgb = img_arr[:, :, :3]
        else:
            carrier_rgb = np.array(img.convert("RGB"), dtype=np.uint8)

        flat_carrier = carrier_rgb.reshape(-1)

        # Probe bits-per-channel configurations (1 to 4 LSBs) to find valid SECSTEG header
        detected_metadata: Optional[StegoMetadata] = None
        detected_bpc: Optional[int] = None
        detected_header_bytes: Optional[int] = None

        # Sample first 2048 bytes of channel data for header parsing
        max_header_probe_bytes = 1024

        for candidate_bpc in (1, 2, 3, 4):
            mask = (1 << candidate_bpc) - 1
            # Number of chunks needed for probe
            chunks_needed = (max_header_probe_bytes * 8) // candidate_bpc
            if chunks_needed > len(flat_carrier):
                continue

            extracted_chunks = flat_carrier[:chunks_needed] & mask
            extracted_header_raw = self._bits_to_bytes(
                extracted_chunks,
                bits_per_chunk=candidate_bpc,
                num_bytes=max_header_probe_bytes,
            )

            try:
                metadata, header_len = self.parse_header_from_bytes(extracted_header_raw)
                if metadata.bits_per_channel == candidate_bpc:
                    detected_metadata = metadata
                    detected_bpc = candidate_bpc
                    detected_header_bytes = header_len
                    break
            except (PayloadNotFoundError, CorruptedImageError, IntegrityCheckFailedError):
                continue

        if not detected_metadata or detected_bpc is None or detected_header_bytes is None:
            raise PayloadNotFoundError(
                "No valid SecureStego data found in this image, or the image header was corrupted."
            )

        # We have the metadata! Calculate total required bytes (header + ciphertext)
        total_stream_bytes = detected_header_bytes + detected_metadata.payload_length
        total_chunks_needed = (total_stream_bytes * 8 + detected_bpc - 1) // detected_bpc

        if total_chunks_needed > len(flat_carrier):
            raise CorruptedImageError("Image is too small to contain the full reported stego payload.")

        # Extract full bit stream
        mask = (1 << detected_bpc) - 1
        full_chunks = flat_carrier[:total_chunks_needed] & mask
        full_extracted_bytes = self._bits_to_bytes(
            full_chunks,
            bits_per_chunk=detected_bpc,
            num_bytes=total_stream_bytes,
        )

        # Slice ciphertext
        ciphertext = full_extracted_bytes[detected_header_bytes : total_stream_bytes]

        if len(ciphertext) != detected_metadata.payload_length:
            raise CorruptedImageError("Ciphertext length mismatch during extraction.")

        encrypted_payload = EncryptedPayload(
            salt=detected_metadata.salt,
            nonce=detected_metadata.nonce,
            tag=detected_metadata.tag,
            ciphertext=ciphertext,
        )

        # Decrypt payload using AES-256-GCM
        decrypted_bytes = decrypt_payload(encrypted_payload, password)

        # Format result
        if detected_metadata.payload_type == TYPE_TEXT:
            try:
                text_content = decrypted_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text_content = decrypted_bytes.decode("latin-1", errors="replace")
            payload_type_str = "text"
            filename = None
        else:
            text_content = None
            payload_type_str = "file"
            filename = detected_metadata.filename or "extracted_file.bin"

        return ExtractionResult(
            payload_type=payload_type_str,
            data=decrypted_bytes,
            text=text_content,
            filename=filename,
            payload_size_bytes=len(decrypted_bytes),
            bits_per_channel=detected_bpc,
            verified_authentic=True,
        )
