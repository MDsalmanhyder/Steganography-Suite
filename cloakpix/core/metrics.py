"""
Image metrics and quality evaluation module for CloakPix.
Calculates PSNR, MSE, SSIM, and Shannon entropy.
"""

import math
from typing import Dict, Tuple, Union
import numpy as np
from PIL import Image


def calculate_mse(image_a: Union[np.ndarray, Image.Image], image_b: Union[np.ndarray, Image.Image]) -> float:
    """
    Computes the Mean Squared Error (MSE) between two images.
    
    Args:
        image_a: Original image as PIL Image or numpy array.
        image_b: Stego/modified image as PIL Image or numpy array.
        
    Returns:
        Mean squared error float value.
    """
    arr_a = np.asarray(image_a, dtype=np.float64)
    arr_b = np.asarray(image_b, dtype=np.float64)

    if arr_a.shape != arr_b.shape:
        raise ValueError(f"Image shapes do not match: {arr_a.shape} vs {arr_b.shape}")

    # Drop alpha channel if present for standard RGB metric calculation, or include if matching
    mse = np.mean((arr_a - arr_b) ** 2)
    return float(mse)


def calculate_psnr(image_a: Union[np.ndarray, Image.Image], image_b: Union[np.ndarray, Image.Image]) -> float:
    """
    Computes Peak Signal-to-Noise Ratio (PSNR) in decibels (dB).
    Higher values indicate better visual fidelity (typically > 50 dB is imperceptible).
    
    Args:
        image_a: Original image.
        image_b: Modified/stego image.
        
    Returns:
        PSNR value in dB (returns 100.0 if identical / MSE is 0).
    """
    mse = calculate_mse(image_a, image_b)
    if mse == 0:
        return 100.0  # Perfect fidelity / identical images

    max_pixel = 255.0
    psnr = 20.0 * math.log10(max_pixel / math.sqrt(mse))
    return float(psnr)


def calculate_ssim(
    image_a: Union[np.ndarray, Image.Image],
    image_b: Union[np.ndarray, Image.Image],
    k1: float = 0.01,
    k2: float = 0.03,
    l_max: float = 255.0,
) -> float:
    """
    Calculates the Structural Similarity Index (SSIM) between two images.
    SSIM ranges from -1 to 1, where 1 means identical structural fidelity.
    
    Args:
        image_a: Original image.
        image_b: Modified/stego image.
        k1, k2: SSIM stability constants.
        l_max: Dynamic range of pixel values (255 for 8-bit images).
        
    Returns:
        SSIM float index between 0.0 and 1.0.
    """
    arr_a = np.asarray(image_a, dtype=np.float64)
    arr_b = np.asarray(image_b, dtype=np.float64)

    if arr_a.shape != arr_b.shape:
        raise ValueError(f"Image shapes do not match: {arr_a.shape} vs {arr_b.shape}")

    c1 = (k1 * l_max) ** 2
    c2 = (k2 * l_max) ** 2

    # Calculate means
    mu_a = np.mean(arr_a)
    mu_b = np.mean(arr_b)

    # Calculate variances and covariance
    sigma_a_sq = np.var(arr_a)
    sigma_b_sq = np.var(arr_b)
    sigma_ab = np.mean((arr_a - mu_a) * (arr_b - mu_b))

    numerator = (2 * mu_a * mu_b + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a ** 2 + mu_b ** 2 + c1) * (sigma_a_sq + sigma_b_sq + c2)

    ssim_val = numerator / denominator
    return float(np.clip(ssim_val, 0.0, 1.0))


def calculate_entropy(data_or_image: Union[np.ndarray, Image.Image, bytes]) -> float:
    """
    Calculates the Shannon entropy in bits per symbol.
    Theoretical maximum for 8-bit bytes/pixels is 8.0 bits.
    
    Args:
        data_or_image: Array, PIL image, or raw byte sequence.
        
    Returns:
        Entropy float value between 0.0 and 8.0.
    """
    if isinstance(data_or_image, Image.Image):
        arr = np.array(data_or_image).flatten()
    elif isinstance(data_or_image, np.ndarray):
        arr = data_or_image.flatten()
    elif isinstance(data_or_image, (bytes, bytearray)):
        arr = np.frombuffer(data_or_image, dtype=np.uint8)
    else:
        raise TypeError("Unsupported data type for entropy calculation.")

    if len(arr) == 0:
        return 0.0

    # Count frequencies of each symbol (0..255)
    counts = np.bincount(arr, minlength=256)
    probabilities = counts[counts > 0] / len(arr)
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return float(entropy)


def calculate_image_capacity(
    width: int,
    height: int,
    channels: int = 3,
    bits_per_channel: int = 1,
    header_overhead_bytes: int = 128,
) -> Dict[str, int]:
    """
    Calculates total raw capacity and usable payload capacity in bytes.
    
    Args:
        width: Image width in pixels.
        height: Image height in pixels.
        channels: Number of color channels (3 for RGB, 4 for RGBA).
        bits_per_channel: Number of LSB bits used per channel (1 to 4).
        header_overhead_bytes: Protocol header reservation bytes.
        
    Returns:
        Dictionary with total_bits, raw_capacity_bytes, usable_capacity_bytes.
    """
    total_slots = width * height * channels
    total_bits = total_slots * bits_per_channel
    raw_capacity_bytes = total_bits // 8
    usable_capacity_bytes = max(0, raw_capacity_bytes - header_overhead_bytes)

    return {
        "width": width,
        "height": height,
        "channels": channels,
        "bits_per_channel": bits_per_channel,
        "total_bits": total_bits,
        "raw_capacity_bytes": raw_capacity_bytes,
        "usable_capacity_bytes": usable_capacity_bytes,
    }
