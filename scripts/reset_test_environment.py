"""
Safe Test & Demo Reset Script for SIH26237.
Clears documents, packages, sessions, ledger blocks and the ledger head anchor.
Preserves principals, recipient public keys and encrypted keystores.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.database.connection import reset_test_database, get_connection  # noqa: E402
from app.ledger.verify import verify_ledger  # noqa: E402


def main():
    print("=" * 65)
    print("SIH26237 - TEST & DEMO ENVIRONMENT RESET")
    print("=" * 65)

    print("\n[1/3] Clearing documents, sessions, ledger blocks and head anchor...")
    reset_test_database()
    print("[OK] Evidence tables cleared; document vault emptied.")

    print("\n[2/3] Checking provisioned principals...")
    conn = get_connection()
    rows = conn.execute("SELECT principal_id, role, name FROM principals ORDER BY role, principal_id").fetchall()
    conn.close()
    print(f"[OK] {len(rows)} principal(s) preserved:")
    for r in rows:
        print(f"     * {r['principal_id']} [{r['role']}] {r['name']}")
    if not rows:
        print("     (none - run scripts/provision_identities.py)")

    print("\n[3/3] Auditing empty ledger...")
    audit = verify_ledger()
    print(f"[OK] Chain Valid: {audit['chain_valid']}  Total Blocks: {audit['total_blocks']}")
    print("=" * 65)


if __name__ == "__main__":
    main()
