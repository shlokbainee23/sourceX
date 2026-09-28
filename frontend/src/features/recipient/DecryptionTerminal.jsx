import React, { useState, useEffect } from 'react';
import {
  Lock,
  Unlock,
  KeyRound,
  Download,
  ShieldCheck,
  FileText,
  CheckCircle2,
} from 'lucide-react';
import { documentsApi, decryptionApi } from '../../services/api';
import { useAuth } from '../../app/AuthContext';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import StepUpModal from '../../components/common/StepUpModal';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function DecryptionTerminal({ preselectedDocId }) {
  const { user } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(preselectedDocId || '');
  const [loadingDocs, setLoadingDocs] = useState(true);

  // Decryption State
  const [stepUpOpen, setStepUpOpen] = useState(false);
  const [decrypting, setDecrypting] = useState(false);
  const [decryptionResult, setDecryptionResult] = useState(null);
  const [error, setError] = useState(null);

  // Delivery Download State
  const [downloaded, setDownloaded] = useState(false);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    let active = true;
    const fetchDocs = async () => {
      setLoadingDocs(true);
      try {
        const docs = await documentsApi.list();
        if (active) {
          setDocuments(docs || []);
          if (docs && docs.length > 0) {
            setSelectedDocId((prev) => prev || docs[0].document_id);
          }
        }
      } catch (err) {
        if (active) setError(err.message || 'Failed to fetch assigned directives.');
      } finally {
        if (active) setLoadingDocs(false);
      }
    };
    fetchDocs();
    return () => {
      active = false;
    };
  }, []);

  const handleStartDecryption = () => {
    if (!selectedDocId) {
      setError('Please select an assigned directive.');
      return;
    }
    setError(null);
    setStepUpOpen(true);
  };

  const handleStepUpSubmit = async (passphrase) => {
    setDecrypting(true);
    setError(null);
    try {
      const result = await decryptionApi.decrypt(selectedDocId, passphrase);
      setDecryptionResult(result);
      setStepUpOpen(false);
      setDownloaded(false);
    } catch (err) {
      setError(err.message || 'Decryption denied. Keystore could not be unlocked or verification failed.');
    } finally {
      setDecrypting(false);
    }
  };

  const handleDownload = async () => {
    if (!decryptionResult || downloaded) return;
    setDownloading(true);
    setError(null);
    try {
      const blob = await decryptionApi.downloadDelivery(decryptionResult.session_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `delivered_${selectedDocId}_${user.principal_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      setDownloaded(true);
    } catch (err) {
      setError(err.message || 'Download failed or delivery copy has already been purged.');
    } finally {
      setDownloading(false);
    }
  };

  const selectedDoc = documents.find((d) => d.document_id === selectedDocId);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <Lock className="w-5 h-5 text-[#b15f2c]" />
            Secure Decryption Terminal
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            STEP-UP CRYPTOGRAPHIC UNLOCK, FORENSIC MARKING & PROVENANCE SIGNING
          </p>
        </div>
      </div>

      {error && <Alert type="error" title="Terminal Notice" message={error} onDismiss={() => setError(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Directive Selection & Decrypt Trigger */}
        <div className="lg:col-span-5 space-y-6">
          <Card
            title="1. Directive Selection"
            subtitle="Select incoming encrypted broadcast directive"
            icon={FileText}
          >
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                  Directive Identifier
                </label>
                <select
                  value={selectedDocId}
                  onChange={(e) => {
                    setSelectedDocId(e.target.value);
                    setDecryptionResult(null);
                    setDownloaded(false);
                  }}
                  disabled={loadingDocs || decrypting}
                  className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c]"
                >
                  {documents.length === 0 ? (
                    <option value="">No assigned directives</option>
                  ) : (
                    documents.map((d) => (
                      <option key={d.document_id} value={d.document_id}>
                        {d.document_id} ({d.classification})
                      </option>
                    ))
                  )}
                </select>
              </div>

              {selectedDoc && (
                <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded font-mono text-xs space-y-2">
                  <div className="flex justify-between">
                    <span className="text-[#8d8d8d]">CLASSIFICATION:</span>
                    <span className="text-[#b15f2c] font-bold">{selectedDoc.classification}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8d8d8d]">ORIGINAL SHA-256:</span>
                    <HashDisplay hash={selectedDoc.original_hash} length={6} />
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#8d8d8d]">ISSUING AUTHORITY:</span>
                    <span className="text-[#0a0a0a] font-medium">{selectedDoc.owner}</span>
                  </div>
                </div>
              )}

              <Button
                variant="primary"
                onClick={handleStartDecryption}
                disabled={!selectedDocId || decrypting}
                loading={decrypting}
                className="w-full"
                icon={Unlock}
              >
                Initiate Step-Up Decryption
              </Button>

              <div className="p-3 bg-[#b15f2c]/08 border border-[#b15f2c]/20 rounded text-[11px] text-[#4a240d] space-y-1">
                <div className="font-semibold text-[#0a0a0a] flex items-center gap-1.5 font-mono text-[11px]">
                  <KeyRound className="w-3.5 h-3.5 text-[#b15f2c]" />
                  <span>STEP-UP CRYPTOGRAPHIC ASSURANCE</span>
                </div>
                <p className="leading-relaxed">
                  Requires keystore passphrase. The ML-KEM private key decapsulates the CEK and your ML-DSA-44 key signs the immutable provenance record. Keys are purged from memory immediately after execution.
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* Right: Verified Decryption Result & One-Time Delivery */}
        <div className="lg:col-span-7">
          <Card
            title="2. Cryptographic Provenance & Delivery"
            subtitle="Verified ledger commitment and one-time delivered copy"
            icon={ShieldCheck}
          >
            {decrypting ? (
              <div className="p-12 text-center space-y-3 font-mono">
                <div className="w-8 h-8 border-2 border-[#b15f2c] border-t-transparent rounded-full animate-spin mx-auto" />
                <div className="text-xs font-bold text-[#0a0a0a] uppercase tracking-wider font-mono">
                  Cryptographic Operation In Progress
                </div>
                <p className="text-[11px] text-[#8d8d8d] max-w-sm mx-auto leading-relaxed">
                  Executing ML-KEM-768 decapsulation, AES-256-GCM decryption, ISO 32000-1 watermark embedding, and ML-DSA-44 provenance signature commitment to ledger...
                </p>
              </div>
            ) : decryptionResult ? (
              <div className="space-y-5 font-mono text-xs">
                {/* Result Summary Banner */}
                <div className="p-4 bg-[#2d6a4f]/08 border border-[#2d6a4f]/25 rounded-lg space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#1b4332] uppercase tracking-wide flex items-center gap-1.5 font-mono">
                      <CheckCircle2 className="w-4 h-4 text-[#2d6a4f]" />
                      PROVENANCE COMMITTED TO LEDGER
                    </span>
                    <Badge status="VERIFIED" size="xs" />
                  </div>
                  <p className="text-[11px] text-[#1b4332] font-sans">
                    Document successfully decrypted and marked. An immutable decryption record was signed by {user.principal_id} and committed to Block #{decryptionResult.block_index}.
                  </p>
                </div>

                {/* Evidence Details Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                    <span className="text-[#8d8d8d] text-[11px] font-semibold">SESSION ID:</span>
                    <div className="font-bold text-[#0a0a0a]">{decryptionResult.session_id}</div>
                  </div>

                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                    <span className="text-[#8d8d8d] text-[11px] font-semibold">LEDGER BLOCK INDEX:</span>
                    <div className="font-bold text-[#b15f2c]">Block #{decryptionResult.block_index}</div>
                  </div>

                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                    <span className="text-[#8d8d8d] text-[11px] font-semibold">WATERMARK TOKEN (OPAQUE):</span>
                    <HashDisplay hash={decryptionResult.watermark_token} length={6} />
                  </div>

                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                    <span className="text-[#8d8d8d] text-[11px] font-semibold">DELIVERED DOCUMENT HASH:</span>
                    <HashDisplay hash={decryptionResult.delivered_document_hash} length={6} />
                  </div>

                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1 md:col-span-2">
                    <span className="text-[#8d8d8d] text-[11px] font-semibold">150-DPI VISUAL INVARIANCE RENDER HASH:</span>
                    <div className="flex items-center gap-2">
                      <HashDisplay hash={decryptionResult.delivered_render_hash} length={8} />
                      <span className="text-[#2d6a4f] text-[10px] font-sans font-semibold">✓ VISUALLY IDENTICAL</span>
                    </div>
                  </div>

                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1 md:col-span-2">
                    <span className="text-[#8d8d8d] text-[11px] font-semibold">ML-DSA-44 RECIPIENT SIGNATURE:</span>
                    <HashDisplay hash={decryptionResult.signature} length={12} />
                  </div>
                </div>

                {/* One-Time Download Section */}
                <div className="p-4 bg-[#fafaf8] border border-[#e6e5e2] rounded-lg space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-semibold text-[#0a0a0a] uppercase tracking-wide text-xs font-mono">
                        One-Time Delivered Copy
                      </h4>
                      <p className="text-[11px] text-[#8d8d8d] font-sans mt-0.5">
                        {downloaded
                          ? 'DELIVERY COMPLETE: Protected delivery copy destroyed from disk.'
                          : 'Download the marked confidential directive. The server-side copy will be permanently destroyed.'}
                      </p>
                    </div>
                    {downloaded && <Badge status="ACTIVE" label="CLAIMED" size="xs" />}
                  </div>

                  <Button
                    variant={downloaded ? 'secondary' : 'primary'}
                    onClick={handleDownload}
                    disabled={downloaded || downloading}
                    loading={downloading}
                    className="w-full"
                    icon={Download}
                  >
                    {downloaded
                      ? 'Delivered Copy Destroyed (HTTP 410)'
                      : 'Download Marked Directive (One-Time Only)'}
                  </Button>
                </div>
              </div>
            ) : (
              <div className="p-8">
                <EmptyState
                  icon={Lock}
                  title="Awaiting Step-Up Authentication"
                  description="Select an assigned directive on the left and initiate step-up decryption to verify provenance and access your delivery copy."
                />
              </div>
            )}
          </Card>
        </div>
      </div>

      <StepUpModal
        isOpen={stepUpOpen}
        onClose={() => setStepUpOpen(false)}
        onSubmit={handleStepUpSubmit}
        principalId={user?.principal_id}
        documentId={selectedDocId}
        loading={decrypting}
      />
    </div>
  );
}
