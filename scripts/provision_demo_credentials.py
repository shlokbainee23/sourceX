"""
Provision clean, documented demo credentials for SIH26237.
Sets known passphrases for all default stations so the workstation UI is immediately usable.
"""

import hashlib
import os
import shutil
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app import config
from app.crypto.identity import DEFAULT_PRINCIPALS, provision_principal, get_principal
from app.crypto.keystore import unlock_keystore
from app.database.connection import get_connection, init_db
from app import trust

DEMO_CREDENTIALS = {
    "WESEE_HQ": "WeseeHQ@2026!",
    "R001": "CommanderAlpha@2026!",
    "R002": "OfficerBravo@2026!",
    "R003": "OfficerCharlie@2026!",
    "INVESTIGATOR_01": "Investigator@2026!",
    "AUDITOR_01": "Auditor@2026!",
}

def main():
    data_dir = config.data_dir()
    print(f"Data directory: {data_dir}")

    # Backup existing data directory
    backup_dir = data_dir.parent / "data.backup"
    if data_dir.exists() and not backup_dir.exists():
        print(f"Backing up existing data to {backup_dir}...")
        shutil.copytree(data_dir, backup_dir)

    # Clean data directory
    if (data_dir / "sih26237.sqlite").exists():
        (data_dir / "sih26237.sqlite").unlink()
    if (data_dir / "ledger_head.json").exists():
        (data_dir / "ledger_head.json").unlink()
    if (data_dir / "keystore").exists():
        shutil.rmtree(data_dir / "keystore")
    if (data_dir / "documents").exists():
        shutil.rmtree(data_dir / "documents")

    init_db()

    print("\n--- Provisioning Default Principals ---")
    authority_passphrase = DEMO_CREDENTIALS["WESEE_HQ"]

    for p in DEFAULT_PRINCIPALS:
        pid = p["principal_id"]
        pw = DEMO_CREDENTIALS[pid]
        res = provision_principal(pid, p["role"], p["name"], pw, title=p.get("title"))
        print(f"[OK] {pid:<16} ({p['role']:<12}) -> Passphrase: {pw}")

    # Establish Trust Anchor and Manifest
    print("\n--- Establishing Trust Anchor & Manifest ---")
    authority = get_principal("WESEE_HQ")
    pk = bytes.fromhex(authority["mldsa_public_key"])
    fp = hashlib.sha256(pk).hexdigest()

    pin_path = config.authority_pin_path()
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_text(fp + "\n")
    print(f"[OK] Pinned authority fingerprint at {pin_path}: {fp}")

    # Unlock authority keystore and issue manifest
    keys = unlock_keystore("WESEE_HQ", authority_passphrase)
    manifest_res = trust.issue_and_import(
        "WESEE_HQ",
        pk,
        keys["mldsa_sk"],
        "demo-bootstrap",
        "Initial demonstration trust manifest with all 6 stations attested",
        authority_key_id="WESEE_HQ#1"
    )
    keys.clear()
    print(f"[OK] Trust Manifest v{manifest_res['version']} issued & imported (SHA-256: {manifest_res['manifest_sha256'][:16]}...)")

    print("\n=======================================================")
    print("DEMO CREDENTIALS INITIALIZED SUCCESSFULLY")
    print("=======================================================")
    for pid, pw in DEMO_CREDENTIALS.items():
        print(f"  {pid:<16} : {pw}")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
