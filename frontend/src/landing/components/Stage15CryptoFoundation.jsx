import React from 'react';
import { Cpu, Shield, KeyRound, Lock, Layers } from 'lucide-react';

export default function Stage15CryptoFoundation() {
  const primitives = [
    {
      standard: 'FIPS 203',
      name: 'ML-KEM-768',
      role: 'Post-Quantum Key Establishment',
      detail: 'Encapsulates symmetric document encryption keys per recipient station. Never encrypts document bytes directly.',
      icon: Cpu,
    },
    {
      standard: 'FIPS 204',
      name: 'ML-DSA-44',
      role: 'Post-Quantum Digital Signatures',
      detail: 'Signs canonical JSON provenance records and block headers. 2420-byte deterministic signature verification.',
      icon: Shield,
    },
    {
      standard: 'NIST SP 800-38D',
      name: 'AES-256-GCM',
      role: 'Authenticated Encryption',
      detail: 'One ephemeral 256-bit content encryption key (CEK) per directive with 128-bit integrity tag.',
      icon: Lock,
    },
    {
      standard: 'RFC 5869',
      name: 'HKDF-SHA256',
      role: 'Key Derivation Function',
      detail: 'Derives key encryption keys (KEKs) from the shared secret output of ML-KEM-768.',
      icon: KeyRound,
    },
    {
      standard: 'RFC 7914',
      name: 'scrypt',
      role: 'Software Keystore Protection',
      detail: 'Memory-hard password hashing (N=16384, r=8, p=1) protecting stored private keys on disk.',
      icon: Lock,
    },
    {
      standard: 'FIPS 180-4',
      name: 'SHA-256 & Append-Only Ledger',
      role: 'Evidence Continuity & Hash Chaining',
      detail: 'Strictly append-only SQLite tables guarded by triggers preventing mutations, drops, or rollback.',
      icon: Layers,
    },
  ];

  return (
    <section className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative">
      <div className="max-w-6xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 15 // CRYPTOGRAPHIC PILLARS
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            CRYPTOGRAPHIC FOUNDATION.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            Zero reliance on proprietary or unproven algorithms. Every claim is enforced by open, standardized, post-quantum cryptography.
          </p>
        </div>

        {/* 6 Primitive Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {primitives.map((p) => {
            const Icon = p.icon;
            return (
              <div
                key={p.name}
                className="p-6 bg-white border border-[#e6e5e2] rounded-xl shadow-sm space-y-4 hover:border-[#d8d6d2] transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="w-10 h-10 rounded bg-[#f1f0ee] border border-[#e6e5e2] flex items-center justify-center text-[#b15f2c]">
                    <Icon className="w-5 h-5" />
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#f1f0ee] border border-[#e6e5e2] text-[#8d8d8d] uppercase">
                    {p.standard}
                  </span>
                </div>

                <div>
                  <h3 className="text-lg font-bold text-[#0a0a0a] font-mono">{p.name}</h3>
                  <div className="text-xs font-semibold text-[#b15f2c] font-mono mt-0.5">
                    {p.role}
                  </div>
                </div>

                <p className="text-xs text-[#3a3a3a] font-sans leading-relaxed">
                  {p.detail}
                </p>
              </div>
            );
          })}
        </div>

        <div className="p-4 rounded-lg bg-[#f1f0ee] border border-[#e6e5e2] text-center font-mono text-xs text-[#8d8d8d]">
          STRICT AIR-GAP ASSURANCE: ZERO RUNTIME NETWORK TRANSMISSIONS ENFORCED AT SOCKET BOUNDARY
        </div>
      </div>
    </section>
  );
}
