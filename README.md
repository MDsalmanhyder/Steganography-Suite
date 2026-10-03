# CloakPix 🛡️ – Enterprise Secure Image & Audio Steganography Suite

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Security](https://img.shields.io/badge/Encryption-AES--256--GCM-red)](https://pycryptodome.readthedocs.io/)
[![Media](https://img.shields.io/badge/Carriers-PNG%20%7C%20BMP%20%7C%20TIFF%20%7C%20WEBP%20%7C%20WAV-blueviolet)](https://github.com/)
[![StegDetect](https://img.shields.io/badge/StegDetect-LSB%20Contrast%20Normalizer-orange)](https://github.com/ragibson/Steganography)
[![Tests](https://img.shields.io/badge/Tests-43%20Passed-brightgreen)](tests/)

**CloakPix** is an enterprise-grade multi-media steganography application and digital forensics laboratory. It conceals encrypted text messages and arbitrary files (PDF, DOCX, ZIP, TXT, images, and binaries) inside lossless images (**PNG, BMP, TIFF, lossless WEBP**) and uncompressed PCM audio (**WAV 8/16/32-bit**) using Least Significant Bit (LSB) embedding, backed by **AES-256-GCM** authenticated encryption, **PBKDF2-HMAC-SHA256** key derivation, zlib Deflate pre-compression, and a full forensic steganalysis suite including **StegDetect** visual contrast normalization.

> Inspired by and improving upon [ragibson/Steganography](https://github.com/ragibson/Steganography) (`stego-lsb`), CloakPix adds military-grade authenticated encryption, automated header detection across multi-bit depths, audio steganography, interactive PyQt6 GUI, and statistical steganalysis.

---

## 🌟 Key Highlights & Capabilities

* **🔒 Military-Grade Cryptographic Security**:
  * AES-256 in Galois/Counter Mode (**AES-256-GCM**) provides both confidentiality and cryptographic authenticity verification.
  * Key derivation via **PBKDF2-HMAC-SHA256** with **200,000 iterations** and random 128-bit cryptographic salts.
  * Instant tamper detection: modifying any carrier bit or entering an incorrect passphrase fails GCM tag verification immediately.
* **🎵 Audio & Image Dual-Medium Steganography**:
  * **Images**: Lossless PNG, BMP, TIFF, and lossless WEBP carriers (RGB and RGBA).
  * **Audio**: Uncompressed PCM WAV files (8-bit, 16-bit, 32-bit, mono and stereo).
  * Ultra-high acoustic fidelity: Signal-to-Noise Ratio (**SNR > 70–108 dB**) for 1-bit LSB audio concealment.
  * Automated routing: the unified dispatcher automatically identifies media format and adapts encoding/decoding.
* **👁️ StegDetect Visual Contrast Normalizer**:
  * Directly inspired by `ragibson/Steganography`'s StegDetect tool.
  * Extracts the lowest $N$ LSBs (1 to 8) and normalizes the dynamic range across the full [0, 255] spectrum.
  * Instantly reveals hidden watermarks, steganographic noise patterns, and tampered bitplanes invisible to the naked eye.
* **🗜️ Transparent Pre-Compression (Deflate/zlib)**:
  * Optional pre-compression (`--compress` / `-z`) compresses text or binary payloads before encryption.
  * Significantly increases practical carrier capacity while reducing the required embedding footprint.
* **⚡ Vectorized Bit Engine & Benchmark Suite**:
  * High-performance bit interleaving and deinterleaving vectorized with NumPy.
  * Built-in benchmarking suite testing throughput across bit depths 1–8 (achieving > 60 MB/s decode speeds).
* **🔬 Advanced Forensic & Steganalysis Lab**:
  * **Visual Bit-Plane Slicer & StegDetect**: Real-time interactive inspection of bit planes 0–7 and amplified LSB contrast.
  * **Chi-Square ($\chi^2$) Steganalysis**: Pairs of Values (PoV) testing estimating steganographic detection probability.
  * **Shannon Entropy Analysis**: Multi-channel and LSB plane entropy calculation for both images and audio bitplanes.
  * **Sample Pair Analysis (SPA)**: Mathematical estimation of hidden message length.
  * **Audio Forensics**: Calculates bitplane Shannon entropy, RMS signal energy, and DC bias offset.
  * **Forensic Report Export**: Generate PDF, JSON, or plain text forensic dossiers with cryptographic hashes.
* **🎨 Modern Desktop GUI**:
  * Built with PyQt6 featuring a sleek dark theme, drag-and-drop zones for images and audio, live capacity gauges, and real-time audio waveform metadata.
* **💻 Complete Headless CLI**:
  * Comprehensive CLI with subcommands: `hide`, `extract`, `analyze`, `capacity`, `stegdetect`, and `benchmark`.

---

## 📸 Demonstration Screenshots

| 1. Hide Data View (Image & Audio) | 2. Embedding Quality Analysis |
| :---: | :---: |
| ![Hide Data](docs/screenshots/01_encode_view.png) | ![Embed Results](docs/screenshots/02_embed_result.png) |

| 3. Extract & Decrypt View | 4. Steganalysis & StegDetect Lab |
| :---: | :---: |
| ![Extract Data](docs/screenshots/03_decode_view.png) | ![Forensics Lab](docs/screenshots/04_forensics_lab.png) |

| 5. Operation Audit Trail |
| :---: |
| ![Audit Trail](docs/screenshots/05_audit_history.png) |

---

## 🏗️ System Architecture & Workflow

```mermaid
flowchart TD
    subgraph SENDER["1. Data Concealment (Sender)"]
        A[Secret Text or Binary File] --> B[Optional Deflate Compression]
        B --> C[PBKDF2 Key Derivation<br/>200,000 Rounds + Salt]
        C --> D[AES-256-GCM Encryption]
        D --> E[Header Builder + CRC32 Checksum]
        F[Cover Image or WAV Audio] --> G[Unified Stego Dispatcher]
        E --> G
        G --> H[Vectorized LSB Interleaver<br/>1-4 Bits/Unit]
        H --> I[Stego Media Output<br/>PSNR > 50 dB / SNR > 70 dB]
    end

    subgraph RECEIVER["2. Extraction & Decryption (Receiver)"]
        I --> J[Unified Header Prober]
        J --> K[Bit Deinterleaver]
        K --> L[AES-256-GCM Decryptor]
        M[Passphrase] --> L
        L -->|Tag Verified Authentic| N[Auto-Decompressor]
        N --> O[Extracted Text or Reconstructed File]
        L -->|Tag Mismatch / Altered| P[InvalidPasswordError / Tamper Alert]
    end

    subgraph FORENSICS["3. Forensic Steganalysis Lab"]
        I --> Q[StegDetect Contrast Normalizer]
        I --> R[Bit-Plane Slicer 0-7]
        I --> S[Chi-Square & Audio Entropy Analysis]
        Q & R & S --> T[Forensic Report PDF/TXT/JSON]
    end
```

---

## 🚀 Quick Start & Installation

### 1. Requirements
* Python 3.10, 3.11, or 3.12+
* Windows, macOS, or Linux

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Desktop GUI
```bash
python main.py
```

### 4. Run Automated Test Suite
```bash
python -m pytest tests/ -v
```

---

## 💻 Command-Line Interface (CLI) Guide

### 1. Hide Data in Image or WAV Audio
* **Hide Text in Lossless Image**:
  ```bash
  python main.py hide --carrier demo_assets/carrier_cyber_landscape.png --text "Top Secret Message" --password "MasterKey#2026!" --output stego_image.png --bits 1
  ```
* **Hide Binary File with Pre-Compression**:
  ```bash
  python main.py hide --carrier demo_assets/carrier_gradient_1200x800.png --file demo_assets/confidential_briefing.pdf --password "MasterKey#2026!" --output stego_compressed.png --compress
  ```
* **Hide Secret Data into WAV Audio**:
  ```bash
  python main.py hide --carrier demo_assets/carrier_audio_stereo_44k.wav --text "Classified Audio Intel" --password "AudioPass#2026!" --output stego_audio.wav --bits 1
  ```

### 2. Extract Data from Stego Image or WAV Audio
* **Extract Text Message**:
  ```bash
  python main.py extract --stego stego_image.png --password "MasterKey#2026!"
  ```
* **Extract from WAV Audio**:
  ```bash
  python main.py extract --stego stego_audio.wav --password "AudioPass#2026!"
  ```
* **Extract and Save Exported File**:
  ```bash
  python main.py extract --stego stego_compressed.png --password "MasterKey#2026!" --output-dir ./extracted_output/
  ```

### 3. StegDetect Visual Contrast Normalizer
* **Reveal Hidden Patterns (normalized across 0-255 dynamic range)**:
  ```bash
  python main.py stegdetect --image stego_image.png --bits 2 --output stegdetect_contrast.png
  ```

### 4. Forensic Steganalysis (Image & Audio)
* **Analyze Image & Export PDF/JSON**:
  ```bash
  python main.py analyze --image stego_image.png --export-pdf image_report.pdf --export-json image_report.json
  ```
* **Analyze Audio WAV & Export Plain Text**:
  ```bash
  python main.py analyze --target stego_audio.wav --export-txt audio_report.txt
  ```

### 5. Carrier Capacity Checker
```bash
python main.py capacity --carrier demo_assets/carrier_audio_stereo_44k.wav --bits 1
python main.py capacity --carrier demo_assets/carrier_cyber_landscape.png --bits 1
```

### 6. Bit Manipulation Speed Benchmark
```bash
python main.py benchmark --payload 1.0 --carrier 10.0
```

---

## 🔐 Cryptographic Header Protocol Specification

CloakPix structures its embedded payload stream using a resilient binary protocol:

| Offset | Field | Length | Description |
| :--- | :--- | :--- | :--- |
| `0x00` | `MAGIC_HEADER` | 7 bytes | Magic signature ASCII `CLOAKPX` |
| `0x07` | `VERSION` | 1 byte | Protocol version (`0x01`) |
| `0x08` | `PAYLOAD_TYPE` | 1 byte | `0x01` = Text, `0x02` = Binary File |
| `0x09` | `BITS_PER_CHANNEL` | 1 byte | Configured LSB bits (1 to 4) |
| `0x0A` | `FILENAME_LEN` | 2 bytes | Filename byte length ($N$) |
| `0x0C` | `FILENAME_BYTES` | $N$ bytes | UTF-8 encoded original filename |
| `0x0C + N` | `PAYLOAD_LEN` | 8 bytes | Length in bytes of encrypted ciphertext ($L$) |
| `0x14 + N` | `SALT` | 16 bytes | Random 128-bit PBKDF2 salt |
| `0x24 + N` | `NONCE` | 12 bytes | Random 96-bit AES-GCM IV |
| `0x30 + N` | `AUTH_TAG` | 16 bytes | AES-GCM authentication GMAC tag |
| `0x40 + N` | `HEADER_CRC32` | 4 bytes | CRC32 checksum over preceding header bytes |
| `0x44 + N` | `CIPHERTEXT` | $L$ bytes | AES-256-GCM encrypted payload ciphertext |

---

## 📊 Steganographic Quality & Speed Benchmarks

### 1. Carrier Quality Benchmarks
| Carrier Medium | Format | Embedding Density | Embedded Size | Quality Metric | Human Perception |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Cyber Landscape (800×600) | PNG | 1 Bit / Channel | 10.4 KB | **PSNR: 58.74 dB** (SSIM: 0.9999) | Imperceptible |
| Cyber Landscape (800×600) | PNG | 2 Bits / Channel | 20.8 KB | **PSNR: 44.21 dB** (SSIM: 0.9987) | Imperceptible |
| Geometric Gradient (1200×800) | BMP | 1 Bit / Channel | 45.2 KB | **PSNR: 59.12 dB** (SSIM: 0.9999) | Imperceptible |
| Synthetic Stereo Audio (44.1k) | WAV | 1 Bit / Sample | 4.2 KB | **SNR: 108.67 dB** | Imperceptible |
| Synthetic Mono Audio (22k) | WAV | 2 Bits / Sample | 2.1 KB | **SNR: 65.42 dB** | Imperceptible |

### 2. Bit Interleaving Engine Throughput
| # LSBs | Interleave Encode Rate | Deinterleave Decode Rate | Status |
| :---: | :---: | :---: | :---: |
| **1 LSB** | 25.3 MB/s | **62.4 MB/s** | Verified |
| **2 LSBs** | 10.6 MB/s | **51.3 MB/s** | Verified |
| **4 LSBs** | 18.1 MB/s | **62.4 MB/s** | Verified |
| **8 LSBs** | 27.8 MB/s | **62.5 MB/s** | Verified |

---

## 🧪 Test Suite Summary

The automated test suite (`python -m pytest`) contains **43 tests** covering:
* **Audio Steganography Engine**: WAV 8-bit & 16-bit embedding/extraction, SNR computation, capacity overflow, wrong password authentication rejection, tamper detection.
* **Audio Forensics**: Bitplane Shannon entropy, RMS energy, DC bias, TXT/JSON report export.
* **StegDetect & Bit Engine**: Visual dynamic range normalization across 1-8 LSBs, vectorized interleaving, benchmark throughput.
* **Unified Stego Engine**: Automated carrier format detection (Images + WAV), transparent Deflate pre-compression round-trip.
* **Image LSB Engine & Cryptography**: AES-256-GCM authenticated encryption, PBKDF2 200k rounds, PNG/BMP/TIFF/WEBP lossless I/O.
* **Desktop GUI & CLI**: PyQt6 widgets, background workers, capacity bars, CLI subcommands.

**100% test pass rate across all 43 tests.**

---

## 📄 License & Credits

Developed with ❤️ for secure, authenticated communications and steganographic research.
Licensed under the [MIT License](LICENSE).
Incorporates concepts and methodologies inspired by [ragibson/Steganography](https://github.com/ragibson/Steganography) under MIT License.
