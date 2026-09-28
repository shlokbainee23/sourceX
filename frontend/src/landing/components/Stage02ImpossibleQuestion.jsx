import React, { useState } from 'react';
import { Users, AlertTriangle, Copy, ArrowRight } from 'lucide-react';
import DocumentStoryObject from './DocumentStoryObject';

export default function Stage02ImpossibleQuestion() {
  const [selectedCopy, setSelectedCopy] = useState('R002');

  const recipients = [
    { id: 'R001', name: 'Commander Alpha', rank: 'Naval Command', status: 'Delivered', leaked: false },
    { id: 'R002', name: 'Officer Bravo', rank: 'Fleet Signals', status: 'Delivered (Leaked Copy)', leaked: true },
    { id: 'R003', name: 'Officer Charlie', rank: 'Tactical Systems', status: 'Delivered', leaked: false },
  ];

  return (
    <section
      id="stage-distribution"
      className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative"
    >
      <div className="max-w-6xl mx-auto space-y-16">
        {/* Editorial Section Header */}
        <div className="max-w-3xl space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 02 // BROADCAST REPLICATION
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase tracking-tight text-[#0a0a0a] sx-heading">
            THE IMPOSSIBLE QUESTION.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans leading-relaxed">
            One strategic directive is broadcast to multiple authorized recipients. Each recipient downloads and decrypts an identical plaintext copy.
          </p>
        </div>

        {/* Triple Copy Visual Convergence */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {recipients.map((rec) => {
            const isLeaked = rec.leaked;
            return (
              <div
                key={rec.id}
                className={`p-5 rounded-lg border transition-all duration-300 relative ${
                  isLeaked
                    ? 'bg-[#8b3a2a]/06 border-[#8b3a2a]/40 shadow-lg md:-translate-y-3 md:scale-[1.02] ring-1 ring-[#8b3a2a]/30'
                    : 'bg-white border-[#e6e5e2] shadow-sm hover:border-[#d8d6d2]'
                }`}
              >
                {/* Header label */}
                <div className="flex items-center justify-between border-b border-[#e6e5e2] pb-3 mb-4 text-xs font-mono">
                  <div className="flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-[#8d8d8d]" />
                    <span className="font-bold text-[#111111]">{rec.id}</span>
                  </div>
                  {isLeaked ? (
                    <span className="px-2 py-0.5 rounded bg-[#8b3a2a]/10 border border-[#8b3a2a]/30 text-[#8b3a2a] font-bold text-[10px]">
                      SEPARATED LEAK
                    </span>
                  ) : (
                    <span className="text-[#8d8d8d] text-[10px]">SECURE COPY</span>
                  )}
                </div>

                {/* Recipient Details */}
                <div className="mb-4">
                  <div className="text-sm font-semibold text-[#0a0a0a]">{rec.name}</div>
                  <div className="text-[11px] text-[#8d8d8d] font-mono">{rec.rank}</div>
                </div>

                {/* Document Sheet representation */}
                <DocumentStoryObject
                  state={isLeaked ? 'LEAKED' : 'DECRYPTED'}
                  recipient={`${rec.id} · ${rec.name}`}
                  docId="DOC-2026-FLEET-08"
                  className="scale-95 origin-top"
                />

                <div className="mt-4 pt-3 border-t border-[#e6e5e2] text-[11px] font-mono text-[#8d8d8d] flex items-center justify-between">
                  <span>150-DPI PIXEL RENDER:</span>
                  <span className="text-[#111111] font-bold">100% IDENTICAL</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Narrative Climax Tension */}
        <div className="p-8 rounded-lg bg-[#8b3a2a]/08 border border-[#8b3a2a]/30 text-center max-w-3xl mx-auto space-y-4">
          <div className="flex items-center justify-center gap-2 text-[#8b3a2a] font-mono text-xs uppercase tracking-widest font-bold">
            <AlertTriangle className="w-4 h-4" />
            <span>INCIDENT REPORTED</span>
          </div>

          <h3 className="text-2xl sm:text-3xl font-extrabold text-[#0a0a0a] font-mono tracking-tight">
            A COPY HAS LEAKED.
          </h3>

          <p className="text-sm text-[#3a3a3a] font-sans max-w-xl mx-auto">
            The document appears outside the defense perimeter on an open network. All three authorized officers had access to identical text.
          </p>

          <div className="pt-2 text-xl sm:text-3xl font-black font-mono tracking-wider text-[#8b3a2a] uppercase">
            WHO RELEASED IT?
          </div>
        </div>
      </div>
    </section>
  );
}
