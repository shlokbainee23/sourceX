"""
Software and Cryptographic Bills of Materials for SIH26237 (CycloneDX 1.6 JSON).

Aligned with CERT-In "Technical Guidelines on SBOM, QBOM & CBOM, AIBOM and HBOM"
(v2.0) minimum elements and the TEC 910018:2025 recommendation to maintain a
cryptographic inventory. Runs fully offline.

Usage:
    python scripts/generate_bom.py           # write bom/sbom.cdx.json, bom/cbom.cdx.json, bom/SHA256SUMS
    python scripts/generate_bom.py --check   # exit 1 if the environment or crypto parameters drift from bom/

The CBOM is derived from the constants in backend/app/crypto, so it cannot silently
disagree with the implementation. The SBOM covers the Python packages installed in
the running interpreter's environment and the frontend lockfile.
"""

import argparse
import base64
import hashlib
import importlib.metadata as md
import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

BOM_DIR = ROOT / "bom"
APP_VERSION = "3.0.0"
SPEC = "1.6"
GUIDELINE = "CERT-In Technical Guidelines on SBOM, QBOM & CBOM, AIBOM and HBOM v2.0"
EXCLUDED_DISTS = {"pip", "setuptools", "wheel"}


def _direct_requirements() -> set:
    names = set()
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            names.add(line.split("[")[0].split("=")[0].split(">")[0].split("<")[0].strip().lower().replace("_", "-"))
    return names


def _license(meta) -> str:
    expr = meta.get("License-Expression")
    if expr:
        return expr
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or [] if c.startswith("License ::")]
    if classifiers:
        return classifiers[0]
    lic = (meta.get("License") or "").strip()
    return lic.splitlines()[0][:80] if lic else "NOASSERTION"


def python_components() -> list:
    direct = _direct_requirements()
    out = []
    for dist in md.distributions():
        name = dist.metadata["Name"]
        if not name or name.lower() in EXCLUDED_DISTS:
            continue
        norm = name.lower().replace("_", "-")
        record = dist.read_text("RECORD") or ""
        out.append({
            "type": "library",
            "bom-ref": f"pkg:pypi/{norm}@{dist.version}",
            "name": norm,
            "version": dist.version,
            "description": (dist.metadata.get("Summary") or "")[:200],
            "supplier": {"name": dist.metadata.get("Author") or dist.metadata.get("Maintainer")
                         or (dist.metadata.get("Author-email") or "NOASSERTION").split("<")[0].strip() or "NOASSERTION"},
            "licenses": [{"expression": _license(dist.metadata)}],
            "purl": f"pkg:pypi/{norm}@{dist.version}",
            "hashes": [{"alg": "SHA-256", "content": hashlib.sha256(record.encode("utf-8")).hexdigest()}],
            "scope": "required",
            "properties": [
                {"name": "sih:ecosystem", "value": "python"},
                {"name": "sih:direct-dependency", "value": str(norm in direct).lower()},
                {"name": "sih:hash-basis", "value": "SHA-256 of the installed dist-info RECORD (per-file hashes)"},
            ],
        })
    return sorted(out, key=lambda c: c["name"])


def frontend_components() -> list:
    lock = ROOT / "frontend" / "package-lock.json"
    if not lock.exists():
        return []
    data = json.loads(lock.read_text(encoding="utf-8"))
    out = []
    for path, info in (data.get("packages") or {}).items():
        if not path.startswith("node_modules/") or "version" not in info:
            continue
        name = path.split("node_modules/")[-1]
        comp = {
            "type": "library",
            "bom-ref": f"pkg:npm/{name}@{info['version']}",
            "name": name,
            "version": info["version"],
            "licenses": [{"expression": info.get("license") or "NOASSERTION"}],
            "purl": f"pkg:npm/{name.replace('@', '%40')}@{info['version']}",
            "scope": "excluded" if info.get("dev") else "required",
            "properties": [{"name": "sih:ecosystem", "value": "npm"},
                           {"name": "sih:build-only", "value": str(bool(info.get("dev"))).lower()}],
        }
        integrity = info.get("integrity", "")
        if integrity.startswith("sha512-"):
            comp["hashes"] = [{"alg": "SHA-512", "content": base64.b64decode(integrity[7:]).hex()}]
        out.append(comp)
    return sorted(out, key=lambda c: c["bom-ref"])


def _algorithm(ref, name, primitive, functions, oid, level=None, mode=None, param=None, source=None, extra=None):
    props = {"primitive": primitive, "executionEnvironment": "software-plain-ram", "cryptoFunctions": functions}
    if level is not None:
        props["nistQuantumSecurityLevel"] = level
    if mode:
        props["mode"] = mode
    if param:
        props["parameterSetIdentifier"] = param
    comp = {"type": "cryptographic-asset", "bom-ref": ref, "name": name,
            "cryptoProperties": {"assetType": "algorithm", "algorithmProperties": props}}
    if oid:
        comp["cryptoProperties"]["oid"] = oid
    comp["properties"] = [{"name": "sih:quantum-vulnerable", "value": "false"}]
    if source:
        comp["properties"].append({"name": "sih:source", "value": source})
    for k, v in (extra or {}).items():
        comp["properties"].append({"name": f"sih:{k}", "value": str(v)})
    return comp


def _material(ref, name, mtype, size_bits, algorithm_ref, storage, secured_by=None):
    props = {"type": mtype, "size": size_bits, "algorithmRef": algorithm_ref}
    if secured_by:
        props["securedBy"] = secured_by
    return {"type": "cryptographic-asset", "bom-ref": ref, "name": name,
            "cryptoProperties": {"assetType": "related-crypto-material", "relatedCryptoMaterialProperties": props},
            "properties": [{"name": "sih:storage", "value": storage}]}


def crypto_components() -> list:
    from app.crypto import keystore, kdf, pqc_dsa, pqc_kem, symmetric

    keystore_mech = {"mechanism": "scrypt + AES-256-GCM encrypted local software keystore (not an HSM)",
                     "algorithmRef": "crypto/aes-256-gcm"}
    return [
        _algorithm("crypto/ml-kem-768", "ML-KEM-768", "kem", ["keygen", "encapsulate", "decapsulate"],
                   "2.16.840.1.101.3.4.4.2", 3, param="768", source="backend/app/crypto/pqc_kem.py (mlkem)",
                   extra={"standard": "FIPS 203", "use": "per-recipient CEK key establishment only"}),
        _algorithm("crypto/ml-dsa-44", "ML-DSA-44", "signature", ["keygen", "sign", "verify"],
                   "2.16.840.1.101.3.4.3.17", 2, param="44", source="backend/app/crypto/pqc_dsa.py (dilithium_py)",
                   extra={"standard": "FIPS 204", "use": "provenance records, ledger blocks, trust manifests"}),
        _algorithm("crypto/aes-256-gcm", "AES-256-GCM", "ae", ["keygen", "encrypt", "decrypt", "tag"],
                   "2.16.840.1.101.3.4.1.46", 5, mode="gcm", param=str(symmetric.KEY_SIZE * 8),
                   source="backend/app/crypto/symmetric.py (cryptography)",
                   extra={"standard": "NIST SP 800-38D", "nonce-bits": symmetric.NONCE_SIZE * 8,
                          "aad": "document/recipient context binding"}),
        _algorithm("crypto/hkdf-sha256", "HKDF-SHA256", "kdf", ["keyderive"], "1.2.840.113549.1.9.16.3.28",
                   source="backend/app/crypto/kdf.py (cryptography)",
                   extra={"standard": "RFC 5869", "info-prefix": kdf.INFO_STRING.decode()}),
        _algorithm("crypto/sha-256", "SHA-256", "hash", ["digest"], "2.16.840.1.101.3.4.2.1", 2,
                   source="hashlib", extra={"standard": "FIPS 180-4",
                                            "use": "document hashes, record hashes, block chaining, fingerprints"}),
        _algorithm("crypto/scrypt", "scrypt", "kdf", ["keyderive"], "1.3.6.1.4.1.11591.4.11",
                   source="backend/app/crypto/keystore.py (cryptography)",
                   extra={"standard": "RFC 7914", "N": keystore.SCRYPT_N, "r": keystore.SCRYPT_R,
                          "p": keystore.SCRYPT_P, "salt-bits": keystore.SALT_SIZE * 8}),
        _algorithm("crypto/os-csprng", "Operating-system CSPRNG", "drbg", ["generate"], None,
                   source="os.urandom / secrets", extra={"use": "CEKs, nonces, salts, markers, tokens"}),

        _material("key/ml-kem-dk", "ML-KEM-768 decapsulation key", "private-key", pqc_kem.DECAPSULATION_KEY_SIZE * 8,
                  "crypto/ml-kem-768", "encrypted keystore file; process memory while logged in", keystore_mech),
        _material("key/ml-kem-ek", "ML-KEM-768 encapsulation key", "public-key", pqc_kem.ENCAPSULATION_KEY_SIZE * 8,
                  "crypto/ml-kem-768", "SQLite registry (recipients)"),
        _material("key/ml-dsa-sk", "ML-DSA-44 signing key", "private-key", pqc_dsa.SECRET_KEY_SIZE * 8,
                  "crypto/ml-dsa-44", "encrypted keystore file; process memory while logged in", keystore_mech),
        _material("key/ml-dsa-pk", "ML-DSA-44 verification key", "public-key", pqc_dsa.PUBLIC_KEY_SIZE * 8,
                  "crypto/ml-dsa-44", "SQLite registry; SHA-256 attested in signed trust manifest; authority pinned"),
        _material("sig/ml-dsa", "ML-DSA-44 signature", "signature", pqc_dsa.SIGNATURE_SIZE * 8,
                  "crypto/ml-dsa-44", "ledger_blocks, sessions, trust_manifests"),
        _material("key/cek", "Content encryption key", "secret-key", symmetric.KEY_SIZE * 8, "crypto/aes-256-gcm",
                  "never stored in plaintext; wrapped per recipient",
                  {"mechanism": "AES-256-GCM wrap under HKDF(ML-KEM shared secret)", "algorithmRef": "crypto/aes-256-gcm"}),
        _material("key/kem-shared-secret", "ML-KEM shared secret", "shared-secret", 256, "crypto/ml-kem-768",
                  "ephemeral, process memory only"),
        _material("iv/aes-gcm-nonce", "AES-GCM nonce", "nonce", symmetric.NONCE_SIZE * 8, "crypto/aes-256-gcm",
                  "stored beside ciphertext; random per encryption"),
        _material("salt/keystore", "Keystore scrypt salt", "salt", keystore.SALT_SIZE * 8, "crypto/scrypt",
                  "keystore header (authenticated as AAD)"),
    ]


def _bom(components: list, kind: str) -> dict:
    body = json.dumps(components, sort_keys=True).encode()
    return {
        "bomFormat": "CycloneDX",
        "specVersion": SPEC,
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, hashlib.sha256(body).hexdigest())}",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "bom-ref": "sih26237", "name": "sih26237-offline-forensic-attribution",
                          "version": APP_VERSION},
            "authors": [{"name": "SIH26237 team"}],
            "properties": [{"name": "sih:bom-kind", "value": kind},
                           {"name": "sih:guideline", "value": GUIDELINE},
                           {"name": "sih:generated-offline", "value": "true"}],
        },
        "components": components,
    }


def build_sbom() -> dict:
    return _bom(python_components() + frontend_components(), "SBOM")


def build_cbom() -> dict:
    return _bom(crypto_components(), "CBOM (includes QBOM quantum-vulnerability flags)")


def _dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write(bom_dir: Path = BOM_DIR) -> dict:
    bom_dir.mkdir(parents=True, exist_ok=True)
    files = {"sbom.cdx.json": _dump(build_sbom()), "cbom.cdx.json": _dump(build_cbom())}
    sums = []
    for name, text in files.items():
        (bom_dir / name).write_text(text, encoding="utf-8", newline="\n")
        sums.append(f"{hashlib.sha256(text.encode('utf-8')).hexdigest()}  {name}")
    (bom_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
    return {n: len(json.loads(t)["components"]) for n, t in files.items()}


def check(bom_dir: Path = BOM_DIR) -> list:
    """Returns a list of problems; empty means the environment matches the committed BOMs."""
    problems = []
    sums_path = bom_dir / "SHA256SUMS"
    if not sums_path.exists():
        return ["bom/SHA256SUMS missing; run generate_bom.py"]
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        path = bom_dir / name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            problems.append(f"{name} does not match SHA256SUMS (modified in transit or at rest)")
    if problems:
        return problems
    for name, builder in (("sbom.cdx.json", build_sbom), ("cbom.cdx.json", build_cbom)):
        recorded = {c["bom-ref"]: c for c in json.loads((bom_dir / name).read_text(encoding="utf-8"))["components"]}
        current = {c["bom-ref"]: c for c in builder()["components"]}
        for ref in sorted(set(recorded) | set(current)):
            if ref not in current:
                problems.append(f"{name}: {ref} recorded but not present")
            elif ref not in recorded:
                problems.append(f"{name}: {ref} present but not recorded")
            elif json.dumps(recorded[ref], sort_keys=True) != json.dumps(current[ref], sort_keys=True):
                problems.append(f"{name}: {ref} differs from the recorded component")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="verify instead of writing")
    args = parser.parse_args()
    if args.check:
        problems = check()
        for p in problems:
            print(f"[DRIFT] {p}")
        print("[OK] Environment and crypto parameters match bom/" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    counts = write()
    print(f"[OK] Wrote bom/ ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
