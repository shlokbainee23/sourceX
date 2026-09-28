import React from 'react';
import { HelpCircle, CheckCircle2, XCircle } from 'lucide-react';

export default function Stage16SystemQuestioned() {
  return (
    <section className="min-h-[85vh] py-28 px-4 md:px-8 border-t border-[#e6e5e2] flex flex-col justify-center relative">
      <div className="max-w-4xl mx-auto w-full space-y-16 text-center">
        {/* Stage Label */}
        <div className="text-[11px] font-mono uppercase tracking-widest text-[#8d8d8d]">
          STAGE 16 // DEFENSE-GRADE SCRUTINY
        </div>

        <div className="space-y-6">
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            BUILT TO BE QUESTIONED.
          </h2>

          <p className="max-w-2xl mx-auto text-[#3a3a3a] text-sm sm:text-base font-sans leading-relaxed">
            In military intelligence and naval tribunals, assertions without auditable proofs are dismissed. SOURCE-X does not ask you to trust its conclusions.
          </p>
        </div>

        {/* 3 Pillar Scrutiny Flow */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="p-6 bg-white border border-[#e6e5e2] rounded-xl shadow-sm space-y-3">
            <div className="text-xs font-mono text-[#8d8d8d] uppercase">THE INQUIRY</div>
            <h3 className="text-base font-bold text-[#0a0a0a]">
              “Where did this directive originate?”
            </h3>
            <p className="text-xs text-[#3a3a3a] font-sans leading-relaxed">
              We begin from zero assumptions. The recovered file is treated as untrusted until inspected.
            </p>
          </div>

          <div className="p-6 bg-[#2d6a4f]/06 border border-[#2d6a4f]/30 rounded-xl shadow-sm space-y-3">
            <div className="text-xs font-mono text-[#2d6a4f] uppercase flex items-center gap-1.5 font-bold">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>THE PROOF</span>
            </div>
            <h3 className="text-base font-bold text-[#0a0a0a]">
              “Here is the complete chain of evidence.”
            </h3>
            <p className="text-xs text-[#3a3a3a] font-sans leading-relaxed">
              Every token, signature byte, ledger block hash, and authority attestation is provided in the open.
            </p>
          </div>

          <div className="p-6 bg-white border border-[#e6e5e2] rounded-xl shadow-sm space-y-3">
            <div className="text-xs font-mono text-[#8d8d8d] uppercase flex items-center gap-1.5">
              <XCircle className="w-3.5 h-3.5 text-[#8b3a2a]" />
              <span>THE DISCLOSURE</span>
            </div>
            <h3 className="text-base font-bold text-[#0a0a0a]">
              “Here is what could not be verified.”
            </h3>
            <p className="text-xs text-[#3a3a3a] font-sans leading-relaxed">
              If an integrity link is broken or absent, the refusal to attribute is stated explicitly without ambiguity.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
