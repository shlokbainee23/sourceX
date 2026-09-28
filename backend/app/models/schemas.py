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


class InvestigatorCreate(StrictModel):
    principal_id: str = IdStr
    name: str = Field(..., min_length=1, max_length=128)


class EnrollRequest(StrictModel):
    principal_id: str = IdStr
    enrollment_code: str = Field(..., min_length=8, max_length=64)
    passphrase: str = Field(..., min_length=12, max_length=1024)


class AttestRequest(StrictModel):
    principal_id: str = IdStr
    key_id: str = Field(..., max_length=72, pattern=r"^[A-Za-z0-9_-]{1,64}#[1-9][0-9]{0,5}$")
    confirmed_mldsa_pk_sha256: str = Field(..., pattern=r"^[0-9a-f]{64}$")


class KeyCompromiseRequest(StrictModel):
    key_id: str = Field(..., max_length=72, pattern=r"^[A-Za-z0-9_-]{1,64}#[1-9][0-9]{0,5}$")
    compromised_after_block: int = Field(..., ge=0)
    reason: str = Field(..., min_length=3, max_length=256)


class RotateKeysRequest(StrictModel):
    current_passphrase: str = Field(..., min_length=1, max_length=1024)
    new_passphrase: str = Field(..., min_length=12, max_length=1024)


class ChangePassphraseRequest(StrictModel):
    current_passphrase: str = Field(..., min_length=1, max_length=1024)
    new_passphrase: str = Field(..., min_length=12, max_length=1024)


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
    # Step-up: the keystore passphrase is re-entered for every decryption.
    passphrase: str = Field(..., min_length=1, max_length=1024)
    # Accepted only for backward compatibility; must equal the authenticated recipient.
    recipient_id: Optional[str] = Field(default=None, pattern=ID_PATTERN, max_length=64)


class DecryptionResponse(BaseModel):
    session_id: str
    document_id: str
    recipient_id: str
    signer_key_id: str
    watermark_token: str
    decryption_timestamp: str
    delivered_document_hash: str
    source_render_hash: str
    delivered_render_hash: str
    signature: str
    block_index: int
    block_hash: str
    decrypted_file_path: str
    delivery_expires_in_seconds: int
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
    signer_key_id: Optional[str] = None


class Attribution(BaseModel):
    recipient_id: str
    recipient_name: Optional[str] = None
    recipient_role: Optional[str] = None
    document_id: str
    session_id: str
    decryption_timestamp: str
    block_index: int
    block_hash: str
    # Compare against the fingerprint confirmed out-of-band at enrollment/attestation time.
    signer_public_key_sha256: str
    signer_key_id: Optional[str] = None
    classification: Optional[str] = None


class VerificationFailure(BaseModel):
    check: str
    reason: str


class InvestigationResult(BaseModel):
    status: str  # VERIFIED | CORRELATED | NOT_ATTRIBUTABLE | VERIFICATION_ERROR
    attribution_verdict: str
    reason: str
    attribution: Optional[Attribution] = None
    verification: VerificationEvidence
    failures: List[VerificationFailure]
    uploaded_document_hash: str
    content_match: str = "UNKNOWN"  # EXACT | RENDER_IDENTICAL | DIFFERENT | UNKNOWN
    uploaded_render_hash: Optional[str] = None
    dangerous_features: List[str] = []
    watermark_token: Optional[str] = None
    watermark_status: Optional[str] = None
    ledger_error: Optional[str] = None
    trust_anchor: Optional[TrustAnchorEvidence] = None
    witness: Optional[Dict[str, Any]] = None
    limitations: List[str] = []
    report: Optional[Dict[str, Any]] = None
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
    key_trust_warnings: List[Dict[str, Any]] = []
    timestamp_warnings: List[Dict[str, Any]] = []
    anchor_state: Optional[str] = None
    witness: Optional[Dict[str, Any]] = None


class RevokeRequest(StrictModel):
    principal_id: str = IdStr
    reason: str = Field(..., min_length=3, max_length=256)


class TamperRequest(StrictModel):
    block_index: int = Field(..., ge=1)
    field: str = Field(..., max_length=32)
    new_value: Optional[str] = Field(default=None, max_length=4096)
