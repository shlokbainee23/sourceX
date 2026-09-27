"""
Symmetric Authenticated Encryption & Hashing Module for SIH26237.
Uses AES-256-GCM for authenticated encryption and SHA-256 for integrity hashing.
Every AES-GCM call uses a fresh 96-bit nonce from os.urandom and binds its
context (document / recipient) as associated data.
"""

import os
import hashlib
from typing import Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12  # Standard 96-bit nonce for AES-GCM
KEY_SIZE = 32    # 256 bits

DOC_AAD_PREFIX = b"sih26237-document-v3|"
CEK_AAD_PREFIX = b"sih26237-cek-v3|"


def generate_cek() -> bytes:
    """Generate a cryptographically secure 256-bit AES Content Encryption Key."""
    return AESGCM.generate_key(bit_length=256)


def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 hex digest of input bytes."""
    return hashlib.sha256(data).hexdigest()


def document_aad(document_id: str) -> bytes:
    return DOC_AAD_PREFIX + document_id.encode("utf-8")


def cek_aad(document_id: str, recipient_id: str) -> bytes:
    return CEK_AAD_PREFIX + document_id.encode("utf-8") + b"|" + recipient_id.encode("utf-8")


def encrypt_document(plaintext: bytes, cek: bytes, aad: bytes = None) -> Tuple[bytes, bytes]:
    """
    Encrypt document content using AES-256-GCM.
    Returns:
        (ciphertext_with_tag, nonce)
    """
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(cek)
    ciphertext = aesgcm.encrypt(nonce, plaintext, aad)
    return ciphertext, nonce


def decrypt_document(ciphertext: bytes, nonce: bytes, cek: bytes, aad: bytes = None) -> bytes:
    """
    Decrypt document content using AES-256-GCM.
    Raises:
        cryptography.exceptions.InvalidTag if authentication fails
    """
    aesgcm = AESGCM(cek)
    return aesgcm.decrypt(nonce, ciphertext, aad)


def wrap_cek(cek: bytes, wrapping_key: bytes, aad: bytes = b"cek-protection") -> Tuple[bytes, bytes]:
    """
    Wrap the CEK using the derived wrapping key via AES-256-GCM.
    Returns:
        (wrapped_cek, nonce)
    """
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(wrapping_key)
    wrapped = aesgcm.encrypt(nonce, cek, aad)
    return wrapped, nonce


def unwrap_cek(wrapped_cek: bytes, nonce: bytes, wrapping_key: bytes, aad: bytes = b"cek-protection") -> bytes:
    """
    Unwrap the CEK using the derived wrapping key via AES-256-GCM.
    Raises:
        cryptography.exceptions.InvalidTag if the wrapping key, nonce, AAD or wrapped CEK is wrong
    """
    aesgcm = AESGCM(wrapping_key)
    cek = aesgcm.decrypt(nonce, wrapped_cek, aad)
    if len(cek) != KEY_SIZE:
        raise ValueError("Unwrapped CEK has invalid length")
    return cek
