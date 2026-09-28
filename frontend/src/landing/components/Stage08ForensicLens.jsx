import React, { useState } from 'react';
import { Scan, Hash, Shield, Layers, Key, Check } from 'lucide-react';

export default function Stage08ForensicLens() {
  const [activeLayer, setActiveLayer] = useState('marker');

  const inspectionLayers = [
    {
      id: 'marker',
      name: 'PROVENANCE TOKEN',
      icon: Hash,
      highlight: 'PDF Byte Offset 0x000F8A0: Render Mode 3 non-rendering text vector',
      value: 'WM-b5695aa800771689',
      details: '256-bit cryptographic marker embedded without displacing visible glyph positions.',
    },
    {
      id: 'hash',
      name: 'DOCUMENT HASH',
      icon: Scan,
      highlight: 'FIPS 180-4 SHA-256 Canonical Digest',
      value: '64e94e7e0434c78dd1281ce5d90cd58253d1ede02600eacedd70c9fa077557c5',
      details: 'Matches original dispatch directive with zero content modification or redaction.',
    },
    {
      id: 'session',
      name: 'SERVER SESSION',
      icon: Key,
      highlight: 'Ephemeral Server-Side Keystore Unlock Binding',
      value: 'SES-20260928-F2F2C0419EAE48CC',
      details: 'Created during station login; dropped immediately following step-up decryption.',
    },
    {
      id: 'ledger',
      name: 'LEDGER ANCHOR',
      icon: Layers,
      highlight: 'Append-Only Merkle Block #004',
      value: 'BLOCK_HASH: 3a9f0c2b... PREV_HASH: 8d7e1c4a...',
      details: 'Immutably anchored with SQLite tamper-evident triggers and persistent head anchor.',
    },
  ];

  const current = inspectionLayers.find((l) => l.id === activeLayer) || inspectionLayers[0];

  return (
    <section className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative">
      <div className="max-w-5xl mx-auto space-y-14">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 08 // FORENSIC LENS
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            MICRO-LAYER INSPECTION.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            Examine the forensic layers embedded within the leaked file. Touch or click each layer to inspect the underlying cryptographic commitments.
          </p>
        </div>

        {/* Interactive Lens Control Bar */}
        <div className="flex flex-wrap gap-2 border-b border-[#e6e5e2] pb-4">
          {inspectionLayers.map((layer) => {
            const isSelected = layer.id === activeLayer;
            const Icon = layer.icon;
            return (
              <button
                key={layer.id}
                type="button"
                onClick={() => setActiveLayer(layer.id)}
                className={`px-3.5 py-2 rounded text-xs font-mono tracking-wider transition-all flex items-center gap-2 cursor-pointer ${
                  isSelected
                    ? 'bg-[#b15f2c]/10 border border-[#b15f2c] text-[#97501f] font-bold shadow-sm'
                    : 'bg-white border border-[#e6e5e2] text-[#8d8d8d] hover:text-[#0a0a0a] hover:border-[#d8d6d2]'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-[#b15f2c]' : 'text-[#8d8d8d]'}`} />
                <span>{layer.name}</span>
              </button>
            );
          })}
        </div>

        {/* Forensic Loupe Display Card */}
        <div className="p-6 md:p-8 rounded-xl bg-white border border-[#e6e5e2] shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#e6e5e2] pb-3">
            <span className="text-xs font-mono text-[#8d8d8d] uppercase">
              LAYER FOCUS: <strong className="text-[#b15f2c]">{current.name}</strong>
            </span>
            <span className="text-[11px] font-mono text-[#8d8d8d]">
              {current.highlight}
            </span>
          </div>

          <div className="p-4 bg-[#f1f0ee] border border-[#e6e5e2] rounded-lg space-y-2">
            <div className="text-[10px] font-mono text-[#b15f2c] uppercase tracking-wider font-bold">
              RESOLVED FORENSIC VALUE:
            </div>
            <div className="font-mono text-sm md:text-base font-bold text-[#0a0a0a] break-all tracking-wide">
              {current.value}
            </div>
          </div>

          <p className="text-xs sm:text-sm text-[#3a3a3a] font-sans leading-relaxed">
            {current.details}
          </p>

          <div className="pt-2 flex items-center justify-between text-[11px] font-mono text-[#8d8d8d] border-t border-[#e6e5e2]">
            <span>FORENSIC SCAN RESOLUTION: 150-DPI INVARIANCE</span>
            <span className="text-[#2d6a4f] font-bold">CRYPTO BINDING ACTIVE</span>
          </div>
        </div>
      </div>
    </section>
  );
}
