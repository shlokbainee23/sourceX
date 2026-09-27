"""
Encrypted local software keystore for SIH26237.

Model:
    passphrase --scrypt(random 16-byte salt)--> 256-bit key
    private key material --AES-256-GCM(random 12-byte nonce, AAD = canonical header)--> ciphertext

The header (format, version, principal, role, KDF parameters, salt, nonce) is
authenticated as AAD, so downgrading KDF parameters or re-labelling a keystore for
another principal breaks decryption. A wrong passphrase and a modified file are
cryptographically indistinguishable: both fail the GCM tag check and unlock is denied.

This is a software keystore on local disk. It is NOT an HSM: while a principal is
logged in, its private keys are held in server process memory.
"""

import json
import os
from pathlib import Path
from typing import Dict

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app import config
from app.ledger.canonical import canonicalize_json
from app.validation import is_valid_id

KEYSTORE_FORMAT = "sih26237-encrypted-keystore"
KEYSTORE_VERSION = 1
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
SALT_SIZE = 16
NONCE_SIZE = 12

# Private key fields and their exact byte lengths, per role.
KEY_FIELDS = {
    "mlkem_dk": 2400,
    "mldsa_sk": 2560,
}


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


def _header_aad(header: dict) -> bytes:
    return canonicalize_json(header)


def _encode_secrets(secrets_map: Dict[str, bytes]) -> bytes:
    for name, value in secrets_map.items():
        if name not in KEY_FIELDS or len(value) != KEY_FIELDS[name]:
            raise KeystoreError(f"Unexpected key field or length for {name}")
    return canonicalize_json({name: value.hex() for name, value in secrets_map.items()})


def create_keystore(principal_id: str, role: str, passphrase: str, secrets_map: Dict[str, bytes]) -> Path:
    """Encrypts private key material and writes it atomically. Refuses to overwrite."""
    if not isinstance(passphrase, str) or len(passphrase) < config.MIN_PASSPHRASE_LENGTH:
        raise KeystoreError(f"Passphrase must be at least {config.MIN_PASSPHRASE_LENGTH} characters")
    path = keystore_path(principal_id)
    if path.exists():
        raise KeystoreError(f"Keystore for {principal_id} already exists")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    header = {
        "format": KEYSTORE_FORMAT,
        "version": KEYSTORE_VERSION,
        "principal_id": principal_id,
        "role": role,
        "kdf": {"name": "scrypt", "n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P, "salt": salt.hex()},
        "cipher": {"name": "AES-256-GCM", "nonce": nonce.hex()},
    }
    key = _derive_key(passphrase, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    ciphertext = AESGCM(key).encrypt(nonce, _encode_secrets(secrets_map), _header_aad(header))

    document = dict(header)
    document["ciphertext"] = ciphertext.hex()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(document, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path


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
        if (
            header["format"] != KEYSTORE_FORMAT
            or header["version"] != KEYSTORE_VERSION
            or kdf["name"] != "scrypt"
            or cipher["name"] != "AES-256-GCM"
            or len(salt) != SALT_SIZE
            or len(nonce) != NONCE_SIZE
            or len(ciphertext) < 16
        ):
            raise KeystoreCorrupted(f"Keystore for {principal_id} has an invalid structure")
        if header["principal_id"] != principal_id:
            raise KeystoreCorrupted(f"Keystore file does not belong to {principal_id}")
        # Refuse weakened KDF parameters even before the AAD check.
        if kdf["n"] < SCRYPT_N or kdf["r"] < SCRYPT_R or kdf["p"] < SCRYPT_P:
            raise KeystoreCorrupted(f"Keystore for {principal_id} uses weakened KDF parameters")
    except KeystoreError:
        raise
    except Exception:
        raise KeystoreCorrupted(f"Keystore for {principal_id} is unreadable or malformed")
    return header, salt, nonce, ciphertext


def keystore_role(principal_id: str) -> str:
    header, _, _, _ = _load_header(principal_id)
    return header["role"]


def unlock_keystore(principal_id: str, passphrase: str) -> Dict[str, bytes]:
    """Returns the decrypted private key map. Raises KeystoreError subclasses on any failure."""
    header, salt, nonce, ciphertext = _load_header(principal_id)
    kdf = header["kdf"]
    try:
        key = _derive_key(passphrase, salt, kdf["n"], kdf["r"], kdf["p"])
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, _header_aad(header))
    except InvalidTag:
        raise KeystoreUnlockFailed("Wrong passphrase or keystore integrity failure")
    except Exception:
        raise KeystoreCorrupted(f"Keystore for {principal_id} could not be processed")

    try:
        decoded = json.loads(plaintext.decode("utf-8"))
        result = {}
        for name, value in decoded.items():
            raw = bytes.fromhex(value)
            if name not in KEY_FIELDS or len(raw) != KEY_FIELDS[name]:
                raise ValueError
            result[name] = raw
    except Exception:
        raise KeystoreCorrupted(f"Keystore payload for {principal_id} is malformed")
    return result
