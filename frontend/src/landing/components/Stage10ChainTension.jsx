import React from 'react';
import { ArrowDown, ShieldCheck } from 'lucide-react';

export default function Stage10ChainTension({ onResolve }) {
  return (
    <section className="min-h-[80vh] py-28 px-4 md:px-8 border-t border-[#e6e5e2] flex flex-col justify-center items-center text-center relative overflow-hidden">
      {/* Subtle background glow */}
      <div className="absolute inset-0 bg-radial from-[#b15f2c]/05 via-transparent to-transparent pointer-events-none" />

      <div className="max-w-3xl mx-auto space-y-10 relative z-10">
        <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
          STAGE 10 // THE CLIMAX
        </div>

        {/* Tension Meter */}
        <div className="space-y-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#2d6a4f]/10 border border-[#2d6a4f]/30 text-[#2d6a4f] font-mono text-xs font-bold tracking-wider">
            <ShieldCheck className="w-4 h-4" />
            <span>09 / 10 EVIDENCE CONSISTENCY VERIFIED</span>
          </div>

          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading leading-tight">
            10 / 10 CAN THE ORIGIN BE ESTABLISHED?
          </h2>

          <p className="max-w-xl mx-auto text-[#3a3a3a] text-sm sm:text-base font-sans leading-relaxed">
            The document itself is silent. But the provenance token, the document hash, the recipient signature, and the ledger block hold unbroken mathematical continuity.
          </p>
        </div>

        {/* Visual Chain Connector */}
        <div className="flex items-center justify-center gap-2 text-xs font-mono text-[#8d8d8d]">
          <span>TOKEN</span>
          <span className="text-[#b15f2c]">→</span>
          <span>RECORD</span>
          <span className="text-[#b15f2c]">→</span>
          <span>SIGNATURE</span>
          <span className="text-[#b15f2c]">→</span>
          <span>LEDGER</span>
          <span className="text-[#b15f2c]">→</span>
          <span className="text-[#0a0a0a] font-bold">SOURCE</span>
        </div>

        <div className="pt-4">
          <button
            type="button"
            onClick={onResolve}
            className="sx-btn-primary cursor-pointer text-xs md:text-sm py-3 px-8"
          >
            <span>RESOLVE ATTRIBUTION</span>
            <ArrowDown className="w-4 h-4 text-[#cf8047] animate-bounce" />
          </button>
        </div>
      </div>
    </section>
  );
}
