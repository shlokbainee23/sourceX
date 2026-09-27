"""
Pydantic Schemas for SIH26237 API request and response data models.
Request models forbid unexpected fields and validate identifiers strictly.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.validation import ID_PATTERN


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


IdStr = Field(..., pattern=ID_PATTERN, max_length=64)


class LoginRequest(StrictModel):
    principal_id: str = IdStr
    passphrase: str = Field(..., min_length=1, max_length=1024)


class LoginResponse(BaseModel):
    token: str
    principal_id: str
    role: str
    name: str
    expires_in_seconds: int


class PrincipalResponse(BaseModel):
    principal_id: str
    role: str
    name: str


class RecipientCreate(StrictModel):
    recipient_id: str = IdStr
    name: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=128)
    initial_passphrase: str = Field(..., min_length=12, max_length=1024)


class RecipientResponse(BaseModel):
    recipient_id: str
    name: str
    role: str
    mlkem_public_key: str
    mldsa_public_key: str
    status: str
    created_at: str


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    original_hash: str
    classification: str
    owner: str
    created_at: str
    status: str


class EncryptRequest(StrictModel):
    document_id: str = IdStr
    authorized_recipient_ids: List[str] = Field(..., min_length=1, max_length=100)


class DecryptRequest(StrictModel):
    document_id: str = IdStr
    # Accepted only for backward compatibility; must equal the authenticated recipient.
    recipient_id: Optional[str] = Field(default=None, pattern=ID_PATTERN, max_length=64)


class DecryptionResponse(BaseModel):
    session_id: str
    document_id: str
    recipient_id: str
    watermark_token: str
    decryption_timestamp: str
    delivered_document_hash: str
    signature: str
    block_index: int
    block_hash: str
    decrypted_file_path: str
    message: str


class VerificationEvidence(BaseModel):
    watermark_found: bool
    watermark_valid: bool
    session_found: bool
    document_hash_match: bool
    record_consistent: bool
    ledger_record_found: bool
    signature_valid: bool
    ledger_chain_valid: bool
    document_provenance_valid: bool
    identity_trusted: bool


class TrustAnchorEvidence(BaseModel):
    manifest_version: Optional[int] = None
    manifest_sha256: Optional[str] = None
    authority_pin: Optional[str] = None


class Attribution(BaseModel):
    recipient_id: str
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    document_id: str
    session_id: str
    decryption_timestamp: str
    block_index: int
    block_hash: str
    # Compare against the fingerprint recorded out-of-band at provisioning time.
    signer_public_key_sha256: str
    classification: Optional[str] = None


class VerificationFailure(BaseModel):
    check: str
    reason: str


class InvestigationResult(BaseModel):
    status: str  # VERIFIED | UNVERIFIED | VERIFICATION_ERROR
    attribution_verdict: str
    reason: str
    attribution: Optional[Attribution] = None
    verification: VerificationEvidence
    failures: List[VerificationFailure]
    uploaded_document_hash: str
    watermark_token: Optional[str] = None
    watermark_status: Optional[str] = None
    ledger_error: Optional[str] = None
    trust_anchor: Optional[TrustAnchorEvidence] = None
    # Flat compatibility fields, populated only when status == VERIFIED.
    recipient_id: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    document_id: Optional[str] = None
    session_id: Optional[str] = None
    decryption_timestamp: Optional[str] = None
    block_index: Optional[int] = None
    block_hash: Optional[str] = None
    document_hash_match: bool = False
    signature_valid: bool = False
    ledger_chain_valid: bool = False


class InvarianceRequest(StrictModel):
    session_a: str = IdStr
    session_b: str = IdStr


class LedgerBlockResponse(BaseModel):
    block_index: int
    timestamp: str
    event_type: str
    previous_hash: str
    record_hash: str
    canonical_record: Dict[str, Any]
    signature: str
    signer_id: str
    block_hash: str


class LedgerVerificationResult(BaseModel):
    chain_valid: bool
    total_blocks: int
    verified_blocks: int
    broken_block_index: Optional[int] = None
    error_message: Optional[str] = None
    verification_details: List[Dict[str, Any]]


class RevokeRequest(StrictModel):
    principal_id: str = IdStr
    reason: str = Field(..., min_length=3, max_length=256)


class TamperRequest(StrictModel):
    block_index: int = Field(..., ge=1)
    field: str = Field(..., max_length=32)
    new_value: Optional[str] = Field(default=None, max_length=4096)
