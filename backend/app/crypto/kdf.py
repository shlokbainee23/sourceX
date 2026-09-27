"""
Key Derivation Function (KDF) using HKDF-SHA256.
Derives AES-256 wrapping keys from ML-KEM-768 shared secrets with domain separation.
The info string binds the derived key to the (document, recipient) context.
"""

from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

INFO_STRING = b"sih26237-cek-wrapping-v3"


def derive_cek_wrapping_key(shared_secret: bytes, document_id: str = "", recipient_id: str = "", salt: bytes = None) -> bytes:
    """
    Derives a 256-bit (32-byte) wrapping key from the 32-byte ML-KEM shared secret.
    """
    if len(shared_secret) != 32:
        raise ValueError("ML-KEM shared secret must be 32 bytes")
    info = INFO_STRING + b"|" + document_id.encode("utf-8") + b"|" + recipient_id.encode("utf-8")
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=info,
    )
    return hkdf.derive(shared_secret)
