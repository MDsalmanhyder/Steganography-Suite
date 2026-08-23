# SecureStego 🛡️ – Enterprise Secure Image Steganography & Forensics Suite

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyQt6-41CD52?logo=qt&logoColor=white)](https://riverbankcomputing.com/software/pyqt/)
[![Security](https://img.shields.io/badge/Encryption-AES--256--GCM-red)](https://pycryptodome.readthedocs.io/)
[![Forensics](https://img.shields.io/badge/Forensics-Chi--Square%20%26%20Entropy-blue)](https://scipy.org/)
[![Tests](https://img.shields.io/badge/Tests-28%20Passed-brightgreen)](tests/)

**SecureStego** is an enterprise-grade cross-platform steganography application and image forensics lab. It allows users to securely conceal encrypted text messages and arbitrary files (PDF, DOCX, ZIP, TXT, images, and binaries) inside lossless PNG images using Least Significant Bit (LSB) embedding, backed by **AES-256-GCM** authenticated encryption, **PBKDF2-HMAC-SHA256** key derivation, and comprehensive image steganalysis tools.

---

## 🌟 Key Highlights & Capabilities

* **🔒 Military-Grade Cryptographic Security**:
  * AES-256 in Galois/Counter Mode (**AES-256-GCM**) provides both confidentiality and cryptographic integrity verification.
  * Key derivation via **PBKDF2-HMAC-SHA256** with **200,000 iterations** and random 128-bit cryptographic salts.
  * Instant tamper detection: any single altered pixel or incorrect password immediately fails GCM tag verification.
* **📦 Universal Arbitrary File & Text Concealment**:
  * Hide secret plain text or binary files such as PDF documents, Word `.docx`, `.zip` archives, `.txt`, and images.
  * Preserves original filenames and payload metadata securely inside the encrypted stego stream.
* **⚡ Vectorized High-Performance LSB Engine**:
  * Configurable embedding density (1, 2, 3, or 4 LSB bits per channel).
  * Extremely high image fidelity (**PSNR > 50 dB** and **SSIM > 0.999** for 1-LSB mode).
  * Automated capacity pre-flight validation preventing buffer overflow.
* **🔬 Advanced Forensic & Steganalysis Lab**:
  * **Visual Bit-Plane Slicer**: Inspect bit planes 0 (LSB) through 7 (MSB) individually across Red, Green, Blue, Grayscale, or Combined channels to detect visual artifacts.
  * **Chi-Square ($\chi^2$) Steganalysis**: Statistical Pairs of Values (PoV) testing estimating steganographic detection probability ($p$-value).
  * **Shannon Entropy Analysis**: Multi-channel and LSB plane entropy calculation.
  * **Sample Pair Analysis (SPA)**: Mathematical estimation of hidden message length.
  * **Metadata & PNG Chunks Inspector**: Parses EXIF, ICC profiles, and custom PNG text chunks.
  * **Forensic Report Export**: Generate audit-ready PDF, JSON, or plain text forensic reports with a single click.
* **🎨 Modern Desktop GUI**:
  * Built with PyQt6 featuring a sleek dark theme, drag-and-drop zones, live capacity gauges, password entropy strength meter, and audit logging.
* **💻 Complete Headless CLI**:
  * Robust command-line interface for automated scripting and server pipelines.

---

## 📸 Demonstration Screenshots

| 1. Hide Data View | 2. Embedding Quality Analysis |
| :---: | :---: |
| ![Hide Data](docs/screenshots/01_encode_view.png) | ![Embed Results](docs/screenshots/02_embed_result.png) |

| 3. Extract & Decrypt View | 4. Steganalysis & Forensics Lab |
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
        A[Secret Text or Binary File] --> B[PBKDF2 Key Derivation<br/>200,000 Rounds + Salt]
        B --> C[AES-256-GCM Encryption]
        C --> D[Header Builder + CRC32 Checksum]
        D --> E[NumPy Vectorized LSB Embedder<br/>1-4 Bits/Channel]
        F[Original Carrier PNG] --> E
        E --> G[Stego Image Output<br/>PSNR > 50 dB]
    end

    subgraph RECEIVER["2. Extraction & Decryption (Receiver)"]
        G --> H[Header Prober & CRC32 Validator]
        H --> I[Bit Stream Slicer]
        I --> J[AES-256-GCM Decryptor]
        K[Passphrase] --> J
        J -->|Tag Verified Authentic| L[Extracted Text or Reconstructed File]
        J -->|Tag Mismatch / Altered| M[InvalidPasswordError / Tamper Alert]
    end

    subgraph FORENSICS["3. Forensic Steganalysis Lab"]
        G --> N[Bit-Plane Slicer 0-7]
        G --> O[Chi-Square Steganalysis]
        G --> P[Shannon Entropy Analysis]
        G --> Q[Metadata & PNG Chunk Inspector]
        N & O & P & Q --> R[Forensic Report PDF/JSON/TXT]
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

### 1. Hide Data in an Image
* **Hide Plain Text**:
  ```bash
  python main.py hide --carrier demo_assets/carrier_cyber_landscape.png --text "Top Secret Message" --password "MasterKey#2026!" --output stego_text.png --bits 1
  ```
* **Hide Arbitrary Binary File (PDF, DOCX, ZIP, etc.)**:
  ```bash
  python main.py hide --carrier demo_assets/carrier_gradient_1200x800.png --file demo_assets/confidential_briefing.pdf --password "MasterKey#2026!" --output stego_pdf.png --bits 2
  ```

### 2. Extract Data from a Stego Image
* **Extract to Console / File**:
  ```bash
  python main.py extract --stego stego_text.png --password "MasterKey#2026!"
  ```
* **Extract and Save Binary File**:
  ```bash
  python main.py extract --stego stego_pdf.png --password "MasterKey#2026!" --output-dir ./extracted_output/
  ```

### 3. Forensic Image Steganalysis
* **Analyze & Export PDF / JSON Reports**:
  ```bash
  python main.py analyze --image stego_text.png --export-pdf forensic_report.pdf --export-json forensic_report.json
  ```
* **Extract Specific Bit Plane Slice**:
  ```bash
  python main.py analyze --image stego_text.png --slice-bit 0 --slice-channel combined --slice-out lsb_plane.png
  ```

### 4. Check Image Data Capacity
```bash
python main.py capacity --image demo_assets/carrier_cyber_landscape.png --bits 1
```

---

## 🔐 Cryptographic Header Protocol Specification

SecureStego structures its embedded payload stream using a resilient binary protocol:

| Offset | Field | Length | Description |
| :--- | :--- | :--- | :--- |
| `0x00` | `MAGIC_HEADER` | 7 bytes | Magic signature ASCII `SECSTEG` |
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

## 📊 Steganographic Quality Benchmarks

Experimental results on standard carrier images:

| Carrier Image | Embedding Density | Embedded Size | PSNR (dB) | MSE | SSIM | Human Perception |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Cyber Landscape (800×600) | 1 Bit / Channel | 10.4 KB | **58.74 dB** | 0.0868 | 0.99994 | Imperceptible |
| Cyber Landscape (800×600) | 2 Bits / Channel | 20.8 KB | **44.21 dB** | 2.4510 | 0.99870 | Imperceptible |
| Geometric Gradient (1200×800) | 1 Bit / Channel | 45.2 KB | **59.12 dB** | 0.0792 | 0.99997 | Imperceptible |
| Geometric Gradient (1200×800) | 3 Bits / Channel | 135.0 KB | **38.45 dB** | 9.2104 | 0.99120 | Near Imperceptible |

---

## 🧪 Test Suite Summary

The test suite covers:
* **AES-256-GCM & PBKDF2**: Deterministic key derivation, tamper detection, wrong passphrase rejection.
* **LSB Engine**: Text embedding, binary file embedding (PDF, ZIP, DOCX, TXT), multi-bit density (1-4 LSBs), RGBA transparency preservation, capacity overflow checks.
* **Forensics**: Bit-plane slicing, Shannon entropy distribution, Chi-Square steganalysis, PDF/JSON report generation.
* **CLI & GUI**: Command parser verification, background worker threads, and UI widgets.

All 28 tests pass with 100% coverage on core functionality.

---

## 📄 License & Credits

Developed with ❤️ for secure, authenticated communications and steganographic research.
Licensed under the [MIT License](LICENSE).
