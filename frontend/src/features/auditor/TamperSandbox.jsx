import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  RotateCcw,
  ShieldAlert,
  CheckCircle2,
  Layers,
  Wrench,
  RefreshCw,
} from 'lucide-react';
import { ledgerApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import ConfirmModal from '../../components/common/ConfirmModal';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function TamperSandbox() {
  const [blocks, setBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Tamper Form
  const [targetBlockIndex, setTargetBlockIndex] = useState(1);
  const [targetField, setTargetField] = useState('canonical_record');
  const [customValue, setCustomValue] = useState('{"tampered": true}');
  const [tampering, setTampering] = useState(false);
  const [showTamperConfirm, setShowTamperConfirm] = useState(false);

  // Reset State
  const [resetting, setResetting] = useState(false);
  const [showResetConfirm, setShowResetConfirm] = useState(false);

  // Verification result
  const [verificationResult, setVerificationResult] = useState(null);

  const loadBlocks = async () => {
    setLoading(true);
    setError(null);
    try {
      const b = await ledgerApi.getBlocks();
      setBlocks(b || []);
      if (b && b.length > 1) {
        setTargetBlockIndex(b[1].block_index);
      } else if (b && b.length > 0) {
        setTargetBlockIndex(b[0].block_index);
      }
    } catch (err) {
      setError(err.message || 'Failed to load ledger blocks.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBlocks();
  }, []);

  const handleApplyTamper = async () => {
    setShowTamperConfirm(false);
    setTampering(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await ledgerApi.tamperTest(Number(targetBlockIndex), targetField, customValue);
      setSuccessMsg(`Simulated tampering injected into Block #${targetBlockIndex} (Field: ${targetField}).`);
      const v = await ledgerApi.verify();
      setVerificationResult(v);
      await loadBlocks();
    } catch (err) {
      setError(err.message || 'Tamper test execution failed.');
    } finally {
      setTampering(false);
    }
  };

  const handleReset = async () => {
    setShowResetConfirm(false);
    setResetting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await ledgerApi.reset();
      setSuccessMsg('Demo environment reset successfully. New ledger instance initialized.');
      setVerificationResult(null);
      await loadBlocks();
    } catch (err) {
      setError(err.message || 'Reset failed.');
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Simulation Isolation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full bg-[#b15f2c]/10 border border-[#b15f2c]/30 text-[10px] font-mono font-bold text-[#b15f2c] uppercase tracking-wider">
              DEMONSTRATION / ADVERSARIAL TEST MODE
            </span>
          </div>
          <h2 className="text-xl font-bold text-[#0a0a0a] tracking-tight flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-[#b15f2c]" />
            Adversarial Ledger Tamper Sandbox
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-1">
            VERIFY MATHEMATICAL TAMPER-EVIDENCE BY SIMULATING DIRECT DATABASE CORRUPTION
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={loadBlocks} loading={loading} size="sm" icon={RefreshCw}>
            Refresh
          </Button>
          <Button
            variant="secondary"
            onClick={() => setShowResetConfirm(true)}
            loading={resetting}
            size="sm"
            icon={RotateCcw}
            className="text-[#8b3a2a] hover:bg-[#8b3a2a]/10 hover:border-[#8b3a2a]/30"
          >
            Reset Demo State
          </Button>
        </div>
      </div>

      {error && <Alert type="error" title="Notice" message={error} onDismiss={() => setError(null)} />}
      {successMsg && <Alert type="success" title="Execution Completed" message={successMsg} onDismiss={() => setSuccessMsg(null)} />}

      {/* Verification Status Banner if tested */}
      {verificationResult && (
        <div
          className={`p-4 rounded-xl border font-mono text-xs flex items-center justify-between gap-3 ${
            verificationResult.chain_valid
              ? 'bg-[#2d6a4f]/10 border-[#2d6a4f]/30 text-[#1b4332]'
              : 'bg-[#8b3a2a]/10 border-[#8b3a2a]/30 text-[#5c1d11]'
          }`}
        >
          <div className="flex items-center gap-3">
            {verificationResult.chain_valid ? (
              <CheckCircle2 className="w-5 h-5 text-[#2d6a4f] shrink-0" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-[#8b3a2a] shrink-0" />
            )}
            <div>
              <div className="font-bold tracking-wide uppercase">
                CHAIN VERIFICATION STATUS: {verificationResult.chain_valid ? 'INTACT' : 'TAMPER DETECTED — CHAIN BROKEN'}
              </div>
              <div className="text-[12px] font-sans mt-0.5 opacity-90">
                {verificationResult.error_message || 'Cryptographic chain verification failed as expected under simulated corruption.'}
              </div>
            </div>
          </div>
          <Badge status={verificationResult.chain_valid ? 'VERIFIED' : 'FAILED'} size="sm" />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Tamper Control Card */}
        <div className="lg:col-span-5 space-y-6">
          <Card
            title="Inject Controlled Tamper"
            subtitle="Directly alters SQLite storage outside normal signing logic"
            icon={Wrench}
          >
            <div className="space-y-4 font-mono text-xs">
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded-lg text-[11px] text-[#3a3a3a] space-y-1 font-sans">
                <span className="font-bold font-mono text-[#b15f2c]">SIMULATION PURPOSE:</span>
                <p>
                  Demonstrates that any unauthorized direct modification of raw disk records causes subsequent verification, attribution, and auditor checks to fail closed.
                </p>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#3a3a3a] mb-1.5 font-sans">
                  Target Block Index
                </label>
                <select
                  value={targetBlockIndex}
                  onChange={(e) => setTargetBlockIndex(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#d8d6d2] rounded-lg text-[#0a0a0a] text-xs focus:outline-none focus:ring-1 focus:ring-[#b15f2c]"
                >
                  {blocks.map((b) => (
                    <option key={b.block_index} value={b.block_index}>
                      Block #{b.block_index} ({b.event_type}) — {b.signer_id}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#3a3a3a] mb-1.5 font-sans">
                  Target Field to Corrupt
                </label>
                <select
                  value={targetField}
                  onChange={(e) => setTargetField(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#d8d6d2] rounded-lg text-[#0a0a0a] text-xs focus:outline-none focus:ring-1 focus:ring-[#b15f2c]"
                >
                  <option value="canonical_record">canonical_record (Payload)</option>
                  <option value="timestamp">timestamp (Time spoofing)</option>
                  <option value="previous_hash">previous_hash (Break hash chain)</option>
                  <option value="signature">signature (Corrupt ML-DSA signature)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#3a3a3a] mb-1.5 font-sans">
                  Tampered Value Injection
                </label>
                <input
                  type="text"
                  value={customValue}
                  onChange={(e) => setCustomValue(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#d8d6d2] rounded-lg text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c]"
                />
              </div>

              <Button
                variant="danger"
                onClick={() => setShowTamperConfirm(true)}
                disabled={tampering || blocks.length === 0}
                loading={tampering}
                className="w-full justify-center"
                icon={AlertTriangle}
              >
                Execute Controlled Tamper Test
              </Button>
            </div>
          </Card>
        </div>

        {/* Ledger State List */}
        <div className="lg:col-span-7">
          <Card
            title="Current Ledger Chain State"
            subtitle="Inspect all blocks subject to hash verification"
            icon={Layers}
            bodyClassName="p-0"
          >
            {blocks.length === 0 ? (
              <EmptyState
                icon={Layers}
                title="No Ledger Blocks Found"
                description="Initialize operations to generate immutable ledger blocks."
              />
            ) : (
              <div className="overflow-x-auto max-h-96 overflow-y-auto">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-[#fafaf8] text-[#8d8d8d] border-b border-[#e6e5e2] sticky top-0">
                    <tr>
                      <th className="px-4 py-3 font-semibold">BLOCK</th>
                      <th className="px-4 py-3 font-semibold">EVENT</th>
                      <th className="px-4 py-3 font-semibold">SIGNER</th>
                      <th className="px-4 py-3 font-semibold">BLOCK HASH</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#e6e5e2]">
                    {blocks.map((b) => (
                      <tr
                        key={b.block_index}
                        className={
                          Number(targetBlockIndex) === b.block_index
                            ? 'bg-[#b15f2c]/08 font-bold'
                            : 'hover:bg-[#fafaf8]'
                        }
                      >
                        <td className="px-4 py-3 text-[#b15f2c]">#{b.block_index}</td>
                        <td className="px-4 py-3 text-[#0a0a0a] font-sans">{b.event_type}</td>
                        <td className="px-4 py-3 text-[#3a3a3a]">{b.signer_id}</td>
                        <td className="px-4 py-3">
                          <HashDisplay hash={b.block_hash} length={6} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>

      <ConfirmModal
        isOpen={showTamperConfirm}
        onClose={() => setShowTamperConfirm(false)}
        onConfirm={handleApplyTamper}
        title="Execute Adversarial Tamper Simulation"
        message={`Confirm tampering Block #${targetBlockIndex}, field '${targetField}'?`}
        consequences="This will deliberately corrupt the SQLite database to verify that the cryptographic verification engine detects tampering and refuses attribution."
        reversible={false}
        confirmText="Inject Tamper"
        variant="danger"
        loading={tampering}
      />

      <ConfirmModal
        isOpen={showResetConfirm}
        onClose={() => setShowResetConfirm(false)}
        onConfirm={handleReset}
        title="Reset Demonstration Environment"
        message="Are you sure you want to reset demo ledger blocks and sessions?"
        consequences="Clears demo documents, sessions, and ledger blocks. Principals, encrypted software keystores, trust manifests, and audit trail are preserved."
        reversible={false}
        confirmText="Reset Ledger"
        variant="danger"
        loading={resetting}
      />
    </div>
  );
}

