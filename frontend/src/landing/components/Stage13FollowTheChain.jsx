import React from 'react';
import { ArrowDown, Link2, CheckCircle2 } from 'lucide-react';

export default function Stage13FollowTheChain() {
  const chainLinks = [
    { num: '01', title: 'AUTHORITY', desc: 'Trust anchor attested; root directive registered' },
    { num: '02', title: 'DIRECTIVE', desc: 'Canonical SHA-256 calculated; original securely deleted' },
    { num: '03', title: 'BROADCAST', desc: '1 CEK encapsulated per recipient via ML-KEM-768' },
    { num: '04', title: 'RECIPIENT', desc: 'Authorized naval station unlocks hardware/software keystore' },
    { num: '05', title: 'DECRYPTION', desc: 'P0 step-up passphrase knowledge verified in session' },
    { num: '06', title: 'PROVENANCE', desc: 'Render mode 3 opaque 256-bit token generated' },
    { num: '07', title: 'SIGNED RECORD', desc: 'Decryption payload digitally signed with ML-DSA-44' },
    { num: '08', title: 'LEDGER BLOCK', desc: 'Committed to SQLite append-only chain with triggers' },
    { num: '09', title: 'RECOVERY', desc: 'External leaked document ingested into offline memory' },
    { num: '10', title: 'ATTRIBUTION', desc: '10-point fail-closed verification resolves origin' },
  ];

  return (
    <section className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative">
      <div className="max-w-6xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 13 // FULL ARCHITECTURE
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            FOLLOW THE PROVENANCE CHAIN.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            Ten interlocking cryptographic links spanning the entire lifecycle from directive issuance to courtroom attribution.
          </p>
        </div>

        {/* 10-Step Architectural Ribbon */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 font-mono text-xs">
          {chainLinks.map((link) => (
            <div
              key={link.num}
              className="p-4 bg-white border border-[#e6e5e2] rounded-lg shadow-sm space-y-2 hover:-translate-y-1 hover:shadow-md hover:border-[#b15f2c] transition-all duration-200 cursor-default"
            >
              <div className="flex items-center justify-between text-[10px] text-[#8d8d8d]">
                <span>LINK #{link.num}</span>
                <CheckCircle2 className="w-3 h-3 text-[#b15f2c]" />
              </div>
              <div className="text-sm font-bold text-[#0a0a0a] tracking-wide">
                {link.title}
              </div>
              <p className="text-[11px] text-[#3a3a3a] font-sans leading-snug">
                {link.desc}
              </p>
            </div>
          ))}
        </div>

        {/* Narrative Banner */}
        <div className="p-6 rounded-lg bg-[#f1f0ee] border border-[#e6e5e2] text-center font-mono text-xs text-[#8d8d8d] max-w-3xl mx-auto space-y-2">
          <div className="text-[#b15f2c] font-bold uppercase tracking-wider">
            UNBROKEN EVIDENCE CONTINUITY
          </div>
          <p className="text-[#3a3a3a] font-sans">
            Every step is recorded before the next can proceed. No link can be forged or backdated after a leak occurs.
          </p>
        </div>
      </div>
    </section>
  );
}
