"""
SBOM / CBOM tests: the cryptographic inventory must match the implementation, and
drift or in-transit modification of the committed BOM must be detected.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import testenv  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_bom  # noqa: E402

from app.crypto import keystore, pqc_dsa, pqc_kem, symmetric  # noqa: E402


def _by_ref(bom):
    return {c["bom-ref"]: c for c in bom["components"]}


def test_cbom_matches_implementation_constants():
    c = _by_ref(generate_bom.build_cbom())
    size = lambda ref: c[ref]["cryptoProperties"]["relatedCryptoMaterialProperties"]["size"]  # noqa: E731
    assert size("key/ml-kem-dk") == pqc_kem.DECAPSULATION_KEY_SIZE * 8
    assert size("key/ml-kem-ek") == pqc_kem.ENCAPSULATION_KEY_SIZE * 8
    assert size("key/ml-dsa-sk") == pqc_dsa.SECRET_KEY_SIZE * 8
    assert size("key/ml-dsa-pk") == pqc_dsa.PUBLIC_KEY_SIZE * 8
    assert size("sig/ml-dsa") == pqc_dsa.SIGNATURE_SIZE * 8
    assert size("key/cek") == symmetric.KEY_SIZE * 8
    props = {p["name"]: p["value"] for p in c["crypto/scrypt"]["properties"]}
    assert props["sih:N"] == str(keystore.SCRYPT_N) and props["sih:r"] == str(keystore.SCRYPT_R)
    assert c["crypto/ml-kem-768"]["cryptoProperties"]["oid"] == "2.16.840.1.101.3.4.4.2"
    assert c["crypto/ml-dsa-44"]["cryptoProperties"]["oid"] == "2.16.840.1.101.3.4.3.17"


def test_no_quantum_vulnerable_algorithms_in_inventory():
    for comp in generate_bom.build_cbom()["components"]:
        if comp["cryptoProperties"]["assetType"] == "algorithm":
            flags = {p["name"]: p["value"] for p in comp["properties"]}
            assert flags["sih:quantum-vulnerable"] == "false", comp["name"]


def test_committed_bom_matches_environment():
    assert generate_bom.check() == []


def test_sbom_lists_direct_dependencies_with_hashes():
    comps = generate_bom.build_sbom()["components"]
    direct = {c["name"] for c in comps
              if {"name": "sih:direct-dependency", "value": "true"} in c.get("properties", [])}
    assert {"fastapi", "cryptography", "mlkem", "dilithium-py", "pymupdf"} <= direct
    assert all(c.get("hashes") for c in comps if c["purl"].startswith("pkg:pypi/"))


def test_modified_bom_detected(tmp_path):
    work = tmp_path / "bom"
    shutil.copytree(generate_bom.BOM_DIR, work)
    cbom_path = work / "cbom.cdx.json"
    data = json.loads(cbom_path.read_text(encoding="utf-8"))
    for comp in data["components"]:
        if comp["bom-ref"] == "key/ml-kem-dk":
            comp["cryptoProperties"]["relatedCryptoMaterialProperties"]["size"] = 1
    cbom_path.write_text(json.dumps(data), encoding="utf-8")
    assert any("SHA256SUMS" in p for p in generate_bom.check(work))

    sums = f"{hashlib.sha256(cbom_path.read_bytes()).hexdigest()}  cbom.cdx.json\n"
    sums += next(line for line in (work / "SHA256SUMS").read_text().splitlines() if "sbom" in line) + "\n"
    (work / "SHA256SUMS").write_text(sums, encoding="utf-8")
    assert any("key/ml-kem-dk differs" in p for p in generate_bom.check(work))
