import React, { useState, useEffect } from 'react';
import { KeyRound, ShieldCheck, Cpu, RefreshCw } from 'lucide-react';
import { recipientsApi } from '../../services/api';
import { useAuth } from '../../app/AuthContext';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import Alert from '../../components/common/Alert';

export default function StationKeyStatus() {
  const { user } = useAuth();
  const [recipientData, setRecipientData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadKeyStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const recs = await recipientsApi.list();
      const match = recs.find((r) => r.recipient_id === user.principal_id);
      setRecipientData(match || null);
    } catch (err) {
      setError(err.message || 'Failed to load station key details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKeyStatus();
  }, [user]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <KeyRound className="w-5 h-5 text-[#b15f2c]" />
            Station Cryptographic Key Posture
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            POST-QUANTUM LOCAL KEYSTORE & ATTESTATION IDENTITY FOR {user?.principal_id}
          </p>
        </div>
        <Button variant="secondary" onClick={loadKeyStatus} loading={loading} size="sm" icon={RefreshCw}>
          Refresh Keys
        </Button>
      </div>

      {error && <Alert type="error" title="Notice" message={error} onDismiss={() => setError(null)} />}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card
          title="Station Identity & Keystore"
          subtitle="Enrolled cryptographic principal in WESEE Trust Manifest"
          icon={ShieldCheck}
        >
          <div className="space-y-3 font-mono text-xs">
            <div className="flex justify-between py-1 border-b border-[#e6e5e2]">
              <span className="text-[#8d8d8d]">PRINCIPAL ID:</span>
              <span className="text-[#0a0a0a] font-bold">{user?.principal_id}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#e6e5e2]">
              <span className="text-[#8d8d8d]">ASSIGNED ROLE:</span>
              <span className="text-[#b15f2c] font-semibold">{user?.role}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#e6e5e2]">
              <span className="text-[#8d8d8d]">OFFICER NAME:</span>
              <span className="text-[#0a0a0a] font-medium">{user?.name}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#e6e5e2]">
              <span className="text-[#8d8d8d]">ATTESTATION STATUS:</span>
              <Badge status={recipientData?.status || 'ACTIVE'} size="xs" />
            </div>
            <div className="flex justify-between py-1">
              <span className="text-[#8d8d8d]">STORAGE FORMAT:</span>
              <span className="text-[#3a3a3a]">scrypt + AES-256-GCM Keystore (Disk)</span>
            </div>
          </div>
        </Card>

        <Card
          title="Attested Public Keys"
          subtitle="Cryptographic public parameters published to Authority"
          icon={Cpu}
        >
          <div className="space-y-4 font-mono text-xs">
            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
              <span className="text-[#8d8d8d] text-[11px] font-semibold">
                ML-KEM-768 PUBLIC ENCAPSULATION KEY:
              </span>
              <HashDisplay hash={recipientData?.mlkem_public_key} length={8} />
              <div className="text-[10px] text-[#8d8d8d] font-sans pt-1">
                Used by Authority to wrap Content Encryption Keys for this station.
              </div>
            </div>

            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
              <span className="text-[#8d8d8d] text-[11px] font-semibold">
                ML-DSA-44 PUBLIC VERIFICATION KEY:
              </span>
              <HashDisplay hash={recipientData?.mldsa_public_key} length={8} />
              <div className="text-[10px] text-[#8d8d8d] font-sans pt-1">
                Used by Investigators to verify provenance signatures on decrypted directives.
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
