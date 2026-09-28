import React, { useState, useEffect } from 'react';
import { Layers, CheckCircle2, ShieldAlert, RefreshCw, Eye } from 'lucide-react';
import { ledgerApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import Modal from '../../components/common/Modal';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function LedgerExplorer() {
  const [blocks, setBlocks] = useState([]);
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(null);

  // Selected Block Modal
  const [selectedBlock, setSelectedBlock] = useState(null);

  const loadLedger = async () => {
    setLoading(true);
    setError(null);
    try {
      const [b, v] = await Promise.all([
        ledgerApi.getBlocks(),
        ledgerApi.verify(),
      ]);
      setBlocks(b || []);
      setVerification(v || null);
    } catch (err) {
      setError(err.message || 'Failed to load ledger blocks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLedger();
  }, []);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const v = await ledgerApi.verify();
      setVerification(v);
    } catch (err) {
      setError(err.message || 'Ledger verification failed.');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <Layers className="w-5 h-5 text-[#b15f2c]" />
            Append-Only Ledger Explorer
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            CRYPTOGRAPHIC HASH-CHAINED FORENSIC PROVENANCE LEDGER
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={loadLedger} loading={loading} size="sm" icon={RefreshCw}>
            Refresh
          </Button>
          <Button variant="primary" onClick={handleVerify} loading={verifying} size="sm" icon={CheckCircle2}>
            Verify Chain Integrity
          </Button>
        </div>
      </div>

      {error && <Alert type="error" title="Ledger Notice" message={error} onDismiss={() => setError(null)} />}

      {/* Verification Summary Banner */}
      {verification && (
        <div
          className={`p-4 rounded-lg border font-mono text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs ${
            verification.chain_valid
              ? 'bg-[#2d6a4f]/08 border-[#2d6a4f]/30 text-[#1b4332]'
              : 'bg-[#8b3a2a]/08 border-[#8b3a2a]/30 text-[#541a10]'
          }`}
        >
          <div className="flex items-center gap-3">
            {verification.chain_valid ? (
              <CheckCircle2 className="w-5 h-5 text-[#2d6a4f] shrink-0" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-[#8b3a2a] shrink-0" />
            )}
            <div>
              <div className="font-bold uppercase tracking-wide">
                LEDGER INTEGRITY: {verification.chain_valid ? 'MATHEMATICALLY VALID' : 'TAMPER / INTEGRITY VIOLATION DETECTED'}
              </div>
              <div className="text-[11px] text-[#3a3a3a] font-sans mt-0.5">
                {verification.chain_valid
                  ? `All ${verification.total_blocks} blocks chained with valid SHA-256 hashes and digital signatures.`
                  : verification.error_message || 'Chain validation failed.'}
              </div>
            </div>
          </div>
          <Badge status={verification.chain_valid ? 'VERIFIED' : 'FAILED'} size="sm" />
        </div>
      )}

      {/* Blocks Table */}
      <Card
        title="Ledger Blocks Chain"
        subtitle={`Total committed blocks: ${blocks.length}`}
        icon={Layers}
        bodyClassName="p-0"
      >
        {blocks.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={Layers}
              title="Ledger at Genesis"
              description="No event blocks have been recorded yet. Operations from Authority, Recipient, or Investigator will commit blocks to this chain."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#fafaf8] text-[#8d8d8d] border-b border-[#e6e5e2]">
                <tr>
                  <th className="px-4 py-3">BLOCK</th>
                  <th className="px-4 py-3">EVENT TYPE</th>
                  <th className="px-4 py-3">SIGNER</th>
                  <th className="px-4 py-3">BLOCK HASH</th>
                  <th className="px-4 py-3">PREVIOUS HASH</th>
                  <th className="px-4 py-3">TIMESTAMP</th>
                  <th className="px-4 py-3 text-right">INSPECT</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e6e5e2]">
                {blocks.map((b) => (
                  <tr key={b.block_index} className="hover:bg-[#fafaf8] transition-colors">
                    <td className="px-4 py-3 font-bold text-[#b15f2c]">
                      #{b.block_index}
                    </td>
                    <td className="px-4 py-3 font-semibold text-[#0a0a0a]">
                      {b.event_type}
                    </td>
                    <td className="px-4 py-3 text-[#3a3a3a]">
                      {b.signer_id || 'SYSTEM'}
                    </td>
                    <td className="px-4 py-3">
                      <HashDisplay hash={b.block_hash} length={6} />
                    </td>
                    <td className="px-4 py-3">
                      <HashDisplay hash={b.previous_hash} length={6} />
                    </td>
                    <td className="px-4 py-3 text-[11px] text-[#8d8d8d] font-sans">
                      {new Date(b.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setSelectedBlock(b)}
                        icon={Eye}
                      >
                        Inspect
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Block Details Modal */}
      <Modal
        isOpen={!!selectedBlock}
        onClose={() => setSelectedBlock(null)}
        title={`Ledger Block #${selectedBlock?.block_index}`}
        subtitle={`Event: ${selectedBlock?.event_type}`}
        maxWidth="max-w-2xl"
      >
        {selectedBlock && (
          <div className="space-y-4 font-mono text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                <span className="text-[#8d8d8d] text-[10px] font-semibold">SIGNER PRINCIPAL:</span>
                <div className="text-[#0a0a0a] font-bold">{selectedBlock.signer_id}</div>
              </div>
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                <span className="text-[#8d8d8d] text-[10px] font-semibold">TIMESTAMP:</span>
                <div className="text-[#0a0a0a]">{selectedBlock.timestamp}</div>
              </div>
            </div>

            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
              <span className="text-[#8d8d8d] text-[10px] font-semibold">PREVIOUS BLOCK HASH:</span>
              <HashDisplay hash={selectedBlock.previous_hash} truncate={false} />
            </div>

            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
              <span className="text-[#8d8d8d] text-[10px] font-semibold">BLOCK HASH:</span>
              <HashDisplay hash={selectedBlock.block_hash} truncate={false} />
            </div>

            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
              <span className="text-[#8d8d8d] text-[10px] font-semibold">RECORD SHA-256 HASH:</span>
              <HashDisplay hash={selectedBlock.record_hash} truncate={false} />
            </div>

            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
              <span className="text-[#8d8d8d] text-[10px] font-semibold">ML-DSA-44 DIGITAL SIGNATURE:</span>
              <HashDisplay hash={selectedBlock.signature} length={16} />
            </div>

            {selectedBlock.canonical_record && (
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-2">
                <span className="text-[#0a0a0a] text-[10px] uppercase font-bold">
                  CANONICAL RECORD PAYLOAD:
                </span>
                <pre className="p-2.5 bg-white border border-[#e6e5e2] rounded overflow-x-auto text-[11px] text-[#0a0a0a] max-h-48 overflow-y-auto font-mono">
                  {JSON.stringify(selectedBlock.canonical_record, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
