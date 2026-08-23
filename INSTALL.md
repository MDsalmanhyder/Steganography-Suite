# SecureStego – Installation & Setup Guide

This guide provides instructions for setting up and running **SecureStego** across Windows, macOS, and Linux environments.

---

## 1. System Requirements

* **Python**: Python 3.10, 3.11, or 3.12+
* **Memory**: Minimum 512 MB RAM (2 GB recommended for analyzing high-resolution 4K images)
* **Operating Systems**:
  * Windows 10 / 11 (x64 / ARM64)
  * macOS 12 Monterey or newer (Apple Silicon / Intel)
  * Linux (Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux)

---

## 2. Installation Steps

### Option A: Standard Installation

1. **Clone or Extract the Repository**:
   ```bash
   cd "c:/Users/salma/Downloads/steganography tool"
   ```

2. **Create and Activate a Virtual Environment (Recommended)**:
   * **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * **macOS / Linux (Bash / Zsh)**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Install Required Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 3. Running the Application

### Running the Desktop GUI

To launch the modern dark-themed PyQt6 GUI application:
```bash
python main.py
```
or explicitly:
```bash
python -m securestego.app
```

---

### Running the Command-Line Interface (CLI)

SecureStego comes with a full-featured CLI for scripting, batch operations, and headless servers:

#### 1. Display Help & Subcommands:
```bash
python main.py --help
```

#### 2. Hide a Secret Text Message:
```bash
python main.py hide --carrier demo_assets/carrier_cyber_landscape.png --text "Classified mission rendezvous coordinates." --password "YourStrongPassword#2026" --output stego_image.png --bits 1
```

#### 3. Hide a Secret Binary File (PDF, DOCX, ZIP, Image, etc.):
```bash
python main.py hide --carrier demo_assets/carrier_gradient_1200x800.png --file demo_assets/confidential_briefing.pdf --password "YourStrongPassword#2026" --output stego_pdf.png --bits 2
```

#### 4. Extract and Decrypt Hidden Payload:
```bash
python main.py extract --stego stego_image.png --password "YourStrongPassword#2026"
```
To save the extracted payload to a file:
```bash
python main.py extract --stego stego_pdf.png --password "YourStrongPassword#2026" --output-dir ./extracted_files/
```

#### 5. Run Forensic Steganalysis & Export PDF Report:
```bash
python main.py analyze --image stego_image.png --export-pdf forensic_report.pdf --export-json forensic_report.json
```

#### 6. Calculate Carrier Image Capacity:
```bash
python main.py capacity --image demo_assets/carrier_cyber_landscape.png --bits 1
```

---

## 4. Running the Test Suite

To verify system integrity and run all 28 automated unit/integration tests:
```bash
python -m pytest tests/ -v
```

---

## 5. Troubleshooting & FAQ

* **Q: Why does my extracted file have an invalid password error?**
  * *A: SecureStego uses AES-256-GCM authenticated encryption. An incorrect password or any single-bit alteration in the stego image (e.g. from JPEG compression or resizing) triggers an immediate cryptographic integrity check failure.*
* **Q: Can I use JPEG as a carrier image?**
  * *A: Steganography requires lossless formats like PNG, BMP, or TIFF. Lossy JPEG compression irreversibly modifies the least significant bits upon saving, which destroys embedded steganographic payloads.*
* **Q: How can I maximize visual quality?**
  * *A: Use 1 LSB bit per channel (`--bits 1`), which yields a PSNR > 50 dB (virtually imperceptible to the human eye and standard image viewers).*
