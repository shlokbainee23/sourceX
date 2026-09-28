"""
Cryptographic unit tests for SIH26237.
ML-KEM-768, ML-DSA-44, HKDF-SHA256, AES-256-GCM and the encrypted keystore.
Run with pytest or directly: python tests/test_crypto.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testenv  # noqa: E402,F401

from app.crypto.identity import get_recipient_public_keys  # noqa: E402
from app.crypto.kdf import derive_cek_wrapping_key  # noqa: E402
from app.crypto.pqc_dsa import dsa_keygen, dsa_sign, dsa_verify  # noqa: E402
from app.crypto.pqc_kem import kem_decapsulate, kem_encapsulate, kem_keygen  # noqa: E402
from app.crypto.symmetric import (  # noqa: E402
    cek_aad, compute_sha256, decrypt_document, document_aad, encrypt_document, generate_cek, unwrap_cek, wrap_cek,
)


def test_pqc_kem():
    ek, dk = kem_keygen()
    assert len(ek) == 1184 and len(dk) in (64, 2400)
    ss_sender, ct = kem_encapsulate(ek)
    assert len(ss_sender) == 32 and len(ct) == 1088
    assert kem_decapsulate(dk, ct) == ss_sender
    print("[OK] ML-KEM-768 encapsulation/decapsulation.")


def test_pqc_dsa():
    pk, sk = dsa_keygen()
    assert len(pk) == 1312 and len(sk) in (32, 2560)
    msg = b"SIH26237 canonical decryption record"
    sig = dsa_sign(sk, msg, context=b"sih26237/ledger-record/v3")
    assert len(sig) == 2420
    assert dsa_verify(pk, msg, sig, context=b"sih26237/ledger-record/v3") is True
    assert dsa_verify(pk, msg + b"_tampered", sig, context=b"sih26237/ledger-record/v3") is False
    print("[OK] ML-DSA-44 sign/verify and tamper rejection.")


def test_hybrid_encryption_pipeline():
    ek, dk = kem_keygen()
    plaintext = b"%PDF-1.4\nCONFIDENTIAL NAVAL TACTICAL ORDERS"
    cek = generate_cek()
    ct, nonce = encrypt_document(plaintext, cek, document_aad("DOC-1"))

    ss, kem_ct = kem_encapsulate(ek)
    wk = derive_cek_wrapping_key(ss, "DOC-1", "R001")
    wrapped, wnonce = wrap_cek(cek, wk, cek_aad("DOC-1", "R001"))

    ss2 = kem_decapsulate(dk, kem_ct)
    cek2 = unwrap_cek(wrapped, wnonce, derive_cek_wrapping_key(ss2, "DOC-1", "R001"), cek_aad("DOC-1", "R001"))
    assert cek2 == cek
    out = decrypt_document(ct, nonce, cek2, document_aad("DOC-1"))
    assert compute_sha256(out) == compute_sha256(plaintext)
    print("[OK] Hybrid ML-KEM + HKDF + AES-256-GCM pipeline.")


def test_hkdf_key_separation():
    ss = b"\x01" * 32
    assert derive_cek_wrapping_key(ss, "DOC-1", "R001") != derive_cek_wrapping_key(ss, "DOC-1", "R002")
    assert derive_cek_wrapping_key(ss, "DOC-1", "R001") != derive_cek_wrapping_key(ss, "DOC-2", "R001")
    print("[OK] HKDF derives distinct keys per (document, recipient).")


def test_nonces_are_unique():
    cek = generate_cek()
    nonces = {encrypt_document(b"x", cek)[1] for _ in range(200)}
    assert len(nonces) == 200
    print("[OK] AES-GCM nonces are fresh per encryption.")


def test_identity_keystore(creds):
    from app.crypto.keystore import unlock_keystore
    for rid in ("R001", "R002", "R003"):
        pub = get_recipient_public_keys(rid)
        priv = unlock_keystore(rid, creds[rid])
        assert len(pub["mlkem_ek"]) == 1184 and len(pub["mldsa_pk"]) == 1312
        assert len(priv["mlkem_dk"]) in (64, 2400) and len(priv["mldsa_sk"]) in (32, 2560)
    print("[OK] Encrypted keystores unlock and match registry sizes.")


if __name__ == "__main__":
    c = testenv.provision_test_principals()
    test_pqc_kem()
    test_pqc_dsa()
    test_hybrid_encryption_pipeline()
    test_hkdf_key_separation()
    test_nonces_are_unique()
    test_identity_keystore(c)
    print("\nALL CRYPTOGRAPHIC TESTS PASSED.")
