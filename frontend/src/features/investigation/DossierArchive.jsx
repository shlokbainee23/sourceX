import React, { useState, useEffect } from 'react';
import { Archive, FileText, ArrowRight, RefreshCw, CheckCircle2 } from 'lucide-react';
import { investigationApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import Modal from '../../components/common/Modal';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function DossierArchive() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Selected Report Modal
  const [selectedReport, setSelectedReport] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const loadReports = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await investigationApi.listReports();
      setReports(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load investigation dossiers.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleOpenReport = async (reportId) => {
    setLoadingDetail(true);
    try {
      const detail = await investigationApi.getReport(reportId);
      setSelectedReport(detail);
    } catch (err) {
      setError(err.message || 'Failed to fetch report details.');
    } finally {
      setLoadingDetail(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <Archive className="w-5 h-5 text-[#b15f2c]" />
            Investigation Dossier Archive
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            CRYPTOGRAPHICALLY SIGNED HISTORICAL EVIDENCE REPORTS COMMITTED TO LEDGER
          </p>
        </div>
        <Button variant="secondary" onClick={loadReports} loading={loading} size="sm" icon={RefreshCw}>
          Refresh Dossiers
        </Button>
      </div>

      {error && <Alert type="error" title="Dossier Notice" message={error} onDismiss={() => setError(null)} />}

      <Card
        title="Stored Investigation Reports"
        subtitle={`Total registered dossiers: ${reports.length}`}
        icon={FileText}
        bodyClassName="p-0"
      >
        {reports.length === 0 ? (
          <div className="p-8">
            <EmptyState
              icon={Archive}
              title="No Dossiers Archived"
              description="No forensic reports have been recorded yet. When an investigator analyzes a suspect document, a signed report is committed to the ledger and archived here."
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-[#fafaf8] text-[#8d8d8d] border-b border-[#e6e5e2]">
                <tr>
                  <th className="px-4 py-3">REPORT ID</th>
                  <th className="px-4 py-3">INVESTIGATOR</th>
                  <th className="px-4 py-3">BLOCK</th>
                  <th className="px-4 py-3">REPORT SHA-256</th>
                  <th className="px-4 py-3">RECORDED AT</th>
                  <th className="px-4 py-3 text-right">ACTION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e6e5e2]">
                {reports.map((r) => (
                  <tr key={r.report_id} className="hover:bg-[#fafaf8] transition-colors">
                    <td className="px-4 py-3 font-semibold text-[#0a0a0a]">
                      {r.report_id}
                    </td>
                    <td className="px-4 py-3 text-[#b15f2c] font-semibold">
                      {r.investigator_id}
                    </td>
                    <td className="px-4 py-3 text-[#0a0a0a]">
                      Block #{r.block_index}
                    </td>
                    <td className="px-4 py-3">
                      <HashDisplay hash={r.report_sha256} length={6} />
                    </td>
                    <td className="px-4 py-3 text-[11px] text-[#8d8d8d] font-sans">
                      {new Date(r.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleOpenReport(r.report_id)}
                        loading={loadingDetail && selectedReport?.report_id === r.report_id}
                        icon={ArrowRight}
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

      {/* Report Inspection Modal */}
      <Modal
        isOpen={!!selectedReport}
        onClose={() => setSelectedReport(null)}
        title={`Dossier ${selectedReport?.report_id || ''}`}
        subtitle="Independent re-verification of document hash, signature, and ledger entry"
        maxWidth="max-w-2xl"
      >
        {selectedReport && (
          <div className="space-y-4 font-mono text-xs">
            <div className="p-3 bg-[#2d6a4f]/08 border border-[#2d6a4f]/25 rounded flex items-center justify-between">
              <span className="font-semibold text-[#1b4332] flex items-center gap-1.5 font-mono">
                <CheckCircle2 className="w-4 h-4 text-[#2d6a4f]" />
                CRYPTOGRAPHIC INTEGRITY: {selectedReport.valid ? 'VALID' : 'INVALID'}
              </span>
              <Badge status={selectedReport.valid ? 'VERIFIED' : 'FAILED'} size="xs" />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                <span className="text-[#8d8d8d] text-[10px] font-semibold">INVESTIGATOR PRINCIPAL:</span>
                <div className="text-[#0a0a0a] font-bold">{selectedReport.investigator_id}</div>
              </div>
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
                <span className="text-[#8d8d8d] text-[10px] font-semibold">LEDGER COMMITMENT:</span>
                <div className="text-[#b15f2c] font-bold">Block #{selectedReport.block_index}</div>
              </div>
            </div>

            <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-1">
              <span className="text-[#8d8d8d] text-[10px] font-semibold">CANONICAL REPORT SHA-256:</span>
              <HashDisplay hash={selectedReport.report_sha256} truncate={false} />
            </div>

            {selectedReport.report && (
              <div className="p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded space-y-2">
                <span className="text-[#0a0a0a] text-[10px] uppercase font-bold">
                  CANONICAL REPORT PAYLOAD (IMMUTABLE):
                </span>
                <pre className="p-2.5 bg-white border border-[#e6e5e2] rounded overflow-x-auto text-[11px] text-[#0a0a0a] max-h-60 overflow-y-auto font-mono">
                  {JSON.stringify(selectedReport.report, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
