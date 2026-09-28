import React, { useState } from 'react';
import {
  FileText,
  Lock,
  Radio,
  KeyRound,
  ShieldCheck,
  Layers,
  AlertTriangle,
  Search,
  CheckCircle2,
  XCircle,
  Hash,
} from 'lucide-react';

export default function DocumentStoryObject({
  state = 'DOCUMENT',
  recipient = 'R002 · Officer Bravo',
  tokenRef = 'WM-b5695aa800771689',
  docId = 'DOC-2026-FLEET-08',
  docHash = '64e94e7e0434c78dd1281ce5d90cd58253d1ede02600eacedd70c9fa077557c5',
  _session = 'SES-20260928-F2F2C041',
  blockIndex = 4,
  _interactive = false,
  className = '',
}) {
  const [tilt, setTilt] = useState({ x: 0, y: 0 });

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width - 0.5) * 6; // -3 to +3 deg
    const y = ((e.clientY - rect.top) / rect.height - 0.5) * -6;
    setTilt({ x, y });
  };

  const handleMouseLeave = () => {
    setTilt({ x: 0, y: 0 });
  };

  const getBadgeForState = () => {
    switch (state) {
      case 'ENCRYPTED':
        return { label: 'AES-256-GCM ENCRYPTED', color: 'border-[#cf8047]/50 text-[#97501f] bg-[#f1f0ee]', icon: Lock };
      case 'BROADCAST':
        return { label: 'BROADCAST DIRECTIVE', color: 'border-[#b15f2c]/40 text-[#97501f] bg-[#f1f0ee]', icon: Radio };
      case 'DECRYPTED':
        return { label: 'DECRYPTED VIA STEP-UP', color: 'border-[#b15f2c]/50 text-[#b15f2c] bg-[#b15f2c]/10', icon: KeyRound };
      case 'PROVENANCE':
        return { label: 'PROVENANCE MARKER ATTACHED', color: 'border-[#b15f2c] text-[#97501f] bg-[#b15f2c]/12', icon: Hash };
      case 'SIGNED':
        return { label: 'SIGNED ML-DSA-44', color: 'border-[#b15f2c] text-[#97501f] bg-[#b15f2c]/14', icon: ShieldCheck };
      case 'RECORDED':
        return { label: `LEDGER BLOCK #${blockIndex}`, color: 'border-[#0a0a0a] text-[#0a0a0a] bg-[#f1f0ee]', icon: Layers };
      case 'LEAKED':
        return { label: 'PERIMETER LEAK DETECTED', color: 'border-[#8b3a2a] text-[#8b3a2a] bg-[rgba(139,58,42,0.08)]', icon: AlertTriangle };
      case 'RECOVERED':
        return { label: 'FORENSIC INTAKE #EV-884', color: 'border-[#b15f2c]/50 text-[#97501f] bg-[#f1f0ee]', icon: Search };
      case 'INVESTIGATED':
        return { label: 'INTERROGATING EVIDENCE', color: 'border-[#b15f2c] text-[#b15f2c] bg-[#b15f2c]/10', icon: Search };
      case 'VERIFIED':
        return { label: 'ATTRIBUTED TO RECIPIENT', color: 'border-[#2d6a4f] text-[#1b4332] bg-[#2d6a4f]/12 font-bold', icon: CheckCircle2 };
      case 'UNVERIFIED':
        return { label: 'UNVERIFIED · FAIL-CLOSED', color: 'border-[#8b3a2a] text-[#8b3a2a] bg-[rgba(139,58,42,0.08)]', icon: XCircle };
      default:
        return { label: 'CANONICAL DIRECTIVE', color: 'border-[#e6e5e2] text-[#3a3a3a] bg-[#f1f0ee]', icon: FileText };
    }
  };

  const badge = getBadgeForState();
  const BadgeIcon = badge.icon;

  return (
    <div
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{
        transform: `perspective(1000px) rotateX(${tilt.y}deg) rotateY(${tilt.x}deg)`,
      }}
      className={`sx-document-sheet p-5 md:p-6 w-full max-w-lg mx-auto font-mono select-none relative overflow-hidden bg-white text-[#111111] transition-transform duration-200 ${className}`}
    >
      {/* Forensic Scanning Laser Line during Investigation */}
      {(state === 'INVESTIGATED' || state === 'PROVENANCE') && (
        <div className="sx-scanner-beam" />
      )}

      {/* Background Watermark/Micro-Ribbon Indicator (State >= PROVENANCE) */}
      {(state === 'PROVENANCE' || state === 'SIGNED' || state === 'RECORDED' || state === 'RECOVERED' || state === 'INVESTIGATED' || state === 'VERIFIED') && (
        <div className="absolute top-0 bottom-0 left-0 w-1.5 bg-[#b15f2c]" />
      )}

      {/* Top Header & Classification */}
      <div className="flex items-center justify-between border-b border-[#e6e5e2] pb-3 mb-4 text-[10px] tracking-wider text-[#8d8d8d]">
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#b15f2c]" />
          <span className="font-bold text-[#0a0a0a]">WESEE / MoD ASSET</span>
        </div>
        <div className="px-2 py-0.5 rounded bg-[#f1f0ee] border border-[#e6e5e2] text-[#3a3a3a] font-bold">
          RESTRICTED
        </div>
      </div>

      {/* State Status Banner */}
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded border text-[11px] font-mono tracking-tight mb-4 ${badge.color}`}>
        <BadgeIcon className="w-3.5 h-3.5 shrink-0" />
        <span className="font-semibold">{badge.label}</span>
      </div>

      {/* Document Body Content */}
      <div className="space-y-3 font-sans text-xs text-[#3a3a3a]">
        <div className="font-mono text-[11px] text-[#8d8d8d] flex items-center justify-between border-b border-[#e6e5e2] pb-2">
          <span>IDENTIFIER:</span>
          <span className="text-[#0a0a0a] font-bold">{docId}</span>
        </div>

        {/* Content simulation based on state */}
        {state === 'ENCRYPTED' ? (
          <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded font-mono text-[10px] text-[#97501f] break-all leading-relaxed">
            <span className="text-[#8d8d8d] block mb-1">// ML-KEM-768 + AES-256-GCM CIPHERTEXT:</span>
            7c4a92b8d0e1f3a58e2d4c6b8a0f1e3d5c7b9a1f3e5d7c9b1a3f5e7d9c1b3a5f...
          </div>
        ) : (
          <div className="space-y-2 py-1">
            <div className="h-2 bg-[#d8d6d2] rounded w-11/12" />
            <div className="h-2 bg-[#e6e5e2] rounded w-4/5" />
            <div className="h-2 bg-[#e6e5e2] rounded w-9/12" />
            <div className="h-2 bg-[#e6e5e2] rounded w-2/3" />
          </div>
        )}

        {/* Technical Provenance Footer Data */}
        <div className="pt-3 border-t border-[#e6e5e2] text-[10px] font-mono space-y-1 text-[#8d8d8d]">
          <div className="flex items-center justify-between">
            <span className="text-[#8d8d8d]">SHA-256:</span>
            <span className="text-[#111111] font-semibold truncate max-w-[200px]" title={docHash}>
              {docHash.slice(0, 16)}...{docHash.slice(-8)}
            </span>
          </div>

          {(state === 'DECRYPTED' || state === 'PROVENANCE' || state === 'SIGNED' || state === 'RECORDED' || state === 'VERIFIED') && (
            <div className="flex items-center justify-between text-[#97501f]">
              <span className="text-[#8d8d8d]">RECIPIENT:</span>
              <span className="font-semibold">{recipient}</span>
            </div>
          )}

          {(state === 'PROVENANCE' || state === 'SIGNED' || state === 'RECORDED' || state === 'INVESTIGATED' || state === 'VERIFIED') && (
            <div className="flex items-center justify-between text-[#b15f2c]">
              <span className="text-[#8d8d8d]">MARKER TOKEN:</span>
              <span className="font-bold">{tokenRef}</span>
            </div>
          )}

          {(state === 'RECORDED' || state === 'VERIFIED') && (
            <div className="flex items-center justify-between text-[#0a0a0a]">
              <span className="text-[#8d8d8d]">LEDGER PROOF:</span>
              <span className="font-semibold">BLOCK #{blockIndex} · CHAIN VERIFIED</span>
            </div>
          )}

          {state === 'VERIFIED' && (
            <div className="mt-2 p-2 rounded bg-[#2d6a4f]/10 border border-[#2d6a4f]/40 text-[11px] text-[#1b4332] font-bold flex items-center justify-between">
              <span>PROVENANCE RESULT:</span>
              <span>10 / 10 CHECKS PASSED</span>
            </div>
          )}

          {state === 'UNVERIFIED' && (
            <div className="mt-2 p-2 rounded bg-[#f1f0ee] border border-[#d8d6d2] text-[11px] text-[#8b3a2a] font-semibold flex items-center justify-between">
              <span>PROVENANCE RESULT:</span>
              <span>ATTRIBUTION REFUSED</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
