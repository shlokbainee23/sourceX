import React, { useState, useEffect } from 'react';
import { Eye, ShieldCheck, CheckCircle2, AlertTriangle, Layers, RefreshCw } from 'lucide-react';
import { investigationApi, ledgerApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function VisualInvarianceTool() {
  const [sessions, setSessions] = useState([]);
  const [sessionA, setSessionA] = useState('');
  const [sessionB, setSessionB] = useState('');
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState(null);
  const [error, setError] = useState(null);

  const loadSessions = async () => {
    setLoadingSessions(true);
    setError(null);
    try {
      const blocks = await ledgerApi.getBlocks();
      // Extract sessions from DOCUMENT_DECRYPTED blocks
      const decBlocks = (blocks || []).filter((b) => b.event_type === 'DOCUMENT_DECRYPTED');
      const sessionList = decBlocks.map((b) => {
        const rec = b.canonical_record || {};
        return {
          session_id: rec.session_id || `SES-B${b.block_index}`,
          document_id: rec.document_id || 'DOC-???',
          recipient_id: b.signer_id || rec.recipient_id || 'R???',
          block_index: b.block_index,
        };
      });

      setSessions(sessionList);
      if (sessionList.length >= 2) {
        setSessionA(sessionList[0].session_id);
        setSessionB(sessionList[1].session_id);
      } else if (sessionList.length === 1) {
        setSessionA(sessionList[0].session_id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load ledger sessions.');
    } finally {
      setLoadingSessions(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleCompare = async (e) => {
    e.preventDefault();
    if (!sessionA || !sessionB) {
      setError('Please select two distinct sessions for comparison.');
      return;
    }
    if (sessionA === sessionB) {
      setError('Sessions must be distinct. Select two different recipient delivery sessions.');
      return;
    }

    setComparing(true);
    setError(null);
    setComparisonResult(null);

    try {
      const res = await investigationApi.compareInvariance(sessionA, sessionB);
      setComparisonResult(res);
    } catch (err) {
      setError(err.message || 'Visual invariance comparison failed.');
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <Eye className="w-5 h-5 text-[#b15f2c]" />
            Visual Invariance & Forensic Distinction Analyzer
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            150-DPI PAGE RASTERIZATION ANALYSIS & FORENSIC SEPARATION PROOF
          </p>
        </div>
        <Button variant="secondary" onClick={loadSessions} loading={loadingSessions} size="sm" icon={RefreshCw}>
          Refresh Sessions
        </Button>
      </div>

      {error && <Alert type="error" title="Invariance Notice" message={error} onDismiss={() => setError(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Selection Card */}
        <div className="lg:col-span-5 space-y-6">
          <Card
            title="Session Comparison Target"
            subtitle="Select two delivered session records to test visual equivalence"
            icon={Layers}
          >
            {sessions.length < 2 ? (
              <div className="p-6 text-center space-y-2 bg-[#fafaf8] rounded border border-[#e6e5e2]">
                <AlertTriangle className="w-6 h-6 text-[#b15f2c] mx-auto" />
                <h4 className="text-xs font-bold text-[#0a0a0a] uppercase font-mono">
                  Insufficient Sessions for Comparison
                </h4>
                <p className="text-xs text-[#8d8d8d] font-sans">
                  Visual invariance requires at least two distinct recipient delivery sessions. Currently {sessions.length} session(s) recorded in ledger.
                </p>
              </div>
            ) : (
              <form onSubmit={handleCompare} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                    Session Sample A
                  </label>
                  <select
                    value={sessionA}
                    onChange={(e) => setSessionA(e.target.value)}
                    className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c]"
                  >
                    {sessions.map((s) => (
                      <option key={s.session_id} value={s.session_id}>
                        {s.session_id} ({s.recipient_id} — {s.document_id})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                    Session Sample B
                  </label>
                  <select
                    value={sessionB}
                    onChange={(e) => setSessionB(e.target.value)}
                    className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c]"
                  >
                    {sessions.map((s) => (
                      <option key={s.session_id} value={s.session_id}>
                        {s.session_id} ({s.recipient_id} — {s.document_id})
                      </option>
                    ))}
                  </select>
                </div>

                <Button
                  type="submit"
                  variant="primary"
                  loading={comparing}
                  disabled={comparing || sessionA === sessionB}
                  className="w-full"
                  icon={Eye}
                >
                  Analyze 150-DPI Invariance
                </Button>
              </form>
            )}

            <div className="mt-4 p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded font-mono text-[11px] text-[#8d8d8d] space-y-1">
              <span className="text-[#0a0a0a] font-semibold">ISO 32000-1 INVARIANCE CRITERIA:</span>
              <p className="leading-relaxed">
                Each delivered copy must produce an identical SHA-256 raster hash at 150 DPI (zero pixel variance for human readers) while retaining distinct file SHA-256 hashes to guarantee forensic attribution.
              </p>
            </div>
          </Card>
        </div>

        {/* Results Card */}
        <div className="lg:col-span-7">
          <Card
            title="Raster Comparison Verdict"
            subtitle="Page-by-page rendering comparison recorded at delivery"
            icon={ShieldCheck}
          >
            {comparisonResult ? (
              <div className="space-y-4 font-mono text-xs">
                {/* Result Verdict Banner */}
                <div
                  className={`p-4 rounded-lg border space-y-2 ${
                    comparisonResult.is_visually_identical
                      ? 'bg-[#2d6a4f]/08 border-[#2d6a4f]/30'
                      : 'bg-[#8b3a2a]/08 border-[#8b3a2a]/30'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm uppercase flex items-center gap-2 text-[#0a0a0a] font-mono">
                      {comparisonResult.is_visually_identical ? (
                        <>
                          <CheckCircle2 className="w-5 h-5 text-[#2d6a4f]" />
                          <span>VISUALLY IDENTICAL · 0 DIFFERING PIXELS</span>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="w-5 h-5 text-[#8b3a2a]" />
                          <span>VISUAL DISCREPANCY DETECTED</span>
                        </>
                      )}
                    </span>
                    <Badge
                      status={comparisonResult.is_visually_identical ? 'VERIFIED' : 'FAILED'}
                      label={comparisonResult.is_visually_identical ? 'PASSED' : 'DISCREPANCY'}
                      size="sm"
                    />
                  </div>
                  <p className="text-[11px] text-[#3a3a3a] font-sans">
                    {comparisonResult.is_visually_identical
                      ? 'Both delivered copies render pixel-identically at 150 DPI across all pages. The human viewer experiences zero distortion or visible artifact.'
                      : 'The rendered output differs between the two copies.'}
                  </p>
                </div>

                {/* Evidence Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                    <span className="text-[#8d8d8d] text-[10px] font-semibold">SAMPLE A RENDER HASH:</span>
                    <HashDisplay hash={comparisonResult.render_hash_a} length={6} />
                  </div>

                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                    <span className="text-[#8d8d8d] text-[10px] font-semibold">SAMPLE B RENDER HASH:</span>
                    <HashDisplay hash={comparisonResult.render_hash_b} length={6} />
                  </div>

                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                    <span className="text-[#8d8d8d] text-[10px] font-semibold">SAMPLE A FILE SHA-256:</span>
                    <HashDisplay hash={comparisonResult.delivered_document_hash_a} length={6} />
                  </div>

                  <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                    <span className="text-[#8d8d8d] text-[10px] font-semibold">SAMPLE B FILE SHA-256:</span>
                    <HashDisplay hash={comparisonResult.delivered_document_hash_b} length={6} />
                  </div>
                </div>

                <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded flex items-center justify-between">
                  <span className="text-[#8d8d8d]">FORENSICALLY DISTINCT COPIES:</span>
                  <span className="text-[#2d6a4f] font-bold">
                    {comparisonResult.forensically_distinct ? 'YES (DISTINCT HASHES)' : 'NO'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-8">
                <EmptyState
                  icon={Eye}
                  title="Awaiting Comparison Execution"
                  description="Select two recipient delivery sessions on the left and run analysis to evaluate render hash equivalence at 150 DPI."
                />
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
