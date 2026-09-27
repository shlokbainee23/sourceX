"""
ML-DSA-44 (NIST FIPS 204) Implementation Wrapper.
Handles post-quantum digital signatures over canonical provenance records.
"""

from typing import Tuple
from dilithium_py.ml_dsa import ML_DSA_44

PUBLIC_KEY_SIZE = 1312
SECRET_KEY_SIZE = 2560
SIGNATURE_SIZE = 2420


def dsa_keygen() -> Tuple[bytes, bytes]:
    """
    Generate an ML-DSA-44 keypair.
    Returns:
        (public_key, private_key) as raw bytes (1312 / 2560 bytes).
    """
    pk, sk = ML_DSA_44.keygen()
    return pk, sk


def dsa_sign(sk: bytes, message: bytes) -> bytes:
    """
    Sign canonical message bytes using an ML-DSA-44 private key.
    Returns:
        signature as raw bytes (2420 bytes).
    """
    if len(sk) != SECRET_KEY_SIZE:
        raise ValueError("Invalid ML-DSA-44 private key length")
    return ML_DSA_44.sign(sk, message)


def dsa_verify(pk: bytes, message: bytes, signature: bytes) -> bool:
    """
    Verify an ML-DSA-44 signature. Fails closed: any malformed input or library
    error returns False, never True.
    """
    try:
        if not isinstance(pk, (bytes, bytearray)) or len(pk) != PUBLIC_KEY_SIZE:
            return False
        if not isinstance(signature, (bytes, bytearray)) or len(signature) != SIGNATURE_SIZE:
            return False
        return ML_DSA_44.verify(bytes(pk), message, bytes(signature)) is True
    except Exception:
        return False


def dsa_verify_hex(pk: bytes, message: bytes, signature_hex: str) -> bool:
    try:
        sig = bytes.fromhex(signature_hex)
    except (ValueError, TypeError):
        return False
    return dsa_verify(pk, message, sig)
