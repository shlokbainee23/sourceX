"""
FastAPI application entry point for SIH26237.
Offline forensic attribution prototype: ML-KEM-768 + HKDF + AES-256-GCM broadcast
encryption, ML-DSA-44 signed decryption records and a tamper-evident hash-chained ledger.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.api.auth import router as auth_router
from app.api.decryption import router as decryption_router
from app.api.documents import router as documents_router
from app.api.encryption import router as encryption_router
from app.api.investigation import router as investigation_router
from app.api.ledger import audit_router, router as ledger_router
from app.api.recipients import router as recipients_router
from app.api.trust import router as trust_router
from app.crypto.identity import legacy_plaintext_key_files
from app.trust import TrustError, current_manifest
from app.database.connection import get_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("sih26237")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    conn = get_connection()
    principals = conn.execute("SELECT COUNT(*) FROM principals").fetchone()[0]
    conn.close()
    if principals == 0:
        logger.warning("No principals provisioned. Run: python scripts/provision_identities.py")
    if legacy_plaintext_key_files():
        logger.warning("Legacy PLAINTEXT key files present in keystore directory. "
                       "Run scripts/provision_identities.py to migrate and destroy them.")
    try:
        m = current_manifest()
        logger.info("Trust manifest v%s verified against pinned authority anchor.", m["version"])
    except TrustError as exc:
        logger.warning("Trust store not usable (%s): attribution will fail closed until "
                       "scripts/provision_identities.py --issue-manifest is run.", exc.code)
    logger.info("SIH26237 offline provenance engine online (demo mode: %s).", config.demo_mode_enabled())
    yield


app = FastAPI(
    title="SIH26237 Offline Forensic Attribution Engine",
    description="Offline prototype with ML-KEM-768, ML-DSA-44 and a tamper-evident hash-chained ledger",
    version="3.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Never leak exception text or stack traces to clients.
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Internal error. The operation was not completed."})


app.include_router(auth_router)
app.include_router(recipients_router)
app.include_router(documents_router)
app.include_router(encryption_router)
app.include_router(decryption_router)
app.include_router(investigation_router)
app.include_router(ledger_router)
app.include_router(audit_router)
app.include_router(trust_router)


@app.get("/")
def root():
    return {
        "system": "SIH26237 Offline Forensic Attribution System",
        "status": "OPERATIONAL",
        "algorithms": {
            "key_encapsulation": "ML-KEM-768 (FIPS 203)",
            "digital_signatures": "ML-DSA-44 (FIPS 204)",
            "symmetric": "AES-256-GCM",
            "kdf": "HKDF-SHA256",
            "keystore_kdf": "scrypt",
        },
    }


@app.get("/api/health")
def health():
    return {"status": "HEALTHY"}
