import React from 'react';
import { ShieldCheck, Layers } from 'lucide-react';

export default function Stage05ProvenanceEvent() {
  return (
    <section className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative">
      <div className="max-w-5xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 05 // EVIDENCE CONVERGENCE
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            THE SIGNED PROVENANCE RECORD.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            A watermark alone is never evidence. Attribution requires that the marker, the document hash, and the recipient identity form a cryptographically signed commitment.
          </p>
        </div>

        {/* 4 Converging Components */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
          <div className="p-4 bg-white border border-[#e6e5e2] rounded-lg shadow-sm space-y-2">
            <span className="text-[10px] text-[#8d8d8d] uppercase">ELEMENT 01</span>
            <div className="text-[#0a0a0a] font-bold">DOCUMENT HASH</div>
            <div className="text-[10px] text-[#8d8d8d] truncate">64e94e7e0434c78d...</div>
          </div>

          <div className="p-4 bg-white border border-[#e6e5e2] rounded-lg shadow-sm space-y-2">
            <span className="text-[10px] text-[#8d8d8d] uppercase">ELEMENT 02</span>
            <div className="text-[#0a0a0a] font-bold">RECIPIENT IDENTITY</div>
            <div className="text-[10px] text-[#b15f2c] font-semibold">R002 · Officer Bravo</div>
          </div>

          <div className="p-4 bg-white border border-[#e6e5e2] rounded-lg shadow-sm space-y-2">
            <span className="text-[10px] text-[#8d8d8d] uppercase">ELEMENT 03</span>
            <div className="text-[#0a0a0a] font-bold">SERVER SESSION</div>
            <div className="text-[10px] text-[#8d8d8d]">SES-2026-F2F2C041</div>
          </div>

          <div className="p-4 bg-[#b15f2c]/08 border border-[#b15f2c]/40 rounded-lg shadow-sm space-y-2">
            <span className="text-[10px] text-[#b15f2c] uppercase font-bold">ELEMENT 04</span>
            <div className="text-[#97501f] font-bold">OPAQUE MARKER</div>
            <div className="text-[10px] text-[#97501f] font-bold">WM-b5695aa80077...</div>
          </div>
        </div>

        {/* Convergence Result: Signed Record into Ledger */}
        <div className="p-6 md:p-8 bg-white border border-[#e6e5e2] rounded-xl shadow-sm space-y-6">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-[#e6e5e2] pb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-[#b15f2c]/10 border border-[#b15f2c]/30 flex items-center justify-center text-[#b15f2c] shrink-0">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#0a0a0a] uppercase tracking-wide">
                  SIGNED PROVENANCE RECORD · ML-DSA-44
                </h3>
                <p className="text-xs text-[#8d8d8d] font-mono">
                  Canonical JSON payload committed to immutable ledger block
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-[#2d6a4f]/10 border border-[#2d6a4f]/30 text-[#2d6a4f] text-xs font-mono font-bold">
              <Layers className="w-3.5 h-3.5" />
              <span>APPEND-ONLY COMMIT: BLOCK #004</span>
            </div>
          </div>

          {/* Canonical Payload representation */}
          <div className="p-4 bg-[#0a0a0a] border border-[#2d2d2d] rounded-lg font-mono text-[11px] text-[#e6e5e2] overflow-x-auto space-y-1">
            <div className="text-[#8d8d8d]">// Canonical Record committed before transmission</div>
            <div>&#123;</div>
            <div className="pl-4 text-[#a3a3a3]">"record_type": <span className="text-[#cf8047]">"DOCUMENT_DECRYPTION"</span>,</div>
            <div className="pl-4 text-[#a3a3a3]">"document_id": <span className="text-white">"DOC-2026-FLEET-08"</span>,</div>
            <div className="pl-4 text-[#a3a3a3]">"recipient_id": <span className="text-[#cf8047] font-bold">"R002"</span>,</div>
            <div className="pl-4 text-[#a3a3a3]">"session_id": <span className="text-white">"SES-20260928-F2F2C041"</span>,</div>
            <div className="pl-4 text-[#a3a3a3]">"watermark_token": <span className="text-[#cf8047] font-bold">"WM-b5695aa800771689"</span>,</div>
            <div className="pl-4 text-[#a3a3a3]">"mldsa_signature": <span className="text-[#cf8047]">"3d8a9f0b12e4...2420_bytes"</span></div>
            <div>&#125;</div>
          </div>

          <div className="border-t border-[#e6e5e2] pt-4 text-xs text-[#3a3a3a] font-sans space-y-1 leading-relaxed">
            <p>
              <strong className="text-[#0a0a0a]">A claim is created.</strong>{' '}
              <strong className="text-[#0a0a0a]">The claim is signed.</strong>{' '}
              <strong className="text-[#0a0a0a]">The evidence is recorded.</strong>
            </p>
            <p className="text-[#b15f2c] font-medium">
              SOURCE-X doesn't rely on an isolated mark. It establishes an immutable, verifiable chain of provenance.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
