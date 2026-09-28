import React, { useState } from 'react';
import { ShieldX, AlertCircle, RefreshCw } from 'lucide-react';
import DocumentStoryObject from './DocumentStoryObject';

export default function Stage12Unverified() {
  const [tamperScenario, setTamperScenario] = useState('tampered_hash');

  const scenarios = [
    { id: 'tampered_hash', name: 'Document Hash Altered', failure: 'Check #02 Fails: Leaked copy modified post-decryption' },
    { id: 'missing_token', name: 'Watermark Stripped', failure: 'Check #01 Fails: Non-rendering layer absent or corrupted' },
    { id: 'broken_ledger', name: 'Ledger Tamper Detected', failure: 'Check #07 Fails: Previous block hash mismatch in chain' },
  ];

  const current = scenarios.find((s) => s.id === tamperScenario) || scenarios[0];

  return (
    <section className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative">
      <div className="max-w-5xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#8d8d8d]">
            STAGE 12 // THE FAIL-CLOSED STANDARD
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            DISCIPLINED FORENSIC UNCERTAINTY.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            If a single check fails, attribution halts immediately. The system never guesses, never fabricates probabilities, and never names a suspect without complete cryptographic proof.
          </p>
        </div>

        {/* Interactive Adversarial Scenario Switcher */}
        <div className="flex flex-wrap gap-2 border-b border-[#e6e5e2] pb-4">
          {scenarios.map((sc) => {
            const isSelected = sc.id === tamperScenario;
            return (
              <button
                key={sc.id}
                type="button"
                onClick={() => setTamperScenario(sc.id)}
                className={`px-3.5 py-2 rounded text-xs font-mono tracking-wider transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#8b3a2a]/10 border border-[#8b3a2a]/40 text-[#8b3a2a] font-bold shadow-sm'
                    : 'bg-white border border-[#e6e5e2] text-[#8d8d8d] hover:text-[#0a0a0a] hover:border-[#d8d6d2]'
                }`}
              >
                <span>SIMULATE: {sc.name}</span>
              </button>
            );
          })}
        </div>

        {/* Fail-Closed Result Card */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center bg-white border border-[#8b3a2a]/30 rounded-xl p-6 md:p-8 shadow-sm">
          <div className="md:col-span-6 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-[#8b3a2a]/10 border border-[#8b3a2a]/30 flex items-center justify-center text-[#8b3a2a]">
                <ShieldX className="w-6 h-6 text-[#8b3a2a]" />
              </div>
              <div>
                <span className="text-[10px] font-mono text-[#8b3a2a] uppercase tracking-widest block font-bold">
                  FAIL-CLOSED OUTCOME
                </span>
                <h3 className="text-xl font-bold text-[#8b3a2a] uppercase tracking-wide">
                  UNVERIFIED / REFUSED
                </h3>
              </div>
            </div>

            <div className="p-4 bg-[#f1f0ee] border border-[#e6e5e2] rounded font-mono text-xs text-[#3a3a3a] space-y-2">
              <div className="text-[10px] text-[#8d8d8d] uppercase tracking-wider font-bold">
                TRIGGERED ANOMALY:
              </div>
              <div className="text-[#8b3a2a] font-bold leading-relaxed">
                {current.failure}
              </div>
            </div>

            <div className="space-y-2 font-mono text-xs text-[#8d8d8d]">
              <div className="flex justify-between py-1 border-b border-[#e6e5e2]">
                <span>SUSPECT NAMES REPORTED:</span>
                <span className="text-[#0a0a0a] font-bold">ZERO (0)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#e6e5e2]">
                <span>CONFIDENCE PROBABILITY:</span>
                <span className="text-[#0a0a0a] font-bold">NONE (REFUSED)</span>
              </div>
              <div className="flex justify-between py-1">
                <span>SYSTEM INTEGRITY:</span>
                <span className="text-[#2d6a4f] font-bold">PRESERVED (FAIL-CLOSED)</span>
              </div>
            </div>

            <div className="border-t border-[#e6e5e2] pt-4 space-y-1">
              <div className="text-sm font-bold font-mono tracking-wider text-[#0a0a0a] uppercase">
                NO VALID EVIDENCE. NO ATTRIBUTION.
              </div>
              <p className="text-xs text-[#3a3a3a] font-sans leading-relaxed">
                A system that guesses is a liability. SOURCE-X guarantees that every positive attribution is defensible before a formal court of inquiry.
              </p>
            </div>
          </div>

          <div className="md:col-span-6">
            <DocumentStoryObject
              state="UNVERIFIED"
              docId="DOC-2026-FLEET-08"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
