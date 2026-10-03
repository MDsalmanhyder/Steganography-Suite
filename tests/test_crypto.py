"""
Unit tests for cryptographic engine in CloakPix.
Tests AES-256-GCM encryption, decryption, PBKDF2 key derivation, and tamper resistance.
"""

import pytest
from cloakpix.core.crypto import (
    derive_key,
    encrypt_payload,
    decrypt_payload,
    evaluate_password_strength,
    KEY_SIZE_BYTES,
    SALT_SIZE_BYTES,
)
from cloakpix.core.exceptions import InvalidPasswordError


def test_derive_key_length_and_determinism():
    salt = b"0" * SALT_SIZE_BYTES
    password = "SuperSecretPassword123!"
    key1 = derive_key(password, salt, iterations=1000)
    key2 = derive_key(password, salt, iterations=1000)
    
    assert len(key1) == KEY_SIZE_BYTES
    assert key1 == key2


def test_derive_key_different_passwords():
    salt = b"0" * SALT_SIZE_BYTES
    key1 = derive_key("Password123", salt, iterations=1000)
    key2 = derive_key("Password124", salt, iterations=1000)
    assert key1 != key2


def test_encrypt_decrypt_roundtrip():
    secret_text = "This is a top-secret message to be concealed in the pixels."
    password = "CorrectHorseBatteryStaple!"
    
    payload = encrypt_payload(secret_text.encode("utf-8"), password)
    assert payload.ciphertext != secret_text.encode("utf-8")
    assert len(payload.salt) == 16
    assert len(payload.nonce) == 12
    assert len(payload.tag) == 16

    decrypted_bytes = decrypt_payload(payload, password)
    assert decrypted_bytes.decode("utf-8") == secret_text


def test_decrypt_with_wrong_password_fails():
    secret_bytes = b"Classified military coordinate data."
    payload = encrypt_payload(secret_bytes, "CorrectPassword123")
    
    with pytest.raises(InvalidPasswordError):
        decrypt_payload(payload, "WrongPassword456")


def test_decrypt_with_tampered_ciphertext_fails():
    secret_bytes = b"Financial transaction ledger payload."
    payload = encrypt_payload(secret_bytes, "MasterKey123")
    
    # Tamper with single byte in ciphertext
    tampered_bytes = bytearray(payload.ciphertext)
    tampered_bytes[0] ^= 0xFF
    tampered_payload = type(payload)(
        salt=payload.salt,
        nonce=payload.nonce,
        tag=payload.tag,
        ciphertext=bytes(tampered_bytes),
    )

    with pytest.raises(InvalidPasswordError):
        decrypt_payload(tampered_payload, "MasterKey123")


def test_decrypt_with_tampered_tag_fails():
    secret_bytes = b"Integrity check payload."
    payload = encrypt_payload(secret_bytes, "MasterKey123")
    
    tampered_tag = bytearray(payload.tag)
    tampered_tag[0] ^= 0x01
    tampered_payload = type(payload)(
        salt=payload.salt,
        nonce=payload.nonce,
        tag=bytes(tampered_tag),
        ciphertext=payload.ciphertext,
    )

    with pytest.raises(InvalidPasswordError):
        decrypt_payload(tampered_payload, "MasterKey123")


def test_password_strength_evaluation():
    score_empty, label_empty, _ = evaluate_password_strength("")
    assert score_empty == 0
    assert label_empty == "Empty"

    score_weak, label_weak, _ = evaluate_password_strength("abc")
    assert score_weak < 40
    assert label_weak == "Weak"

    score_strong, label_strong, _ = evaluate_password_strength("C0mpl3x_P@ssw0rd!#2026")
    assert score_strong >= 80
    assert label_strong in ("Strong", "Very Strong")
