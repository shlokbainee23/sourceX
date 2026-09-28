import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';

const CHECK_DEFINITIONS = [
  {
    key: 'watermark_found',
    label: '01. Watermark Extraction',
    description: 'ISO 32000-1 non-rendering text marker extracted from document streams',
  },
  {
    key: 'watermark_valid',
    label: '02. Token Cryptographic Validity',
    description: 'Watermark token conforms to 256-bit CSPRNG entropy format',
  },
  {
    key: 'session_found',
    label: '03. Session Row Resolution',
    description: 'Matched active session record associated with the extracted token',
  },
  {
    key: 'document_hash_match',
    label: '04. Exact Document Hash Match',
    description: 'Delivered document SHA-256 matches the delivered hash recorded at decryption',
  },
  {
    key: 'record_consistent',
    label: '05. Canonical Record Consistency',
    description: 'Session parameters match canonical record committed at decryption time',
  },
  {
    key: 'ledger_record_found',
    label: '06. Ledger Record Existence',
    description: 'Decryption event found in append-only tamper-evident ledger block',
  },
  {
    key: 'signature_valid',
    label: '07. ML-DSA-44 Signature Verification',
    description: 'Recipient post-quantum digital signature verified over canonical record',
  },
  {
    key: 'ledger_chain_valid',
    label: '08. Ledger Hash Chain Integrity',
    description: 'Ledger block hashes are mathematically unbroken from genesis to head',
  },
  {
    key: 'document_provenance_valid',
    label: '09. Document Provenance Lineage',
    description: 'Valid chain from authority registration through broadcast encryption',
  },
  {
    key: 'identity_trusted',
    label: '10. Trust Anchor & Attestation',
    description: 'Recipient signing key verified against pinned WESEE authority manifest',
  },
];

export default function VerdictDisplay({ result }) {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  if (!result) return null;

  const isVerified = result.status === 'VERIFIED';
  const isCorrelated = result.status === 'CORRELATED';
  const verification = result.verification || {};
  const attribution = result.attribution || {};

  // Count passed checks
  const passedCount = CHECK_DEFINITIONS.filter((c) => verification[c.key]).length;

  return (
    <div className="space-y-6">
      {/* LEVEL 1: OPERATIONAL VERDICT */}
      {isVerified ? (
        <div className="p-5 rounded-lg border bg-[#2d6a4f]/08 border-[#2d6a4f]/30 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2d6a4f]/20 pb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#2d6a4f]/15 border border-[#2d6a4f]/30 flex items-center justify-center text-[#2d6a4f] shrink-0">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#2d6a4f] font-semibold">
                  FORENSIC ATTRIBUTION VERDICT
                </span>
                <h3 className="text-sm font-bold text-[#0a0a0a] uppercase tracking-wide font-mono">
                  ATTRIBUTION VERIFIED — EXACT MATCH
                </h3>
              </div>
            </div>
            <Badge status="VERIFIED" size="lg" />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-xs">
            <div className="p-3 bg-white border border-[#2d6a4f]/25 rounded shadow-xs">
              <span className="text-[#8d8d8d] text-[10px] font-semibold">ATTRIBUTED RECIPIENT:</span>
              <div className="text-sm font-bold text-[#1b4332] mt-0.5 font-mono">
                {attribution.recipient_id || result.recipient_id}
              </div>
              <div className="text-[11px] text-[#3a3a3a] font-sans mt-0.5">
                {attribution.recipient_name || result.recipient_name || 'Authorized Officer'}
              </div>
            </div>

            <div className="p-3 bg-white border border-[#2d6a4f]/25 rounded shadow-xs">
              <span className="text-[#8d8d8d] text-[10px] font-semibold">EVIDENCE CHECKS:</span>
              <div className="text-sm font-bold text-[#1b4332] mt-0.5 font-mono">
                {passedCount} / 10 CHECKS PASSED
              </div>
              <div className="text-[11px] text-[#2d6a4f] font-sans mt-0.5">
                All cryptographic gates satisfied
              </div>
            </div>

            <div className="p-3 bg-white border border-[#2d6a4f]/25 rounded shadow-xs">
              <span className="text-[#8d8d8d] text-[10px] font-semibold">LEDGER & TRUST ANCHOR:</span>
              <div className="text-sm font-bold text-[#1b4332] mt-0.5 font-mono">
                BLOCK #{attribution.block_index || result.block_index}
              </div>
              <div className="text-[11px] text-[#2d6a4f] font-sans mt-0.5">
                Chain & Pin verified valid
              </div>
            </div>
          </div>
        </div>
      ) : isCorrelated ? (
        <div className="p-5 rounded-lg border bg-[#b15f2c]/08 border-[#b15f2c]/30 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#b15f2c]/20 pb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#b15f2c]/15 border border-[#b15f2c]/30 flex items-center justify-center text-[#b15f2c] shrink-0">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#b15f2c] font-semibold">
                  FORENSIC CORRELATION VERDICT
                </span>
                <h3 className="text-sm font-bold text-[#0a0a0a] uppercase tracking-wide font-mono">
                  CORRELATED — CONTENT MODIFIED AFTER DELIVERY
                </h3>
              </div>
            </div>
            <Badge status="CORRELATED" size="lg" />
          </div>

          <div className="p-3.5 bg-white border border-[#b15f2c]/20 rounded text-xs space-y-2">
            <p className="font-semibold text-[#5a2e12] font-mono text-[11px]">
              FAIL-CLOSED NOTICE: Exact attribution cannot be cryptographically proven.
            </p>
            <p className="text-[#3a3a3a] font-sans text-xs leading-relaxed">
              The embedded watermark token matches recipient copy ({attribution.recipient_id || 'correlated station'}), but the file hash differs from the signed delivered copy. Per security doctrine, modified documents do not produce verifiable attribution.
            </p>
          </div>
        </div>
      ) : (
        <div className="p-5 rounded-lg border bg-[#8b3a2a]/08 border-[#8b3a2a]/30 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#8b3a2a]/20 pb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-[#8b3a2a]/15 border border-[#8b3a2a]/30 flex items-center justify-center text-[#8b3a2a] shrink-0">
                <ShieldAlert className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#8b3a2a] font-semibold">
                  FAIL-CLOSED ATTRIBUTION VERDICT
                </span>
                <h3 className="text-sm font-bold text-[#0a0a0a] uppercase tracking-wide font-mono">
                  ATTRIBUTION NOT ESTABLISHED
                </h3>
              </div>
            </div>
            <Badge status="NOT_ATTRIBUTABLE" label="FAIL CLOSED" size="lg" />
          </div>

          <div className="p-3.5 bg-white border border-[#8b3a2a]/20 rounded text-xs space-y-2 font-mono">
            <p className="font-semibold text-[#8b3a2a] text-[11px]">
              REASON: {result.reason || 'Verification criteria not satisfied.'}
            </p>
            <p className="text-[#3a3a3a] font-sans text-xs leading-relaxed">
              No recipient has been attributed. Cryptographic evidence was insufficient, invalid, or absent. In accordance with Indian Navy / WESEE forensic standards, the system has failed closed with zero suspects.
            </p>
          </div>
        </div>
      )}

      {/* LEVEL 2: 10-CHECK FORENSIC EVIDENCE BREAKDOWN */}
      <div className="bg-white border border-[#e6e5e2] rounded-lg overflow-hidden shadow-xs">
        <div className="p-4 border-b border-[#e6e5e2] bg-[#fafaf8] flex items-center justify-between">
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#0a0a0a] font-mono">
              10-Point Cryptographic Verification Checklist
            </h4>
            <p className="text-[11px] text-[#8d8d8d] font-mono mt-0.5">
              ALL 10 CHECKS MUST PASS INDEPENDENTLY FOR POSITIVE ATTRIBUTION
            </p>
          </div>
          <span className="font-mono text-xs font-bold px-2.5 py-1 rounded bg-[#f1f0ee] border border-[#e6e5e2] text-[#0a0a0a]">
            {passedCount} / 10 SATISFIED
          </span>
        </div>

        <div className="divide-y divide-[#e6e5e2]">
          {CHECK_DEFINITIONS.map((c) => {
            const passed = !!verification[c.key];
            return (
              <div
                key={c.key}
                className={`p-3.5 flex items-center justify-between gap-4 transition-colors ${
                  passed ? 'hover:bg-[#fafaf8]' : 'bg-[#8b3a2a]/04 hover:bg-[#8b3a2a]/08'
                }`}
              >
                <div className="flex items-start gap-3 min-w-0">
                  {passed ? (
                    <CheckCircle2 className="w-4 h-4 text-[#2d6a4f] mt-0.5 shrink-0" />
                  ) : (
                    <XCircle className="w-4 h-4 text-[#8b3a2a] mt-0.5 shrink-0" />
                  )}
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-[#0a0a0a] font-mono">
                      {c.label}
                    </div>
                    <div className="text-[11px] text-[#8d8d8d] font-sans truncate">
                      {c.description}
                    </div>
                  </div>
                </div>

                <div className="shrink-0">
                  <Badge
                    status={passed ? 'SUCCESS' : 'FAILED'}
                    label={passed ? 'PASSED' : 'NOT SATISFIED'}
                    size="xs"
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* TECHNICAL DETAILS TOGGLE */}
      <div className="border border-[#e6e5e2] rounded-lg overflow-hidden bg-white shadow-xs">
        <button
          type="button"
          onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
          className="w-full p-4 text-left flex items-center justify-between text-xs font-mono font-bold text-[#0a0a0a] hover:bg-[#fafaf8] transition-colors"
        >
          <span>TECHNICAL CRYPTOGRAPHIC EVIDENCE INSPECTION</span>
          {showTechnicalDetails ? (
            <ChevronUp className="w-4 h-4 text-[#8d8d8d]" />
          ) : (
            <ChevronDown className="w-4 h-4 text-[#8d8d8d]" />
          )}
        </button>

        {showTechnicalDetails && (
          <div className="p-4 border-t border-[#e6e5e2] bg-[#fafaf8] font-mono text-xs space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="p-2.5 bg-white border border-[#e6e5e2] rounded space-y-1">
                <span className="text-[#8d8d8d] text-[10px] font-semibold">UPLOADED FILE SHA-256:</span>
                <HashDisplay hash={result.uploaded_document_hash} length={8} />
              </div>

              <div className="p-2.5 bg-white border border-[#e6e5e2] rounded space-y-1">
                <span className="text-[#8d8d8d] text-[10px] font-semibold">EXTRACTED TOKEN (OPAQUE):</span>
                <HashDisplay hash={result.watermark_token} length={8} />
              </div>

              {attribution.session_id && (
                <div className="p-2.5 bg-white border border-[#e6e5e2] rounded space-y-1">
                  <span className="text-[#8d8d8d] text-[10px] font-semibold">MATCHED SESSION ID:</span>
                  <div className="text-[#0a0a0a] font-bold">{attribution.session_id}</div>
                </div>
              )}

              {attribution.block_index !== undefined && (
                <div className="p-2.5 bg-white border border-[#e6e5e2] rounded space-y-1">
                  <span className="text-[#8d8d8d] text-[10px] font-semibold">LEDGER BLOCK:</span>
                  <div className="text-[#b15f2c] font-bold">Block #{attribution.block_index}</div>
                </div>
              )}
            </div>

            {result.failures && result.failures.length > 0 && (
              <div className="p-3 bg-[#8b3a2a]/08 border border-[#8b3a2a]/20 rounded space-y-1.5">
                <span className="text-[#8b3a2a] font-bold text-[11px]">DISQUALIFYING FAILURES:</span>
                <ul className="list-disc list-inside text-[#541a10] text-[11px] space-y-1 font-sans">
                  {result.failures.map((f, i) => (
                    <li key={i}>
                      <span className="font-mono font-semibold">{f.check}</span>: {f.reason}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
