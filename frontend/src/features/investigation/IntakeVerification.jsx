import React, { useState } from 'react';
import { Search, Upload, FileCheck, ShieldAlert, FileText } from 'lucide-react';
import { investigationApi } from '../../services/api';
import Button from '../../components/common/Button';
import Card from '../../components/common/Card';
import Alert from '../../components/common/Alert';
import EmptyState from '../../components/common/EmptyState';
import VerdictDisplay from './VerdictDisplay';

export default function IntakeVerification() {
  const [file, setFile] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleInvestigate = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a suspect PDF document to investigate.');
      return;
    }
    setAnalyzing(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const data = await investigationApi.investigate(formData);
      setResult(data);
    } catch (err) {
      setError(err.message || 'Forensic investigation failed.');
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
        <div>
          <h2 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide flex items-center gap-2 font-mono">
            <Search className="w-5 h-5 text-[#b15f2c]" />
            Forensic Leak Intake & Verification
          </h2>
          <p className="text-xs text-[#8d8d8d] font-mono mt-0.5">
            CRYPTOGRAPHIC EVIDENCE INGESTION AND 10-POINT FAIL-CLOSED ATTRIBUTION PIPELINE
          </p>
        </div>
      </div>

      {error && <Alert type="error" title="Intake Error" message={error} onDismiss={() => setError(null)} />}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Upload & Run Analysis Card */}
        <div className="lg:col-span-4 space-y-6">
          <Card
            title="Suspect Document Intake"
            subtitle="Ingest leaked PDF file for forensic marker extraction"
            icon={Upload}
          >
            <form onSubmit={handleInvestigate} className="space-y-4">
              <div className="border-2 border-dashed border-[#d8d6d2] hover:border-[#b15f2c] rounded-lg p-5 text-center bg-[#fafaf8] transition-colors">
                <input
                  type="file"
                  id="leak-file"
                  accept=".pdf"
                  onChange={(e) => {
                    setFile(e.target.files[0]);
                    setResult(null);
                  }}
                  className="hidden"
                />
                <label htmlFor="leak-file" className="cursor-pointer block">
                  <FileCheck className="w-8 h-8 text-[#b15f2c] mx-auto mb-2 opacity-90" />
                  <span className="text-xs text-[#b15f2c] font-semibold hover:underline block truncate px-2 font-mono">
                    {file ? file.name : 'Select or drop suspect PDF'}
                  </span>
                  <p className="text-[11px] text-[#8d8d8d] mt-1 font-mono">
                    Scans ISO 32000-1 text streams for 256-bit opaque markers
                  </p>
                </label>
              </div>

              <Button
                type="submit"
                variant="primary"
                loading={analyzing}
                disabled={!file || analyzing}
                className="w-full"
                icon={Search}
              >
                Execute 10-Point Verification
              </Button>
            </form>

            <div className="mt-4 p-3 bg-[#8b3a2a]/08 border border-[#8b3a2a]/20 rounded font-mono text-[11px] text-[#541a10] space-y-1">
              <div className="text-[#8b3a2a] font-bold flex items-center gap-1.5 font-mono text-[11px]">
                <ShieldAlert className="w-3.5 h-3.5 text-[#8b3a2a]" />
                <span>FAIL-CLOSED POLICY</span>
              </div>
              <p className="leading-relaxed">
                Attribution is reported as VERIFIED only if all 10 checks pass. Any missing record, hash mismatch, or signature invalidity returns NOT_ATTRIBUTABLE with zero named suspects.
              </p>
            </div>
          </Card>
        </div>

        {/* Verdict & Evidence Cards */}
        <div className="lg:col-span-8">
          {analyzing ? (
            <div className="p-16 text-center space-y-3 font-mono bg-white border border-[#e6e5e2] rounded-lg shadow-xs">
              <div className="w-8 h-8 border-2 border-[#b15f2c] border-t-transparent rounded-full animate-spin mx-auto" />
              <div className="text-xs font-bold text-[#0a0a0a] uppercase tracking-wider font-mono">
                Forensic Analysis In Progress
              </div>
              <p className="text-[11px] text-[#8d8d8d] max-w-sm mx-auto leading-relaxed">
                Extracting watermarks, verifying document SHA-256 against ledger, checking ML-DSA-44 signatures, and resolving trust manifest...
              </p>
            </div>
          ) : result ? (
            <VerdictDisplay result={result} />
          ) : (
            <div className="p-12 bg-white border border-[#e6e5e2] rounded-lg shadow-xs">
              <EmptyState
                icon={FileText}
                title="Awaiting Evidence Intake"
                description="Upload a suspect PDF document to initiate 10-point forensic attribution against the append-only ledger and WESEE trust anchor."
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
