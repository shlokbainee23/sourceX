import React from 'react';
import { EyeOff, FileQuestion, ArrowDown } from 'lucide-react';

export default function Stage03TheProblem({ onProceed }) {
  return (
    <section className="min-h-screen py-28 px-4 md:px-8 border-t border-[#e6e5e2] flex flex-col justify-center relative">
      <div className="max-w-4xl mx-auto w-full space-y-16 text-center">
        {/* Subtle stage label */}
        <div className="text-[11px] font-mono uppercase tracking-widest text-[#8d8d8d]">
          STAGE 03 // THE INSPECTION LIMIT
        </div>

        {/* The Blind Spot */}
        <div className="space-y-6">
          <div className="w-12 h-12 rounded-full bg-[#f1f0ee] border border-[#e6e5e2] mx-auto flex items-center justify-center text-[#8d8d8d]">
            <EyeOff className="w-6 h-6" />
          </div>

          <h2 className="text-3xl sm:text-5xl font-black uppercase text-[#0a0a0a] tracking-tight sx-heading">
            VISUAL INSPECTION CANNOT TELL THEM APART.
          </h2>

          <div className="max-w-2xl mx-auto space-y-4 text-[#3a3a3a] text-base sm:text-lg leading-relaxed font-sans">
            <p>
              In raster graphics and layout engines, every byte renders identically. No font weight differs. No pixel shifted.
            </p>
            <p className="text-[#111111] font-medium">
              The document knows <span className="text-[#0a0a0a] font-semibold">what</span> it is.
              <br />
              It does not reveal <span className="text-[#b15f2c] font-semibold">who</span> received it.
            </p>
          </div>
        </div>

        {/* Major Conceptual Pivot */}
        <div className="my-16 py-12 px-6 rounded-xl bg-white border border-[#e6e5e2] shadow-md space-y-6">
          <div className="text-xs font-mono text-[#b15f2c] uppercase tracking-widest font-bold">
            THE PARADIGM SHIFT
          </div>

          <h3 className="text-2xl sm:text-4xl font-extrabold text-[#0a0a0a] font-mono tracking-tight max-w-2xl mx-auto leading-tight">
            WHAT IF THE ORIGIN WAS ESTABLISHED <span className="text-[#b15f2c]">BEFORE</span> THE LEAK?
          </h3>

          <p className="max-w-xl mx-auto text-sm text-[#3a3a3a]">
            Not through post-hoc forensic guessing or statistical watermarking, but through a deterministic cryptographic covenant enforced at the instant of decryption.
          </p>

          <div className="pt-4">
            <button
              type="button"
              onClick={onProceed}
              className="sx-btn-secondary cursor-pointer"
            >
              <span>WITNESS THE REWIND</span>
              <ArrowDown className="w-3.5 h-3.5 text-[#b15f2c]" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
