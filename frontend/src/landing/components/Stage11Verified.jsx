import React from 'react';
import { CheckCircle2, UserCheck, ShieldCheck, ArrowRight, Layers } from 'lucide-react';
import DocumentStoryObject from './DocumentStoryObject';

export default function Stage11Verified() {
  return (
    <section className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative">
      <div className="max-w-5xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#2d6a4f]">
            STAGE 11 // POSITIVE ATTRIBUTION
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded bg-[#2d6a4f]/10 border border-[#2d6a4f]/30 text-[#2d6a4f] text-xs font-mono font-bold tracking-wider">
            <CheckCircle2 className="w-4 h-4 text-[#2d6a4f]" />
            <span>VERIFICATION COMPLETE // 10 OF 10 CHECKS PASSED</span>
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            ATTRIBUTION ESTABLISHED.
          </h2>
        </div>

        {/* Provenance Flow Resolution */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 font-mono text-center text-xs">
          <div className="p-3 bg-white border border-[#e6e5e2] rounded shadow-sm">
            <span className="text-[#8d8d8d] block text-[10px]">EVIDENCE 01</span>
            <span className="text-[#0a0a0a] font-semibold">RECOVERED DOC</span>
          </div>
          <div className="p-3 bg-[#b15f2c]/08 border border-[#b15f2c]/30 rounded shadow-sm">
            <span className="text-[#b15f2c] block text-[10px]">EVIDENCE 02</span>
            <span className="text-[#97501f] font-semibold">TOKEN MATCH</span>
          </div>
          <div className="p-3 bg-white border border-[#e6e5e2] rounded shadow-sm">
            <span className="text-[#8d8d8d] block text-[10px]">EVIDENCE 03</span>
            <span className="text-[#0a0a0a] font-semibold">ML-DSA-44 SIGNED</span>
          </div>
          <div className="p-3 bg-white border border-[#e6e5e2] rounded shadow-sm">
            <span className="text-[#8d8d8d] block text-[10px]">EVIDENCE 04</span>
            <span className="text-[#0a0a0a] font-semibold">BLOCK #004</span>
          </div>
          <div className="p-3 bg-[#2d6a4f]/10 border border-[#2d6a4f]/40 rounded text-[#2d6a4f] font-bold shadow-sm col-span-2 sm:col-span-1">
            <span className="text-[#2d6a4f] block text-[10px]">SOURCE ORIGIN</span>
            <span>R002 CONFIRMED</span>
          </div>
        </div>

        {/* Attribution Dossier Card */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center bg-white border border-[#2d6a4f]/40 rounded-xl p-6 md:p-8 shadow-md">
          {/* Attributed Identity Card */}
          <div className="md:col-span-6 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-[#2d6a4f]/10 border border-[#2d6a4f]/30 flex items-center justify-center text-[#2d6a4f]">
                <UserCheck className="w-6 h-6" />
              </div>
              <div>
                <span className="text-[10px] font-mono text-[#2d6a4f] uppercase tracking-widest block font-bold">
                  ATTRIBUTED RECIPIENT STATION
                </span>
                <h3 className="text-xl font-bold text-[#0a0a0a]">
                  Officer Bravo (R002)
                </h3>
                <p className="text-xs text-[#8d8d8d] font-mono">
                  Communications Director · Fleet Signals
                </p>
              </div>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded flex justify-between">
                <span className="text-[#8d8d8d]">SIGNING KEY ID:</span>
                <span className="text-[#0a0a0a] font-bold">R002#1 (ML-DSA-44)</span>
              </div>
              <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded flex justify-between">
                <span className="text-[#8d8d8d]">LEDGER PROVENANCE:</span>
                <span className="text-[#2d6a4f] font-bold">BLOCK #004 · TRIGGER VERIFIED</span>
              </div>
              <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded flex justify-between">
                <span className="text-[#8d8d8d]">CONFIDENCE METRIC:</span>
                <span className="text-[#0a0a0a] font-bold">EXACT MATHEMATICAL PROOF</span>
              </div>
            </div>

            {/* Climax Editorial Quote */}
            <div className="border-t border-[#e6e5e2] pt-6 space-y-2">
              <p className="text-sm md:text-base text-[#3a3a3a] font-sans italic">
                “The document didn't identify its source.”
              </p>
              <p className="text-lg md:text-2xl font-black font-mono text-[#2d6a4f] tracking-wide uppercase">
                THE EVIDENCE DID.
              </p>
            </div>
          </div>

          {/* Persistent Object Verified State */}
          <div className="md:col-span-6">
            <DocumentStoryObject
              state="VERIFIED"
              recipient="R002 · Officer Bravo"
              tokenRef="WM-b5695aa800771689"
              docId="DOC-2026-FLEET-08"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
