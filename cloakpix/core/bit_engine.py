"""
High-Speed Vectorized Bit Interleaving and Benchmarking Engine for CloakPix.
Inspired by and compatible with ragibson/Steganography's bit_manipulation module.
Provides low-level bit packing/unpacking and throughput benchmarking across 1-8 LSBs.
"""

from math import ceil
from time import time
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


def roundup(x: float, base: int = 1) -> int:
    """Rounds up x to the nearest multiple of base."""
    return int(ceil(x / float(base))) * base


def lsb_interleave_bytes(
    carrier: bytes,
    payload: bytes,
    num_lsb: int = 1,
    truncate: bool = False,
    byte_depth: int = 1,
    num_lsbs: Optional[int] = None,
) -> bytes:
    """
    Interleaves payload bits into the lowest num_lsb bits of carrier bytes.
    Vectorized with NumPy for high throughput.
    
    Args:
        carrier: Carrier byte sequence.
        payload: Payload byte sequence.
        num_lsb: Number of LSB bits used per carrier element (1 to 8).
        truncate: If True, returns only modified portion of carrier.
        byte_depth: Bytes per sample/channel (1 for 8-bit, 2 for 16-bit).
        num_lsbs: Optional alias for num_lsb.
        
    Returns:
        Interleaved bytes.
    """
    effective_lsb = num_lsbs if num_lsbs is not None else num_lsb
    if not (1 <= effective_lsb <= 8):
        raise ValueError("num_lsb must be between 1 and 8.")

    plen = len(payload)
    if plen == 0:
        return carrier

    # Unpack payload into bits
    payload_arr = np.frombuffer(payload, dtype=np.uint8)
    payload_bits = np.unpackbits(payload_arr)

    bit_height = roundup(len(payload_bits) / float(effective_lsb))
    total_bits = bit_height * effective_lsb
    if len(payload_bits) < total_bits:
        payload_bits = np.pad(payload_bits, (0, total_bits - len(payload_bits)), "constant")

    # Reshape payload bits into integer chunks
    chunks = payload_bits.reshape(bit_height, effective_lsb)
    powers = (1 << np.arange(effective_lsb - 1, -1, -1, dtype=np.uint8))
    chunk_vals = np.sum(chunks * powers, axis=1).astype(np.uint8)

    num_carrier_elements = len(chunk_vals)
    required_bytes = num_carrier_elements * byte_depth

    if required_bytes > len(carrier):
        raise ValueError(
            f"Carrier size ({len(carrier)} bytes) is too small to contain "
            f"payload ({plen} bytes at {effective_lsb} LSBs; needs {required_bytes} bytes)."
        )

    # Apply to carrier
    mask = np.uint8((~((1 << effective_lsb) - 1)) & 0xFF)
    carrier_arr = np.frombuffer(carrier, dtype=np.uint8).copy()

    if byte_depth == 1:
        carrier_arr[:num_carrier_elements] = (carrier_arr[:num_carrier_elements] & mask) | chunk_vals
    elif byte_depth == 2:
        # In 16-bit little endian, LSB of sample is in the even byte index
        indices = np.arange(0, num_carrier_elements * 2, 2)
        carrier_arr[indices] = (carrier_arr[indices] & mask) | chunk_vals

    if truncate:
        return carrier_arr[:required_bytes].tobytes()
    return carrier_arr.tobytes()


def lsb_deinterleave_bytes(
    carrier: bytes,
    num_bits: Optional[int] = None,
    num_lsb: int = 1,
    byte_depth: int = 1,
    num_bytes: Optional[int] = None,
    num_lsbs: Optional[int] = None,
) -> bytes:
    """
    Deinterleaves num_bits bits from the num_lsb LSBs of carrier bytes.
    
    Args:
        carrier: Stego byte sequence.
        num_bits: Total number of secret bits to recover.
        num_lsb: Number of LSB bits used per carrier element (1 to 8).
        byte_depth: Bytes per sample/channel (1 for 8-bit, 2 for 16-bit).
        num_bytes: Total number of bytes to recover (converted to bits).
        num_lsbs: Optional alias for num_lsb.
        
    Returns:
        Deinterleaved recovered bytes.
    """
    effective_lsb = num_lsbs if num_lsbs is not None else num_lsb
    if not (1 <= effective_lsb <= 8):
        raise ValueError("num_lsb must be between 1 and 8.")

    if num_bits is None:
        if num_bytes is not None:
            num_bits = num_bytes * 8
        else:
            raise ValueError("Either num_bits or num_bytes must be specified.")

    if num_bits <= 0:
        return b""

    chunks_needed = (num_bits + effective_lsb - 1) // effective_lsb
    carrier_arr = np.frombuffer(carrier, dtype=np.uint8)

    if byte_depth == 1:
        extracted_chunks = carrier_arr[:chunks_needed] & ((1 << effective_lsb) - 1)
    elif byte_depth == 2:
        indices = np.arange(0, chunks_needed * 2, 2)
        extracted_chunks = carrier_arr[indices] & ((1 << effective_lsb) - 1)
    else:
        raise ValueError(f"Unsupported byte depth: {byte_depth}")

    # Unpack chunk integers to bits
    bits_list = []
    for i in range(effective_lsb - 1, -1, -1):
        bits_list.append((extracted_chunks >> i) & 1)
    bits = np.column_stack(bits_list).flatten()[:num_bits]

    # Pad to byte multiple
    if len(bits) % 8 != 0:
        bits = np.pad(bits, (0, 8 - (len(bits) % 8)), "constant")

    return np.packbits(bits).tobytes()[: (num_bits + 7) // 8]


class BenchmarkResultList(list):
    """List of benchmark results that also supports dict-style access for top-level stats."""

    def __init__(self, items: list, interleave_mb_s: float = 0.0, deinterleave_mb_s: float = 0.0):
        super().__init__(items)
        self.interleave_speed_mb_s = interleave_mb_s
        self.deinterleave_speed_mb_s = deinterleave_mb_s

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, str):
            if item == "interleave_speed_mb_s":
                return self.interleave_speed_mb_s
            elif item == "deinterleave_speed_mb_s":
                return self.deinterleave_speed_mb_s
            raise KeyError(item)
        return super().__getitem__(item)

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, str) and item in ("interleave_speed_mb_s", "deinterleave_speed_mb_s"):
            return True
        return super().__contains__(item)


def run_benchmark(
    payload_mb: float = 1.0,
    carrier_mb: float = 10.0,
    carrier_size_bytes: Optional[int] = None,
    num_runs: int = 1,
) -> BenchmarkResultList:
    """
    Benchmarks bit interleaving and deinterleaving throughput across 1-8 LSBs.
    Matches and exceeds ragibson/Steganography's bit_manipulation test().
    """
    if carrier_size_bytes is not None:
        carrier_mb = max(0.01, carrier_size_bytes / (1024.0 * 1024.0))
        payload_mb = carrier_mb / 8.0

    payload_size = max(64, int(payload_mb * 1024 * 1024))
    carrier_size = max(512, int(carrier_mb * 1024 * 1024))

    payload = np.random.bytes(payload_size)
    carrier = np.random.bytes(carrier_size)

    results = []

    for num_lsb in range(1, 9):
        # Encode speed
        t0 = time()
        for _ in range(num_runs):
            stego = lsb_interleave_bytes(carrier, payload, num_lsb, truncate=True)
        t_encode = (time() - t0) / num_runs
        encode_rate = payload_mb / t_encode if t_encode > 0 else 0.0

        # Decode speed
        num_bits = payload_size * 8
        t1 = time()
        for _ in range(num_runs):
            recovered = lsb_deinterleave_bytes(stego, num_bits=num_bits, num_lsb=num_lsb)
        t_decode = (time() - t1) / num_runs
        decode_rate = payload_mb / t_decode if t_decode > 0 else 0.0

        assert recovered == payload, f"Roundtrip failed for {num_lsb} LSBs!"

        results.append({
            "num_lsb": num_lsb,
            "encode_rate_mb_s": round(encode_rate, 2),
            "decode_rate_mb_s": round(decode_rate, 2),
            "encode_time_sec": round(t_encode, 4),
            "decode_time_sec": round(t_decode, 4),
        })

    avg_enc = sum(r["encode_rate_mb_s"] for r in results) / len(results)
    avg_dec = sum(r["decode_rate_mb_s"] for r in results) / len(results)

    return BenchmarkResultList(results, interleave_mb_s=round(avg_enc, 2), deinterleave_mb_s=round(avg_dec, 2))
