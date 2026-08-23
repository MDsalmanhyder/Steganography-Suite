"""
Script to generate test assets and demo files for SecureStego.
"""

import os
import zipfile
import numpy as np
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def generate_assets():
    os.makedirs("demo_assets", exist_ok=True)

    # 1. Carrier 1: Cyber Landscape (800x600 PNG)
    arr1 = np.zeros((600, 800, 3), dtype=np.uint8)
    for y in range(600):
        for x in range(800):
            arr1[y, x, 0] = int((np.sin(x / 40.0) + 1.0) * 100 + 20)
            arr1[y, x, 1] = int((np.cos(y / 30.0) + 1.0) * 110 + 10)
            arr1[y, x, 2] = int(((x + y) / 1400.0) * 200 + 30)
    Image.fromarray(arr1, mode="RGB").save("demo_assets/carrier_cyber_landscape.png", "PNG")
    print("Created demo_assets/carrier_cyber_landscape.png")

    # 2. Carrier 2: Geometric Gradient (1200x800 PNG)
    arr2 = np.zeros((800, 1200, 3), dtype=np.uint8)
    for y in range(800):
        for x in range(1200):
            arr2[y, x, 0] = int((x / 1200.0) * 255)
            arr2[y, x, 1] = int((y / 800.0) * 255)
            arr2[y, x, 2] = int(((x * y) / (1200.0 * 800.0)) * 255)
    Image.fromarray(arr2, mode="RGB").save("demo_assets/carrier_gradient_1200x800.png", "PNG")
    print("Created demo_assets/carrier_gradient_1200x800.png")

    # 3. Secret Text Message
    msg = (
        "[TOP SECRET - EYES ONLY]\n"
        "Operation CyberSentinel 2026\n"
        "Coordinates: 37°46'29.2\"N 122°25'09.8\"W\n"
        "Rendezvous: 2026-08-25 04:00 UTC\n"
        "Payload Hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855\n"
        "All operational agents are instructed to maintain encrypted stego channels."
    )
    with open("demo_assets/secret_intel_message.txt", "w", encoding="utf-8") as f:
        f.write(msg)
    print("Created demo_assets/secret_intel_message.txt")

    # 4. Secret PDF Document
    c = canvas.Canvas("demo_assets/confidential_briefing.pdf", pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "CONFIDENTIAL SECURITY BRIEFING")
    c.setFont("Helvetica", 11)
    c.drawString(72, 690, "Project: SecureStego Steganographic Data Exchange")
    c.drawString(72, 670, "Classification: RESTRICTED")
    c.drawString(72, 650, "Date: August 2026")
    c.drawString(72, 620, "1. This document has been extracted from an encrypted LSB steganogram.")
    c.drawString(72, 600, "2. Cryptographic algorithm: AES-256-GCM authenticated with PBKDF2.")
    c.drawString(72, 580, "3. Image integrity verified via Galois/Counter Mode authentication tag.")
    c.save()
    print("Created demo_assets/confidential_briefing.pdf")

    # 5. Secret ZIP Archive
    with zipfile.ZipFile("demo_assets/classified_payload.zip", "w") as zf:
        zf.writestr("network_keys.pem", "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0...\n-----END RSA PRIVATE KEY-----\n")
        zf.writestr("system_manifest.json", '{"deployment": "secure_zone_1", "status": "active"}')
    print("Created demo_assets/classified_payload.zip")

    # 6. Secret DOCX (simulated binary)
    with open("demo_assets/mission_plan.docx", "wb") as f:
        f.write(b"PK\x03\x04\x14\x00\x00\x00\x08\x00DOCX-SIMULATED-BINARY-CONTENT-" + b"X" * 500)
    print("Created demo_assets/mission_plan.docx")

    print("\nAll demo assets generated successfully in demo_assets/")


if __name__ == "__main__":
    generate_assets()
