"""
ML-DSA-44 (NIST FIPS 204) signatures for SIH26237.

Backend: OpenSSL via pyca/cryptography. New keys are stored as the 32-byte FIPS 204
seed and expanded by OpenSSL on use. Verification always uses OpenSSL.

Legacy: keystores written before format v2 hold the 2560-byte expanded secret key,
which OpenSSL cannot import. Those keys can still sign through dilithium_py until the
principal rotates. dilithium_py is not thread-safe (concurrent signing produced
invalid signatures in testing), so every legacy call is serialized.

Every signature carries a FIPS 204 context string (domain separation): a signature
made for one purpose never verifies for another. Records signed before domain
separation was introduced used the empty context; verifiers select it explicitly.
"""

import threading
from typing import Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import mldsa

ALGORITHM = "ML-DSA-44"
PUBLIC_KEY_SIZE = 1312
SIGNATURE_SIZE = 2420
SEED_SIZE = 32
SECRET_KEY_SIZE = SEED_SIZE
LEGACY_SECRET_KEY_SIZE = 2560
SECRET_SIZES = (SEED_SIZE, LEGACY_SECRET_KEY_SIZE)

CTX_LEGACY = b""
CTX_LEDGER_RECORD = b"sih26237/ledger-record/v3"
CTX_TRUST_MANIFEST = b"sih26237/trust-manifest/v2"
CTX_CHECKPOINT = b"sih26237/ledger-checkpoint/v1"
CTX_WITNESS_COSIGNATURE = b"sih26237/witness-cosignature/v1"
CTX_INVESTIGATION_REPORT = b"sih26237/investigation-report/v1"
CTX_KEY_POSSESSION = b"sih26237/key-possession/v1"

_LEGACY_LOCK = threading.Lock()


def dsa_keygen() -> Tuple[bytes, bytes]:
    """Returns (public_key 1312 bytes, seed 32 bytes)."""
    sk = mldsa.MLDSA44PrivateKey.generate()
    return sk.public_key().public_bytes_raw(), sk.private_bytes_raw()


def public_key_from_secret(secret: bytes) -> bytes:
    if len(secret) != SEED_SIZE:
        raise ValueError("Public key derivation requires a 32-byte ML-DSA-44 seed")
    return mldsa.MLDSA44PrivateKey.from_seed_bytes(secret).public_key().public_bytes_raw()


def dsa_sign(secret: bytes, message: bytes, *, context: bytes) -> bytes:
    if not isinstance(context, bytes) or len(context) > 255:
        raise ValueError("ML-DSA context must be at most 255 bytes")
    if len(secret) == SEED_SIZE:
        return mldsa.MLDSA44PrivateKey.from_seed_bytes(secret).sign(message, context)
    if len(secret) == LEGACY_SECRET_KEY_SIZE:
        from dilithium_py.ml_dsa import ML_DSA_44
        with _LEGACY_LOCK:
            return ML_DSA_44.sign(secret, message, ctx=context)
    raise ValueError("Invalid ML-DSA-44 secret key length")


def dsa_verify(pk: bytes, message: bytes, signature: bytes, *, context: bytes) -> bool:
    """Fails closed: malformed input or any library error returns False."""
    try:
        if not isinstance(pk, (bytes, bytearray)) or len(pk) != PUBLIC_KEY_SIZE:
            return False
        if not isinstance(signature, (bytes, bytearray)) or len(signature) != SIGNATURE_SIZE:
            return False
        mldsa.MLDSA44PublicKey.from_public_bytes(bytes(pk)).verify(bytes(signature), message, context)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False
    except Exception:
        return False


def dsa_verify_hex(pk: bytes, message: bytes, signature_hex: str, *, context: bytes) -> bool:
    try:
        sig = bytes.fromhex(signature_hex)
    except (ValueError, TypeError):
        return False
    return dsa_verify(pk, message, sig, context=context)
