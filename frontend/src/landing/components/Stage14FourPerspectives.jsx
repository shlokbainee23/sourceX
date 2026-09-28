import React, { useState } from 'react';
import { Anchor, Inbox, Search, Layers } from 'lucide-react';
import DocumentStoryObject from './DocumentStoryObject';

export default function Stage14FourPerspectives() {
  const [activeRole, setActiveRole] = useState('AUTHORITY');

  const perspectives = {
    AUTHORITY: {
      role: 'AUTHORITY',
      station: 'WESEE_HQ (Headquarters Command)',
      icon: Anchor,
      title: 'Command & Attestation Authority',
      purpose: 'Register canonical documents, manage broadcast encryption packages, maintain pinned trust anchor, and issue monotonic Trust Manifests.',
      action: 'Register Directive & Encapsulate KEKs',
      documentState: 'ENCRYPTED',
      telemetry: 'TRUST ANCHOR ATTESTED · PQC KEYS ACTIVE',
    },
    RECIPIENT: {
      role: 'RECIPIENT',
      station: 'R001 / R002 / R003 (Naval Officers)',
      icon: Inbox,
      title: 'Decryption & Operational Station',
      purpose: 'Receive broadcast directives, execute mandatory P0 step-up authentication, download one-time delivery copy, and sign provenance record upon release.',
      action: 'Execute Step-Up Keystore Decryption',
      documentState: 'DECRYPTED',
      telemetry: 'KEK UNLOCKED IN MEMORY · STEP-UP VERIFIED',
    },
    INVESTIGATOR: {
      role: 'INVESTIGATOR',
      station: 'INVESTIGATOR_01 (Naval Forensics Lab)',
      icon: Search,
      title: 'Forensic Intake & Verification Room',
      purpose: 'Ingest leaked materials, extract non-rendering vector marks, execute 10-point fail-closed verification engine, and archive signed investigation dossiers.',
      action: 'Execute 10-Point Attribution Engine',
      documentState: 'INVESTIGATED',
      telemetry: '10 / 10 FORENSIC PREDICATES EVALUATED',
    },
    AUDITOR: {
      role: 'AUDITOR',
      station: 'AUDITOR_01 (Independent Inspector)',
      icon: Layers,
      title: 'Ledger Explorer & Tamper Sandbox',
      purpose: 'Verify hash-chained blocks from Genesis to Tail, inspect SQLite append-only triggers, review the immutable audit trail, and simulate adversarial tampering.',
      action: 'Verify Entire Blockchain Continuity',
      documentState: 'RECORDED',
      telemetry: 'APPEND-ONLY LEDGER ANCHORED · 0 ANOMALIES',
    },
  };

  const current = perspectives[activeRole];
  const Icon = current.icon;

  return (
    <section className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative">
      <div className="max-w-6xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 14 // ROLE-AWARE OPERATIONAL SURFACES
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            FOUR OPERATIONAL PERSPECTIVES.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            The same cryptographic provenance object viewed through the lens of four distinct military disciplines.
          </p>
        </div>

        {/* Perspective Selector Tabs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Object.keys(perspectives).map((key) => {
            const p = perspectives[key];
            const isSelected = key === activeRole;
            const TabIcon = p.icon;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setActiveRole(key)}
                className={`p-4 rounded-lg border text-left transition-all cursor-pointer ${
                  isSelected
                    ? 'bg-[#b15f2c]/10 border-[#b15f2c] text-[#0a0a0a] shadow-sm'
                    : 'bg-white border-[#e6e5e2] text-[#3a3a3a] hover:text-[#0a0a0a] hover:border-[#d8d6d2] shadow-sm'
                }`}
              >
                <TabIcon className={`w-5 h-5 mb-2 ${isSelected ? 'text-[#b15f2c]' : 'text-[#8d8d8d]'}`} />
                <div className="font-mono text-xs font-bold text-[#0a0a0a]">{p.role}</div>
                <div className="text-[11px] text-[#8d8d8d] truncate mt-0.5">{p.title}</div>
              </button>
            );
          })}
        </div>

        {/* Focused Role Workspace Lens */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center bg-white border border-[#e6e5e2] rounded-xl p-6 md:p-8 shadow-sm">
          <div className="lg:col-span-7 space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded bg-[#b15f2c]/10 border border-[#b15f2c]/30 flex items-center justify-center text-[#b15f2c]">
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <div className="text-[10px] font-mono text-[#b15f2c] uppercase tracking-wider font-bold">
                  ACTIVE TERMINAL ROLE
                </div>
                <h3 className="text-xl font-bold text-[#0a0a0a] uppercase">
                  {current.title}
                </h3>
              </div>
            </div>

            <div className="space-y-3">
              <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded font-mono text-xs flex justify-between">
                <span className="text-[#8d8d8d]">DEFAULT STATION:</span>
                <span className="text-[#0a0a0a] font-bold">{current.station}</span>
              </div>
              <p className="text-xs md:text-sm text-[#3a3a3a] font-sans leading-relaxed">
                {current.purpose}
              </p>
            </div>

            <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded font-mono text-xs text-[#3a3a3a] flex items-center justify-between">
              <span className="text-[#8d8d8d]">SECURITY TELEMETRY:</span>
              <span className="text-[#2d6a4f] font-bold">{current.telemetry}</span>
            </div>
          </div>

          <div className="lg:col-span-5">
            <DocumentStoryObject
              state={current.documentState}
              docId="DOC-2026-FLEET-08"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
