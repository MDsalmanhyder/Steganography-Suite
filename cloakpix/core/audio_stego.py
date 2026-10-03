"""
Audio Steganography Engine for CloakPix.
High-performance LSB audio steganography for uncompressed PCM WAV files (.wav).
Protects payloads with AES-256-GCM authenticated encryption and PBKDF2 key derivation.
Inspired by and improving upon WavSteg with cryptographic authenticity and automated header probing.
"""

import io
import math
import os
import struct
import wave
import zlib
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np

from cloakpix.core.crypto import (
    EncryptedPayload,
    encrypt_payload,
    decrypt_payload,
    SALT_SIZE_BYTES,
    NONCE_SIZE_BYTES,
    TAG_SIZE_BYTES,
)
from cloakpix.core.exceptions import (
    CapacityOverflowError,
    CorruptedImageError,
    InvalidPasswordError,
    IntegrityCheckFailedError,
    PayloadNotFoundError,
    UnsupportedFormatError,
)
from cloakpix.core.stego_engine import (
    MAGIC_HEADER,
    PROTOCOL_VERSION,
    TYPE_TEXT,
    TYPE_FILE,
    StegoMetadata,
)


@dataclass
class AudioEmbeddingResult:
    """Results returned after embedding payload into an audio carrier."""
    stego_wav_bytes: bytes
    payload_type: str
    payload_bytes: int
    total_embedded_bytes: int
    capacity_used_pct: float
    snr_db: float
    sample_rate: int
    channels: int
    bits_per_sample: int
    audio_samples: bytes = b""
    audio_params: Any = None


@dataclass
class AudioExtractionResult:
    """Results returned after extracting payload from a stego audio carrier."""
    payload_type: str
    data: bytes
    text: Optional[str]
    filename: Optional[str]
    payload_size_bytes: int
    bits_per_sample: int
    verified_authentic: bool


def calculate_audio_capacity(
    wav_input: Union[str, bytes],
    bits_per_sample: int = 1,
) -> Dict[str, Union[int, float, str]]:
    """
    Calculates data hiding capacity for a WAV audio file.
    
    Args:
        wav_input: File path or raw bytes of a WAV audio file.
        bits_per_sample: Number of LSB bits used per audio sample (1 to 4).
        
    Returns:
        Dict with total samples, sample rate, channels, raw capacity, usable capacity, duration.
    """
    if isinstance(wav_input, (bytes, bytearray)):
        wf = wave.open(io.BytesIO(wav_input), "rb")
    elif isinstance(wav_input, str):
        if not os.path.exists(wav_input):
            raise FileNotFoundError(f"Audio file not found: {wav_input}")
        wf = wave.open(wav_input, "rb")
    else:
        raise TypeError("wav_input must be a file path string or bytes.")

    with wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        comptype = wf.getcomptype()

    if comptype != "NONE":
        raise UnsupportedFormatError(f"Compressed WAV formats ({comptype}) are not supported. Use uncompressed PCM.")

    total_samples = n_frames * n_channels
    duration_sec = n_frames / float(framerate) if framerate > 0 else 0.0

    raw_capacity_bits = total_samples * bits_per_sample
    raw_capacity_bytes = raw_capacity_bits // 8

    # Reserve ~128 bytes for header, crypto salt, nonce, tag, filename
    usable_capacity_bytes = max(0, raw_capacity_bytes - 128)

    return {
        "channels": n_channels,
        "sample_width_bytes": sampwidth,
        "sample_rate_hz": framerate,
        "total_frames": n_frames,
        "total_samples": total_samples,
        "duration_seconds": round(duration_sec, 2),
        "bits_per_sample": sampwidth * 8,
        "sample_bit_depth": sampwidth * 8,
        "audio_bit_depth": sampwidth * 8,
        "embedding_bits": bits_per_sample,
        "raw_capacity_bytes": raw_capacity_bytes,
        "usable_capacity_bytes": usable_capacity_bytes,
    }


def calculate_audio_snr(
    carrier_samples: np.ndarray,
    stego_samples: np.ndarray,
) -> float:
    """
    Computes the Signal-to-Noise Ratio (SNR) in dB between carrier and stego audio.
    Higher values indicate superior fidelity (typically > 60-80 dB is CD quality).
    """
    signal = carrier_samples.astype(np.float64)
    noise = (stego_samples.astype(np.float64) - signal)

    signal_power = np.mean(signal ** 2)
    noise_power = np.mean(noise ** 2)

    if noise_power == 0:
        return float("inf")  # Perfect fidelity / identical samples
    if signal_power == 0:
        return 0.0

    snr = 10.0 * math.log10(signal_power / noise_power)
    return float(round(snr, 2))


class AudioStegoEngine:
    """
    Engine for concealing and extracting encrypted data inside PCM WAV audio.
    """

    def __init__(self, default_bits_per_sample: int = 1):
        if not 1 <= default_bits_per_sample <= 4:
            raise ValueError("Bits per sample must be between 1 and 4.")
        self.default_bits_per_sample = default_bits_per_sample

    def _read_wav(
        self,
        wav_input: Union[str, bytes],
    ) -> Tuple[wave._wave_params, np.ndarray]:
        """Reads WAV file and returns wave parameters and numpy sample array."""
        if isinstance(wav_input, (bytes, bytearray)):
            f = io.BytesIO(wav_input)
        elif isinstance(wav_input, str):
            if not os.path.exists(wav_input):
                raise FileNotFoundError(f"Carrier WAV not found: {wav_input}")
            f = open(wav_input, "rb")
        else:
            raise TypeError("wav_input must be a file path string or bytes.")

        with wave.open(f, "rb") as wf:
            params = wf.getparams()
            raw_frames = wf.readframes(params.nframes)

        sampwidth = params.sampwidth
        if sampwidth == 1:
            dtype = np.uint8
        elif sampwidth == 2:
            dtype = np.int16
        elif sampwidth == 4:
            dtype = np.int32
        else:
            raise UnsupportedFormatError(f"Unsupported WAV sample width: {sampwidth} bytes (only 8, 16, 32-bit PCM supported).")

        samples = np.frombuffer(raw_frames, dtype=dtype)
        return params, samples

    def _write_wav(
        self,
        params: wave._wave_params,
        samples: np.ndarray,
        output_path: Optional[str] = None,
    ) -> bytes:
        """Writes numpy sample array to WAV format bytes and optional file."""
        out_buf = io.BytesIO()
        with wave.open(out_buf, "wb") as wf:
            wf.setparams(params)
            wf.writeframes(samples.tobytes())

        wav_bytes = out_buf.getvalue()
        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(wav_bytes)

        return wav_bytes

    @staticmethod
    def save_audio(
        samples_or_result_or_bytes: Any,
        params_or_path: Any = None,
        output_path: Optional[str] = None,
    ) -> None:
        """Writes audio samples or complete WAV bytes to a file."""
        if isinstance(samples_or_result_or_bytes, AudioEmbeddingResult):
            dest = params_or_path
            os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(samples_or_result_or_bytes.stego_wav_bytes)
            return

        if output_path is None:
            dest = params_or_path
            os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(samples_or_result_or_bytes)
        else:
            dest = output_path
            params = params_or_path
            os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
            raw_bytes = (
                samples_or_result_or_bytes
                if isinstance(samples_or_result_or_bytes, (bytes, bytearray))
                else samples_or_result_or_bytes.tobytes()
            )
            with wave.open(dest, "wb") as wf:
                wf.setparams(params)
                wf.writeframes(raw_bytes)

    def embed(
        self,
        carrier_input: Optional[Union[str, bytes]] = None,
        password: str = "",
        secret_text: Optional[str] = None,
        secret_file_path: Optional[str] = None,
        secret_bytes: Optional[bytes] = None,
        secret_filename: Optional[str] = None,
        bits_per_sample: Optional[int] = None,
        output_path: Optional[str] = None,
        compress: bool = False,
        wav_path: Optional[str] = None,
    ) -> AudioEmbeddingResult:
        """
        Embeds an encrypted payload into a WAV audio file.
        """
        carrier = carrier_input or wav_path
        if carrier is None:
            raise ValueError("carrier_input or wav_path must be provided.")
        carrier_input = carrier
        bpc = bits_per_sample or self.default_bits_per_sample
        if not 1 <= bpc <= 4:
            raise ValueError("Bits per sample must be between 1 and 4.")

        # Resolve payload
        if secret_text is not None:
            raw_payload = secret_text.encode("utf-8")
            payload_type = TYPE_TEXT
            filename = ""
        elif secret_file_path is not None:
            if not os.path.exists(secret_file_path):
                raise FileNotFoundError(f"Secret payload file not found: {secret_file_path}")
            with open(secret_file_path, "rb") as f:
                raw_payload = f.read()
            payload_type = TYPE_FILE
            filename = os.path.basename(secret_file_path)
        elif secret_bytes is not None:
            raw_payload = secret_bytes
            payload_type = TYPE_FILE
            filename = secret_filename or "payload.bin"
        else:
            raise ValueError("Must provide secret_text, secret_file_path, or secret_bytes.")

        # Optional pre-compression
        if compress:
            raw_payload = zlib.compress(raw_payload, level=9)

        # Encrypt with AES-256-GCM
        enc = encrypt_payload(raw_payload, password)

        # Build protocol header
        fn_bytes = filename.encode("utf-8")
        fn_len = len(fn_bytes)
        pre_crc_header = struct.pack(
            f">7sBBB H{fn_len}sQ16s12s16s",
            MAGIC_HEADER,
            PROTOCOL_VERSION,
            payload_type,
            bpc,
            fn_len,
            fn_bytes,
            len(enc.ciphertext),
            enc.salt,
            enc.nonce,
            enc.tag,
        )
        crc32_val = zlib.crc32(pre_crc_header) & 0xFFFFFFFF
        header = pre_crc_header + struct.pack(">I", crc32_val)

        full_stream = header + enc.ciphertext
        total_stream_bytes = len(full_stream)
        total_bits_needed = total_stream_bytes * 8
        total_samples_needed = (total_bits_needed + bpc - 1) // bpc

        # Read carrier WAV
        params, samples = self._read_wav(carrier_input)
        total_samples = len(samples)

        if total_samples_needed > total_samples:
            max_allowed = (total_samples * bpc) // 8
            raise CapacityOverflowError(
                required_bytes=total_stream_bytes,
                available_bytes=max_allowed,
                message=(
                    f"Payload stream ({total_stream_bytes:,} bytes) exceeds audio capacity "
                    f"({max_allowed:,} bytes at {bpc} bit(s)/sample)."
                ),
            )

        # Convert full_stream bytes to bits
        stream_arr = np.frombuffer(full_stream, dtype=np.uint8)
        bits = np.unpackbits(stream_arr)

        pad_len = (total_samples_needed * bpc) - len(bits)
        if pad_len > 0:
            bits = np.pad(bits, (0, pad_len), "constant", constant_values=0)

        chunks = bits.reshape(total_samples_needed, bpc)
        powers = (1 << np.arange(bpc - 1, -1, -1, dtype=np.uint8))
        chunk_vals = np.sum(chunks * powers, axis=1)

        # Embed into audio samples
        stego_samples = np.copy(samples)
        target = stego_samples[:total_samples_needed]
        mask = ~((1 << bpc) - 1)

        if samples.dtype == np.uint8:
            target[:] = (target & mask) | chunk_vals
        elif samples.dtype == np.int16:
            mask_16 = np.int16(mask)
            target[:] = (target & mask_16) | np.int16(chunk_vals)
        else:
            mask_32 = np.int32(mask)
            target[:] = (target & mask_32) | np.int32(chunk_vals)

        # Calculate SNR
        snr = calculate_audio_snr(samples, stego_samples)
        capacity_used = round((total_samples_needed / total_samples) * 100.0, 2)

        # Write stego WAV
        wav_bytes = self._write_wav(params, stego_samples, output_path)

        return AudioEmbeddingResult(
            stego_wav_bytes=wav_bytes,
            payload_type="text" if payload_type == TYPE_TEXT else "file",
            payload_bytes=len(raw_payload),
            total_embedded_bytes=total_stream_bytes,
            capacity_used_pct=capacity_used,
            snr_db=snr,
            sample_rate=params.framerate,
            channels=params.nchannels,
            bits_per_sample=bpc,
            audio_samples=stego_samples.tobytes(),
            audio_params=params,
        )

    def extract(
        self,
        stego_input: Optional[Union[str, bytes]] = None,
        password: str = "",
        decompress: bool = False,
        wav_path: Optional[str] = None,
    ) -> AudioExtractionResult:
        """
        Extracts and decrypts payload from a stego WAV audio file.
        """
        target = stego_input or wav_path
        if target is None:
            raise ValueError("stego_input or wav_path must be provided.")
        params, samples = self._read_wav(target)
        total_samples = len(samples)

        # Probe candidate bits-per-sample (1 to 4)
        detected_meta: Optional[StegoMetadata] = None
        detected_bpc: Optional[int] = None
        detected_header_bytes: Optional[int] = None

        max_probe_bytes = 1024
        from cloakpix.core.stego_engine import StegoEngine
        dummy_img_engine = StegoEngine()

        for cand_bpc in (1, 2, 3, 4):
            chunks_needed = (max_probe_bytes * 8) // cand_bpc
            if chunks_needed > total_samples:
                continue

            extracted_chunks = (samples[:chunks_needed] & ((1 << cand_bpc) - 1)).astype(np.uint8)
            extracted_header_raw = dummy_img_engine._bits_to_bytes(
                extracted_chunks,
                bits_per_chunk=cand_bpc,
                num_bytes=max_probe_bytes,
            )

            try:
                meta, h_len = dummy_img_engine.parse_header_from_bytes(extracted_header_raw)
                if meta.bits_per_channel == cand_bpc:
                    detected_meta = meta
                    detected_bpc = cand_bpc
                    detected_header_bytes = h_len
                    break
            except (PayloadNotFoundError, CorruptedImageError, IntegrityCheckFailedError):
                continue

        if not detected_meta or detected_bpc is None or detected_header_bytes is None:
            raise PayloadNotFoundError(
                "No valid CloakPix header detected in this audio file, or incorrect encryption format."
            )

        total_stream_bytes = detected_header_bytes + detected_meta.payload_length
        total_chunks_needed = (total_stream_bytes * 8 + detected_bpc - 1) // detected_bpc

        if total_chunks_needed > total_samples:
            raise CorruptedImageError("Audio file is too short to contain the full reported payload.")

        full_chunks = (samples[:total_chunks_needed] & ((1 << detected_bpc) - 1)).astype(np.uint8)
        full_extracted_bytes = dummy_img_engine._bits_to_bytes(
            full_chunks,
            bits_per_chunk=detected_bpc,
            num_bytes=total_stream_bytes,
        )

        ciphertext = full_extracted_bytes[detected_header_bytes : total_stream_bytes]
        if len(ciphertext) != detected_meta.payload_length:
            raise CorruptedImageError("Audio ciphertext length mismatch.")

        enc_payload = EncryptedPayload(
            salt=detected_meta.salt,
            nonce=detected_meta.nonce,
            tag=detected_meta.tag,
            ciphertext=ciphertext,
        )

        # Decrypt with AES-256-GCM (guarantees authenticity)
        decrypted_bytes = decrypt_payload(enc_payload, password)

        # Check if pre-compressed
        if decompress or decrypted_bytes.startswith(b"\x78\x9c") or decrypted_bytes.startswith(b"\x78\x01") or decrypted_bytes.startswith(b"\x78\xda"):
            try:
                decrypted_bytes = zlib.decompress(decrypted_bytes)
            except Exception:
                pass

        if detected_meta.payload_type == TYPE_TEXT:
            try:
                text_content = decrypted_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text_content = decrypted_bytes.decode("latin-1", errors="replace")
            payload_type_str = "text"
            filename = None
        else:
            text_content = None
            payload_type_str = "file"
            filename = detected_meta.filename or "extracted_audio_payload.bin"

        return AudioExtractionResult(
            payload_type=payload_type_str,
            data=decrypted_bytes,
            text=text_content,
            filename=filename,
            payload_size_bytes=len(decrypted_bytes),
            bits_per_sample=detected_bpc,
            verified_authentic=True,
        )
