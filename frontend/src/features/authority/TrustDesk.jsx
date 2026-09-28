import React, { useState, useEffect } from 'react';
import {
  KeyRound,
  ShieldCheck,
  AlertTriangle,
  XCircle,
} from 'lucide-react';
import { trustApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import ConfirmModal from '../../components/common/ConfirmModal';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function TrustDesk() {
  const [manifest, setManifest] = useState(null);
  const [anchor, setAnchor] = useState(null);
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Revocation Modal
  const [revokeModalOpen, setRevokeModalOpen] = useState(false);
  const [revokePrincipalId, setRevokePrincipalId] = useState('');
  const [revokeReason, setRevokeReason] = useState('Security rotation');
  const [revoking, setRevoking] = useState(false);

  const loadTrustState = async () => {
    setLoading(true);
    setError(null);
    try {
      const [m, a, p] = await Promise.all([
        trustApi.getManifest().catch((e) => ({ error: e.message })),
        trustApi.getAnchor().catch((e) => ({ error: e.message })),
        trustApi.getPending().catch(() => []),
      ]);
      setManifest(m.error ? null : m);
      setAnchor(a.error ? null : a);
      setPending(p || []);
    } catch (err) {
      setError(err.message || 'Failed to load trust state.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrustState();
  }, []);

  const handleRevoke = async () => {
    if (!revokePrincipalId) return;
    setRevoking(true);
    setError(null);
    try {
      await trustApi.revoke(revokePrincipalId, revokeReason);
      setSuccessMsg(`Principal ${revokePrincipalId} revoked and all active sessions terminated.`);
      setRevokeModalOpen(false);
      await loadTrustState();
    } catch (err) {
      setError(err.message || 'Revocation operation failed.');
    } finally {
      setRevoking(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <KeyRound className="w-5 h-5 text-[#b15f2c]" />
            Trust Desk & Manifest Authority
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            CRYPTOGRAPHIC TRUST ROOT, PINNED ANCHOR & PUBLIC KEY ATTESTATION REGISTRY
          </p>
        </div>
        <Button variant="secondary" onClick={loadTrustState} loading={loading} size="sm">
          Refresh Trust Desk
        </Button>
      </div>

      {error && <Alert type="error" title="Trust Desk Notice" message={error} onDismiss={() => setError(null)} />}
      {successMsg && <Alert type="success" title="Trust State Updated" message={successMsg} onDismiss={() => setSuccessMsg(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Trust Root & Anchor Info */}
        <div className="lg:col-span-6 space-y-6">
          <Card
            title="Installation Trust Anchor"
            subtitle="Pinned ML-DSA-44 authority fingerprint stored outside data directory"
            icon={ShieldCheck}
          >
            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1.5">
                <div className="text-[#8d8d8d] text-[11px] font-semibold">AUTHORITY PIN FINGERPRINT:</div>
                <HashDisplay hash={anchor?.authority_pin} truncate={false} />
                <div className="text-[#8d8d8d] text-[10px] pt-1">
                  Pinned Location: {anchor?.pinned_file || 'trust_anchor/authority.pin'}
                </div>
              </div>

              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1.5">
                <div className="text-[#8d8d8d] text-[11px] font-semibold">MANIFEST VERSION:</div>
                <div className="text-[#b15f2c] font-bold text-sm">
                  {manifest ? `Version #${manifest.version}` : 'NOT LOADED'}
                </div>
                {manifest && (
                  <>
                    <div className="text-[#8d8d8d] text-[11px] pt-1 font-semibold">MANIFEST PACKAGE SHA-256:</div>
                    <HashDisplay hash={manifest.manifest_sha256} length={8} />
                    <div className="text-[#8d8d8d] text-[11px] pt-1 font-semibold">ATTESTED PRINCIPALS:</div>
                    <div className="text-[#0a0a0a]">
                      {manifest.principals ? manifest.principals.join(', ') : 'None'}
                    </div>
                  </>
                )}
              </div>
            </div>
          </Card>

          {/* Revoke Principal Console */}
          <Card
            title="Principal Revocation Console"
            subtitle="Revokes key material and immediately invalidates active sessions"
            icon={AlertTriangle}
          >
            <div className="space-y-4">
              <p className="text-xs text-[#3a3a3a] leading-relaxed">
                Revocation updates the trust manifest monotonically, marks the principal as REVOKED,
                and terminates any ongoing session. Existing signed records in the ledger remain verifiable.
              </p>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                    Target Principal ID
                  </label>
                  <input
                    type="text"
                    value={revokePrincipalId}
                    onChange={(e) => setRevokePrincipalId(e.target.value)}
                    placeholder="e.g. R003"
                    className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#8b3a2a] focus:border-[#8b3a2a]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                    Reason
                  </label>
                  <input
                    type="text"
                    value={revokeReason}
                    onChange={(e) => setRevokeReason(e.target.value)}
                    placeholder="Passphrase compromise / transfer"
                    className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs focus:outline-none focus:ring-1 focus:ring-[#8b3a2a] focus:border-[#8b3a2a]"
                  />
                </div>
              </div>

              <Button
                variant="danger"
                onClick={() => setRevokeModalOpen(true)}
                disabled={!revokePrincipalId.trim()}
                className="w-full"
                icon={XCircle}
              >
                Initiate Revocation Procedure
              </Button>
            </div>
          </Card>
        </div>

        {/* Pending Attestations List */}
        <div className="lg:col-span-6">
          <Card
            title="Pending Key Attestations"
            subtitle="Keys generated by station enrollment awaiting authority confirmation"
            icon={KeyRound}
            bodyClassName="p-0"
          >
            {pending.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={ShieldCheck}
                  title="All Principals Attested"
                  description="No keys pending attestation. All active stations in the manifest are cryptographically verified."
                />
              </div>
            ) : (
              <div className="divide-y divide-[#e6e5e2]">
                {pending.map((item) => (
                  <div key={item.principal_id} className="p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-xs text-[#0a0a0a]">
                        {item.principal_id} ({item.name})
                      </span>
                      <Badge status="PENDING" size="xs" />
                    </div>
                    <p className="text-[11px] text-[#8d8d8d]">
                      Confirm the ML-DSA-44 key fingerprint out of band with the key holder before attesting.
                    </p>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      <ConfirmModal
        isOpen={revokeModalOpen}
        onClose={() => setRevokeModalOpen(false)}
        onConfirm={handleRevoke}
        title="Confirm Principal Revocation"
        message={`Are you sure you want to permanently revoke ${revokePrincipalId}?`}
        consequences="This principal will be prohibited from decrypting any further documents. All active login tokens for this principal will be terminated immediately."
        reversible={false}
        confirmText="Confirm Revocation"
        variant="danger"
        loading={revoking}
      />
    </div>
  );
}
