"""
Encrypted local software keystore for SIH26237.

Model:
    passphrase --scrypt(random 16-byte salt)--> 256-bit key
    private key material --AES-256-GCM(random 12-byte nonce, AAD = canonical header)--> ciphertext

The header (format, version, principal, role, key ID, algorithms, KDF parameters,
salt, nonce) is authenticated as AAD, so downgrading KDF parameters, re-labelling a
keystore for another principal or swapping key IDs breaks decryption. A wrong
passphrase and a modified file are indistinguishable: both fail the GCM tag check.

Format v2 stores compact FIPS seeds (ML-DSA-44: 32 bytes, ML-KEM-768: 64 bytes) and
keeps superseded ML-KEM decapsulation keys ("retired") so documents encrypted to an
earlier key remain readable after rotation. Superseded signing keys are NOT kept.
Format v1 (expanded keys) is still readable so existing principals can log in and
rotate; it is never written again.

This is a software keystore on local disk, NOT an HSM: while a key is in use, it is
in server process memory.
"""

import json
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app import config
from app.crypto import pqc_dsa, pqc_kem
from app.ledger.canonical import canonicalize_json
from app.validation import is_valid_id

KEYSTORE_FORMAT = "sih26237-encrypted-keystore"
KEYSTORE_VERSION = 2
SUPPORTED_VERSIONS = (1, 2)
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
SALT_SIZE = 16
NONCE_SIZE = 12
MAX_RETIRED_KEYS = 32

SECRET_SIZES = {
    "mlkem_dk": pqc_kem.SECRET_SIZES,
    "mldsa_sk": pqc_dsa.SECRET_SIZES,
}
LEGACY_KEY_FIELDS = {"mlkem_dk": 2400, "mldsa_sk": 2560}
RETIRED_PREFIX = "retired_mlkem_dk:"


class KeystoreError(Exception):
    """Base class. Messages never contain key material or passphrases."""


class KeystoreNotFound(KeystoreError):
    pass


class KeystoreCorrupted(KeystoreError):
    pass


class KeystoreUnlockFailed(KeystoreError):
    """Wrong passphrase OR keystore ciphertext/header modified."""


def keystore_path(principal_id: str) -> Path:
    if not is_valid_id(principal_id):
        raise KeystoreError("Invalid principal identifier")
    return config.keystore_dir() / f"{principal_id}.keystore.json"


def _derive_key(passphrase: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return Scrypt(salt=salt, length=32, n=n, r=r, p=p).derive(passphrase.encode("utf-8"))


def _check_passphrase(passphrase: str) -> None:
    if not isinstance(passphrase, str) or len(passphrase) < config.MIN_PASSPHRASE_LENGTH:
        raise KeystoreError(f"Passphrase must be at least {config.MIN_PASSPHRASE_LENGTH} characters")
    if len(passphrase) > 1024:
        raise KeystoreError("Passphrase is too long")


def _encode_secrets(secrets_map: Dict[str, bytes]) -> bytes:
    out = {}
    for name, value in secrets_map.items():
        if name.startswith(RETIRED_PREFIX):
            key_id = name[len(RETIRED_PREFIX):]
            if not is_valid_key_id(key_id) or len(value) not in pqc_kem.SECRET_SIZES:
                raise KeystoreError("Unexpected retired key entry")
        elif name not in SECRET_SIZES or len(value) not in SECRET_SIZES[name]:
            raise KeystoreError(f"Unexpected key field or length for {name}")
        out[name] = value.hex()
    if sum(1 for n in out if n.startswith(RETIRED_PREFIX)) > MAX_RETIRED_KEYS:
        raise KeystoreError("Too many retired keys")
    return canonicalize_json(out)


def is_valid_key_id(key_id: str) -> bool:
    if not isinstance(key_id, str) or "#" not in key_id:
        return False
    pid, _, seq = key_id.rpartition("#")
    return is_valid_id(pid) and seq.isdigit() and 0 < len(seq) <= 6 and not seq.startswith("0")


def _write_atomic(path: Path, document: dict) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(document, indent=2))
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_keystore(principal_id: str, role: str, key_id: Optional[str], passphrase: str,
                   secrets_map: Dict[str, bytes], *, replace: bool = False) -> Path:
    """Encrypts private key material and writes it atomically. Refuses to overwrite unless replace=True."""
    _check_passphrase(passphrase)
    if key_id is not None and not is_valid_key_id(key_id):
        raise KeystoreError("Invalid key identifier")
    path = keystore_path(principal_id)
    if path.exists() and not replace:
        raise KeystoreError(f"Keystore for {principal_id} already exists")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    header = {
        "format": KEYSTORE_FORMAT,
        "version": KEYSTORE_VERSION,
        "principal_id": principal_id,
        "role": role,
        "key_id": key_id,
        "algorithms": {
            "signature": pqc_dsa.ALGORITHM if "mldsa_sk" in secrets_map else None,
            "kem": pqc_kem.ALGORITHM if "mlkem_dk" in secrets_map else None,
        },
        "kdf": {"name": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P, "salt": salt.hex()},
        "cipher": {"name": "AES-256-GCM", "nonce": nonce.hex()},
    }
    key = _derive_key(passphrase, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    ciphertext = AESGCM(key).encrypt(nonce, _encode_secrets(secrets_map), canonicalize_json(header))
    document = dict(header)
    document["ciphertext"] = ciphertext.hex()
    _write_atomic(path, document)
    return path


def create_keystore(principal_id: str, role: str, passphrase: str, secrets_map: Dict[str, bytes],
                    key_id: Optional[str] = None) -> Path:
    return write_keystore(principal_id, role, key_id, passphrase, secrets_map)


def _load_header(principal_id: str):
    path = keystore_path(principal_id)
    if not path.exists():
        raise KeystoreNotFound(f"No keystore provisioned for {principal_id}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        ciphertext = bytes.fromhex(document.pop("ciphertext"))
        header = document
        kdf = header["kdf"]
        cipher = header["cipher"]
        salt = bytes.fromhex(kdf["salt"])
        nonce = bytes.fromhex(cipher["nonce"])
        expected = {"format", "version", "principal_id", "role", "kdf", "cipher"}
        if header.get("version") == 2:
            expected |= {"key_id", "algorithms"}
        if (
            set(header) != expected
            or header["format"] != KEYSTORE_FORMAT
            or header["version"] not in SUPPORTED_VERSIONS
            or kdf["name"] != "scrypt"
            or cipher["name"] != "AES-256-GCM"
            or len(salt) != SALT_SIZE
            or len(nonce) != NONCE_SIZE
            or len(ciphertext) < 16
        ):
            raise KeystoreCorrupted(f"Keystore for {principal_id} has an invalid structure")
        if header["principal_id"] != principal_id:
            raise KeystoreCorrupted(f"Keystore file does not belong to {principal_id}")
        if kdf["n"] < SCRYPT_N or kdf["r"] < SCRYPT_R or kdf["p"] < SCRYPT_P:
            raise KeystoreCorrupted(f"Keystore for {principal_id} uses weakened KDF parameters")
    except KeystoreError:
        raise
    except Exception:
        raise KeystoreCorrupted(f"Keystore for {principal_id} is unreadable or malformed")
    return header, salt, nonce, ciphertext


def keystore_role(principal_id: str) -> str:
    return _load_header(principal_id)[0]["role"]


def keystore_info(principal_id: str) -> dict:
    """Public header facts: format version, key ID and whether it holds legacy (expanded) keys."""
    header = _load_header(principal_id)[0]
    return {"version": header["version"], "key_id": header.get("key_id") or f"{principal_id}#1",
            "role": header["role"]}


def unlock_keystore(principal_id: str, passphrase: str) -> Dict[str, bytes]:
    """
    Returns {"mldsa_sk"?, "mlkem_dk"?, "retired_mlkem_dk:<key_id>"*} as bytes.
    Raises KeystoreError subclasses on any failure.
    """
    header, salt, nonce, ciphertext = _load_header(principal_id)
    kdf = header["kdf"]
    try:
        key = _derive_key(passphrase, salt, kdf["n"], kdf["r"], kdf["p"])
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, canonicalize_json(header))
    except InvalidTag:
        raise KeystoreUnlockFailed("Wrong passphrase or keystore integrity failure")
    except Exception:
        raise KeystoreCorrupted(f"Keystore for {principal_id} could not be processed")

    try:
        decoded = json.loads(plaintext.decode("utf-8"))
        result = {}
        for name, value in decoded.items():
            raw = bytes.fromhex(value)
            if header["version"] == 1:
                if name not in LEGACY_KEY_FIELDS or len(raw) != LEGACY_KEY_FIELDS[name]:
                    raise ValueError
            elif name.startswith(RETIRED_PREFIX):
                if not is_valid_key_id(name[len(RETIRED_PREFIX):]) or len(raw) not in pqc_kem.SECRET_SIZES:
                    raise ValueError
            elif name not in SECRET_SIZES or len(raw) not in SECRET_SIZES[name]:
                raise ValueError
            result[name] = raw
    except Exception:
        raise KeystoreCorrupted(f"Keystore payload for {principal_id} is malformed")
    return result


def retired_kem_keys(keys: Dict[str, bytes]) -> Dict[str, bytes]:
    return {name[len(RETIRED_PREFIX):]: v for name, v in keys.items() if name.startswith(RETIRED_PREFIX)}
