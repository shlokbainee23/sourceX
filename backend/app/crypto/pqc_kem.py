"""
ML-KEM-768 (NIST FIPS 203) Implementation Wrapper.
Handles Post-Quantum Key Encapsulation Mechanism for recipient key establishment.
"""

from typing import Tuple
from mlkem.ml_kem import ML_KEM, ML_KEM_768

# Initialize NIST FIPS 203 ML-KEM-768 parameter set
_kem_instance = ML_KEM(ML_KEM_768)

ENCAPSULATION_KEY_SIZE = 1184
DECAPSULATION_KEY_SIZE = 2400
CIPHERTEXT_SIZE = 1088

def kem_keygen() -> Tuple[bytes, bytes]:
    """
    Generate an ML-KEM-768 keypair.
    Returns:
        (encapsulation_key, decapsulation_key) as raw bytes.
        Length: ek is 1184 bytes, dk is 2400 bytes.
    """
    ek, dk = _kem_instance.key_gen()
    return ek, dk

def kem_encapsulate(ek: bytes) -> Tuple[bytes, bytes]:
    """
    Encapsulate a shared secret using recipient's ML-KEM-768 public key (ek).
    Returns:
        (shared_secret, ciphertext) as raw bytes.
        Length: shared_secret is 32 bytes, ciphertext is 1088 bytes.
    """
    if len(ek) != ENCAPSULATION_KEY_SIZE:
        raise ValueError("Invalid ML-KEM-768 encapsulation key length")
    ss, ct = _kem_instance.encaps(ek)
    return ss, ct

def kem_decapsulate(dk: bytes, ct: bytes) -> bytes:
    """
    Decapsulate ciphertext using recipient's ML-KEM-768 private key (dk).
    Returns:
        shared_secret (32 bytes)
    """
    if len(dk) != DECAPSULATION_KEY_SIZE or len(ct) != CIPHERTEXT_SIZE:
        raise ValueError("Invalid ML-KEM-768 decapsulation key or ciphertext length")
    ss = _kem_instance.decaps(dk, ct)
    return ss
