import React, { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';

export default function Stage09TenQuestions({ _onComplete }) {
  const [activeCheck, setActiveCheck] = useState(0);

  const questions = [
    {
      idx: '01',
      question: 'Is a valid provenance marker present?',
      evidence: 'Extracted marker: WM-b5695aa800771689 matches 256-bit entropy curve.',
      status: 'VERIFIED',
    },
    {
      idx: '02',
      question: 'Does the document hash match?',
      evidence: 'Calculated SHA-256 matches committed source original: 64e94e7e...',
      status: 'VERIFIED',
    },
    {
      idx: '03',
      question: 'Does the provenance record correspond to this document?',
      evidence: 'Document ID DOC-2026-FLEET-08 matches recorded registration.',
      status: 'VERIFIED',
    },
    {
      idx: '04',
      question: 'Does the ledger contain the record?',
      evidence: 'Found canonical decryption record at Block #004 with matching record_hash.',
      status: 'VERIFIED',
    },
    {
      idx: '05',
      question: 'Is the provenance signature valid?',
      evidence: 'ML-DSA-44 post-quantum signature verifies against recipient public key.',
      status: 'VERIFIED',
    },
    {
      idx: '06',
      question: 'Is the signing authority trusted?',
      evidence: 'Trust Manifest v1 signed by authority anchor 77a6b7a3... attests recipient.',
      status: 'VERIFIED',
    },
    {
      idx: '07',
      question: 'Is the ledger chain intact?',
      evidence: 'All SHA-256 previous_hash linkages verify from Genesis to Tail without breaks.',
      status: 'VERIFIED',
    },
    {
      idx: '08',
      question: 'Is the provenance internally consistent?',
      evidence: 'Session ID, timestamp sequence, and principal match cross-table triggers.',
      status: 'VERIFIED',
    },
    {
      idx: '09',
      question: 'Does the recovered evidence agree with the recorded evidence?',
      evidence: 'Zero discrepancies between leaked file extraction and ledger commitment.',
      status: 'VERIFIED',
    },
    {
      idx: '10',
      question: 'Can the origin be established from the complete chain?',
      evidence: 'All 10 mathematical predicates pass simultaneously.',
      status: 'RESOLVING ORIGIN',
    },
  ];

  return (
    <section
      id="stage-verification"
      className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative"
    >
      <div className="max-w-5xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 09 // THE INTERROGATION
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            TEN FORENSIC QUESTIONS.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            Attribution is not a score or a percentage. It is an exacting interrogation of the evidence. Every single predicate must pass without exception.
          </p>
        </div>

        {/* The 10 Questions Interrogation Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
          {/* Question List (Left) */}
          <div className="md:col-span-6 space-y-2 font-mono text-xs">
            {questions.map((q, i) => {
              const isSelected = i === activeCheck;
              const isPast = i < 9;
              return (
                <button
                  key={q.idx}
                  type="button"
                  onClick={() => setActiveCheck(i)}
                  className={`w-full text-left p-3 rounded border transition-all flex items-center justify-between cursor-pointer ${
                    isSelected
                      ? 'bg-[#b15f2c]/10 border-[#b15f2c] text-[#0a0a0a] shadow-sm'
                      : 'bg-white border-[#e6e5e2] text-[#3a3a3a] hover:text-[#0a0a0a] hover:border-[#d8d6d2] shadow-sm'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className={isSelected ? 'text-[#b15f2c] font-bold' : 'text-[#8d8d8d]'}>
                      {q.idx}
                    </span>
                    <span className="font-sans text-xs font-medium truncate max-w-[240px]">
                      {q.question}
                    </span>
                  </div>
                  {isPast ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-[#2d6a4f] shrink-0" />
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-[#b15f2c] animate-ping" />
                  )}
                </button>
              );
            })}
          </div>

          {/* Focused Question Evidence Spotlight (Right) */}
          <div className="md:col-span-6 sticky top-28 space-y-6">
            <div className="p-6 md:p-8 rounded-xl bg-white border border-[#e6e5e2] shadow-sm space-y-6">
              <div className="flex items-center justify-between border-b border-[#e6e5e2] pb-3 text-xs font-mono">
                <span className="text-[#8d8d8d]">INTERROGATION PREDICATE:</span>
                <span className="text-[#b15f2c] font-bold">CHECK #{questions[activeCheck].idx} / 10</span>
              </div>

              <div>
                <h3 className="text-lg md:text-xl font-bold text-[#0a0a0a] font-sans">
                  {questions[activeCheck].question}
                </h3>
              </div>

              <div className="p-4 bg-[#f1f0ee] border border-[#e6e5e2] rounded font-mono text-xs text-[#3a3a3a] space-y-2">
                <div className="text-[10px] text-[#8d8d8d] uppercase tracking-wider font-bold">
                  CRYPTOGRAPHIC PROOF:
                </div>
                <div className="text-[#111111] leading-relaxed">
                  {questions[activeCheck].evidence}
                </div>
              </div>

              <div className="flex items-center justify-between pt-2 text-xs font-mono">
                <span className="text-[#8d8d8d]">PREDICATE VERDICT:</span>
                <span className="px-2.5 py-1 rounded bg-[#2d6a4f]/10 border border-[#2d6a4f]/30 text-[#2d6a4f] font-bold">
                  {questions[activeCheck].status}
                </span>
              </div>
            </div>

            {/* Micro simulation note */}
            <div className="text-[11px] font-mono text-[#8d8d8d] text-center">
              ILLUSTRATIVE SIMULATION OF REAL FORENSIC ENGINE EXECUTION
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
