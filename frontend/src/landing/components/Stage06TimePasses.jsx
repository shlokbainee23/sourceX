import React from 'react';
import { Clock, ShieldAlert, ArrowDown } from 'lucide-react';

export default function Stage06TimePasses({ onProceed }) {
  return (
    <section className="min-h-[85vh] py-28 px-4 md:px-8 border-t border-[#e6e5e2] flex flex-col justify-center items-center text-center relative overflow-hidden">
      {/* Background radial gradient */}
      <div className="absolute inset-0 bg-radial from-[#b15f2c]/05 via-transparent to-transparent pointer-events-none" />

      <div className="max-w-3xl mx-auto space-y-12 relative z-10">
        <div className="text-[11px] font-mono uppercase tracking-widest text-[#8d8d8d]">
          STAGE 06 // PASSAGE OF TIME
        </div>

        {/* Breathing Space */}
        <div className="space-y-6">
          <div className="w-14 h-14 rounded-full bg-[#f1f0ee] border border-[#e6e5e2] mx-auto flex items-center justify-center text-[#8d8d8d]">
            <Clock className="w-7 h-7 text-[#b15f2c]" />
          </div>

          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            MONTHS LATER.
          </h2>

          <div className="max-w-xl mx-auto space-y-3 text-[#3a3a3a] text-base leading-relaxed font-sans">
            <p>
              The append-only ledger continued chaining blocks. Key rotations and routine dispatches were committed.
            </p>
            <p className="text-[#0a0a0a] font-medium">
              Then, an unauthorized excerpt surfaces on an external node.
            </p>
          </div>
        </div>

        {/* The Incident Callout */}
        <div className="p-6 rounded-lg bg-white border border-[#b15f2c]/40 shadow-sm max-w-lg mx-auto space-y-3">
          <div className="flex items-center justify-center gap-2 text-[#8b3a2a] font-mono text-xs font-bold tracking-wider uppercase">
            <ShieldAlert className="w-4 h-4" />
            <span>DOCUMENT RECOVERED IN THE WILD</span>
          </div>

          <p className="text-xs font-mono text-[#3a3a3a]">
            EVIDENCE CUSTODY ID: <span className="text-[#0a0a0a] font-bold">#EV-2026-884</span>
          </p>

          <p className="text-xs text-[#8d8d8d] font-sans">
            The origin is completely unknown to the public. The visual layout has zero visible markings.
          </p>
        </div>

        <div className="pt-4">
          <button
            type="button"
            onClick={onProceed}
            className="sx-btn-primary cursor-pointer text-xs uppercase"
          >
            <span>START FORENSIC INVESTIGATION</span>
            <ArrowDown className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </section>
  );
}
