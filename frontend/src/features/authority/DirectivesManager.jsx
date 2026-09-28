import React, { useState, useEffect } from 'react';
import {
  FileText,
  Upload,
  Lock,
  FileCheck,
  Layers,
} from 'lucide-react';
import { documentsApi, recipientsApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Badge from '../../components/common/Badge';
import HashDisplay from '../../components/common/HashDisplay';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';

export default function DirectivesManager() {
  const [documents, setDocuments] = useState([]);
  const [recipients, setRecipients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Registration Form State
  const [regDocId, setRegDocId] = useState('DOC-2026-001');
  const [regClassification, setRegClassification] = useState('CONFIDENTIAL');
  const [regFile, setRegFile] = useState(null);
  const [registering, setRegistering] = useState(false);

  // Broadcast Encryption State
  const [selectedDocId, setSelectedDocId] = useState('');
  const [selectedRecipients, setSelectedRecipients] = useState(['R001', 'R002', 'R003']);
  const [encrypting, setEncrypting] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [docs, recs] = await Promise.all([
        documentsApi.list(),
        recipientsApi.list(),
      ]);
      setDocuments(docs || []);
      setRecipients(recs || []);
      if (docs && docs.length > 0) {
        setSelectedDocId((prev) => prev || docs[0].document_id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load directives and recipients.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regFile) {
      setError('Please select a PDF document file to register.');
      return;
    }
    setRegistering(true);
    setError(null);
    setSuccessMsg(null);

    const formData = new FormData();
    formData.append('document_id', regDocId);
    formData.append('classification', regClassification);
    formData.append('file', regFile);

    try {
      const res = await documentsApi.register(formData);
      setSuccessMsg(`Directive ${res.document_id} registered. SHA-256 recorded in authority-signed ledger block.`);
      setRegFile(null);
      await loadData();
      setSelectedDocId(res.document_id);
    } catch (err) {
      setError(err.message || 'Registration failed.');
    } finally {
      setRegistering(false);
    }
  };

  const handleEncrypt = async (e) => {
    e.preventDefault();
    if (!selectedDocId) {
      setError('Please select a document to encrypt.');
      return;
    }
    if (selectedRecipients.length === 0) {
      setError('Please select at least one authorized recipient station.');
      return;
    }

    setEncrypting(true);
    setError(null);
    setSuccessMsg(null);

    try {
      await documentsApi.encrypt(selectedDocId, selectedRecipients);
      setSuccessMsg(
        `Directive ${selectedDocId} broadcast-encrypted for ${selectedRecipients.length} recipients (ML-KEM-768 wrapped CEKs).`
      );
      await loadData();
    } catch (err) {
      setError(err.message || 'Broadcast encryption failed.');
    } finally {
      setEncrypting(false);
    }
  };

  const toggleRecipient = (id) => {
    setSelectedRecipients((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <FileText className="w-5 h-5 text-[#b15f2c]" />
            Directive Registry & Broadcast Encryption
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            AUTHORITY COMMAND: REGISTER CONFIDENTIAL DOCUMENTS AND DISPATCH POST-QUANTUM PACKAGES
          </p>
        </div>
        <Button variant="secondary" onClick={loadData} loading={loading} size="sm">
          Refresh Directives
        </Button>
      </div>

      {error && <Alert type="error" title="Operation Refused" message={error} onDismiss={() => setError(null)} />}
      {successMsg && <Alert type="success" title="Cryptographic Commitment Confirmed" message={successMsg} onDismiss={() => setSuccessMsg(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Registration Panel */}
        <div className="lg:col-span-6 space-y-6">
          <Card
            title="1. Register Confidential Directive"
            subtitle="Authority signs document SHA-256 and commits DOCUMENT_REGISTERED block"
            icon={Upload}
          >
            <form onSubmit={handleRegister} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                    Directive Identifier
                  </label>
                  <input
                    type="text"
                    value={regDocId}
                    onChange={(e) => setRegDocId(e.target.value)}
                    required
                    placeholder="DOC-2026-XXX"
                    className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c] focus:border-[#b15f2c]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                    Classification
                  </label>
                  <select
                    value={regClassification}
                    onChange={(e) => setRegClassification(e.target.value)}
                    className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs focus:outline-none focus:ring-1 focus:ring-[#b15f2c] focus:border-[#b15f2c]"
                  >
                    <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                    <option value="SECRET">SECRET</option>
                    <option value="TOP_SECRET">TOP SECRET</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                  Directive File (PDF)
                </label>
                <div className="border-2 border-dashed border-[#d8d6d2] hover:border-[#b15f2c] rounded-lg p-5 text-center bg-[#fafaf8] transition-colors">
                  <input
                    type="file"
                    id="doc-file"
                    accept=".pdf"
                    onChange={(e) => setRegFile(e.target.files[0])}
                    className="hidden"
                  />
                  <label htmlFor="doc-file" className="cursor-pointer block">
                    <FileCheck className="w-8 h-8 text-[#b15f2c] mx-auto mb-2 opacity-90" />
                    <span className="text-xs text-[#b15f2c] font-semibold hover:underline font-mono">
                      {regFile ? regFile.name : 'Select or drop naval brief PDF'}
                    </span>
                    <p className="text-[11px] text-[#8d8d8d] mt-1 font-mono">
                      PDF files up to 25MB · Exact SHA-256 computed on ingestion
                    </p>
                  </label>
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                loading={registering}
                disabled={!regFile || registering}
                className="w-full"
                icon={Upload}
              >
                Register & Sign Ledger Block
              </Button>
            </form>
          </Card>

          {/* Broadcast Encryption Console */}
          <Card
            title="2. Broadcast Encrypt for Stations"
            subtitle="Generates single CEK, wraps with ML-KEM-768 for each selected recipient"
            icon={Lock}
          >
            <form onSubmit={handleEncrypt} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                  Target Registered Directive
                </label>
                <select
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                  className="w-full px-3 py-2 bg-[#fafaf8] border border-[#d8d6d2] rounded text-[#0a0a0a] text-xs font-mono focus:outline-none focus:ring-1 focus:ring-[#b15f2c] focus:border-[#b15f2c]"
                >
                  {documents.length === 0 ? (
                    <option value="">No registered directives</option>
                  ) : (
                    documents.map((d) => (
                      <option key={d.document_id} value={d.document_id}>
                        {d.document_id} ({d.classification}) — {d.status}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-[#0a0a0a] mb-1.5 font-mono">
                  Authorized Recipient Stations ({selectedRecipients.length} selected)
                </label>
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {recipients.length === 0 ? (
                    <div className="text-xs text-[#8d8d8d] italic p-3 bg-[#fafaf8] border border-[#e6e5e2] rounded font-mono">
                      No recipients registered in system.
                    </div>
                  ) : (
                    recipients.map((r) => {
                      const isChecked = selectedRecipients.includes(r.recipient_id);
                      return (
                        <div
                          key={r.recipient_id}
                          onClick={() => toggleRecipient(r.recipient_id)}
                          className={`p-2.5 rounded border text-xs cursor-pointer flex items-center justify-between select-none transition-all ${
                            isChecked
                              ? 'bg-[#b15f2c]/08 border-[#b15f2c] text-[#0a0a0a] shadow-xs'
                              : 'bg-white border-[#e6e5e2] text-[#3a3a3a] hover:border-[#d8d6d2]'
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            <input
                              type="checkbox"
                              checked={isChecked}
                              onChange={() => {}}
                              className="rounded border-[#d8d6d2] text-[#b15f2c] focus:ring-[#b15f2c]"
                            />
                            <div>
                              <div className="font-mono font-bold text-[#0a0a0a]">{r.recipient_id}</div>
                              <div className="text-[11px] text-[#8d8d8d]">{r.name}</div>
                            </div>
                          </div>
                          <Badge status={r.status} size="xs" />
                        </div>
                      );
                    })
                  )}
                </div>
              </div>

              <Button
                type="submit"
                variant="primary"
                loading={encrypting}
                disabled={!selectedDocId || selectedRecipients.length === 0 || encrypting}
                className="w-full"
                icon={Lock}
              >
                Execute Broadcast Encryption
              </Button>
            </form>
          </Card>
        </div>

        {/* Documents Registry Table */}
        <div className="lg:col-span-6">
          <Card
            title="Directives Ledger Registry"
            subtitle={`Total registered directives: ${documents.length}`}
            icon={Layers}
            bodyClassName="p-0"
          >
            {documents.length === 0 ? (
              <div className="p-8">
                <EmptyState
                  icon={FileText}
                  title="No Directives Registered"
                  description="Register a PDF naval directive using the registration console to begin broadcast encryption."
                />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#fafaf8] text-[#8d8d8d] font-mono border-b border-[#e6e5e2]">
                    <tr>
                      <th className="px-4 py-3">DIRECTIVE</th>
                      <th className="px-4 py-3">STATUS</th>
                      <th className="px-4 py-3">ORIGINAL SHA-256</th>
                      <th className="px-4 py-3">CREATED</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#e6e5e2] font-mono">
                    {documents.map((d) => (
                      <tr key={d.document_id} className="hover:bg-[#fafaf8] transition-colors">
                        <td className="px-4 py-3 font-semibold text-[#0a0a0a]">
                          <div>{d.document_id}</div>
                          <div className="text-[10px] text-[#8d8d8d]">{d.classification}</div>
                        </td>
                        <td className="px-4 py-3">
                          <Badge status={d.status} size="xs" />
                        </td>
                        <td className="px-4 py-3">
                          <HashDisplay hash={d.original_hash} length={6} />
                        </td>
                        <td className="px-4 py-3 text-[11px] text-[#8d8d8d]">
                          {new Date(d.created_at).toLocaleDateString()}
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
    </div>
  );
}
