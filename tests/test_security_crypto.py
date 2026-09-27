"""
Adversarial cryptographic tests: wrong recipient, corrupted ciphertext / tag / wrapped key,
context swapping, invalid and altered signatures.
"""

import os

import pytest
from cryptography.exceptions import InvalidTag

from app.crypto.kdf import derive_cek_wrapping_key
from app.crypto.pqc_dsa import dsa_keygen, dsa_sign, dsa_verify, dsa_verify_hex
from app.crypto.pqc_kem import kem_decapsulate, kem_encapsulate, kem_keygen
from app.crypto.symmetric import cek_aad, decrypt_document, document_aad, encrypt_document, generate_cek, unwrap_cek, wrap_cek
from app.ledger.canonical import canonicalize_json
from app.ledger.records import build_decryption_record


@pytest.fixture
def package():
    ek, dk = kem_keygen()
    cek = generate_cek()
    ct, nonce = encrypt_document(b"%PDF-1.7 secret orders", cek, document_aad("DOC-1"))
    ss, kem_ct = kem_encapsulate(ek)
    wrapped, wnonce = wrap_cek(cek, derive_cek_wrapping_key(ss, "DOC-1", "R001"), cek_aad("DOC-1", "R001"))
    return {"dk": dk, "cek": cek, "ct": ct, "nonce": nonce, "kem_ct": kem_ct, "wrapped": wrapped, "wnonce": wnonce}


def _unwrap(p, dk=None, doc="DOC-1", rid="R001", wrapped=None, kem_ct=None):
    ss = kem_decapsulate(dk or p["dk"], kem_ct or p["kem_ct"])
    return unwrap_cek(wrapped or p["wrapped"], p["wnonce"], derive_cek_wrapping_key(ss, doc, rid), cek_aad(doc, rid))


def test_legitimate_unwrap(package):
    assert _unwrap(package) == package["cek"]


def test_wrong_recipient_cannot_unwrap(package):
    _, other_dk = kem_keygen()
    with pytest.raises(InvalidTag):
        _unwrap(package, dk=other_dk)


def test_package_bound_to_recipient_and_document(package):
    with pytest.raises(InvalidTag):
        _unwrap(package, rid="R002")
    with pytest.raises(InvalidTag):
        _unwrap(package, doc="DOC-2")


def test_modified_wrapped_key_rejected(package):
    bad = bytearray(package["wrapped"])
    bad[0] ^= 0x01
    with pytest.raises(InvalidTag):
        _unwrap(package, wrapped=bytes(bad))


def test_modified_kem_ciphertext_rejected(package):
    bad = bytearray(package["kem_ct"])
    bad[10] ^= 0xFF
    with pytest.raises(InvalidTag):
        _unwrap(package, kem_ct=bytes(bad))


def test_corrupted_document_ciphertext_rejected(package):
    bad = bytearray(package["ct"])
    bad[3] ^= 0x01
    with pytest.raises(InvalidTag):
        decrypt_document(bytes(bad), package["nonce"], package["cek"], document_aad("DOC-1"))


def test_corrupted_auth_tag_rejected(package):
    bad = bytearray(package["ct"])
    bad[-1] ^= 0x80
    with pytest.raises(InvalidTag):
        decrypt_document(bytes(bad), package["nonce"], package["cek"], document_aad("DOC-1"))


def test_ciphertext_bound_to_document_id(package):
    with pytest.raises(InvalidTag):
        decrypt_document(package["ct"], package["nonce"], package["cek"], document_aad("DOC-OTHER"))


def test_wrong_cek_rejected(package):
    with pytest.raises(InvalidTag):
        decrypt_document(package["ct"], package["nonce"], os.urandom(32), document_aad("DOC-1"))


def _record():
    return build_decryption_record(document_id="DOC-1", recipient_id="R002", session_id="SES-1",
                                   watermark_token="WM-" + "ab" * 32, source_document_hash="00" * 32,
                                   delivered_document_hash="11" * 32, decryption_timestamp="2026-01-01T00:00:00+00:00")


def test_altered_signed_record_rejected():
    pk, sk = dsa_keygen()
    rec = _record()
    sig = dsa_sign(sk, canonicalize_json(rec))
    assert dsa_verify(pk, canonicalize_json(rec), sig)
    for field, value in (("recipient_id", "R003"), ("delivered_document_hash", "22" * 32),
                         ("watermark_token", "WM-" + "cd" * 32), ("decryption_timestamp", "2027-01-01T00:00:00+00:00")):
        altered = dict(rec, **{field: value})
        assert dsa_verify(pk, canonicalize_json(altered), sig) is False, field


def test_invalid_signatures_rejected():
    pk, sk = dsa_keygen()
    msg = canonicalize_json(_record())
    sig = dsa_sign(sk, msg)
    other_pk, _ = dsa_keygen()
    assert dsa_verify(other_pk, msg, sig) is False
    assert dsa_verify(pk, msg, os.urandom(len(sig))) is False
    assert dsa_verify(pk, msg, sig[:-1]) is False
    assert dsa_verify(pk, msg, b"") is False
    assert dsa_verify(pk[:-1], msg, sig) is False
    assert dsa_verify_hex(pk, msg, "zz" * 10) is False
    assert dsa_verify_hex(pk, msg, sig.hex()) is True


def test_api_corrupted_ciphertext_denies_and_records_nothing(client, clean_ledger):
    import testenv
    from app.config import documents_dir
    from app.database.connection import get_connection

    hq = testenv.login_headers(client, "WESEE_HQ")
    r002 = testenv.login_headers(client, "R002")
    client.post("/api/documents/register", data={"document_id": "DOC-C1"}, files=testenv.upload(testenv.sample_pdf()), headers=hq)
    client.post("/api/documents/encrypt", json={"document_id": "DOC-C1", "authorized_recipient_ids": ["R002"]}, headers=hq)
    path = documents_dir() / "DOC-C1_encrypted.bin"
    data = bytearray(path.read_bytes())
    data[-5] ^= 0x01
    path.write_bytes(bytes(data))

    r = client.post("/api/decrypt", json={"document_id": "DOC-C1"}, headers=r002)
    assert r.status_code == 409
    conn = get_connection()
    assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM ledger_blocks WHERE event_type='DOCUMENT_DECRYPTED'").fetchone()[0] == 0
    conn.close()


def test_api_modified_wrapped_key_denies(client, clean_ledger):
    import testenv
    from app.database.connection import get_connection

    hq = testenv.login_headers(client, "WESEE_HQ")
    r001 = testenv.login_headers(client, "R001")
    client.post("/api/documents/register", data={"document_id": "DOC-C2"}, files=testenv.upload(testenv.sample_pdf()), headers=hq)
    client.post("/api/documents/encrypt", json={"document_id": "DOC-C2", "authorized_recipient_ids": ["R001"]}, headers=hq)
    conn = get_connection()
    wrapped = conn.execute("SELECT wrapped_cek FROM encrypted_packages WHERE document_id='DOC-C2'").fetchone()[0]
    flipped = ("0" if wrapped[0] != "0" else "1") + wrapped[1:]
    conn.execute("UPDATE encrypted_packages SET wrapped_cek = ? WHERE document_id='DOC-C2'", (flipped,))
    conn.close()
    assert client.post("/api/decrypt", json={"document_id": "DOC-C2"}, headers=r001).status_code == 403


def test_api_transplanted_package_denies(client, clean_ledger):
    """Copying R001's package into R003's slot must not let R003 decrypt."""
    import testenv
    from app.database.connection import get_connection

    hq = testenv.login_headers(client, "WESEE_HQ")
    r003 = testenv.login_headers(client, "R003")
    client.post("/api/documents/register", data={"document_id": "DOC-C3"}, files=testenv.upload(testenv.sample_pdf()), headers=hq)
    client.post("/api/documents/encrypt", json={"document_id": "DOC-C3", "authorized_recipient_ids": ["R001"]}, headers=hq)
    conn = get_connection()
    conn.execute("""INSERT INTO encrypted_packages (document_id, recipient_id, kem_ciphertext, wrapped_cek, wrap_nonce, created_at)
                    SELECT document_id, 'R003', kem_ciphertext, wrapped_cek, wrap_nonce, created_at
                    FROM encrypted_packages WHERE document_id='DOC-C3' AND recipient_id='R001'""")
    conn.close()
    assert client.post("/api/decrypt", json={"document_id": "DOC-C3"}, headers=r003).status_code == 403
