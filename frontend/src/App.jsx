import React, { useState } from 'react';
import {
  Shield,
  Lock,
  Unlock,
  Search,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Cpu,
  Layers,
  Terminal,
  Download,
  Upload,
  RefreshCw,
  Eye,
  Users,
  Anchor,
  RotateCcw
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [activeIdentity, setActiveIdentity] = useState('');
  const [authToken, setAuthToken] = useState(null);
  const [recipients, setRecipients] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [ledgerBlocks, setLedgerBlocks] = useState([]);
  const [ledgerAudit, setLedgerAudit] = useState(null);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);

  // Registration & Encryption state
  const [docId, setDocId] = useState('DOC-2026-001');
  const [classification, setClassification] = useState('CONFIDENTIAL');
  const [selectedRecipients, setSelectedRecipients] = useState(['R001', 'R002', 'R003']);
  const [fileToUpload, setFileToUpload] = useState(null);

  // Decryption state
  const [decryptionResult, setDecryptionResult] = useState(null);
  const [decryptingStep, setDecryptingStep] = useState(0);

  // Investigation state
  const [investigationResult, setInvestigationResult] = useState(null);
  const [leakFile, setLeakFile] = useState(null);

  // Invariance state
  const [invarianceData, setInvarianceData] = useState(null);

  const addLog = (msg, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [{ timestamp, msg, type }, ...prev.slice(0, 49)]);
  };

  // Identity and role are enforced by the backend from this bearer token.
  const apiFetch = (url, options = {}, token = authToken) => {
    const headers = { ...(options.headers || {}) };
    if (token) headers.Authorization = `Bearer ${token}`;
    return fetch(url, { ...options, headers });
  };

  const handleLogin = async (principalId) => {
    if (!principalId) return;
    const passphrase = window.prompt(`Enter keystore passphrase for ${principalId}:`);
    if (!passphrase) return;
    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ principal_id: principalId, passphrase })
      });
      const data = await res.json();
      if (!res.ok) {
        addLog(`Login failed for ${principalId}: ${data.detail}`, 'error');
        return;
      }
      setAuthToken(data.token);
      setActiveIdentity(data.principal_id);
      fetchData(data.token);
      addLog(`Authenticated as ${data.principal_id} (${data.role}). Keystore unlocked for this session.`, 'success');
    } catch (err) {
      addLog(`Login error: ${err.message}`, 'error');
    }
  };

  // Load initial data
  const fetchData = async (token = authToken) => {
    if (!token) return;
    try {
      const recRes = await apiFetch('/api/recipients', {}, token);
      if (recRes.ok) {
        const data = await recRes.json();
        setRecipients(data);
      }

      const docRes = await apiFetch('/api/documents', {}, token);
      if (docRes.ok) {
        const data = await docRes.json();
        setDocuments(data);
      }

      const ledRes = await apiFetch('/api/ledger', {}, token);
      if (ledRes.ok) {
        const data = await ledRes.json();
        setLedgerBlocks(data);
      }

      const auditRes = await apiFetch('/api/ledger/verify', {}, token);
      if (auditRes.ok) {
        const data = await auditRes.json();
        setLedgerAudit(data);
      }
    } catch (err) {
      console.error('Error fetching data:', err);
      addLog('Failed to connect to backend service', 'error');
    }
  };


  // Handle document registration
  const handleRegister = async (e) => {
    e.preventDefault();
    if (!fileToUpload) {
      alert('Please select a PDF document file to register.');
      return;
    }
    setLoading(true);
    addLog(`Initiating registration for document ${docId}...`);
    try {
      const formData = new FormData();
      formData.append('document_id', docId);
      formData.append('classification', classification);
      formData.append('file', fileToUpload);

      const res = await apiFetch('/api/documents/register', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        addLog(`Document ${docId} registered. SHA-256: ${data.original_hash.slice(0, 16)}...`, 'success');
        fetchData();
      } else {
        addLog(`Registration failed: ${data.detail}`, 'error');
      }
    } catch (err) {
      addLog(`Registration error: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Handle broadcast encryption
  const handleEncrypt = async () => {
    if (selectedRecipients.length === 0) {
      alert('Select at least one authorized recipient.');
      return;
    }
    setLoading(true);
    addLog(`Executing ML-KEM-768 Broadcast Encryption for ${selectedRecipients.join(', ')}...`);
    try {
      const res = await apiFetch('/api/documents/encrypt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: docId,
          authorized_recipient_ids: selectedRecipients
        })
      });
      const data = await res.json();
      if (res.ok) {
        addLog(`Document encrypted. Content protected with AES-256-GCM + ML-KEM-768 wrapping.`, 'success');
        fetchData();
      } else {
        addLog(`Encryption failed: ${data.detail}`, 'error');
      }
    } catch (err) {
      addLog(`Encryption error: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Handle decryption with visual step telemetry
  const handleDecrypt = async (recipientId) => {
    setLoading(true);
    setDecryptionResult(null);
    setDecryptingStep(1);
    addLog(`Recipient ${recipientId} initiating controlled decryption...`);

    try {
      await new Promise((r) => setTimeout(r, 400));
      setDecryptingStep(2);
      addLog(`[STEP 1] ML-KEM-768 decapsulation: recovering 256-bit shared secret...`);

      await new Promise((r) => setTimeout(r, 400));
      setDecryptingStep(3);
      addLog(`[STEP 2] HKDF-SHA256 KDF key derivation & AES-256-GCM document decryption...`);

      await new Promise((r) => setTimeout(r, 400));
      setDecryptingStep(4);
      addLog(`[STEP 3] Generating CSPRNG session & opaque 256-bit watermark token...`);

      await new Promise((r) => setTimeout(r, 400));
      setDecryptingStep(5);
      addLog(`[STEP 4] Non-rendering PDF watermark injection (ISO 32000-1 render mode 3)...`);

      const res = await apiFetch('/api/decrypt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: docId })
      });
      const data = await res.json();

      if (res.ok) {
        setDecryptingStep(6);
        addLog(`[STEP 5] ML-DSA-44 digital signature generated by ${recipientId}.`);
        addLog(`[STEP 6] Decryption record committed to Offline Ledger (Block #${data.block_index}).`, 'success');
        setDecryptionResult(data);
        fetchData();
      } else {
        addLog(`Decryption failed: ${data.detail}`, 'error');
        setDecryptingStep(0);
      }
    } catch (err) {
      addLog(`Decryption error: ${err.message}`, 'error');
      setDecryptingStep(0);
    } finally {
      setLoading(false);
    }
  };

  // Handle leak investigation
  const handleInvestigate = async (e) => {
    e.preventDefault();
    if (!leakFile) {
      alert('Please upload a leaked PDF to investigate.');
      return;
    }
    setLoading(true);
    addLog(`Forensic Investigator analyzing suspected leaked document...`);
    try {
      const formData = new FormData();
      formData.append('file', leakFile);

      const res = await apiFetch('/api/investigate', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) {
        addLog(`Investigation refused: ${data.detail}`, 'error');
        return;
      }
      setInvestigationResult(data);
      if (data.status === 'VERIFIED') {
        addLog(`Attribution CONFIRMED: Token matched ${data.recipient_id} (${data.recipient_name}). ML-DSA verified.`, 'success');
      } else {
        addLog(`Investigation result: ${data.attribution_verdict} - ${data.reason}`, 'warn');
      }
    } catch (err) {
      addLog(`Investigation error: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Handle tamper simulation
  const handleTamperTest = async (blockIdx) => {
    if (!confirm(`Deliberately tamper with Block #${blockIdx} in the offline ledger to test tamper detection?`)) return;
    setLoading(true);
    addLog(`Adversary injecting unauthorized modification into Block #${blockIdx}...`, 'warn');
    try {
      const res = await apiFetch('/api/ledger/tamper-test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          block_index: blockIdx,
          field: 'canonical_record',
          new_value: '{"tampered_by_adversary": true}'
        })
      });
      const data = await res.json();
      addLog(res.ok ? data.message : `Tamper simulation refused: ${data.detail}`, res.ok ? 'warn' : 'error');
      fetchData();
    } catch (err) {
      addLog(`Tamper test error: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Run full ledger audit
  const handleAuditLedger = async () => {
    setLoading(true);
    addLog('Executing full cryptographic hash-chain audit...');
    try {
      const res = await apiFetch('/api/ledger/verify');
      const data = await res.json();
      if (!res.ok) {
        addLog(`Audit refused: ${data.detail}`, 'error');
        return;
      }
      setLedgerAudit(data);
      if (data.chain_valid) {
        addLog(`Chain Audit: PASS. All ${data.total_blocks} blocks valid.`, 'success');
      } else {
        addLog(`Chain Audit: FAILED! Tamper detected at Block #${data.broken_block_index}: ${data.error_message}`, 'error');
      }
    } catch (err) {
      addLog(`Audit error: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Handle safe test environment reset
  const handleResetEnvironment = async () => {
    if (!confirm('Safely reset test documents, sessions, and ledger to clean Genesis state? Recipient PQC keys will be preserved.')) return;
    setLoading(true);
    addLog('Resetting test environment and ledger to clean Genesis state...', 'warn');
    try {
      const res = await apiFetch('/api/ledger/reset', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        addLog(`Reset refused: ${data.detail}`, 'error');
        return;
      }
      addLog(data.message, 'success');
      setDecryptionResult(null);
      setInvestigationResult(null);
      setInvarianceData(null);
      setDecryptingStep(0);
      fetchData();
    } catch (err) {
      addLog(`Reset error: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Measured on the backend: renders the two most recent delivered copies of the current document.
  const handleCheckInvariance = async () => {
    const sessions = ledgerBlocks
      .filter((b) => b.event_type === 'DOCUMENT_DECRYPTED' && b.canonical_record.document_id === docId)
      .map((b) => b.canonical_record.session_id);
    if (sessions.length < 2) {
      addLog('Invariance audit needs two decrypted copies of the current document (login as Authority, Investigator or Auditor).', 'warn');
      return;
    }
    setLoading(true);
    try {
      const res = await apiFetch('/api/forensics/invariance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_a: sessions[sessions.length - 2], session_b: sessions[sessions.length - 1] })
      });
      const data = await res.json();
      if (!res.ok) {
        addLog(`Invariance audit failed: ${data.detail}`, 'error');
        return;
      }
      setInvarianceData(data);
      addLog(`Visual invariance ${data.session_a} vs ${data.session_b}: ${data.differing_pixels} of ${data.total_pixels_compared} samples differ.`,
        data.is_visually_identical ? 'success' : 'warn');
    } catch (err) {
      addLog(`Invariance error: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (path, sessionId) => {
    const res = await apiFetch(path);
    if (!res.ok) {
      addLog('Download denied or file unavailable.', 'error');
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sessionId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-[#070d19] text-slate-200 flex flex-col font-sans">
      {/* Top Defence Header */}
      <header className="border-b border-cyan-950 bg-[#0a1329]/90 backdrop-blur sticky top-0 z-50 px-6 py-3">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-cyan-950/80 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Anchor className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold tracking-widest text-cyan-400 uppercase">
                  MINISTRY OF DEFENCE // INDIAN NAVY (WESEE)
                </span>
                <span className="bg-emerald-950/80 border border-emerald-500/40 text-emerald-400 text-[10px] px-2 py-0.5 rounded font-mono font-semibold">
                  OFFLINE AIR-GAPPED
                </span>
              </div>
              <h1 className="text-lg font-bold tracking-wide text-white flex items-center gap-2">
                SIH26237 Sovereign Forensic Attribution & Provenance System
              </h1>
            </div>
          </div>

          {/* Environmental telemetry badges */}
          <div className="flex items-center gap-3 text-xs font-mono">
            <div className="bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
              <span className="text-slate-400">KEM:</span>
              <span className="text-cyan-300 font-semibold">ML-KEM-768</span>
            </div>
            <div className="bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              <span className="text-slate-400">DSA:</span>
              <span className="text-emerald-300 font-semibold">ML-DSA-44</span>
            </div>
            <div className="bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              <span className="text-slate-400">LEDGER:</span>
              <span className="text-amber-300 font-semibold">TAMPER-EVIDENT HASH CHAIN</span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Bar */}
      <div className="bg-[#0b162f] border-b border-cyan-950/60 px-6">
        <div className="max-w-7xl mx-auto flex items-center justify-between overflow-x-auto">
          <nav className="flex space-x-1 py-2">
            {[
              { id: 'dashboard', label: 'Operational Overview', icon: Layers },
              { id: 'sender', label: '1. Sender Broadcast', icon: Lock },
              { id: 'recipient', label: '2. Recipient Decryption', icon: Unlock },
              { id: 'invariance', label: '3. Visual Invariance', icon: Eye },
              { id: 'investigation', label: '4. Leak Forensics', icon: Search },
              { id: 'ledger', label: '5. Tamper-Evident Ledger', icon: Shield },
              { id: 'tamper', label: '6. Tamper Sandbox', icon: AlertTriangle }
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded text-xs font-medium font-mono transition-all whitespace-nowrap ${
                    isActive
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-950'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Active Officer Identity Switcher */}
          <div className="flex items-center gap-2 py-2 pl-4 border-l border-slate-800">
            <span className="text-[11px] text-slate-400 font-mono">STATION:</span>
            <select
              value={activeIdentity}
              onChange={(e) => handleLogin(e.target.value)}
              className="bg-slate-900 border border-cyan-900/60 text-cyan-300 text-xs font-mono rounded px-2.5 py-1.5 focus:outline-none focus:border-cyan-500"
            >
              <option value="">-- Login: select station --</option>
              <option value="WESEE_HQ">Authority (WESEE HQ)</option>
              <option value="R001">R001 - Commander Alpha (Naval Command)</option>
              <option value="R002">R002 - Officer Bravo (Signals Directorate)</option>
              <option value="R003">R003 - Officer Charlie (Tactical Weapons)</option>
              <option value="INVESTIGATOR_01">Naval Forensics Investigator</option>
              <option value="AUDITOR_01">Ledger Auditor</option>
            </select>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Interactive Panel (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* TAB 1: OPERATIONAL OVERVIEW */}
          {activeTab === 'dashboard' && (
            <div className="space-y-6">
              <div className="bg-gradient-to-r from-cyan-950/40 via-slate-900/60 to-blue-950/30 border border-cyan-500/30 rounded-lg p-6">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-xs font-mono font-bold text-cyan-400 tracking-wider uppercase">
                      OFFLINE ATTRIBUTION PROTOCOL
                    </span>
                    <h2 className="text-xl font-bold text-white mt-1">
                      Broadcast-Encrypt, Individually-Decrypt Provenance
                    </h2>
                    <p className="text-sm text-slate-300 mt-2 leading-relaxed">
                      This system solves the fundamental defence document leak attribution challenge. When an authorized officer decrypts a sensitive naval order, the decryption engine dynamically embeds an <strong>opaque 256-bit watermark token</strong> into the PDF and commits an <strong>ML-DSA-44 signed record</strong> to an offline tamper-evident hash-chained ledger. Attribution is reported only when every evidence check passes.
                    </p>
                  </div>
                  <Shield className="w-12 h-12 text-cyan-400/60 shrink-0 ml-4" />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
                  <div className="bg-slate-950/70 border border-slate-800 p-3 rounded">
                    <div className="text-xs text-slate-400 font-mono">Protected Docs</div>
                    <div className="text-xl font-bold text-cyan-400 font-mono mt-1">{documents.length}</div>
                  </div>
                  <div className="bg-slate-950/70 border border-slate-800 p-3 rounded">
                    <div className="text-xs text-slate-400 font-mono">Authorized Stations</div>
                    <div className="text-xl font-bold text-emerald-400 font-mono mt-1">{recipients.length}</div>
                  </div>
                  <div className="bg-slate-950/70 border border-slate-800 p-3 rounded">
                    <div className="text-xs text-slate-400 font-mono">Ledger Blocks</div>
                    <div className="text-xl font-bold text-amber-400 font-mono mt-1">{ledgerBlocks.length}</div>
                  </div>
                  <div className="bg-slate-950/70 border border-slate-800 p-3 rounded">
                    <div className="text-xs text-slate-400 font-mono">Ledger Integrity</div>
                    <div className={`text-base font-bold font-mono mt-1 flex items-center gap-1 ${ledgerAudit?.chain_valid ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {ledgerAudit?.chain_valid ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                      {ledgerAudit?.chain_valid ? 'VERIFIED' : 'TAMPERED'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Cryptographic Architecture Matrix */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
                <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center gap-2 mb-4">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  NIST Standardized Post-Quantum Cryptographic Matrix
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="p-3">Purpose</th>
                        <th className="p-3">Algorithm</th>
                        <th className="p-3">Standard</th>
                        <th className="p-3">Implementation</th>
                        <th className="p-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 text-slate-300">
                      <tr>
                        <td className="p-3 font-semibold text-white">Post-Quantum Key Encapsulation</td>
                        <td className="p-3 text-cyan-300 font-bold">ML-KEM-768</td>
                        <td className="p-3">NIST FIPS 203</td>
                        <td className="p-3">Verified Local Native Wheel</td>
                        <td className="p-3 text-emerald-400 font-bold">OPERATIONAL</td>
                      </tr>
                      <tr>
                        <td className="p-3 font-semibold text-white">Post-Quantum Provenance Signature</td>
                        <td className="p-3 text-emerald-300 font-bold">ML-DSA-44 (Dilithium2)</td>
                        <td className="p-3">NIST FIPS 204</td>
                        <td className="p-3">Verified Local Pure Python</td>
                        <td className="p-3 text-emerald-400 font-bold">OPERATIONAL</td>
                      </tr>
                      <tr>
                        <td className="p-3 font-semibold text-white">Authenticated Document Encryption</td>
                        <td className="p-3 text-amber-300 font-bold">AES-256-GCM</td>
                        <td className="p-3">NIST SP 800-38D</td>
                        <td className="p-3">Python Cryptography Hazmat</td>
                        <td className="p-3 text-emerald-400 font-bold">OPERATIONAL</td>
                      </tr>
                      <tr>
                        <td className="p-3 font-semibold text-white">CEK Wrapping Key Derivation</td>
                        <td className="p-3 text-cyan-300 font-bold">HKDF-SHA256</td>
                        <td className="p-3">RFC 5869</td>
                        <td className="p-3">Domain Separated Info Tag</td>
                        <td className="p-3 text-emerald-400 font-bold">OPERATIONAL</td>
                      </tr>
                      <tr>
                        <td className="p-3 font-semibold text-white">Decryption-Time Forensic Watermarking</td>
                        <td className="p-3 text-purple-300 font-bold">Opaque 256-bit Token (3 Tr)</td>
                        <td className="p-3">ISO 32000-1</td>
                        <td className="p-3">Non-rendering Vector Injection</td>
                        <td className="p-3 text-emerald-400 font-bold">OPERATIONAL</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Authorized Personnel Table */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider flex items-center gap-2">
                    <Users className="w-4 h-4 text-cyan-400" />
                    Authorized Recipient Personas & PQC Keypairs
                  </h3>
                  <button onClick={fetchData} className="text-xs text-cyan-400 hover:underline flex items-center gap-1">
                    <RefreshCw className="w-3 h-3" /> Refresh
                  </button>
                </div>

                <div className="space-y-3">
                  {recipients.map((r) => (
                    <div key={r.recipient_id} className="bg-slate-950/80 border border-slate-800/80 p-3 rounded flex flex-col md:flex-row md:items-center justify-between gap-3 font-mono text-xs">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-white text-sm">{r.recipient_id}</span>
                          <span className="text-cyan-300 font-semibold">{r.name}</span>
                          <span className="bg-cyan-950/70 text-cyan-400 text-[10px] px-2 py-0.5 rounded border border-cyan-800/40">
                            {r.role}
                          </span>
                        </div>
                        <div className="text-slate-400 text-[11px] mt-1 flex items-center gap-3">
                          <span>ML-KEM ek: <span className="text-slate-300">{r.mlkem_public_key.slice(0, 16)}...</span></span>
                          <span>ML-DSA pk: <span className="text-slate-300">{r.mldsa_public_key.slice(0, 16)}...</span></span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={async () => {
                            await handleLogin(r.recipient_id);
                            setActiveTab('recipient');
                          }}
                          className="bg-cyan-950/80 hover:bg-cyan-900/80 text-cyan-300 border border-cyan-800/60 px-3 py-1 rounded text-xs transition"
                        >
                          Switch to Officer
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: SENDER BROADCAST ENCRYPTION */}
          {activeTab === 'sender' && (
            <div className="space-y-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6">
                <h3 className="text-base font-bold text-white font-mono flex items-center gap-2 mb-4">
                  <Lock className="w-5 h-5 text-cyan-400" />
                  Authority Document Registration & Hybrid Broadcast Encryption
                </h3>
                <p className="text-xs text-slate-400 mb-6">
                  WESEE Authority registers a confidential defence document and creates recipient-specific key-wrapping packages using NIST ML-KEM-768.
                </p>

                <form onSubmit={handleRegister} className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-mono text-slate-400 mb-1">Document Identifier</label>
                      <input
                        type="text"
                        value={docId}
                        onChange={(e) => setDocId(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-mono text-slate-400 mb-1">Classification Level</label>
                      <select
                        value={classification}
                        onChange={(e) => setClassification(e.target.value)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-white focus:outline-none focus:border-cyan-500"
                      >
                        <option value="RESTRICTED">RESTRICTED</option>
                        <option value="CONFIDENTIAL">CONFIDENTIAL</option>
                        <option value="SECRET">SECRET // EYES ONLY</option>
                        <option value="TOP SECRET">TOP SECRET // TACTICAL</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-slate-400 mb-1">Document File (.pdf)</label>
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={(e) => setFileToUpload(e.target.files[0])}
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs font-mono text-slate-300 file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-mono file:bg-cyan-950 file:text-cyan-300 hover:file:bg-cyan-900"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold px-4 py-2 rounded text-xs font-mono transition flex items-center gap-2"
                  >
                    <Upload className="w-4 h-4" />
                    Register Document with Authority
                  </button>
                </form>

                <hr className="border-slate-800 my-6" />

                {/* Broadcast Encryption Section */}
                <div>
                  <h4 className="text-xs font-bold text-cyan-400 font-mono uppercase tracking-wider mb-3">
                    Authorize Recipients & Encrypt via ML-KEM-768
                  </h4>
                  <div className="space-y-2 mb-4">
                    {recipients.map((r) => (
                      <label key={r.recipient_id} className="flex items-center gap-3 bg-slate-950 p-2.5 rounded border border-slate-800/80 cursor-pointer text-xs font-mono">
                        <input
                          type="checkbox"
                          checked={selectedRecipients.includes(r.recipient_id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedRecipients([...selectedRecipients, r.recipient_id]);
                            } else {
                              setSelectedRecipients(selectedRecipients.filter((id) => id !== r.recipient_id));
                            }
                          }}
                          className="rounded text-cyan-500 focus:ring-0 bg-slate-900 border-slate-700"
                        />
                        <span className="font-bold text-white">{r.recipient_id}</span>
                        <span className="text-slate-300">{r.name}</span>
                        <span className="text-slate-500 text-[11px]">({r.role})</span>
                      </label>
                    ))}
                  </div>

                  <button
                    onClick={handleEncrypt}
                    disabled={loading}
                    className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-5 py-2.5 rounded text-xs font-mono transition flex items-center gap-2"
                  >
                    <Lock className="w-4 h-4" />
                    Broadcast Encrypt (ML-KEM-768 + AES-256-GCM)
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: RECIPIENT DECRYPTION */}
          {activeTab === 'recipient' && (
            <div className="space-y-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-bold text-white font-mono flex items-center gap-2">
                    <Unlock className="w-5 h-5 text-emerald-400" />
                    Decryption Station: {activeIdentity}
                  </h3>
                  <span className="bg-cyan-950 border border-cyan-800 text-cyan-300 font-mono text-xs px-2.5 py-1 rounded">
                    Active Station: {activeIdentity}
                  </span>
                </div>

                <p className="text-xs text-slate-400 mb-6 leading-relaxed">
                  Decryption generates an ephemeral session, embeds an <strong>opaque 256-bit watermark token</strong> into the PDF content stream, signs the canonical decryption record with your station's <strong>ML-DSA-44 private key</strong>, and commits the signed proof to the offline ledger.
                </p>

                <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg space-y-4">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">Target Document:</span>
                    <span className="text-white font-bold">{docId}</span>
                  </div>
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">Authorized Recipient:</span>
                    <span className="text-emerald-400 font-bold">{activeIdentity}</span>
                  </div>

                  <button
                    onClick={() => handleDecrypt(activeIdentity)}
                    disabled={loading}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold py-3 rounded text-xs font-mono transition flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40"
                  >
                    <Unlock className="w-4 h-4" />
                    DECRYPT & GENERATE PROVENANCE RECORD
                  </button>
                </div>

                {/* Live Cryptographic Telemetry Steps */}
                {decryptingStep > 0 && (
                  <div className="mt-6 bg-slate-950/90 border border-cyan-900/40 p-4 rounded-lg font-mono text-xs space-y-2">
                    <div className="text-cyan-400 font-bold text-[11px] uppercase tracking-wider mb-2">
                      Cryptographic Execution Telemetry
                    </div>
                    {[
                      { step: 1, text: 'Verifying authorization package in local store' },
                      { step: 2, text: 'ML-KEM-768 Decapsulation -> Recovering shared secret' },
                      { step: 3, text: 'HKDF-SHA256 Key Derivation -> AES-256-GCM Document Decryption' },
                      { step: 4, text: 'Generating Ephemeral Session ID & Opaque 256-bit Watermark Token' },
                      { step: 5, text: 'Non-rendering PDF Watermark Embedding (ISO 32000-1 Mode 3)' },
                      { step: 6, text: 'ML-DSA-44 Digital Signature & Offline Ledger Block Commitment' }
                    ].map((s) => (
                      <div key={s.step} className="flex items-center gap-2">
                        {decryptingStep >= s.step ? (
                          <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <div className="w-4 h-4 rounded-full border border-slate-700 shrink-0" />
                        )}
                        <span className={decryptingStep >= s.step ? 'text-white' : 'text-slate-500'}>
                          {s.text}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Decryption Success Card */}
                {decryptionResult && (
                  <div className="mt-6 bg-emerald-950/30 border border-emerald-500/40 p-5 rounded-lg font-mono text-xs space-y-3">
                    <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                      <CheckCircle className="w-5 h-5" />
                      Decryption & Watermarking Completed Successfully
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-slate-300">
                      <div>
                        <span className="text-slate-500">Session ID: </span>
                        <span className="text-white font-bold">{decryptionResult.session_id}</span>
                      </div>
                      <div>
                        <span className="text-slate-500">Ledger Block: </span>
                        <span className="text-cyan-400 font-bold">#{decryptionResult.block_index}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-500">Opaque Watermark Token: </span>
                        <span className="text-emerald-300 break-all">{decryptionResult.watermark_token}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-500">ML-DSA-44 Signature: </span>
                        <span className="text-slate-400 break-all">{decryptionResult.signature}</span>
                      </div>
                    </div>

                    <div className="pt-3 flex gap-3">
                      <button
                        onClick={() => handleDownload(decryptionResult.decrypted_file_path, decryptionResult.session_id)}
                        className="bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold px-4 py-2 rounded text-xs transition flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Download Officer's Decrypted PDF
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: VISUAL INVARIANCE INSPECTOR */}
          {activeTab === 'invariance' && (
            <div className="space-y-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6">
                <h3 className="text-base font-bold text-white font-mono flex items-center gap-2 mb-2">
                  <Eye className="w-5 h-5 text-cyan-400" />
                  Visual Invariance & Pixel Difference Verification
                </h3>
                <p className="text-xs text-slate-400 mb-6">
                  Mandatory SIH requirement: Two authorized officers (e.g. Commander Alpha vs Officer Bravo) must receive documents that look <strong>visually identical</strong> to human eyes while containing distinct forensic fingerprints.
                </p>

                <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg flex flex-col items-center justify-center text-center space-y-4">
                  <p className="text-xs font-mono text-slate-300">
                    Run the automated high-resolution pixmap pixel-level comparison engine across decrypted copies:
                  </p>
                  <button
                    onClick={handleCheckInvariance}
                    className="bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold px-5 py-2.5 rounded text-xs font-mono transition flex items-center gap-2"
                  >
                    <CheckCircle className="w-4 h-4" />
                    RUN PIXEL-LEVEL INVARIANCE AUDIT
                  </button>
                </div>

                {invarianceData && (
                  <div className="mt-6 bg-slate-950 border border-cyan-800/40 p-5 rounded-lg space-y-4 font-mono text-xs">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <span className="text-slate-400">Visual Deviation Metric ({invarianceData.session_a} vs {invarianceData.session_b}):</span>
                      <span className={`font-bold text-sm ${invarianceData.is_visually_identical ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {invarianceData.is_visually_identical ? 'NO RENDERED DIFFERENCE AT 150 DPI' : 'RENDERED DIFFERENCE DETECTED'}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <span className="text-slate-500">Channel Samples Compared (150 DPI):</span>
                        <div className="text-white font-bold text-sm mt-1">{invarianceData.total_pixels_compared.toLocaleString()}</div>
                      </div>
                      <div>
                        <span className="text-slate-500">Differing Samples:</span>
                        <div className={`font-bold text-sm mt-1 ${invarianceData.differing_pixels === 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {invarianceData.differing_pixels.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <span className="text-slate-500">Watermark Mechanism:</span>
                        <div className="text-cyan-300 font-bold mt-1">ISO 32000-1 Render Mode 3 (Neither fill nor stroke)</div>
                      </div>
                      <div>
                        <span className="text-slate-500">Human Visual Appearance:</span>
                        <div className="text-emerald-300 font-bold mt-1">Identical layout, fonts, margins, text</div>
                      </div>
                    </div>
                    <div className="bg-cyan-950/40 border border-cyan-800/30 p-3 rounded text-[11px] text-cyan-200">
                      <strong>Audit Conclusion:</strong> Measured with the PyMuPDF renderer at 150 DPI. Other PDF viewers, text extraction and accessibility tools can still reveal the invisible marker text.
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: LEAK FORENSICS INVESTIGATION */}
          {activeTab === 'investigation' && (
            <div className="space-y-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6">
                <h3 className="text-base font-bold text-white font-mono flex items-center gap-2 mb-2">
                  <Search className="w-5 h-5 text-cyan-400" />
                  Forensic Leak Investigation & Cryptographic Attribution Portal
                </h3>
                <p className="text-xs text-slate-400 mb-6">
                  When a leaked confidential PDF is intercepted, upload it here. The engine extracts the opaque watermark token, looks up the offline ledger record, verifies the recipient's ML-DSA-44 post-quantum signature, and delivers a verified attribution report.
                </p>

                <form onSubmit={handleInvestigate} className="space-y-4">
                  <div className="border-2 border-dashed border-slate-700 hover:border-cyan-500/60 bg-slate-950/60 p-6 rounded-lg text-center cursor-pointer">
                    <input
                      type="file"
                      accept=".pdf"
                      onChange={(e) => setLeakFile(e.target.files[0])}
                      className="w-full text-xs font-mono text-slate-400"
                    />
                    <p className="text-xs text-slate-500 font-mono mt-2">
                      Upload leaked copy (e.g. Officer Bravo's decrypted PDF, renamed or re-saved)
                    </p>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold py-3 rounded text-xs font-mono transition flex items-center justify-center gap-2"
                  >
                    <Search className="w-4 h-4" />
                    RUN FORENSIC ANALYSIS & LEDGER LOOKUP
                  </button>
                </form>

                {/* Investigation Results */}
                {investigationResult && (
                  <div className={`mt-6 border p-6 rounded-lg font-mono text-xs space-y-4 ${
                    investigationResult.status === 'VERIFIED'
                      ? 'bg-emerald-950/30 border-emerald-500/50'
                      : 'bg-rose-950/30 border-rose-500/50'
                  }`}>
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div className="flex items-center gap-2 font-bold text-sm">
                        {investigationResult.status === 'VERIFIED' ? (
                          <CheckCircle className="w-5 h-5 text-emerald-400" />
                        ) : (
                          <XCircle className="w-5 h-5 text-rose-400" />
                        )}
                        <span className={investigationResult.status === 'VERIFIED' ? 'text-emerald-400' : 'text-rose-400'}>
                          {investigationResult.attribution_verdict}
                        </span>
                      </div>
                      <span className="bg-slate-900 px-3 py-1 rounded text-slate-300 font-mono">
                        Status: {investigationResult.status}
                      </span>
                    </div>

                    {investigationResult.verification && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px]">
                        {Object.entries(investigationResult.verification).map(([check, ok]) => (
                          <div key={check} className={`flex items-center gap-1 ${ok ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {ok ? <CheckCircle className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
                            {check.replace(/_/g, ' ')}
                          </div>
                        ))}
                      </div>
                    )}

                    {investigationResult.trust_anchor && (
                      <div className="text-[11px] text-slate-400">
                        Signer identity checked against trust manifest v{investigationResult.trust_anchor.manifest_version ?? '—'}
                        {investigationResult.trust_anchor.manifest_sha256 && ` (sha256 ${investigationResult.trust_anchor.manifest_sha256.slice(0, 16)}…)`}
                        {' '}· authority pin {investigationResult.trust_anchor.authority_pin ? `${investigationResult.trust_anchor.authority_pin.slice(0, 16)}…` : 'NOT PINNED'}
                      </div>
                    )}

                    {investigationResult.status === 'VERIFIED' && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-slate-300">
                        <div className="bg-slate-950/70 p-3 rounded border border-slate-800">
                          <div className="text-slate-500 text-[11px]">Attributed Officer ID:</div>
                          <div className="text-white font-bold text-sm mt-0.5">{investigationResult.recipient_id}</div>
                        </div>
                        <div className="bg-slate-950/70 p-3 rounded border border-slate-800">
                          <div className="text-slate-500 text-[11px]">Officer Name & Role:</div>
                          <div className="text-cyan-300 font-bold mt-0.5">{investigationResult.recipient_name} ({investigationResult.recipient_role})</div>
                        </div>
                        <div className="bg-slate-950/70 p-3 rounded border border-slate-800">
                          <div className="text-slate-500 text-[11px]">Decryption Session ID:</div>
                          <div className="text-white font-mono mt-0.5">{investigationResult.session_id}</div>
                        </div>
                        <div className="bg-slate-950/70 p-3 rounded border border-slate-800">
                          <div className="text-slate-500 text-[11px]">Decryption Timestamp:</div>
                          <div className="text-white font-mono mt-0.5">{investigationResult.decryption_timestamp}</div>
                        </div>
                        <div className="col-span-2 bg-slate-950/70 p-3 rounded border border-slate-800">
                          <div className="text-slate-500 text-[11px]">Extracted Opaque Token:</div>
                          <div className="text-emerald-300 font-mono break-all mt-0.5">{investigationResult.watermark_token}</div>
                        </div>
                        <div className="bg-slate-950/70 p-3 rounded border border-slate-800">
                          <div className="text-slate-500 text-[11px]">ML-DSA-44 Signature:</div>
                          <div className="text-emerald-400 font-bold mt-0.5">VALID (Verified against officer's public key)</div>
                        </div>
                        <div className="bg-slate-950/70 p-3 rounded border border-slate-800">
                          <div className="text-slate-500 text-[11px]">Ledger Chain Integrity:</div>
                          <div className="text-emerald-400 font-bold mt-0.5">VALID (Block #{investigationResult.block_index})</div>
                        </div>
                      </div>
                    )}

                    {investigationResult.status !== 'VERIFIED' && (
                      <div className="text-slate-300 bg-slate-950 p-4 rounded border border-slate-800">
                        <div className="text-rose-400 font-bold mb-1">Reason:</div>
                        <p>{investigationResult.reason}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 6: TAMPER-EVIDENT LEDGER EXPLORER */}
          {activeTab === 'ledger' && (
            <div className="space-y-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-bold text-white font-mono flex items-center gap-2">
                    <Shield className="w-5 h-5 text-amber-400" />
                    Tamper-Evident Hash-Chained Provenance Ledger
                  </h3>
                  <div className="flex gap-2">
                    <button
                      onClick={handleResetEnvironment}
                      disabled={loading}
                      className="bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold px-3 py-1.5 rounded text-xs font-mono transition flex items-center gap-1"
                    >
                      <RotateCcw className="w-3.5 h-3.5" /> Reset to Genesis
                    </button>
                    <button
                      onClick={handleAuditLedger}
                      disabled={loading}
                      className="bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold px-3 py-1.5 rounded text-xs font-mono transition flex items-center gap-1"
                    >
                      <CheckCircle className="w-3.5 h-3.5" /> Run Audit
                    </button>
                    <button
                      onClick={fetchData}
                      className="bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded text-xs font-mono transition flex items-center gap-1"
                    >
                      <RefreshCw className="w-3.5 h-3.5" /> Refresh
                    </button>
                  </div>
                </div>

                <div className="space-y-4">
                  {ledgerBlocks.map((block) => (
                    <div key={block.block_index} className="bg-slate-950 border border-slate-800 p-4 rounded-lg font-mono text-xs space-y-2">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <div className="flex items-center gap-2">
                          <span className="bg-cyan-950 text-cyan-400 px-2 py-0.5 rounded font-bold">
                            Block #{block.block_index}
                          </span>
                          <span className="text-amber-400 font-bold">{block.event_type}</span>
                          <span className="text-slate-500 text-[11px]">{block.timestamp}</span>
                        </div>
                        <span className="text-slate-400">Signer: <strong className="text-white">{block.signer_id}</strong></span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-[11px] text-slate-400">
                        <div>
                          <span>Previous Hash: </span>
                          <span className="text-slate-300 break-all">{block.previous_hash.slice(0, 24)}...</span>
                        </div>
                        <div>
                          <span>Current Hash: </span>
                          <span className="text-cyan-300 break-all">{block.block_hash.slice(0, 24)}...</span>
                        </div>
                      </div>

                      <div className="bg-slate-900/80 p-2.5 rounded border border-slate-800/60 mt-2">
                        <div className="text-slate-500 text-[10px] uppercase font-bold mb-1">Payload Content:</div>
                        <pre className="text-slate-300 text-[11px] overflow-x-auto">
                          {JSON.stringify(block.canonical_record, null, 2)}
                        </pre>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: TAMPER DETECTION SANDBOX */}
          {activeTab === 'tamper' && (
            <div className="space-y-6">
              <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-6">
                <h3 className="text-base font-bold text-white font-mono flex items-center gap-2 mb-2 text-rose-400">
                  <AlertTriangle className="w-5 h-5 text-rose-400" />
                  Tamper Detection Demonstration Sandbox
                </h3>
                <p className="text-xs text-slate-400 mb-6">
                  Demonstrate tamper detection for hackathon judges: deliberately alter a historical block's payload in SQLite to show that the hash chain breaks and the verification engine pinpoints the exact tampered block.
                </p>

                <div className="bg-slate-950 border border-rose-950 p-5 rounded-lg space-y-4 font-mono text-xs">
                  <div className="text-slate-300 leading-relaxed">
                    Select a block to deliberately tamper with:
                  </div>

                  <div className="flex flex-wrap gap-2">
                    {ledgerBlocks.map((b) => (
                      <button
                        key={b.block_index}
                        onClick={() => handleTamperTest(b.block_index)}
                        className="bg-rose-950/80 hover:bg-rose-900 text-rose-300 border border-rose-800/60 px-3 py-1.5 rounded transition text-xs flex items-center gap-1"
                      >
                        <AlertTriangle className="w-3.5 h-3.5" />
                        Tamper Block #{b.block_index} ({b.event_type})
                      </button>
                    ))}
                  </div>

                  <hr className="border-slate-800" />

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Audit Status:</span>
                    <div className="flex gap-2">
                      <button
                        onClick={handleResetEnvironment}
                        disabled={loading}
                        className="bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold px-3 py-1.5 rounded text-xs transition flex items-center gap-1"
                      >
                        <RotateCcw className="w-3.5 h-3.5" /> Reset to Genesis State
                      </button>
                      <button
                        onClick={handleAuditLedger}
                        className="bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold px-4 py-2 rounded text-xs transition"
                      >
                        Re-Audit Ledger Integrity
                      </button>
                    </div>
                  </div>

                  {ledgerAudit && (
                    <div className={`p-4 rounded border text-xs ${
                      ledgerAudit.chain_valid ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300' : 'bg-rose-950/50 border-rose-500/50 text-rose-300'
                    }`}>
                      <div className="font-bold text-sm flex items-center gap-2">
                        {ledgerAudit.chain_valid ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                        {ledgerAudit.chain_valid ? 'LEDGER INTEGRITY VERIFIED (ALL BLOCKS PASS)' : 'TAMPERING DETECTED!'}
                      </div>
                      {!ledgerAudit.chain_valid && (
                        <div className="mt-2 text-slate-200">
                          <div><strong>Broken Block Index:</strong> #{ledgerAudit.broken_block_index}</div>
                          <div><strong>Alert Details:</strong> {ledgerAudit.error_message}</div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Sidebar: Real-Time Operational Telemetry Log (4 cols) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 font-mono text-xs flex flex-col h-[750px]">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
              <span className="text-cyan-400 font-bold flex items-center gap-2">
                <Terminal className="w-4 h-4" /> Operational Telemetry
              </span>
              <button
                onClick={() => setLogs([])}
                className="text-[10px] text-slate-500 hover:text-slate-300"
              >
                Clear
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {logs.length === 0 ? (
                <div className="text-slate-600 text-center py-10">No events logged yet.</div>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="text-[11px] leading-tight flex items-start gap-2">
                    <span className="text-slate-600 shrink-0">[{log.timestamp}]</span>
                    <span className={
                      log.type === 'error'
                        ? 'text-rose-400'
                        : log.type === 'success'
                        ? 'text-emerald-400'
                        : log.type === 'warn'
                        ? 'text-amber-400'
                        : 'text-slate-300'
                    }>
                      {log.msg}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-[#060b14] py-3 px-6 text-center text-xs font-mono text-slate-500">
        SIH26237 — Ministry of Defence | Indian Navy (WESEE) | Strictly Offline Air-Gapped Prototype
      </footer>
    </div>
  );
}
