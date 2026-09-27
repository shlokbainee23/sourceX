"""
Provision SIH26237 principals into encrypted local software keystores.

Usage:
    python scripts/provision_identities.py              # prompt for each passphrase (not echoed)
    python scripts/provision_identities.py --generate   # generate random passphrases, print ONCE

    python scripts/provision_identities.py --issue-manifest   # (re)issue the signed trust manifest only

Already-provisioned principals are skipped. v1 plaintext recipient key files are
migrated into encrypted keystores (public keys unchanged) and then destroyed.
No credentials are written to disk by this script.

Trust anchor: the SHA-256 of the WESEE_HQ ML-DSA-44 public key is pinned in
trust_anchor/authority.pin (outside the data directory; override with
SIH_AUTHORITY_PIN_FILE), and a trust manifest attesting every principal's key
fingerprints is signed by WESEE_HQ and imported into the local trust store.
"""

import argparse
import getpass
import hashlib
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import config  # noqa: E402
from app.crypto.identity import (  # noqa: E402
    DEFAULT_PRINCIPALS,
    destroy_file,
    get_principal,
    legacy_plaintext_key_files,
    principal_exists,
    provision_principal,
)
from app.crypto.keystore import KeystoreError, unlock_keystore  # noqa: E402
from app.database.connection import get_connection, init_db  # noqa: E402
from app import trust  # noqa: E402

AUTHORITY_ID = "WESEE_HQ"


def _unattested_principals() -> list:
    try:
        attested = {e["principal_id"] for e in trust.current_manifest()["manifest"]["principals"]}
    except trust.TrustError as exc:
        if exc.code != trust.NOT_AVAILABLE:
            raise
        attested = set()
    conn = get_connection()
    ids = [r[0] for r in conn.execute("SELECT principal_id FROM principals").fetchall()]
    conn.close()
    return sorted(set(ids) - attested)


def _establish_trust(authority_passphrase: str | None, force: bool) -> int:
    principal = get_principal(AUTHORITY_ID)
    if not principal or not principal["mldsa_public_key"]:
        print(f"[FAIL] {AUTHORITY_ID} is not provisioned; cannot establish the trust anchor")
        return 1
    pk = bytes.fromhex(principal["mldsa_public_key"])
    fingerprint = hashlib.sha256(pk).hexdigest()
    try:
        if trust.write_authority_pin(fingerprint):
            print(f"[OK]   Pinned authority trust anchor at {config.authority_pin_path()}")
        else:
            print(f"[OK]   Authority trust anchor already pinned at {config.authority_pin_path()}")
    except trust.TrustError as exc:
        print(f"[FAIL] {exc} ({config.authority_pin_path()}). Refusing to continue.")
        return 1

    pending = _unattested_principals()
    if not pending and not force:
        print(f"[SKIP] Trust manifest v{trust.current_manifest()['version']} already attests every principal")
        return 0
    if authority_passphrase is None:
        authority_passphrase = getpass.getpass(f"{AUTHORITY_ID} passphrase to sign the trust manifest: ")
    try:
        keys = unlock_keystore(AUTHORITY_ID, authority_passphrase)
    except KeystoreError:
        print(f"[FAIL] Could not unlock {AUTHORITY_ID} keystore; trust manifest not issued")
        return 1
    try:
        result = trust.issue_and_import(AUTHORITY_ID, pk, keys["mldsa_sk"], "provisioning",
                                        "Initial provisioning" if not force else "Re-issued by provisioning script")
    except trust.TrustError as exc:
        print(f"[FAIL] Trust manifest rejected: {exc.code}: {exc}")
        return 1
    finally:
        keys.clear()
    print(f"[OK]   Trust manifest v{result['version']} issued and imported (sha256 {result['manifest_sha256']})")
    return 0


def _prompt(principal_id: str) -> str:
    while True:
        first = getpass.getpass(f"Passphrase for {principal_id} (min {config.MIN_PASSPHRASE_LENGTH} chars): ")
        if len(first) < config.MIN_PASSPHRASE_LENGTH:
            print("  Too short.")
            continue
        if getpass.getpass("  Confirm: ") != first:
            print("  Mismatch.")
            continue
        return first


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--generate", action="store_true", help="generate random passphrases and print them once")
    parser.add_argument("--issue-manifest", action="store_true", help="only (re)issue the signed trust manifest")
    args = parser.parse_args()

    init_db()
    print(f"Data directory: {config.data_dir()}")
    if args.issue_manifest:
        return _establish_trust(None, force=True)
    generated = []
    authority_passphrase = None
    for p in DEFAULT_PRINCIPALS:
        pid = p["principal_id"]
        if principal_exists(pid):
            print(f"[SKIP] {pid} already provisioned")
            continue
        passphrase = secrets.token_urlsafe(15) if args.generate else _prompt(pid)
        result = provision_principal(pid, p["role"], p["name"], passphrase, title=p.get("title"))
        note = " (migrated v1 plaintext keys, plaintext file destroyed)" if result["migrated_legacy_keys"] else ""
        print(f"[OK]   {pid} ({p['role']}) provisioned{note}")
        if pid == AUTHORITY_ID:
            authority_passphrase = passphrase
        if args.generate:
            generated.append((pid, p["role"], passphrase))

    leftovers = legacy_plaintext_key_files()
    for path in leftovers:
        destroy_file(path)
        print(f"[OK]   Destroyed orphaned plaintext key file {path.name}")

    trust_status = _establish_trust(authority_passphrase, force=False)

    if generated:
        print("\nGenerated passphrases (shown once, not stored anywhere - record them securely):")
        for pid, role, pw in generated:
            print(f"  {pid:<16} {role:<13} {pw}")

    print("\nML-DSA-44 public-key fingerprints (SHA-256). Record these OUT-OF-BAND; investigation")
    print("reports the signer fingerprint so a substituted registry key can be spotted:")
    for p in DEFAULT_PRINCIPALS:
        principal = get_principal(p["principal_id"])
        if principal and principal["mldsa_public_key"]:
            fp = hashlib.sha256(bytes.fromhex(principal["mldsa_public_key"])).hexdigest()
            print(f"  {p['principal_id']:<16} {fp}")
    return trust_status


if __name__ == "__main__":
    raise SystemExit(main())
