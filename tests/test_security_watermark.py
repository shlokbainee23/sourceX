"""
Forensic marker adversarial tests: missing, malformed, altered, conflicting, unknown,
duplicate and transplanted markers.
"""

import pymupdf
import pytest

import testenv
from app.watermark.embed import METADATA_KEY, WATERMARK_PREFIX, WATERMARK_SUFFIX, embed_watermark, generate_watermark_token
from app.watermark.extract import CONFLICT, FOUND, MALFORMED, NOT_FOUND, UNREADABLE, extract_watermark_detailed


def craft_pdf(text_marker=None, meta_marker=None) -> bytes:
    doc = pymupdf.open(stream=testenv.sample_pdf(), filetype="pdf")
    if text_marker is not None:
        doc[0].insert_text((10, 830), f"{WATERMARK_PREFIX}{text_marker}{WATERMARK_SUFFIX}", fontsize=4, render_mode=3)
    if meta_marker is not None:
        doc.set_metadata({"keywords": f"{METADATA_KEY}:{meta_marker}"})
    data = doc.tobytes()
    doc.close()
    return data


def test_valid_marker_found():
    tok = generate_watermark_token()
    res = extract_watermark_detailed(embed_watermark(testenv.sample_pdf(), tok))
    assert res.status == FOUND and res.token == tok


def test_missing_marker():
    assert extract_watermark_detailed(testenv.sample_pdf()).status == NOT_FOUND


@pytest.mark.parametrize("bad", [
    "WM-" + "a" * 63,             # too short
    "WM-" + "a" * 65,             # too long
    "WM-" + "A" * 64,             # uppercase hex
    "WM-" + "g" * 64,             # non-hex
    "XX-" + "a" * 64,             # wrong prefix
    "",
])
def test_malformed_marker_rejected(bad):
    assert extract_watermark_detailed(craft_pdf(text_marker=bad)).status in (MALFORMED, NOT_FOUND)
    assert extract_watermark_detailed(craft_pdf(meta_marker=bad)).status in (MALFORMED, NOT_FOUND)


def test_embed_refuses_malformed_token():
    with pytest.raises(ValueError):
        embed_watermark(testenv.sample_pdf(), "WM-short")


def test_conflicting_layers_rejected():
    a, b = generate_watermark_token(), generate_watermark_token()
    res = extract_watermark_detailed(craft_pdf(text_marker=a, meta_marker=b))
    assert res.status == CONFLICT and res.token is None


def test_double_watermarking_is_conflict():
    a, b = generate_watermark_token(), generate_watermark_token()
    twice = embed_watermark(embed_watermark(testenv.sample_pdf(), a), b)
    assert extract_watermark_detailed(twice).status == CONFLICT


def test_not_a_pdf():
    assert extract_watermark_detailed(b"hello world").status == UNREADABLE
    assert extract_watermark_detailed(b"%PDF-1.7 garbage").status == UNREADABLE


def test_tokens_unique_and_well_formed():
    tokens = {generate_watermark_token() for _ in range(1000)}
    assert len(tokens) == 1000


def _investigate(client, headers, pdf):
    return client.post("/api/investigate", files=testenv.upload(pdf), headers=headers).json()


def test_altered_marker_unknown_token(client, clean_ledger):
    flow = testenv.run_basic_flow(client, "DOC-W1", ("R002",))
    tok = flow["dec"]["R002"]["watermark_token"]
    altered = tok[:-1] + ("0" if tok[-1] != "0" else "1")
    res = _investigate(client, flow["inv"], embed_watermark(flow["raw"], altered))
    assert res["status"] == "UNVERIFIED"
    assert res["verification"]["watermark_valid"] is True and res["verification"]["session_found"] is False


def test_correct_marker_on_wrong_document(client, clean_ledger):
    """Transplanting R002's real token into a different document must not attribute."""
    flow = testenv.run_basic_flow(client, "DOC-W2", ("R002",))
    tok = flow["dec"]["R002"]["watermark_token"]
    forged = embed_watermark(testenv.sample_pdf("A COMPLETELY DIFFERENT DOCUMENT"), tok)
    res = _investigate(client, flow["inv"], forged)
    assert res["status"] == "UNVERIFIED" and res["attribution"] is None
    assert res["verification"]["session_found"] is True
    assert res["verification"]["document_hash_match"] is False


def test_malformed_marker_in_investigation(client, clean_ledger):
    flow = testenv.run_basic_flow(client, "DOC-W3", ("R001",))
    res = _investigate(client, flow["inv"], craft_pdf(text_marker="WM-deadbeef"))
    assert res["status"] == "UNVERIFIED" and res["watermark_status"] == MALFORMED


def test_conflicting_marker_in_investigation(client, clean_ledger):
    """A leaked copy carrying a second injected marker is ambiguous and rejected."""
    flow = testenv.run_basic_flow(client, "DOC-W4", ("R001", "R002"))
    doc = pymupdf.open(stream=flow["copies"]["R001"], filetype="pdf")
    doc[0].insert_text((10, 820), f"{WATERMARK_PREFIX}{flow['dec']['R002']['watermark_token']}{WATERMARK_SUFFIX}",
                       fontsize=4, render_mode=3)
    mixed = doc.tobytes()
    doc.close()
    res = _investigate(client, flow["inv"], mixed)
    assert res["status"] == "UNVERIFIED" and res["watermark_status"] == CONFLICT


def test_duplicate_token_rejected_by_database(client, clean_ledger):
    import sqlite3
    from app.database.connection import get_connection
    flow = testenv.run_basic_flow(client, "DOC-W5", ("R001",))
    conn = get_connection()
    row = dict(conn.execute("SELECT * FROM sessions").fetchone())
    row.pop("id")
    row["session_id"] = "SES-DUPLICATE"
    cols = ",".join(row)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(f"INSERT INTO sessions ({cols}) VALUES ({','.join('?' * len(row))})", tuple(row.values()))
    conn.close()
    assert flow["dec"]["R001"]["watermark_token"]
