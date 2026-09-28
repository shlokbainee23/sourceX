"""
ML-KEM-768 (NIST FIPS 203) key establishment for SIH26237.

Backend: OpenSSL via pyca/cryptography. New decapsulation keys are stored as the
64-byte FIPS 203 seed (d || z). Encapsulation always uses OpenSSL, which performs the
FIPS 203 encapsulation-key input check (modulus check) and rejects malformed keys.

Legacy: keystores written before format v2 hold the 2400-byte expanded decapsulation
key, which OpenSSL cannot import; those are decapsulated through the `mlkem` package
(serialized, because thread-safety is not documented) until the principal rotates.
"""

import threading
from typing import Tuple

from cryptography.hazmat.primitives.asymmetric import mlkem

ALGORITHM = "ML-KEM-768"
ENCAPSULATION_KEY_SIZE = 1184
CIPHERTEXT_SIZE = 1088
SHARED_SECRET_SIZE = 32
SEED_SIZE = 64
DECAPSULATION_KEY_SIZE = SEED_SIZE
LEGACY_DECAPSULATION_KEY_SIZE = 2400
SECRET_SIZES = (SEED_SIZE, LEGACY_DECAPSULATION_KEY_SIZE)

_LEGACY_LOCK = threading.Lock()
_legacy_instance = None


def kem_keygen() -> Tuple[bytes, bytes]:
    """Returns (encapsulation_key 1184 bytes, seed 64 bytes)."""
    dk = mlkem.MLKEM768PrivateKey.generate()
    return dk.public_key().public_bytes_raw(), dk.private_bytes_raw()


def public_key_from_secret(secret: bytes) -> bytes:
    if len(secret) != SEED_SIZE:
        raise ValueError("Public key derivation requires a 64-byte ML-KEM-768 seed")
    return mlkem.MLKEM768PrivateKey.from_seed_bytes(secret).public_key().public_bytes_raw()


def kem_encapsulate(ek: bytes) -> Tuple[bytes, bytes]:
    """Returns (shared_secret 32 bytes, ciphertext 1088 bytes). Raises ValueError on an invalid key."""
    if len(ek) != ENCAPSULATION_KEY_SIZE:
        raise ValueError("Invalid ML-KEM-768 encapsulation key length")
    ss, ct = mlkem.MLKEM768PublicKey.from_public_bytes(bytes(ek)).encapsulate()
    return ss, ct


def kem_decapsulate(secret: bytes, ct: bytes) -> bytes:
    """
    Returns the 32-byte shared secret. A modified ciphertext yields an unrelated secret
    (FIPS 203 implicit rejection); the AES-GCM key wrap then fails authentication.
    """
    if len(ct) != CIPHERTEXT_SIZE:
        raise ValueError("Invalid ML-KEM-768 ciphertext length")
    if len(secret) == SEED_SIZE:
        return mlkem.MLKEM768PrivateKey.from_seed_bytes(secret).decapsulate(bytes(ct))
    if len(secret) == LEGACY_DECAPSULATION_KEY_SIZE:
        global _legacy_instance
        with _LEGACY_LOCK:
            if _legacy_instance is None:
                from mlkem.ml_kem import ML_KEM, ML_KEM_768
                _legacy_instance = ML_KEM(ML_KEM_768)
            return _legacy_instance.decaps(bytes(secret), bytes(ct))
    raise ValueError("Invalid ML-KEM-768 decapsulation key length")
