import React, { useState } from 'react';
import { RotateCcw, Key, Clock, Shield, Sparkles } from 'lucide-react';
import DocumentStoryObject from './DocumentStoryObject';

export default function Stage04RewindDecryption() {
  const [tokenGenerated, setTokenGenerated] = useState(true);

  return (
    <section
      id="stage-provenance"
      className="min-h-screen py-24 px-4 md:px-8 border-t border-[#e6e5e2] relative"
    >
      <div className="max-w-5xl mx-auto space-y-16">
        {/* Editorial Header */}
        <div className="space-y-4">
          <div className="text-[11px] font-mono uppercase tracking-widest text-[#b15f2c]">
            STAGE 04 // REWIND TIMELINE
          </div>
          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            THE MOMENT OF DECRYPTION.
          </h2>
          <p className="text-[#3a3a3a] text-sm sm:text-base font-sans max-w-2xl">
            Rewind past the leak, past delivery, to the precise instant the recipient unlocked their private keystore to read the plaintext.
          </p>
        </div>

        {/* Timeline Rewind Steps */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center font-mono text-xs">
          <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded opacity-60">
            <span className="text-[#8d8d8d] block text-[10px]">STEP 4</span>
            <span className="text-[#8d8d8d] line-through">RECOVERED</span>
          </div>
          <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded opacity-60">
            <span className="text-[#8d8d8d] block text-[10px]">STEP 3</span>
            <span className="text-[#8d8d8d] line-through">LEAK EVENT</span>
          </div>
          <div className="p-3 bg-[#f1f0ee] border border-[#d8d6d2] rounded opacity-80">
            <span className="text-[#8d8d8d] block text-[10px]">STEP 2</span>
            <span className="text-[#3a3a3a]">DELIVERY COPY</span>
          </div>
          <div className="p-3 bg-[#b15f2c]/10 border border-[#b15f2c] rounded text-[#97501f] font-bold shadow-sm">
            <span className="text-[#b15f2c] block text-[10px]">STEP 1 (TARGET)</span>
            <span>DECRYPTION EVENT</span>
          </div>
        </div>

        {/* Provenance Generation Card */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center bg-white border border-[#e6e5e2] rounded-xl p-6 md:p-8 shadow-sm">
          {/* Left Details */}
          <div className="md:col-span-6 space-y-6">
            <div className="space-y-1">
              <span className="text-xs font-mono text-[#b15f2c] uppercase tracking-wider font-bold">
                CRYPTOGRAPHIC INTERACTION
              </span>
              <h3 className="text-xl font-bold text-[#0a0a0a] uppercase">
                Zero-Knowledge Provenance Creation
              </h3>
            </div>

            <div className="space-y-3 font-mono text-xs">
              <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded flex justify-between">
                <span className="text-[#8d8d8d]">DOCUMENT ID:</span>
                <span className="text-[#0a0a0a] font-bold">DOC-2026-FLEET-08</span>
              </div>
              <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded flex justify-between">
                <span className="text-[#8d8d8d]">SESSION RECIPIENT:</span>
                <span className="text-[#b15f2c] font-bold">R002 (Officer Bravo)</span>
              </div>
              <div className="p-3 bg-[#f1f0ee] border border-[#e6e5e2] rounded flex justify-between">
                <span className="text-[#8d8d8d]">SERVER SESSION:</span>
                <span className="text-[#3a3a3a]">SES-20260928-F2F2C041</span>
              </div>
              <div className="p-3 bg-[#b15f2c]/08 border border-[#b15f2c]/40 rounded flex justify-between items-center">
                <span className="text-[#b15f2c] font-bold">PROVENANCE TOKEN:</span>
                <span className="text-[#97501f] font-mono font-black tracking-wider">
                  WM-b5695aa800771689
                </span>
              </div>
            </div>

            <p className="text-xs text-[#3a3a3a] font-sans leading-relaxed">
              At the moment of decryption, provenance is created.
              <br />
              <strong className="text-[#0a0a0a]">Not after the leak.</strong>
              <br />
              <strong className="text-[#0a0a0a]">Not during the investigation.</strong>
              <br />
              <span className="text-[#b15f2c] font-bold uppercase tracking-wider">BEFORE IT.</span>
            </p>
          </div>

          {/* Right Document Object Representation */}
          <div className="md:col-span-6">
            <DocumentStoryObject
              state="PROVENANCE"
              recipient="R002 · Officer Bravo"
              tokenRef="WM-b5695aa800771689"
              docId="DOC-2026-FLEET-08"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
