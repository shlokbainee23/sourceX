import React from 'react';
import DocumentStoryObject from './DocumentStoryObject';

export default function Stage07EvidenceRoom() {
  const evidenceNodes = [
    {
      step: '01',
      title: 'RECOVERED DOCUMENT',
      desc: 'Target PDF ingested into forensic memory. Zero external network sockets.',
      status: 'INGESTED',
      color: 'border-[#e6e5e2] text-[#3a3a3a] bg-white shadow-sm',
      badgeColor: 'border-[#e6e5e2] text-[#8d8d8d]',
    },
    {
      step: '02',
      title: 'MARKER DETECTED',
      desc: 'PDF render mode 3 non-rendering text layer extracted: WM-b5695aa800771689',
      status: 'EXTRACTED',
      color: 'border-[#b15f2c]/30 text-[#97501f] bg-[#b15f2c]/06 shadow-sm',
      badgeColor: 'border-[#b15f2c]/40 text-[#b15f2c]',
    },
    {
      step: '03',
      title: 'DOCUMENT HASH CALCULATED',
      desc: 'SHA-256 canonical hash matches registered original: 64e94e7e0434c78d...',
      status: 'VERIFIED EXACT',
      color: 'border-[#e6e5e2] text-[#3a3a3a] bg-white shadow-sm',
      badgeColor: 'border-[#e6e5e2] text-[#8d8d8d]',
    },
    {
      step: '04',
      title: 'PROVENANCE RECORD LOCATED',
      desc: 'Session binding located in ledger index: SES-20260928-F2F2C041',
      status: 'MATCHED',
      color: 'border-[#e6e5e2] text-[#3a3a3a] bg-white shadow-sm',
      badgeColor: 'border-[#e6e5e2] text-[#8d8d8d]',
    },
    {
      step: '05',
      title: 'ML-DSA-44 SIGNATURE FOUND',
      desc: 'Cryptographic digital signature verified using attested public key.',
      status: 'GENUINE',
      color: 'border-[#b15f2c]/30 text-[#97501f] bg-[#b15f2c]/06 shadow-sm',
      badgeColor: 'border-[#b15f2c]/40 text-[#b15f2c]',
    },
    {
      step: '06',
      title: 'LEDGER BLOCK VERIFIED',
      desc: 'Block #004 immutably anchored in hash chain with trigger integrity.',
      status: 'ANCHORED',
      color: 'border-[#2d6a4f]/30 text-[#2d6a4f] bg-[#2d6a4f]/08 shadow-sm',
      badgeColor: 'border-[#2d6a4f]/40 text-[#2d6a4f]',
    },
  ];

  return (
    <section
      id="stage-investigation"
      className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative"
    >
      <div className="max-w-6xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 07 // EVIDENCE COMPOSITION
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            THE FORENSIC EVIDENCE ROOM.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            Investigation is not guesswork. Each artifact links to the next across cryptographic boundaries until the origin is mathematically unavoidable.
          </p>
        </div>

        {/* Dynamic Evidence Node Composition */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Visual Document Object */}
          <div className="lg:col-span-5 space-y-4">
            <div className="text-xs font-mono text-[#8d8d8d] uppercase tracking-wider">
              EVIDENCE ARTIFACT // INGESTION #EV-884
            </div>
            <DocumentStoryObject
              state="INVESTIGATED"
              tokenRef="WM-b5695aa800771689"
              docId="DOC-2026-FLEET-08"
            />
            <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded text-xs font-mono text-[#8d8d8d] flex items-center justify-between">
              <span>INTEGRITY CHAIN STATUS:</span>
              <span className="text-[#b15f2c] font-bold">INTERROGATION IN PROGRESS</span>
            </div>
          </div>

          {/* Right Column: 6 Visible Evidence Nodes */}
          <div className="lg:col-span-7 space-y-3">
            {evidenceNodes.map((node) => (
              <div
                key={node.step}
                className={`p-4 rounded-lg border transition-all duration-200 ${node.color} flex items-start gap-4`}
              >
                <div className="font-mono text-xs font-bold text-[#8d8d8d] pt-0.5">
                  {node.step}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h4 className="text-xs md:text-sm font-bold font-mono tracking-tight text-[#0a0a0a]">
                      {node.title}
                    </h4>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold uppercase shrink-0 ${node.badgeColor}`}>
                      {node.status}
                    </span>
                  </div>
                  <p className="text-xs text-[#3a3a3a] font-sans mt-1">
                    {node.desc}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
